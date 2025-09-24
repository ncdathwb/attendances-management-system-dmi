import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, get_flashed_messages, abort, send_file, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, time
import os
import json
import uuid
from functools import wraps
from config import config
from sqlalchemy.orm import joinedload, selectinload, load_only, defer
from sqlalchemy import func
import re
from collections import defaultdict
import time as time_module
import secrets
from flask_migrate import Migrate
from jinja2 import Template
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import base64
import traceback
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import registerFont
import zipfile
import webbrowser
import subprocess
import platform
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


# Import database models
from database.models import db, User, Attendance, Request, Department, AuditLog, PasswordResetToken, LeaveRequest
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from email.header import Header
from email_utils import send_leave_request_email, send_leave_request_email_async
from state.email_state import email_status
from queue import Queue
from collections import defaultdict
import json
from sqlalchemy.exc import SQLAlchemyError

# Import utility functions
from utils.validators import (
    validate_input_sanitize,
    validate_employee_id,
    validate_str,
    ValidationError,
)
from utils.session import check_session_timeout, update_session_activity, log_audit_action
from utils.signature_manager import signature_manager



# =============================================================================
# PERFORMANCE HELPER FUNCTIONS
# =============================================================================

def get_user_from_session():
    """Lấy user từ session data thay vì query database"""
    if 'user_id' not in session:
        return None
    
    class FastUser:
        def __init__(self, user_id, user_name, user_department, user_roles, employee_id=None):
            self.id = user_id
            self.name = user_name
            self.department = user_department
            self.roles = user_roles
            self.employee_id = employee_id or f"EMP{user_id:04d}"
            
        def get_roles_list(self):
            return self.roles.split(',') if self.roles else ['EMPLOYEE']
        
        def has_role(self, role):
            return role in self.get_roles_list()
    
    return FastUser(
        user_id=session['user_id'],
        user_name=session.get('user_name', 'Nhân viên'),
        user_department=session.get('user_department', 'Chưa xác định'),
        user_roles=session.get('user_roles', 'EMPLOYEE'),
        employee_id=session.get('employee_id')
    )


# =============================================================================
# OPTIMIZED HELPER FUNCTIONS
# =============================================================================

def get_departments_cached():
    """Lấy danh sách departments từ cache"""
    cache_key = 'departments_list'
    cached_departments = session.get(cache_key)
    
    if cached_departments:
        return cached_departments
    
    # Query database và cache kết quả
    departments = User.query.filter_by(is_deleted=False).with_entities(User.department).distinct().all()
    department_list = sorted(set([d[0] for d in departments if d[0]]))
    
    # Cache trong session (expires khi logout)
    session[cache_key] = department_list
    return department_list

def get_user_by_employee_id(employee_id):
    """Lấy user by employee_id với caching"""
    cache_key = f'user_employee_{employee_id}'
    cached_user = session.get(cache_key)
    
    if cached_user:
        return cached_user
    
    # Query database
    user = User.query.filter_by(employee_id=employee_id).first()
    if user:
        # Cache user info
        user_info = {
            'id': user.id,
            'name': user.name,
            'department': user.department,
            'roles': user.roles,
            'employee_id': user.employee_id
        }
        session[cache_key] = user_info
        return user
    
    return None

def get_user_by_department_role(department, role):
    """Lấy user by department và role với caching"""
    cache_key = f'user_dept_role_{department}_{role}'
    cached_user = session.get(cache_key)
    
    if cached_user:
        return cached_user
    
    # Query database
    user = User.query.filter_by(department=department, roles=role, is_deleted=False).first()
    if user:
        # Cache user info
        user_info = {
            'id': user.id,
            'name': user.name,
            'department': user.department,
            'roles': user.roles,
            'employee_id': user.employee_id
        }
        session[cache_key] = user_info
        return user
    
    return None

def get_user_by_role(role):
    """Lấy user by role với caching"""
    cache_key = f'user_role_{role}'
    cached_user = session.get(cache_key)
    
    if cached_user:
        return cached_user
    
    # Query database
    user = User.query.filter_by(roles=role, is_deleted=False).first()
    if user:
        # Cache user info
        user_info = {
            'id': user.id,
            'name': user.name,
            'department': user.department,
            'roles': user.roles,
            'employee_id': user.employee_id
        }
        session[cache_key] = user_info
        return user
    
    return None

def clear_all_caches():
    """Xóa tất cả caches khi logout"""
    cache_keys = ['departments_list', 'user_roles', 'user_department']
    for key in list(session.keys()):
        if key.startswith('user_') or key.startswith('departments_'):
            session.pop(key, None)

app = Flask(__name__)

# Dictionary để lưu trạng thái email gửi
# in-memory state moved to state/email_state.py for a single source of import

# --- Persistent email status model ---
class EmailStatusRecord(db.Model):
    __tablename__ = 'email_status_records'
    __table_args__ = {
        'extend_existing': True
    }
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, index=True, nullable=False, unique=True)
    status = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def _ensure_email_status_table():
    try:
        # Create table if it does not exist without affecting others
        EmailStatusRecord.__table__.create(bind=db.engine, checkfirst=True)
    except Exception as e:
        print(f"[EmailStatus] ensure table error: {e}")

def upsert_email_status(request_id: int, status: str, message: str):
    try:
        _ensure_email_status_table()
        record = EmailStatusRecord.query.filter_by(request_id=request_id).first()
        if record is None:
            record = EmailStatusRecord(request_id=request_id, status=status, message=message)
            db.session.add(record)
        else:
            record.status = status
            record.message = message
        db.session.commit()
        print(f"[EmailStatus] upsert request_id={request_id} -> {status}")
    except Exception as e:
        db.session.rollback()
        print(f"[EmailStatus] upsert error: {e}")

def get_email_status_record(request_id: int):
    try:
        _ensure_email_status_table()
        return EmailStatusRecord.query.filter_by(request_id=request_id).first()
    except Exception as e:
        print(f"[EmailStatus] get error: {e}")
        return None

# --- Helper tính đơn vị nghỉ theo ca ---
def _compute_leave_units_generic(from_date_dt: datetime, from_time_str: str, to_date_dt: datetime, to_time_str: str) -> float:
    try:
        start_dt = datetime.combine(from_date_dt.date(), datetime.strptime(from_time_str, '%H:%M').time())
        end_dt = datetime.combine(to_date_dt.date(), datetime.strptime(to_time_str, '%H:%M').time())
    except Exception:
        # Fallback: tính theo số ngày lịch
        return max(0.0, (to_date_dt - from_date_dt).days + 1)
    if end_dt < start_dt:
        return 0.0
    workday_hours = 8.0
    half_hours = 4.0
    if start_dt.date() == end_dt.date():
        hours = (end_dt - start_dt).total_seconds() / 3600.0
        if hours <= 0:
            return 0.0
        # Logic tính theo thời gian làm việc thực tế (trừ giờ nghỉ)
        # 1 ngày = 8 tiếng làm việc, 0.5 ngày = 4 tiếng làm việc
        # Làm tròn đến 0.5
        days = round((hours / workday_hours) * 2) / 2.0
        return days
    # nhiều ngày
    end_of_first = datetime.combine(start_dt.date(), time(23,59,59))
    first_hours = (end_of_first - start_dt).total_seconds() / 3600.0
    first_unit = round((first_hours / workday_hours) * 2) / 2.0
    
    start_of_last = datetime.combine(end_dt.date(), time(0,0,0))
    last_hours = (end_dt - start_of_last).total_seconds() / 3600.0
    last_unit = round((last_hours / workday_hours) * 2) / 2.0
    
    middle_days = (to_date_dt.date() - from_date_dt.date()).days - 1
    middle_units = max(0, middle_days) * 1.0
    
    total_units = first_unit + middle_units + last_unit
    return round(total_units * 2) / 2.0

# Load configuration
config_name = os.environ.get('FLASK_CONFIG') or 'default'
app.config.from_object(config[config_name])

# Initialize CSRF protection
csrf = CSRFProtect(app)

# CSRF protection is enabled for all routes
# No need to disable in development

# Expose csrf_token() helper to Jinja templates
@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)

# Time formatting helper (convert UTC -> local, e.g., UTC+7)
@app.context_processor
def inject_format_helpers():
    def format_local(dt, hours_offset=7):
        try:
            if not dt:
                return ''
            return (dt + timedelta(hours=hours_offset)).strftime('%d/%m/%Y %H:%M')
        except Exception:
            return dt.strftime('%d/%m/%Y %H:%M') if dt else ''
    return dict(format_local=format_local)

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

# Initialize signature manager
signature_manager.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import rate limiting from utils
from utils.decorators import rate_limit

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=100, window_seconds=300)  # 100 attempts per 5 minutes (tăng cho 300 người)
def login():
    # Check for remember token on GET request
    if request.method == 'GET':
        remember_token = request.cookies.get('remember_token')
        if remember_token:
            user = User.query.filter_by(remember_token=remember_token).first()
            if user and user.remember_token_expires and user.remember_token_expires > datetime.now():
                # Auto login with remember token
                session['user_id'] = user.id
                session['name'] = user.name
                session['user_name'] = user.name
                session['employee_id'] = user.employee_id
                session['user_department'] = user.department
                session['user_roles'] = user.roles
                session['roles'] = user.roles.split(',')
                # Ưu tiên EMPLOYEE nếu user có vai trò này
                user_roles = user.roles.split(',')
                print(f"DEBUG LOGIN: user_roles = {user_roles}")
                if 'EMPLOYEE' in user_roles:
                    session['current_role'] = 'EMPLOYEE'
                    print(f"DEBUG LOGIN: Set current_role to EMPLOYEE")
                else:
                    session['current_role'] = user_roles[0]
                    print(f"DEBUG LOGIN: Set current_role to {user_roles[0]}")
                session['last_activity'] = datetime.now().isoformat()
                
                log_audit_action(
                    user_id=user.id,
                    action='AUTO_LOGIN',
                    table_name='users',
                    record_id=user.id,
                    new_values={'auto_login_time': datetime.now().isoformat()}
                )
                
                flash('Đăng nhập tự động thành công!', 'success')
                return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        employee_id_str = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        # Validate input
        if not employee_id_str or not password:
            flash('Vui lòng nhập đầy đủ mã nhân viên và mật khẩu!', 'error')
            return render_template('login.html', messages=get_flashed_messages(with_categories=False))
        # Validate employee id format (digits only)
        try:
            employee_id = validate_employee_id(employee_id_str)
        except ValidationError as ve:
            flash(ve.message or 'Mã nhân viên không hợp lệ!', 'error')
            return render_template('login.html', messages=get_flashed_messages(with_categories=False))
        
        if not validate_input_sanitize(password):
            flash('Mật khẩu không hợp lệ!', 'error')
            return render_template('login.html', messages=get_flashed_messages(with_categories=False))
        
        try:
            user = User.query.filter_by(employee_id=employee_id).first()
            
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['name'] = user.name
                session['user_name'] = user.name
                session['employee_id'] = user.employee_id
                session['user_department'] = user.department
                session['user_roles'] = user.roles
                session['roles'] = user.roles.split(',')
                # Ưu tiên EMPLOYEE nếu user có vai trò này
                user_roles = user.roles.split(',')
                print(f"DEBUG LOGIN: user_roles = {user_roles}")
                if 'EMPLOYEE' in user_roles:
                    session['current_role'] = 'EMPLOYEE'
                    print(f"DEBUG LOGIN: Set current_role to EMPLOYEE")
                else:
                    session['current_role'] = user_roles[0]
                    print(f"DEBUG LOGIN: Set current_role to {user_roles[0]}")
                session['last_activity'] = datetime.now().isoformat()
                response = redirect(url_for('dashboard'))
                
                log_audit_action(
                    user_id=user.id,
                    action='LOGIN',
                    table_name='users',
                    record_id=user.id,
                    new_values={'login_time': datetime.now().isoformat()}
                )
                
                if remember:
                    # Generate secure remember token
                    remember_token = secrets.token_urlsafe(32)
                    user.remember_token = remember_token
                    user.remember_token_expires = datetime.now() + timedelta(days=30)
                    db.session.commit()
                    response.set_cookie('remember_token', remember_token, max_age=30*24*60*60, httponly=True, secure=app.config.get('SESSION_COOKIE_SECURE', False))
                else:
                    # Clear remember token if not checked
                    if user.remember_token:
                        user.remember_token = None
                        user.remember_token_expires = None
                        db.session.commit()
                    response.delete_cookie('remember_token')
                
                flash('Đăng nhập thành công!', 'success')
                return response
            
            flash('Mã nhân viên hoặc mật khẩu không đúng!', 'error')
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash('Đã xảy ra lỗi khi đăng nhập!', 'error')
    
    return render_template('login.html', messages=get_flashed_messages(with_categories=False))

@app.route('/logout')
def logout():
    """Logout và clear caches"""
    # Clear remember token on logout
    user = User.query.get(session['user_id'])
    if user:
        user.remember_token = None
        user.remember_token_expires = None
        db.session.commit()
    
    # Clear all caches
    clear_all_caches()
    session.clear()
    response = redirect(url_for('login'))
    response.delete_cookie('remember_token')
    return response

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = get_user_from_session()
    if not user:
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('login'))
    
    # Kiểm tra user có active không
    if not user.is_active:
        session.clear()
        flash('Tài khoản đã bị khóa!', 'error')
        return redirect(url_for('login'))
    
    # Kiểm tra session timeout
    if check_session_timeout():
        flash('Phiên đăng nhập đã hết hạn!', 'error')
        return redirect(url_for('login'))
    
    # Cập nhật thời gian hoạt động cuối
    update_session_activity()
    
    # Xử lý tham số role từ query string
    role_param = request.args.get('role')
    if role_param and role_param in user.roles.split(','):
        session['current_role'] = role_param
        print(f"DEBUG: Set current_role to {role_param} from query param")
    
    # Đảm bảo session có đầy đủ thông tin
    if 'roles' not in session:
        session['roles'] = user.roles.split(',')
    
    # Chỉ set current_role nếu chưa có hoặc không hợp lệ
    if 'current_role' not in session:
        # Ưu tiên EMPLOYEE nếu user có vai trò này (chỉ khi đăng nhập lần đầu)
        user_roles = user.roles.split(',')
        if 'EMPLOYEE' in user_roles:
            session['current_role'] = 'EMPLOYEE'
        else:
            session['current_role'] = user_roles[0]
        print(f"DEBUG DASHBOARD: Set current_role to {session['current_role']} (no current_role in session)")
    elif session['current_role'] not in user.roles.split(','):
        # Ưu tiên EMPLOYEE nếu user có vai trò này (chỉ khi current_role không hợp lệ)
        user_roles = user.roles.split(',')
        if 'EMPLOYEE' in user_roles:
            session['current_role'] = 'EMPLOYEE'
        else:
            session['current_role'] = user_roles[0]
        print(f"DEBUG DASHBOARD: Reset current_role to {session['current_role']} (not in user roles)")
    else:
        print(f"DEBUG DASHBOARD: Keep current_role as {session['current_role']} (valid role)")
    
    if 'name' not in session:
        session['name'] = user.name
    if 'employee_id' not in session:
        session['employee_id'] = user.employee_id
    
    print(f"DEBUG: Final current_role: {session['current_role']}, user roles: {user.roles}")
    print(f"DEBUG: Template will receive current_role: {session.get('current_role')}")
    
    # Kiểm tra xem user đã có chữ ký cá nhân chưa
    has_signature = bool(user.personal_signature)
    
    return render_template('dashboard.html', user=user, has_signature=has_signature)

@app.route('/api/attendance', methods=['POST'])
@rate_limit(max_requests=500, window_seconds=60)  # 500 requests per minute (tăng cho 300 người)
def record_attendance():
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    data = request.get_json()
    print('DEBUG raw:', data)
    print('DEBUG signature POST:', data.get('signature'))  # Thêm log signature
    # Validate input
    date = validate_date(data.get('date'))
    check_in = validate_time(data.get('check_in'))
    check_out = validate_time(data.get('check_out'))
    note = validate_note(data.get('note', ''))
    
    # Khai báo holiday_type trước khi sử dụng
    is_holiday = bool(data.get('is_holiday', False))
    holiday_type = validate_holiday_type(data.get('holiday_type'))
    
    # Chỉ chấp nhận HH:MM
    # Lễ Việt Nam không đi làm: break_time = 0:00, ngược lại = 1:00
    if holiday_type == 'vietnamese_holiday' and (not check_in or not check_out):
        raw_break_time = data.get('break_time', '00:00') or '00:00'
    else:
        raw_break_time = data.get('break_time', '01:00') or '01:00'
    if not (isinstance(raw_break_time, str) and re.match(r'^\d{1,2}:[0-5]\d$', raw_break_time)):
        return jsonify({'error': 'Thời gian nghỉ phải ở định dạng HH:MM'}), 400
    comp_time_regular_raw = data.get('comp_time_regular', '00:00') or '00:00'
    comp_time_overtime_raw = data.get('comp_time_overtime', '00:00') or '00:00'
    comp_time_ot_before_22_raw = data.get('comp_time_ot_before_22', '00:00') or '00:00'
    comp_time_ot_after_22_raw = data.get('comp_time_ot_after_22', '00:00') or '00:00'
    overtime_comp_time_raw = data.get('overtime_comp_time', '00:00') or '00:00'
    for fld, val in [('comp_time_regular', comp_time_regular_raw), ('comp_time_overtime', comp_time_overtime_raw), ('comp_time_ot_before_22', comp_time_ot_before_22_raw), ('comp_time_ot_after_22', comp_time_ot_after_22_raw), ('overtime_comp_time', overtime_comp_time_raw)]:
        if not (isinstance(val, str) and re.match(r'^\d{1,2}:[0-5]\d$', val)):
            return jsonify({'error': f'{fld} phải ở định dạng HH:MM'}), 400
    # Quy đổi HH:MM → giờ (float) tương thích trường hiện tại, nhưng mọi tính toán dùng seconds
    def hhmm_to_hours(hhmm):
        """Chuyển đổi an toàn HH:MM sang giờ thập phân"""
        if not hhmm or hhmm == "":
            return 0.0
        try:
            if isinstance(hhmm, (int, float)):
                return float(hhmm)
            if isinstance(hhmm, str) and ":" in hhmm:
                hh, mm = hhmm.split(':')
                return int(hh) + int(mm)/60
            else:
                # Thử chuyển đổi string số
                return float(hhmm)
        except (ValueError, TypeError) as e:
            print(f"Warning: Failed to convert {repr(hhmm)} to hours: {e}")
            return 0.0
    break_time = hhmm_to_hours(raw_break_time)
    comp_time_regular = hhmm_to_hours(comp_time_regular_raw)
    comp_time_overtime = hhmm_to_hours(comp_time_overtime_raw)
    comp_time_ot_before_22 = hhmm_to_hours(comp_time_ot_before_22_raw)
    comp_time_ot_after_22 = hhmm_to_hours(comp_time_ot_after_22_raw)
    overtime_comp_time = hhmm_to_hours(overtime_comp_time_raw)
    shift_code = data.get('shift_code')
    shift_start = validate_time(data.get('shift_start'))
    shift_end = validate_time(data.get('shift_end'))
    next_day_checkout = bool(data.get('next_day_checkout', False))  # Flag cho tăng ca qua ngày mới
    print('DEBUG validated:', 'shift_code:', shift_code, 'shift_start:', shift_start, 'shift_end:', shift_end)
    if not date:
        return jsonify({'error': 'Vui lòng chọn ngày chấm công hợp lệ'}), 400
    if not holiday_type:
        return jsonify({'error': 'Vui lòng chọn loại ngày hợp lệ'}), 400
    # Cho phép không nhập giờ vào/ra cho lễ Việt Nam (nhân viên được 8h mặc định)
    if holiday_type != 'vietnamese_holiday' and (not check_in or not check_out):
        return jsonify({'error': 'Vui lòng nhập đầy đủ giờ vào và giờ ra hợp lệ'}), 400
    if break_time is None:
        return jsonify({'error': 'Thời gian nghỉ không hợp lệ!'}), 400
    if comp_time_regular is None:
        return jsonify({'error': 'Giờ đối ứng trong ca không hợp lệ!'}), 400
    if comp_time_overtime is None:
        return jsonify({'error': 'Giờ đối ứng tăng ca không hợp lệ!'}), 400
    if comp_time_ot_before_22 is None or comp_time_ot_after_22 is None:
        return jsonify({'error': 'Giờ đối ứng tăng ca theo mốc (trước/sau 22h) không hợp lệ!'}), 400
    
    # Validation: Kiểm tra xem có tăng ca hay không trước khi cho phép đối ứng tăng ca
    is_valid, error_message = validate_overtime_comp_time(
        check_in, check_out, shift_start, shift_end, break_time, 
        comp_time_regular, comp_time_overtime, comp_time_ot_before_22, comp_time_ot_after_22, date, data.get('next_day_checkout', False), holiday_type, shift_code
    )
    if not is_valid:
        return jsonify({'error': error_message}), 400
    
    # Lễ Việt Nam không đi làm: không cần shift_code, shift_start, shift_end
    if holiday_type != 'vietnamese_holiday' and (not shift_code or not shift_start or not shift_end):
        return jsonify({'error': 'Vui lòng chọn ca làm việc hợp lệ!'}), 400
    # Tối ưu: Lấy user và existing_attendance trong 1 query
    user = get_user_from_session()
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    
    # Kiểm tra existing attendance với timeout để tránh deadlock
    try:
        existing_attendance = Attendance.query.filter_by(user_id=user.id, date=date).first()
    except Exception as e:
        print(f"Database query error: {e}")
        return jsonify({'error': 'Lỗi truy vấn database, vui lòng thử lại'}), 500
    if existing_attendance:
        if existing_attendance.status != 'rejected':
            return jsonify({'error': 'Bạn đã chấm công cho ngày này rồi, không thể chấm công 2 lần trong 1 ngày.'}), 400
        else:
            db.session.delete(existing_attendance)
            db.session.commit()
    if date > datetime.now().date():
        return jsonify({'error': 'Không thể chấm công cho ngày trong tương lai!'}), 400
    # Tự động lấy chữ ký từ database thay vì yêu cầu user ký
    signature = data.get('signature', '')
    
    # Lấy chữ ký từ database theo thứ tự ưu tiên (với timeout)
    try:
        auto_signature = signature_manager.get_signature_from_database(user.id, 'EMPLOYEE')
    except Exception as e:
        print(f"Signature query error: {e}")
        auto_signature = None  # Fallback nếu có lỗi
    signature_info = {
        'has_signature': False,
        'signature_type': 'none',
        'message': ''
    }
    
    if auto_signature:
        signature = auto_signature
        signature_info = {
            'has_signature': True,
            'signature_type': 'database',
            'message': f'Đã sử dụng chữ ký có sẵn từ database'
        }
        print(f"✅ AUTO SIGNATURE: User {user.name} using signature from database")
    else:
        signature_info = {
            'has_signature': False,
            'signature_type': 'none',
            'message': 'Không có chữ ký trong database, sẽ sử dụng chữ ký mặc định'
        }
        print(f"⚠️ NO AUTO SIGNATURE: User {user.name} has no signature in database")
    
    # Xử lý đặc biệt cho lễ Việt Nam không đi làm
    if holiday_type == 'vietnamese_holiday' and (not check_in or not check_out):
        print(f"DEBUG: Creating Vietnamese holiday attendance without check-in/out")
        # Lễ Việt Nam không đi làm: set giá trị mặc định
        attendance = Attendance(
            user_id=user.id,
            date=date,
            break_time=0.0,  # Không có thời gian nghỉ khi không đi làm
            comp_time_regular=0.0,
            comp_time_overtime=0.0,
            comp_time_ot_before_22=0.0,
            comp_time_ot_after_22=0.0,
            overtime_comp_time=0.0,
            is_holiday=is_holiday,
            holiday_type=holiday_type,
            status='pending',
            overtime_before_22="0:00",
            overtime_after_22="0:00",
            shift_code='5',  # Ca 5 (Ca tự do) cho lễ Việt Nam
            signature=signature,
            check_in=None,  # Không có giờ vào
            check_out=None,  # Không có giờ ra
            shift_start=None,  # Không có giờ bắt đầu ca
            shift_end=None,  # Không có giờ kết thúc ca
            total_work_hours=8.0  # Tự động tính 8h công cho lễ Việt Nam
        )
    else:
        # Logic bình thường cho các trường hợp khác
        attendance = Attendance(
        user_id=user.id,
        date=date,
        break_time=break_time,
        comp_time_regular=comp_time_regular,
        comp_time_overtime=comp_time_overtime,
        comp_time_ot_before_22=comp_time_ot_before_22,
        comp_time_ot_after_22=comp_time_ot_after_22,
        overtime_comp_time=overtime_comp_time,  # Giữ lại để tương thích
        is_holiday=is_holiday,
        holiday_type=holiday_type,
        status='pending',
        overtime_before_22="0:00",
        overtime_after_22="0:00",
        shift_code=shift_code,
        signature=signature
    )
    
    # Nếu user có vai trò cao hơn, lưu chữ ký vào field tương ứng
    if 'TEAM_LEADER' in user.roles.split(','):
        attendance.team_leader_signature = signature
    if 'MANAGER' in user.roles.split(','):
        attendance.manager_signature = signature
    db.session.add(attendance)
    
    # Chỉ set check_in/check_out khi có giờ vào/ra (không áp dụng cho lễ Việt Nam không đi làm)
    if check_in and check_out:
        attendance.check_in = datetime.combine(date, check_in)
    
    # Xử lý giờ ra - nếu là tăng ca qua ngày mới thì cộng thêm 1 ngày
    if next_day_checkout:
        # Bật qua đêm: set check_out sang ngày hôm sau, cho phép cả trường hợp check_out_time > check_in_time
        # Kiểm tra thời gian làm việc có hợp lý không (tối thiểu 1 giờ)
        work_duration = (datetime.combine(date + timedelta(days=1), check_out) - datetime.combine(date, check_in)).total_seconds() / 3600
        if work_duration < 1.0:
            return jsonify({'error': 'Thời gian làm việc quá ngắn. Vui lòng kiểm tra lại giờ vào/ra.'}), 400
        attendance.check_out = datetime.combine(date + timedelta(days=1), check_out)
        print(f"DEBUG: Tăng ca qua ngày mới - check_out: {attendance.check_out}")
    else:
        attendance.check_out = datetime.combine(date, check_out)
    
    attendance.shift_start = shift_start
    attendance.shift_end = shift_end
    
    attendance.note = note
    # Chỉ gọi update_work_hours() khi có giờ vào/ra (trường hợp lễ Việt Nam không đi làm đã set total_work_hours=8.0)
    if check_in and check_out:
        attendance.update_work_hours()
    try:
        print(f"DEBUG: About to commit attendance for user {user.id}, date {date}, holiday_type {holiday_type}")
        db.session.commit()
        print(f"DEBUG: Successfully committed attendance with ID {attendance.id}")
        log_audit_action(
            user_id=user.id,
            action='CREATE_ATTENDANCE',
            table_name='attendances',
            record_id=attendance.id,
            new_values={
                'date': attendance.date.isoformat(),
                'check_in': attendance.check_in.isoformat() if attendance.check_in else None,
                'check_out': attendance.check_out.isoformat() if attendance.check_out else None,
                'status': attendance.status
            }
        )
        print(f"DEBUG: Returning success response")
        return jsonify({
            'message': 'Chấm công thành công',
            'work_hours': attendance.total_work_hours,
            'overtime_before_22': attendance.overtime_before_22,
            'overtime_after_22': attendance.overtime_after_22,
            'signature_info': signature_info
        })
    except Exception as e:
        print(f"Database error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Đã xảy ra lỗi khi lưu dữ liệu'}), 500

@app.route('/api/attendance/history')
def get_attendance_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    try:
        user = get_user_from_session()
        if not user:
            return jsonify({'error': 'Không tìm thấy người dùng'}), 404
        current_role = session.get('current_role', user.roles.split(',')[0])
        if request.args.get('all') == '1':
            if current_role != 'ADMIN':
                return jsonify({'error': 'Chỉ quản trị viên mới có thể xem lịch sử chấm công toàn bộ'}), 403
            if not has_role(session['user_id'], 'ADMIN'):
                return jsonify({'error': 'Bạn không có quyền truy cập dữ liệu toàn bộ'}), 403
            page = validate_int(request.args.get('page', 1), min_val=1)
            per_page = validate_int(request.args.get('per_page', 10), min_val=1, max_val=100)
            search = validate_input_sanitize(request.args.get('search', '').strip())
            department = validate_input_sanitize(request.args.get('department', '').strip())
            date_from = validate_date(request.args.get('date_from', '').strip()) if request.args.get('date_from') else None
            date_to = validate_date(request.args.get('date_to', '').strip()) if request.args.get('date_to') else None
            
            if page is None or per_page is None:
                return jsonify({'error': 'Tham số phân trang không hợp lệ'}), 400
                
            # Eager-load user để tránh N+1
            q = Attendance.query.options(joinedload(Attendance.user)).filter_by(approved=True)
            
            # Filter theo tên nhân viên hoặc mã nhân viên
            if search:
                search_lower = search.lower().strip()
                # Tách từ khóa tìm kiếm thành các từ riêng lẻ
                search_words = search_lower.split()
                
                # Tạo điều kiện tìm kiếm cho từng từ
                name_conditions = []
                for word in search_words:
                    name_conditions.append(func.lower(User.name).contains(word))
                
                # Tạo điều kiện tìm kiếm đơn giản - tìm theo từng từ riêng lẻ
                name_conditions = []
                for word in search_words:
                    name_conditions.append(func.lower(User.name).contains(word))
                
                # Thêm điều kiện tìm kiếm theo mã nhân viên
                name_conditions.append(func.lower(func.cast(User.employee_id, db.String)).contains(search_lower))
                
                # Kết hợp tất cả điều kiện với OR
                q = q.join(Attendance.user).filter(db.or_(*name_conditions))
            
            # Filter theo phòng ban
            if department:
                q = q.join(Attendance.user).filter(User.department == department)
            
            # Filter theo khoảng thời gian
            if date_from:
                q = q.filter(Attendance.date >= date_from)
            if date_to:
                q = q.filter(Attendance.date <= date_to)
            total = q.count()
            # Optimize with eager loading to prevent N+1 queries
            attendances = q.options(
                joinedload(Attendance.user),
                joinedload(Attendance.approver)
            ).order_by(Attendance.date.desc()).offset((page-1)*per_page).limit(per_page).all()
            history = []
            for att in attendances:
                att_dict = att.to_dict()
                att_dict['user_name'] = att.user.name if att.user else '-'
                att_dict['department'] = att.user.department if att.user else '-'
                att_dict['approver_name'] = att.approver.name if att.approver else '-'
                
                # Debug logging để kiểm tra dữ liệu đối ứng
                print(f"Debug - Attendance {att.id} comp time data:")
                print(f"  comp_time_regular: {att.comp_time_regular}")
                print(f"  comp_time_overtime: {att.comp_time_overtime}")
                print(f"  comp_time_ot_before_22: {att.comp_time_ot_before_22}")
                print(f"  comp_time_ot_after_22: {att.comp_time_ot_after_22}")
                print(f"  to_dict comp_time_regular: {att_dict.get('comp_time_regular')}")
                print(f"  to_dict comp_time_overtime: {att_dict.get('comp_time_overtime')}")
                print(f"  to_dict comp_time_ot_before_22: {att_dict.get('comp_time_ot_before_22')}")
                print(f"  to_dict comp_time_ot_after_22: {att_dict.get('comp_time_ot_after_22')}")
                
                history.append(att_dict)
            return jsonify({
                'total': total,
                'page': page,
                'per_page': per_page,
                'data': history
            })
        else:
            current_month = datetime.now().month
            current_year = datetime.now().year
            # Optimize with eager loading
            attendances = Attendance.query.filter_by(user_id=user.id)\
                .options(joinedload(Attendance.approver))\
                .filter(db.extract('month', Attendance.date) == current_month)\
                .filter(db.extract('year', Attendance.date) == current_year)\
                .order_by(Attendance.date.desc())\
                .all()
            history = []
            for att in attendances:
                history.append(att.to_dict())
            return jsonify(history)
    except Exception as e:
        print(f"Error in get_attendance_history: {str(e)}")
        return jsonify({'error': 'Đã xảy ra lỗi khi lấy lịch sử chấm công'}), 500

def validate_overtime_comp_time(check_in, check_out, shift_start, shift_end, break_time, comp_time_regular, comp_time_overtime, comp_time_ot_before_22, comp_time_ot_after_22, date, next_day_checkout=False, holiday_type='normal', shift_code=None):
    """Validate overtime compensation time based on actual work hours and time periods.
    Sử dụng giây (int) cho so sánh để loại bỏ sai số khi dùng số thực.
    """
    
    # Cuối tuần & Lễ Việt Nam: KHÔNG cho phép đối ứng trong ca
    if holiday_type in ['weekend', 'vietnamese_holiday']:
        if (comp_time_regular or 0) > 0:
            return False, "Ngày nghỉ (cuối tuần/Lễ VN) không được phép dùng đối ứng trong ca (comp_time_regular). Chỉ được dùng đối ứng tăng ca."
        if (comp_time_overtime or 0) > 0:
            return False, "Ngày nghỉ (cuối tuần/Lễ VN) không được phép dùng đối ứng tăng ca tổng (comp_time_overtime). Chỉ được dùng đối ứng tăng ca trước/sau 22h."
    
    if check_in and check_out and shift_start and shift_end:
        def to_seconds(hours_float):
            """Chuyển đổi an toàn giờ sang giây"""
            try:
                if hours_float is None or hours_float == "":
                    return 0
                if isinstance(hours_float, str) and ":" in hours_float:
                    # Xử lý format HH:MM
                    hh, mm = hours_float.split(':')
                    return int(hh) * 3600 + int(mm) * 60
                else:
                    return int(round(float(hours_float) * 3600))
            except (ValueError, TypeError) as e:
                print(f"Warning: Failed to convert {repr(hours_float)} to seconds: {e}")
                return 0
        # Tính toán thời gian làm việc thực tế
        check_in_dt = datetime.combine(date, check_in)
        # Nếu bật qua đêm, giờ ra thuộc ngày hôm sau
        effective_check_out_date = date + timedelta(days=1) if next_day_checkout else date
        check_out_dt = datetime.combine(effective_check_out_date, check_out)
        shift_start_dt = datetime.combine(date, shift_start)
        shift_end_dt = datetime.combine(date, shift_end)
        # Nếu ca qua nửa đêm
        if shift_end <= shift_start:
            shift_end_dt = shift_end_dt + timedelta(days=1)
        
        # Tính thời gian làm việc thực tế (trừ thời gian nghỉ)
        actual_work_hours = (check_out_dt - check_in_dt).total_seconds() / 3600 - break_time
        actual_work_seconds = max(0, int(round((check_out_dt - check_in_dt).total_seconds())) - to_seconds(break_time))
        
        # Tính thời gian ca làm việc chuẩn (giữ lại để dùng ở nơi khác nếu cần)
        standard_shift_hours = (shift_end_dt - shift_start_dt).total_seconds() / 3600
        
        # Tính phần giờ trong ca để ràng buộc đối ứng trong ca
        overlap_start = max(check_in_dt, shift_start_dt)
        overlap_end = min(check_out_dt, shift_end_dt)
        time_in_shift_hours = max(0.0, (overlap_end - overlap_start).total_seconds() / 3600) if overlap_end > overlap_start else 0.0
        regular_available_hours = max(0.0, time_in_shift_hours - break_time)
        time_in_shift_seconds = max(0, int(round((overlap_end - overlap_start).total_seconds()))) if overlap_end > overlap_start else 0
        regular_available_seconds = max(0, time_in_shift_seconds - to_seconds(break_time))
        
        # Tính toán tăng ca theo logic thực tế (giống như trong update_work_hours)
        # Mốc 22h
        cutoff_22h = time(22, 0)
        twenty_two = datetime.combine(date, cutoff_22h)
        
        # Tính tăng ca theo loại ngày
        if holiday_type in ['vietnamese_holiday', 'weekend']:
            # Ngày lễ và cuối tuần: tính thời gian từ check_in đến 22:00
            if holiday_type == 'vietnamese_holiday':
                # Lễ Việt Nam: giới hạn đến 22:00
                if check_out_dt <= twenty_two:
                    # Toàn bộ thời gian làm việc trước 22h
                    overtime_before_22_hours = (check_out_dt - check_in_dt).total_seconds() / 3600
                else:
                    # Tính thời gian từ check_in đến 22:00
                    if check_in_dt < twenty_two:
                        # Có thời gian trước 22h
                        overtime_before_22_hours = (twenty_two - check_in_dt).total_seconds() / 3600
                    else:
                        # Không có thời gian trước 22h
                        overtime_before_22_hours = 0
            else:
                # Cuối tuần: vẫn phân biệt tăng ca trước và sau 22h
                # Tăng ca trước 22h: từ check_in đến min(22:00, check_out) (đã trừ giờ nghỉ)
                if check_in_dt < twenty_two:
                    # Giới hạn bởi thời gian làm việc thực tế
                    actual_end = min(check_out_dt, twenty_two)
                    overtime_before_22_hours = (actual_end - check_in_dt).total_seconds() / 3600
                    # Trừ giờ nghỉ ngay từ đầu cho cuối tuần
                    overtime_before_22_hours = max(0.0, overtime_before_22_hours - break_time)
                else:
                    overtime_before_22_hours = 0
        elif holiday_type == 'japanese_holiday':
            # Lễ Nhật: tăng ca = tổng giờ làm - giờ công thường
            # Giờ công thường = min(total_work_hours, 8h) - đối ứng trong ca
            regular_work_hours = min(actual_work_hours + break_time, 8.0)  # Đã trừ giờ nghỉ
            overtime_total = max(0.0, actual_work_hours - regular_work_hours)
            
            # Phân bổ ưu tiên phần sau 22h trước, phần còn lại cho trước 22h
            if overtime_total > 0.0:
                regular_end = check_in_dt + timedelta(hours=regular_work_hours)
                # Dung lượng trước 22h
                before_window_end = min(check_out_dt, twenty_two)
                capacity_before = 0.0
                if before_window_end > regular_end:
                    capacity_before = max(0.0, (before_window_end - regular_end).total_seconds() / 3600)
                
                # Dung lượng sau 22h
                after_window_start = max(regular_end, twenty_two)
                capacity_after = 0.0
                if check_out_dt > after_window_start:
                    capacity_after = max(0.0, (check_out_dt - after_window_start).total_seconds() / 3600)
                
                # Phân bổ: sau 22h trước
                overtime_after_22_hours = min(overtime_total, capacity_after)
                remaining = max(0.0, overtime_total - overtime_after_22_hours)
                overtime_before_22_hours = min(capacity_before, remaining)
            else:
                overtime_before_22_hours = 0.0
                overtime_after_22_hours = 0.0
        else:
            # Ngày thường: Tính OT trước 22h
            # Kiểm tra shift_code để quyết định có tính đi làm sớm không
            if shift_code == '5':
                # Ca 5 (tự do): tính cả đi làm sớm và về muộn
                # 1) Trước giờ vào ca
                pre_start = check_in_dt
                pre_end = min(check_out_dt, shift_start_dt, twenty_two)
                pre_shift_ot = max(0, (pre_end - pre_start).total_seconds() / 3600) if pre_end > pre_start and check_in_dt < shift_start_dt else 0

                # 2) Sau giờ ra ca nhưng trước 22h
                post_start = max(check_in_dt, shift_end_dt)
                post_end = min(check_out_dt, twenty_two)
                post_shift_ot = max(0, (post_end - post_start).total_seconds() / 3600) if post_end > post_start and check_out_dt > shift_end_dt else 0

                overtime_before_22_hours = pre_shift_ot + post_shift_ot
            else:
                # Ca 1-4: chỉ tính về muộn, không tính đi làm sớm
                # Chỉ tính phần sau giờ ra ca nhưng trước 22h
                post_start = max(check_in_dt, shift_end_dt)
                post_end = min(check_out_dt, twenty_two)
                post_shift_ot = max(0, (post_end - post_start).total_seconds() / 3600) if post_end > post_start and check_out_dt > shift_end_dt else 0

                overtime_before_22_hours = post_shift_ot
        
        # Tính tăng ca sau 22h
        if holiday_type in ['vietnamese_holiday', 'weekend']:
            if holiday_type == 'vietnamese_holiday':
                # Lễ Việt Nam: hợp nhất xử lý, tính cả phần qua đêm
                ot2_start = max(check_in_dt, twenty_two)
                if check_out_dt > ot2_start:
                    overtime_after_22_hours = (check_out_dt - ot2_start).total_seconds() / 3600
                else:
                    overtime_after_22_hours = 0
            else:
                # Cuối tuần: tăng ca sau 22h từ 22:00 đến check_out
                if check_out_dt > twenty_two:
                    overtime_after_22_hours = (check_out_dt - twenty_two).total_seconds() / 3600
                else:
                    overtime_after_22_hours = 0
        elif holiday_type == 'japanese_holiday':
            # Lễ Nhật: overtime_after_22_hours đã được tính ở trên
            pass
        else:
            # Ngày thường: hợp nhất xử lý, tính cả phần qua đêm
            ot2_start = max(check_in_dt, twenty_two)
            if check_out_dt > ot2_start:
                overtime_after_22_hours = (check_out_dt - ot2_start).total_seconds() / 3600
            else:
                overtime_after_22_hours = 0
        
        # Có tăng ca khi có bất kỳ phần nào > 0 (so sánh theo giây để chính xác)
        overtime_before_22_seconds = int(round(max(0.0, locals().get('overtime_before_22_hours', 0.0)) * 3600)) if 'overtime_before_22_hours' in locals() else 0
        overtime_after_22_seconds = int(round(max(0.0, locals().get('overtime_after_22_hours', 0.0)) * 3600)) if 'overtime_after_22_hours' in locals() else 0
        has_overtime = (overtime_before_22_seconds > 0) or (overtime_after_22_seconds > 0)
        
        # 0) Không bắt buộc người dùng phải chọn đối ứng
        # 1) Cho phép chọn nhiều loại đối ứng cùng lúc
        chosen = [
            (comp_time_regular or 0.0) > 1e-9,
            (comp_time_ot_before_22 or 0.0) > 1e-9,
            (comp_time_ot_after_22 or 0.0) > 1e-9,
            (comp_time_overtime or 0.0) > 1e-9
        ]
        # Không cần giới hạn số loại đối ứng được chọn

        # 2) Nếu không có tăng ca: chỉ cho phép đối ứng trong ca
        if not has_overtime:
            if (comp_time_ot_before_22 or 0) > 0 or (comp_time_ot_after_22 or 0) > 0 or (comp_time_overtime or 0) > 0:
                return False, f'Không có tăng ca trong ngày này. Bạn chỉ có thể nhập đối ứng trong ca. Tổng thời gian làm việc: {actual_work_seconds/3600:.1f} giờ.'
            # Ràng buộc đối ứng trong ca không vượt quá giờ làm thực tế/giờ trong ca
            if (comp_time_regular or 0) > (min(actual_work_hours, regular_available_hours) + 1e-6):
                return False, f'Đối ứng trong ca quá cao. Bạn đã nhập {comp_time_regular:.1f} giờ, nhưng tối đa chỉ được {min(actual_work_hours, regular_available_hours):.1f} giờ.'
        
        # 3) LOGIC MỚI: Kiểm tra quy tắc đối ứng dựa trên giờ làm việc
        if has_overtime:
            # Nếu < 8h: chỉ cho phép đối ứng trong ca
            if actual_work_seconds < 8 * 3600:
                if (comp_time_ot_before_22 or 0) > 0 or (comp_time_ot_after_22 or 0) > 0 or (comp_time_overtime or 0) > 0:
                    return False, f'Giờ làm việc ({actual_work_hours:.1f}h) < 8h. Bạn chỉ có thể nhập đối ứng trong ca (comp_time_regular).'
            
            # Nếu ≥ 8h và chỉ có tăng ca trước 22h: chỉ cho phép đối ứng trong ca và trước 22h
            elif actual_work_seconds >= 8 * 3600 and overtime_before_22_seconds > 0 and overtime_after_22_seconds <= 0:
                if (comp_time_ot_after_22 or 0) > 0 or (comp_time_overtime or 0) > 0:
                    return False, f'Giờ làm việc ({actual_work_hours:.1f}h) ≥ 8h và chỉ có tăng ca trước 22h. Bạn chỉ có thể nhập đối ứng trong ca (comp_time_regular) và đối ứng tăng ca trước 22h (comp_time_ot_before_22).'
            
            # Nếu ≥ 8h và có tăng ca sau 22h: cho phép tất cả loại đối ứng
            # (logic này đã được xử lý ở dưới)
        
        # Kiểm tra logic thời gian tăng ca trước và sau 22h
        if has_overtime:
            # Kiểm tra tăng ca trước 22h
            if (comp_time_ot_before_22 or 0) > 0:
                if overtime_before_22_seconds <= 0:
                    return False, 'Không có tăng ca trước 22h trong ngày này. Vui lòng xóa đối ứng trước 22h.'

                # Kiểm tra không vượt quá thực tế
                if to_seconds(comp_time_ot_before_22) > overtime_before_22_seconds:
                    return False, f'Đối ứng tăng ca trước 22h quá cao. Bạn đã nhập {comp_time_ot_before_22:.1f} giờ, nhưng thực tế chỉ có {overtime_before_22_seconds/3600:.1f} giờ tăng ca trước 22h.'
            
            # Kiểm tra tăng ca sau 22h
            if (comp_time_ot_after_22 or 0) > 0:
                if overtime_after_22_seconds <= 0:
                    return False, 'Không có thời gian làm việc sau 22h. Vui lòng xóa đối ứng sau 22h.'
                
                if to_seconds(comp_time_ot_after_22) > overtime_after_22_seconds:
                    return False, f'Đối ứng tăng ca sau 22h quá cao. Bạn đã nhập {comp_time_ot_after_22:.1f} giờ, nhưng thực tế chỉ có {overtime_after_22_seconds/3600:.1f} giờ tăng ca sau 22h.'
            
            # Legacy: nếu dùng comp_time_overtime thì ràng buộc theo tổng OT
            if (comp_time_overtime or 0) > 0:
                total_overtime_seconds = overtime_before_22_seconds + overtime_after_22_seconds
                if to_seconds(comp_time_overtime) > total_overtime_seconds:
                    return False, f'Đối ứng tăng ca quá cao. Bạn đã nhập {comp_time_overtime:.1f} giờ, nhưng tối đa chỉ được {total_overtime_seconds/3600:.1f} giờ tăng ca.'

            # Nếu chọn đối ứng trong ca khi có tăng ca: vẫn hợp lệ nhưng không vượt quá phần giờ trong ca
            if (comp_time_regular or 0) > 0:
                if to_seconds(comp_time_regular) > min(actual_work_seconds, regular_available_seconds):
                    return False, f'Đối ứng trong ca quá cao. Bạn đã nhập {comp_time_regular:.1f} giờ, nhưng tối đa chỉ được {min(actual_work_seconds, regular_available_seconds)/3600:.1f} giờ.'
    
    # Cuối tuần: kiểm tra tổng đối ứng không vượt quá tổng giờ làm thực tế
    if holiday_type == 'weekend':
        if check_in and check_out:
            total_comp_time_seconds = to_seconds(comp_time_ot_before_22) + to_seconds(comp_time_ot_after_22)
            if 'actual_work_seconds' in locals() and total_comp_time_seconds > actual_work_seconds:
                return False, f'Cuối tuần: Tổng đối ứng ({total_comp_time_seconds/3600:.1f}h) không được vượt quá tổng giờ làm thực tế ({actual_work_seconds/3600:.1f}h)'
    
    return True, None

def validate_role(role):
    """Validate role value and return role name"""
    role_map = {
        1: 'Nhân viên',
        2: 'Trưởng nhóm',
        3: 'Quản lý',
        4: 'Quản trị viên'
    }
    if role not in role_map:
        raise ValueError("Giá trị vai trò không hợp lệ. Phải là 1 (Nhân viên), 2 (Trưởng nhóm), 3 (Quản lý), hoặc 4 (Quản trị viên)")
    return role_map[role]

def get_user_roles(user_id):
    """Get all roles for a user"""
    user = db.session.get(User, user_id)
    if not user:
        return []
    return user.roles.split(',')

def has_role(user_id, required_role):
    """Check if user has a specific role"""
    user = db.session.get(User, user_id)
    if not user:
        return False
    return required_role in user.roles.split(',')

def check_approval_permission(user_id, attendance_id, current_role):
    """Check if user has permission to approve specific attendance"""
    user = db.session.get(User, user_id)
    if not user:
        return False, "❌ KHÔNG TÌM THẤY NGƯỜI DÙNG"
    
    attendance = Attendance.query.options(joinedload(Attendance.user)).get(attendance_id)
    if not attendance:
        return False, "❌ KHÔNG TÌM THẤY BẢN GHI CHẤM CÔNG"
    
    # ADMIN và MANAGER có thể duyệt tất cả
    if current_role in ['ADMIN', 'MANAGER']:
        return True, ""
    
    # TEAM_LEADER có thể duyệt nhân viên cùng phòng ban (bao gồm cả bản thân)
    if current_role == 'TEAM_LEADER':
        if not attendance.user or attendance.user.department != user.department:
            return False, "❌ KHÔNG CÙNG PHÒNG BAN: Chỉ duyệt được nhân viên cùng phòng"
        return True, ""
    
    return False, "❌ KHÔNG CÓ QUYỀN DUYỆT CHẤM CÔNG"

def check_attendance_access_permission(user_id, attendance_id, action='read'):
    """Check if user has permission to access specific attendance record"""
    user = db.session.get(User, user_id)
    if not user:
        return False, "❌ KHÔNG TÌM THẤY NGƯỜI DÙNG"
    
    attendance = Attendance.query.options(joinedload(Attendance.user)).get(attendance_id)
    if not attendance:
        return False, "❌ KHÔNG TÌM THẤY BẢN GHI CHẤM CÔNG"
    
    current_role = session.get('current_role', user.roles.split(',')[0])
    
    # ADMIN có thể truy cập tất cả
    if current_role == 'ADMIN':
        return True, ""
    
    # MANAGER có thể truy cập nhân viên cùng phòng ban
    if current_role == 'MANAGER':
        if not attendance.user or attendance.user.department != user.department:
            return False, "❌ KHÔNG CÙNG PHÒNG BAN: Chỉ xem được nhân viên cùng phòng"
        return True, ""
    
    # TEAM_LEADER có thể truy cập nhân viên cùng phòng ban
    if current_role == 'TEAM_LEADER':
        if not attendance.user or attendance.user.department != user.department:
            return False, "❌ KHÔNG CÙNG PHÒNG BAN: Chỉ xem được nhân viên cùng phòng"
        return True, ""
    
    # EMPLOYEE chỉ có thể truy cập bản ghi của chính mình
    if current_role == 'EMPLOYEE':
        if attendance.user_id != user_id:
            return False, "❌ CHỈ XEM ĐƯỢC BẢN GHI CỦA MÌNH"
        return True, ""
    
    return False, "❌ KHÔNG CÓ QUYỀN XEM BẢN GHI NÀY"

def check_request_access_permission(user_id, request_id, action='read'):
    """Check if user has permission to access specific request record"""
    user = db.session.get(User, user_id)
    if not user:
        return False, "❌ KHÔNG TÌM THẤY NGƯỜI DÙNG"
    
    req = Request.query.options(joinedload(Request.user)).get(request_id)
    if not req:
        return False, "❌ KHÔNG TÌM THẤY YÊU CẦU"
    
    current_role = session.get('current_role', user.roles.split(',')[0])
    
    # ADMIN có thể truy cập tất cả
    if current_role == 'ADMIN':
        return True, ""
    
    # MANAGER có thể truy cập yêu cầu của nhân viên cùng phòng ban
    if current_role == 'MANAGER':
        if not req.user or req.user.department != user.department:
            return False, "❌ KHÔNG CÙNG PHÒNG BAN: Chỉ xem được yêu cầu cùng phòng"
        return True, ""
    
    # TEAM_LEADER có thể truy cập yêu cầu của nhân viên cùng phòng ban
    if current_role == 'TEAM_LEADER':
        if not req.user or req.user.department != user.department:
            return False, "❌ KHÔNG CÙNG PHÒNG BAN: Chỉ xem được yêu cầu cùng phòng"
        return True, ""
    
    # EMPLOYEE chỉ có thể truy cập yêu cầu của chính mình
    if current_role == 'EMPLOYEE':
        if req.user_id != user_id:
            return False, "❌ CHỈ XEM ĐƯỢC YÊU CẦU CỦA MÌNH"
        return True, ""
    
    return False, "❌ KHÔNG CÓ QUYỀN XEM YÊU CẦU NÀY"

def check_leave_approval_permission(user_id, leave_request_id, current_role):
    """Check if user has permission to approve/reject specific leave request (mirror attendance)."""
    user = db.session.get(User, user_id)
    if not user:
        return False, "❌ KHÔNG TÌM THẤY NGƯỜI DÙNG"
    leave_req = LeaveRequest.query.options(joinedload(LeaveRequest.user)).get(leave_request_id)
    if not leave_req:
        return False, "❌ KHÔNG TÌM THẤY ĐƠN NGHỈ PHÉP"

    # ADMIN và MANAGER có thể phê duyệt tất cả
    if current_role in ['ADMIN', 'MANAGER']:
        return True, ""

    # TEAM_LEADER có thể phê duyệt nhân viên cùng phòng ban (bao gồm chính mình)
    if current_role == 'TEAM_LEADER':
        if not leave_req.user or leave_req.user.department != user.department:
            return False, "❌ KHÔNG CÙNG PHÒNG BAN: Chỉ duyệt được nhân viên cùng phòng"
        return True, ""

    # Các vai trò khác không có quyền
    return False, "❌ KHÔNG CÓ QUYỀN DUYỆT ĐƠN NGHỈ PHÉP"

# Import session utilities from utils
from utils.session import check_session_timeout, update_session_activity, log_audit_action

def require_role(required_role):
    """Decorator to require specific role for route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                return redirect(url_for('login'))
            
            # Kiểm tra vai trò hiện tại trong session
            current_role = session.get('current_role')
            if current_role != required_role:
                # Nếu user có vai trò yêu cầu trong DB thì tự động chuyển vai trò để tránh race-condition
                if has_role(session['user_id'], required_role):
                    session['current_role'] = required_role
                    try:
                        print(f"INFO ROLE AUTO-SWITCH: user_id={session['user_id']} from {current_role} -> {required_role}")
                    except Exception:
                        pass
                else:
                    flash(f'⚠️ CẦN CHUYỂN VAI TRÒ: Chuyển sang vai trò {required_role} để truy cập trang này', 'error')
                    return redirect(url_for('dashboard'))
            
            # Kiểm tra user có role này trong database không
            if not has_role(session['user_id'], required_role):
                flash('❌ KHÔNG CÓ QUYỀN: Bạn không có quyền truy cập trang này', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Role-based route decorators
def require_admin(f):
    return require_role('ADMIN')(f)

def require_manager(f):
    return require_role('MANAGER')(f)

def require_team_lead(f):
    return require_role('TEAM_LEADER')(f)

def require_employee(f):
    return require_role('EMPLOYEE')(f)

@app.route('/admin/users')
@require_admin
def admin_users():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Mặc định 10/trang, không cho chọn
    search = request.args.get('search', '', type=str).strip()
    department_filter = request.args.get('department', '', type=str).strip()

    query = User.query.filter_by(is_deleted=False)  # Chỉ hiển thị users chưa bị soft delete
    if search:
        # Cải thiện tìm kiếm: chuyển về lowercase và sử dụng func.lower() để đảm bảo không phân biệt hoa thường
        search_lower = search.lower().strip()
        # Tách từ khóa tìm kiếm thành các từ riêng lẻ
        search_words = search_lower.split()
        
        # Tạo điều kiện tìm kiếm đơn giản - tìm theo từng từ riêng lẻ
        name_conditions = []
        for word in search_words:
            name_conditions.append(func.lower(User.name).contains(word))
        
        # Thêm điều kiện tìm kiếm theo mã nhân viên
        name_conditions.append(func.lower(func.cast(User.employee_id, db.String)).contains(search_lower))
        
        # Kết hợp tất cả điều kiện với OR
        query = query.filter(db.or_(*name_conditions))
    if department_filter:
        query = query.filter(User.department == department_filter)
    query = query.order_by(User.name.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items

    # Danh sách phòng ban duy nhất, sắp xếp theo tên (chỉ từ users chưa bị xóa)
    all_departments = User.query.filter_by(is_deleted=False).with_entities(User.department).distinct().all()
    departments = sorted(set([d[0] for d in all_departments if d[0]]))

    # Calculate statistics
    admin_count = sum(1 for user in users if 'ADMIN' in user.roles.split(','))
    active_count = sum(1 for user in users if user.is_active)
    department_count = len(set(user.department for user in users))
    # Tính toán phân trang đẹp (hiển thị 5 trang quanh trang hiện tại)
    start_page = max(1, pagination.page - 2)
    end_page = min(pagination.pages, pagination.page + 2)
    if end_page - start_page < 4:
        end_page = min(pagination.pages, start_page + 4)
        start_page = max(1, end_page - 4)
    page_range = range(start_page, end_page + 1)

    return render_template(
        'admin/users.html',
        users=users,
        admin_count=admin_count,
        active_count=active_count,
        department_count=department_count,
        pagination=pagination,
        search=search,
        departments=departments,
        department_filter=department_filter,
        per_page=per_page,
        page_range=page_range
    )

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@require_admin
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        try:
            name = validate_input_sanitize(request.form.get('name'))
            department = validate_input_sanitize(request.form.get('department'))
            
            if not name:
                flash('Tên người dùng không hợp lệ', 'error')
                return redirect(url_for('edit_user', user_id=user_id))
            if not department:
                flash('Phòng ban không hợp lệ', 'error')
                return redirect(url_for('edit_user', user_id=user_id))
            
            # Get selected roles from checkboxes
            selected_roles = []
            role_mapping = {
                'EMPLOYEE': 'EMPLOYEE',
                'TEAM_LEADER': 'TEAM_LEADER', 
                'MANAGER': 'MANAGER',
                'ADMIN': 'ADMIN'
            }
            
            for role_key, role_value in role_mapping.items():
                if request.form.get(f'role_{role_key}') == 'on':
                    selected_roles.append(role_value)
            
            if not selected_roles:
                flash('Vui lòng chọn ít nhất một vai trò!', 'error')
                return redirect(url_for('edit_user', user_id=user_id))
            
            # Update user
            old_values = {
                'name': user.name,
                'department': user.department,
                'roles': user.roles
            }
            
            user.name = name
            user.roles = ','.join(selected_roles)
            user.department = department
            
            db.session.commit()
            
            # Log the action
            log_audit_action(
                user_id=session['user_id'],
                action='UPDATE_USER',
                table_name='users',
                record_id=user_id,
                old_values=old_values,
                new_values={
                    'name': name,
                    'department': department,
                    'roles': ','.join(selected_roles)
                }
            )
            
            flash('Cập nhật người dùng thành công', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            print(f"Error updating user: {str(e)}")
            flash('Đã xảy ra lỗi khi cập nhật người dùng!', 'error')
            return redirect(url_for('edit_user', user_id=user_id))
    # Danh sách phòng ban duy nhất, sắp xếp theo tên (chỉ từ users chưa bị xóa)
    all_departments = User.query.filter_by(is_deleted=False).with_entities(User.department).distinct().all()
    departments = sorted(set([d[0] for d in all_departments if d[0]]))
    
    return render_template('admin/edit_user.html', user=user, departments=departments)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@require_admin
def create_user():
    if request.method == 'POST':
        try:
            # Validate input
            employee_id_str = request.form.get('employee_id')
            password = request.form.get('password')
            name = validate_input_sanitize(request.form.get('name'))
            department = validate_input_sanitize(request.form.get('department'))
            
            # Validate employee_id
            employee_id = validate_employee_id(employee_id_str)
            if not employee_id:
                flash('Mã nhân viên không hợp lệ!', 'error')
                return render_template('admin/create_user.html')
            
            # Validate password
            if not validate_str(password, max_length=100):
                flash('Mật khẩu không hợp lệ!', 'error')
                return render_template('admin/create_user.html')
            
            # Validate name and department
            if not name:
                flash('Tên người dùng không hợp lệ', 'error')
                return render_template('admin/create_user.html')
            if not department:
                flash('Phòng ban không hợp lệ', 'error')
                return render_template('admin/create_user.html')
            
            # Check if employee_id already exists (chỉ kiểm tra users chưa bị xóa)
            existing_user = User.query.filter_by(employee_id=employee_id, is_deleted=False).first()
            if existing_user:
                flash('Mã nhân viên đã tồn tại!', 'error')
                return render_template('admin/create_user.html')
            
            # Get selected roles from checkboxes
            selected_roles = []
            role_mapping = {
                'EMPLOYEE': 'EMPLOYEE',
                'TEAM_LEADER': 'TEAM_LEADER', 
                'MANAGER': 'MANAGER',
                'ADMIN': 'ADMIN'
            }
            
            for role_key, role_value in role_mapping.items():
                if request.form.get(f'role_{role_key}') == 'on':
                    selected_roles.append(role_value)
            
            if not selected_roles:
                flash('Vui lòng chọn ít nhất một vai trò!', 'error')
                return render_template('admin/create_user.html')
            
            # Create new user
            new_user = User(
                employee_id=employee_id,
                name=name,
                department=department,
                roles=','.join(selected_roles),
                is_active=True
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            # Log the action
            log_audit_action(
                user_id=session['user_id'],
                action='CREATE_USER',
                table_name='users',
                record_id=new_user.id,
                new_values={
                    'employee_id': employee_id,
                    'name': name,
                    'department': department,
                    'roles': ','.join(selected_roles)
                }
            )
            
            flash('Tạo người dùng thành công!', 'success')
            return redirect(url_for('admin_users'))
            
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            flash('Đã xảy ra lỗi khi tạo người dùng!', 'error')
            # Danh sách phòng ban duy nhất, sắp xếp theo tên
            all_departments = User.query.with_entities(User.department).distinct().all()
            departments = sorted(set([d[0] for d in all_departments if d[0]]))
            return render_template('admin/create_user.html', departments=departments)
    
    # Danh sách phòng ban duy nhất, sắp xếp theo tên (chỉ từ users chưa bị xóa)
    all_departments = User.query.filter_by(is_deleted=False).with_entities(User.department).distinct().all()
    departments = sorted(set([d[0] for d in all_departments if d[0]]))
    
    return render_template('admin/create_user.html', departments=departments)

@app.route('/switch-role', methods=['POST'])
def switch_role():
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    data = request.get_json()
    role = validate_role_value(data.get('role'))
    if not role:
        return jsonify({'error': 'Vai trò không hợp lệ'}), 400
    user = get_user_from_session()
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    if role not in user.roles.split(','):
        return jsonify({'error': 'Vai trò không hợp lệ'}), 400
    old_role = session.get('current_role')
    session['current_role'] = role
    log_audit_action(
        user_id=user.id,
        action='SWITCH_ROLE',
        table_name='users',
        record_id=user.id,
        old_values={'current_role': old_role},
        new_values={'current_role': role}
    )
    return jsonify({'message': 'Đã chuyển vai trò thành công'}), 200

# API endpoint để submit request
@app.route('/api/request/submit', methods=['POST'])
def submit_request():
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    data = request.get_json()
    user = get_user_from_session()
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    # Validate input
    request_type = validate_input_sanitize(data.get('request_type'))
    start_date = validate_date(data.get('start_date'))
    end_date = validate_date(data.get('end_date'))
    reason = validate_reason(data.get('reason'))
    if not request_type:
        return jsonify({'error': 'Loại yêu cầu không hợp lệ'}), 400
    if not start_date:
        return jsonify({'error': 'Ngày bắt đầu không hợp lệ'}), 400
    if not end_date:
        return jsonify({'error': 'Ngày kết thúc không hợp lệ'}), 400
    if not reason:
        return jsonify({'error': 'Lý do không hợp lệ'}), 400
    if start_date > end_date:
        return jsonify({'error': 'Ngày bắt đầu phải trước ngày kết thúc'}), 400
    if start_date < datetime.now().date():
        return jsonify({'error': 'Không thể tạo yêu cầu cho ngày trong quá khứ'}), 400
    leader = User.query.filter_by(department=user.department, roles='TEAM_LEADER', is_deleted=False).first()
    if not leader:
        return jsonify({'error': 'Không tìm thấy trưởng nhóm cho phòng ban này'}), 400
    new_request = Request(
        user_id=user.id,
        request_type=request_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        current_approver_id=leader.id,
        step='leader',
        status='pending'
    )
    db.session.add(new_request)
    db.session.commit()
    return jsonify({'message': 'Gửi yêu cầu thành công'}), 201

# API endpoint để phê duyệt/từ chối request
@app.route('/api/request/<int:request_id>/approve', methods=['POST'])
def approve_request(request_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    data = request.get_json()
    action = data.get('action')  # 'approve' hoặc 'reject'
    reason = validate_reason(data.get('reason', '')) if data.get('action') == 'reject' else ''
    if action not in ['approve', 'reject']:
        return jsonify({'error': 'Hành động không hợp lệ'}), 400
    if action == 'reject' and not reason:
        return jsonify({'error': 'Lý do từ chối không hợp lệ'}), 400
    has_permission, error_message = check_request_access_permission(session['user_id'], request_id, 'approve')
    if not has_permission:
        return jsonify({'error': error_message}), 403
    req = Request.query.options(joinedload(Request.user)).get_or_404(request_id)
    approver = get_user_from_session()
    if req.current_approver_id != approver.id:
        return jsonify({'error': 'Bạn không có quyền phê duyệt yêu cầu này'}), 403
    if action == 'approve':
        if req.step == 'leader':
            manager = User.query.filter_by(department=req.user.department, roles='MANAGER', is_deleted=False).first()
            if not manager:
                return jsonify({'error': 'Không tìm thấy quản lý cho phòng ban này'}), 400
            req.current_approver_id = manager.id
            req.step = 'manager'
        elif req.step == 'manager':
            admin = User.query.filter_by(roles='ADMIN', is_deleted=False).first()
            if not admin:
                return jsonify({'error': 'Không tìm thấy quản trị viên'}), 400
            req.current_approver_id = admin.id
            req.step = 'admin'
        elif req.step == 'admin':
            req.status = 'approved'
            req.step = 'done'
    else:  # reject
        req.status = 'rejected'
        req.step = 'employee_edit'
        req.reject_reason = reason
        req.current_approver_id = req.user_id
    db.session.commit()
    return jsonify({'message': 'Cập nhật yêu cầu thành công'}), 200

@app.route('/api/attendance/<int:attendance_id>', methods=['DELETE'])
def delete_attendance(attendance_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    
    # Kiểm tra session timeout
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    
    # Cập nhật thời gian hoạt động cuối
    update_session_activity()
    
    # Kiểm tra quyền truy cập (chỉ EMPLOYEE có thể xóa bản ghi của chính mình)
    has_permission, error_message = check_attendance_access_permission(session['user_id'], attendance_id, 'delete')
    if not has_permission:
        return jsonify({'error': error_message}), 403
    
    att = Attendance.query.get(attendance_id)
    if not att:
        return jsonify({'error': 'Không tìm thấy bản ghi'}), 404
    if att.approved:
        return jsonify({'error': 'Bản ghi đã được phê duyệt, không thể xóa!'}), 400
    try:
        # Log attendance deletion
        log_audit_action(
            user_id=session['user_id'],
            action='DELETE_ATTENDANCE',
            table_name='attendances',
            record_id=attendance_id,
            old_values={
                'date': att.date.isoformat(),
                'check_in': att.check_in.isoformat() if att.check_in else None,
                'check_out': att.check_out.isoformat() if att.check_out else None,
                'status': att.status
            }
        )
        
        db.session.delete(att)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Lỗi khi xóa bản ghi!'}), 500

@app.route('/api/attendance/<int:attendance_id>', methods=['GET'])
def get_attendance(attendance_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    
    # Kiểm tra session timeout
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    
    # Cập nhật thời gian hoạt động cuối
    update_session_activity()
    
    # Kiểm tra quyền truy cập
    has_permission, error_message = check_attendance_access_permission(session['user_id'], attendance_id, 'read')
    if not has_permission:
        return jsonify({'error': error_message}), 403
    
    attendance = Attendance.query.options(joinedload(Attendance.user)).get(attendance_id)
    if not attendance:
        return jsonify({'error': 'Không tìm thấy bản ghi'}), 404
    
    # Lấy thông tin người dùng
    user_info = {
        'name': attendance.user.name if attendance.user else 'Unknown',
        'employee_id': attendance.user.employee_id if attendance.user else 'Unknown',
        'department': attendance.user.department if attendance.user else 'Unknown'
    }
    
    # Lấy thông tin người phê duyệt nếu có
    approver_info = None
    if attendance.approved_by:
        approver = User.query.get(attendance.approved_by)
        if approver:
            approver_info = {
                'name': approver.name,
                'employee_id': approver.employee_id,
                'department': approver.department,
                'roles': approver.roles
            }
    
    return jsonify({
        'id': attendance.id,
        'date': attendance.date.strftime('%d/%m/%Y'),
        'check_in': attendance.check_in.strftime('%H:%M') if attendance.check_in else None,
        'check_out': attendance.check_out.strftime('%H:%M') if attendance.check_out else None,
        'break_time': attendance._format_hours_minutes(attendance.break_time),
        'comp_time_regular': attendance._format_hours_minutes(attendance.comp_time_regular),
        'comp_time_overtime': attendance._format_hours_minutes(attendance.comp_time_overtime),
        'comp_time_ot_before_22': attendance._format_hours_minutes(attendance.comp_time_ot_before_22),
        'comp_time_ot_after_22': attendance._format_hours_minutes(attendance.comp_time_ot_after_22),
        'overtime_comp_time': attendance._format_hours_minutes(attendance.overtime_comp_time),
        'is_holiday': attendance.is_holiday,
        'holiday_type': attendance.holiday_type,
        'note': attendance.note,
        'approved': attendance.approved,
        'status': attendance.status,
        'shift_code': attendance.shift_code,
        'shift_start': attendance.shift_start.strftime('%H:%M') if attendance.shift_start else None,
        'shift_end': attendance.shift_end.strftime('%H:%M') if attendance.shift_end else None,
        'signature': attendance.signature,
        'team_leader_signature': attendance.team_leader_signature,
        'manager_signature': attendance.manager_signature,
        'user_name': user_info['name'],
        'user_employee_id': user_info['employee_id'],
        'user_department': user_info['department'],
        'approver_info': approver_info,
        'approved_at': attendance.approved_at.isoformat() if attendance.approved_at else None
    })

@app.route('/api/attendance/<int:attendance_id>', methods=['PUT'])
def update_attendance(attendance_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    has_permission, error_message = check_attendance_access_permission(session['user_id'], attendance_id, 'update')
    if not has_permission:
        return jsonify({'error': error_message}), 403
    attendance = Attendance.query.get(attendance_id)
    if not attendance:
        return jsonify({'error': 'Không tìm thấy bản ghi'}), 404
    if attendance.approved:
        return jsonify({'error': 'Bản ghi đã được phê duyệt, không thể sửa!'}), 400
    data = request.get_json()
    print('DEBUG signature PUT:', data.get('signature'))  # Thêm log signature
    # Validate input
    date = validate_date(data.get('date'))
    check_in = validate_time(data.get('check_in'))
    check_out = validate_time(data.get('check_out'))
    note = validate_note(data.get('note', ''))
    break_time = validate_float(data.get('break_time', 1.0), min_val=0, max_val=8)
    comp_time_regular = validate_float(data.get('comp_time_regular', 0.0), min_val=0, max_val=8)
    comp_time_overtime = validate_float(data.get('comp_time_overtime', 0.0), min_val=0, max_val=8)
    comp_time_ot_before_22 = validate_float(data.get('comp_time_ot_before_22', 0.0), min_val=0, max_val=8)
    comp_time_ot_after_22 = validate_float(data.get('comp_time_ot_after_22', 0.0), min_val=0, max_val=8)
    overtime_comp_time = validate_float(data.get('overtime_comp_time', 0.0), min_val=0, max_val=8)  # Giữ lại để tương thích
    is_holiday = bool(data.get('is_holiday', False))
    holiday_type = validate_holiday_type(data.get('holiday_type'))
    shift_code = data.get('shift_code')
    shift_start = validate_time(data.get('shift_start'))
    shift_end = validate_time(data.get('shift_end'))
    next_day_checkout = bool(data.get('next_day_checkout', False))  # Flag cho tăng ca qua ngày mới
    # Lấy thông tin user trước khi sử dụng
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    
    # Tự động lấy chữ ký từ database khi cập nhật
    signature = data.get('signature', '')
    
    # Nếu không có chữ ký hoặc chữ ký rỗng, lấy từ database
    if not signature:
        auto_signature = signature_manager.get_signature_from_database(user.id, 'EMPLOYEE')
        if auto_signature:
            signature = auto_signature
            attendance.signature = signature
            print(f"✅ AUTO SIGNATURE UPDATE: User {user.name} using signature from database")
        else:
            print(f"⚠️ NO AUTO SIGNATURE UPDATE: User {user.name} has no signature in database")
    else:
        # Nếu có chữ ký mới, cập nhật
        attendance.signature = signature
        print(f"📝 MANUAL SIGNATURE UPDATE: User {user.name} using new signature")
    
    if not date:
        return jsonify({'error': 'Vui lòng chọn ngày chấm công hợp lệ'}), 400
    if not holiday_type:
        return jsonify({'error': 'Vui lòng chọn loại ngày hợp lệ'}), 400
    if not check_in or not check_out:
        return jsonify({'error': 'Vui lòng nhập đầy đủ giờ vào và giờ ra hợp lệ'}), 400
    if break_time is None:
        return jsonify({'error': 'Thời gian nghỉ không hợp lệ!'}), 400
    if comp_time_regular is None:
        return jsonify({'error': 'Giờ đối ứng trong ca không hợp lệ!'}), 400
    if comp_time_overtime is None:
        return jsonify({'error': 'Giờ đối ứng tăng ca không hợp lệ!'}), 400
    if comp_time_ot_before_22 is None or comp_time_ot_after_22 is None:
        return jsonify({'error': 'Giờ đối ứng tăng ca theo mốc (trước/sau 22h) không hợp lệ!'}), 400
    
    # Validation: Kiểm tra xem có tăng ca hay không trước khi cho phép đối ứng tăng ca
    is_valid, error_message = validate_overtime_comp_time(
        check_in, check_out, shift_start, shift_end, break_time, 
        comp_time_regular, comp_time_overtime, comp_time_ot_before_22, comp_time_ot_after_22, date, data.get('next_day_checkout', False), holiday_type, shift_code
    )
    if not is_valid:
        return jsonify({'error': error_message}), 400
    
    if not shift_code or not shift_start or not shift_end:
        return jsonify({'error': 'Vui lòng chọn ca làm việc hợp lệ!'}), 400
    
    # Kiểm tra xem có bản ghi khác cùng ngày không (trừ bản ghi hiện tại)
    
    existing_attendance = Attendance.query.filter(
        Attendance.user_id == user.id,
        Attendance.date == date,
        Attendance.id != attendance_id
    ).first()
    
    if existing_attendance:
        if existing_attendance.status != 'rejected':
            return jsonify({'error': 'Bạn đã chấm công cho ngày này rồi, không thể chấm công 2 lần trong 1 ngày.'}), 400
        else:
            db.session.delete(existing_attendance)
            db.session.commit()
    
    attendance.date = date
    attendance.check_in = datetime.combine(date, check_in)
    
    # Xử lý giờ ra - nếu là tăng ca qua ngày mới thì cộng thêm 1 ngày
    if next_day_checkout:
        attendance.check_out = datetime.combine(date + timedelta(days=1), check_out)
        print(f"DEBUG UPDATE: Tăng ca qua ngày mới - check_out: {attendance.check_out}")
    else:
        attendance.check_out = datetime.combine(date, check_out)
    
    attendance.note = note
    attendance.break_time = break_time
    attendance.comp_time_regular = comp_time_regular
    attendance.comp_time_overtime = comp_time_overtime
    attendance.comp_time_ot_before_22 = comp_time_ot_before_22
    attendance.comp_time_ot_after_22 = comp_time_ot_after_22
    attendance.overtime_comp_time = overtime_comp_time
    attendance.is_holiday = is_holiday
    attendance.holiday_type = holiday_type
    attendance.shift_code = shift_code
    attendance.shift_start = shift_start
    attendance.shift_end = shift_end
    if attendance.status == 'rejected':
        attendance.status = 'pending'
    if date > datetime.now().date():
        return jsonify({'error': 'Không thể chấm công cho ngày trong tương lai!'}), 400
    attendance.update_work_hours()
    try:
        db.session.commit()
        log_audit_action(
            user_id=session['user_id'],
            action='UPDATE_ATTENDANCE',
            table_name='attendances',
            record_id=attendance_id,
            old_values={
                'date': attendance.date.isoformat(),
                'check_in': attendance.check_in.isoformat() if attendance.check_in else None,
                'check_out': attendance.check_out.isoformat() if attendance.check_out else None,
                'status': attendance.status
            },
            new_values={
                'date': date.isoformat(),
                'check_in': datetime.combine(date, check_in).isoformat(),
                'check_out': attendance.check_out.isoformat(),
                'status': attendance.status
            }
        )
        message = 'Cập nhật chấm công thành công'
        return jsonify({
            'message': message,
            'work_hours': attendance.total_work_hours,
            'overtime_before_22': attendance.overtime_before_22,
            'overtime_after_22': attendance.overtime_after_22
        })
    except Exception as e:
        print(f"Database error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Đã xảy ra lỗi khi cập nhật dữ liệu'}), 500

@app.route('/api/signature/check', methods=['POST'])
def check_signature_status():
    """API để kiểm tra trạng thái chữ ký cho phê duyệt"""
    print(f"DEBUG: check_signature_status called with data: {request.get_json()}")
    
    if 'user_id' not in session:
        print("DEBUG: No user_id in session")
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        print("DEBUG: Session timeout")
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    
    data = request.get_json()
    attendance_id = data.get('attendance_id')
    request_id = data.get('request_id')
    check_session = data.get('check_session', False)
    current_role = session.get('current_role')
    user_id = session['user_id']
    
    print(f"DEBUG: check_session={check_session}, current_role={current_role}, user_id={user_id}")
    
    # Nếu chỉ kiểm tra session signature
    if check_session:
        print(f"DEBUG: Checking session signature for user {user_id}, role {current_role}")
        session_signature, session_meta = signature_manager.get_signature_from_session(user_id, current_role)
        print(f"DEBUG: Session signature result: {session_signature}")
        return jsonify({
            'session_signature': session_signature if session_signature else None
        })
    
    # Sử dụng Signature Manager để kiểm tra trạng thái
    signature_status = signature_manager.check_signature_status(user_id, current_role, attendance_id)
    print(f"DEBUG: Signature status result: {signature_status}")
    print(f"DEBUG: Backend signature check - User: {user_id}, Role: {current_role}, Attendance: {attendance_id}")
    print(f"DEBUG: Backend result details: has_db_signature={signature_status.get('has_db_signature')}, is_reused_signature={signature_status.get('is_reused_signature')}")
    return jsonify(signature_status)

@app.route('/api/signature/validate-quality', methods=['POST'])
def validate_signature_quality():
    """验证签名质量"""
    if 'user_id' not in session:
        return jsonify({'error': 'Chưa đăng nhập'}), 401
    
    data = request.get_json()
    signature = data.get('signature')
    
    if not signature:
        return jsonify({
            'valid': False,
            'error': 'Không có dữ liệu chữ ký'
        })
    
    # 使用签名处理器验证质量
    quality_result = signature_manager.validate_signature_quality(signature)
    
    return jsonify(quality_result)

@app.route('/api/signature/fit-to-form', methods=['POST'])
def fit_signature_to_form():
    """Điều chỉnh chữ ký vừa khít với ô ký trong biểu mẫu"""
    if 'user_id' not in session:
        return jsonify({'error': 'Chưa đăng nhập'}), 401
    
    data = request.get_json()
    signature = data.get('signature')
    box_type = data.get('box_type', 'default')
    
    if not signature:
        return jsonify({
            'success': False,
            'error': 'Không có dữ liệu chữ ký'
        })
    
    # Điều chỉnh chữ ký vừa khít với ô
    fitted_signature = signature_manager.fit_signature_to_form_box(signature, box_type)
    
    # Kiểm tra xem có vừa không
    fit_result = signature_manager.validate_signature_fit(signature, box_type)
    
    return jsonify({
        'success': True,
        'fitted_signature': fitted_signature,
        'fit_result': fit_result
    })

@app.route('/api/signature/create-form-signatures', methods=['POST'])
def create_form_signatures():
    """Tạo chữ ký cho toàn bộ biểu mẫu"""
    if 'user_id' not in session:
        return jsonify({'error': 'Chưa đăng nhập'}), 401
    
    data = request.get_json()
    signatures = data.get('signatures', {})
    
    if not signatures:
        return jsonify({
            'success': False,
            'error': 'Không có dữ liệu chữ ký'
        })
    
    # Tạo chữ ký cho toàn bộ biểu mẫu
    form_signatures = signature_manager.create_form_signatures(signatures)
    
    return jsonify({
        'success': True,
        'form_signatures': form_signatures
    })

@app.route('/api/signature/save-session', methods=['POST'])
def save_signature_to_session():
    """API để lưu chữ ký vào session"""
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    
    data = request.get_json()
    signature = data.get('signature')
    signature_type = data.get('type', 'new')  # 'new', 'reused', 'session_reused', 'database_reused'
    dont_ask_again = data.get('dont_ask_again', False)
    
    if not signature:
        return jsonify({'error': 'Chữ ký không hợp lệ'}), 400
    
    current_role = session.get('current_role')
    user_id = session['user_id']
    
    # Lưu chữ ký vào session với flag don't ask again
    success = signature_manager.save_signature_to_session(
        user_id, current_role, signature, signature_type, dont_ask_again
    )
    
    if success:
        # Ghi log chi tiết
        signature_manager.log_signature_action(
            user_id=user_id,
            action='SAVE_SESSION',
            signature_type=signature_type,
            additional_data={'dont_ask_again': dont_ask_again}
        )
        
        message = 'Đã lưu chữ ký vào phiên'
        if dont_ask_again:
            message += ' và đặt không hỏi lại trong phiên này'
        
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': 'Không thể lưu chữ ký'}), 500

@app.route('/api/signature/clear-session', methods=['POST'])
def clear_session_signature():
    """API để xóa chữ ký khỏi session"""
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    
    current_role = session.get('current_role')
    user_id = session['user_id']
    
    success = signature_manager.clear_session_signature(user_id, current_role)
    
    if success:
        return jsonify({'success': True, 'message': 'Đã xóa chữ ký khỏi phiên'})
    else:
        return jsonify({'error': 'Không thể xóa chữ ký'}), 500

@app.route('/api/attendance/<int:attendance_id>/approve', methods=['POST'])
@rate_limit(max_requests=200, window_seconds=60)  # 200 approvals per minute (tăng cho 300 người)
def approve_attendance(attendance_id):
    # Ghi log đầu vào phê duyệt (ảnh chụp session)
    try:
        print(f"🧭 PHÊ DUYỆT - VÀO HÀM: attendance_id={attendance_id}, session_user_id={session.get('user_id')}, session_roles={session.get('roles')}, current_role={session.get('current_role')}")
    except Exception:
        pass
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    user = get_user_from_session()
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    current_role = session.get('current_role', user.roles.split(',')[0])
    print(f"🧑‍💼 NGỮ CẢNH PHÊ DUYỆT: người_dùng={user.name}, vai_trò_người_dùng={user.roles}, vai_trò_hiện_tại={current_role}")
    if current_role not in ['TEAM_LEADER', 'MANAGER', 'ADMIN']:
        return jsonify({'error': 'Bạn không có quyền phê duyệt chấm công'}), 403
    has_permission, error_message = check_approval_permission(user.id, attendance_id, current_role)
    if not has_permission:
        return jsonify({'error': error_message}), 403
    data = request.get_json()
    action = data.get('action')  # 'approve' hoặc 'reject'
    reason = validate_reason(data.get('reason', '')) if data.get('action') == 'reject' else ''
    approver_signature = data.get('signature')  # Chữ ký người phê duyệt
    
    print(f"🔍 BACKEND APPROVAL: User {user.name} ({current_role}) attempting to {action} attendance {attendance_id}")
    print(f"🔍 BACKEND SIGNATURE: Signature provided: {'Yes' if approver_signature else 'No'}")
    
    if action not in ['approve', 'reject']:
        return jsonify({'error': 'Hành động không hợp lệ'}), 400
    
    # Lấy thông tin attendance để kiểm tra
    attendance = Attendance.query.get(attendance_id)
    if not attendance:
        return jsonify({'error': 'Không tìm thấy bản ghi chấm công'}), 404
    print(f"🗂️ BẢN GHI CHẤM CÔNG: id={attendance.id}, trạng_thái_trước={attendance.status}, đã_duyệt={attendance.approved}, user_id={attendance.user_id}")
    
    # Kiểm tra chữ ký bắt buộc khi phê duyệt
    if action == 'approve':
        # Admin không cần chữ ký
        if current_role == 'ADMIN':
            approver_signature = None
            signature_type = 'admin_no_signature'
            print(f"👑 BACKEND ADMIN: Admin {user.name} - no signature required")
        else:
            # Kiểm tra chữ ký cá nhân trước - BẮT BUỘC cho non-admin users
            if not user.has_personal_signature():
                print(f"❌ BACKEND SIGNATURE REQUIRED: User {user.name} ({current_role}) has no personal signature")
                return jsonify({
                    'error': 'Bạn chưa có chữ ký cá nhân. Vui lòng thiết lập chữ ký trong phần Cài đặt trước khi phê duyệt.',
                    'redirect_to_settings': True
                }), 400
            
            # Logic chữ ký thông minh: ưu tiên chữ ký cá nhân, sau đó là chữ ký từ database
            if user.has_personal_signature():
                # Ưu tiên 1: Chữ ký cá nhân
                approver_signature = user.personal_signature
                signature_type = 'personal_signature'
                print(f"✅ BACKEND PERSONAL: User {user.name} using personal signature")
            else:
                # Ưu tiên 2: Chữ ký từ session (nếu có và được cho phép)
                session_signature, session_meta = signature_manager.get_signature_from_session(user.id, current_role)
                if session_signature and signature_manager.should_use_session_signature(user.id, current_role):
                    approver_signature = session_signature
                    signature_type = 'session_reused'
                    print(f"🔄 BACKEND SESSION: User {user.name} reusing signature from session")
                else:
                    # Ưu tiên 3: Chữ ký từ database (bao gồm tái sử dụng từ vai trò thấp hơn)
                    db_signature = signature_manager.get_signature_from_database(user.id, current_role, attendance_id)
                    if db_signature:
                        approver_signature = db_signature
                        signature_type = 'database_reused'
                        print(f"💾 BACKEND DATABASE: User {user.name} reusing signature from database")
                    elif approver_signature:
                        # Ưu tiên 4: Chữ ký mới được gửi từ frontend
                        signature_type = 'new'
                        print(f"🆕 BACKEND NEW: User {user.name} using newly created signature")
                    else:
                        # Không có chữ ký nào, yêu cầu ký mới
                        print(f"❌ BACKEND SIGNATURE: No signature found for {user.name}, signature required")
                        return jsonify({'error': 'Chữ ký là bắt buộc khi phê duyệt. Vui lòng ký tên để xác nhận.'}), 400
    
    if action == 'reject' and not reason:
        return jsonify({'error': 'Lý do từ chối không hợp lệ'}), 400
    if attendance.approved:
        return jsonify({'error': 'Bản ghi đã được phê duyệt hoàn tất'}), 400
    if action == 'approve':
        old_status = attendance.status
        if current_role == 'TEAM_LEADER':
            if attendance.status != 'pending':
                return jsonify({'error': 'Bản ghi không ở trạng thái chờ duyệt'}), 400
            attendance.status = 'pending_manager'
            attendance.approved_by = user.id
            attendance.approved_at = datetime.now()
            # Lưu chữ ký vào field tương ứng với vai trò hiện tại
            if approver_signature:
                attendance.team_leader_signature = approver_signature
            attendance.team_leader_signer_id = user.id  # Lưu ID người ký trưởng nhóm
            message = 'Đã chuyển lên Quản lý phê duyệt'
            print(f"✅ BACKEND TEAM_LEADER: {user.name} approved attendance {attendance_id}, status: pending_manager")
        elif current_role == 'MANAGER':
            if attendance.status != 'pending_manager':
                return jsonify({'error': 'Bản ghi chưa được Trưởng nhóm phê duyệt'}), 400
            attendance.status = 'pending_admin'
            attendance.approved_by = user.id
            attendance.approved_at = datetime.now()
            # Lưu chữ ký vào field tương ứng với vai trò hiện tại
            if approver_signature:
                attendance.manager_signature = approver_signature
            attendance.manager_signer_id = user.id  # Lưu ID người ký quản lý
            message = 'Đã chuyển lên Admin phê duyệt'
            print(f"✅ BACKEND MANAGER: {user.name} approved attendance {attendance_id}, status: pending_admin")
        elif current_role == 'ADMIN':
            if attendance.status not in ['pending_manager', 'pending_admin']:
                return jsonify({'error': 'Bản ghi chưa được cấp dưới phê duyệt'}), 400
            attendance.status = 'approved'
            attendance.approved = True
            attendance.approved_by = user.id
            attendance.approved_at = datetime.now()
            message = 'Phê duyệt hoàn tất'
            print(f"✅ BACKEND ADMIN: {user.name} completed approval for attendance {attendance_id}, status: approved")
            # Commit NGAY lập tức để trạng thái cập nhật cho phía Nhân viên, không phụ thuộc Selenium
            try:
                db.session.commit()
                print("💾 BACKEND ADMIN: Status committed before opening Selenium (ensures EMPLOYEE view updates immediately)")
            except Exception as e:
                db.session.rollback()
                print(f"⚠️ BACKEND ADMIN: Pre-commit failed before Selenium: {str(e)}")
            
            # Mở Chrome với Selenium để tương tác với Google Drive
            print(f"🚀 BACKEND ADMIN: Starting Selenium process for admin {user.name}")
            try:
                # Truyền dữ liệu attendance vào Selenium
                # Hàm chuyển đổi định dạng giờ -> H:MM
                def to_hhmm_smart(val):
                    try:
                        if val is None:
                            return '0:00'
                        if isinstance(val, str):
                            v = val.strip()
                            if v == '' or v.lower() in ['nan', 'none', 'nul', 'null', '-']:
                                return '0:00'
                            # Chuỗi dạng H:MM
                            if ':' in v:
                                parts = v.split(':', 1)
                                if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                                    h = int(parts[0].strip())
                                    m = int(parts[1].strip())
                                    if m < 0: m = 0
                                    if m > 59: m = m % 60
                                    if h < 0: h = 0
                                    return f"{h}:{m:02d}"
                                # Sai định dạng → cố chuyển như số giờ
                                try:
                                    num = float(v.replace(':', '.'))
                                except Exception:
                                    return '0:00'
                            else:
                                # Chuỗi số: coi như số giờ thập phân hoặc phút nếu nguyên nhỏ
                                num = float(v)
                        elif isinstance(val, (int, float)):
                            num = float(val)
                        else:
                            return '0:00'

                        # Chuẩn hóa âm → 0
                        if num < 0:
                            num = 0
                        # Heuristic sửa: 
                        # - Giá trị nhỏ (<= 24) coi là GIỜ
                        # - Giá trị nguyên lớn (>= 60 và <= 1440) có thể là PHÚT
                        # - Còn lại: coi là GIỜ thập phân
                        if float(num).is_integer():
                            i = int(num)
                            if 0 <= i <= 24:
                                total_minutes = i * 60
                            elif 60 <= i <= 1440:
                                total_minutes = i
                            else:
                                total_minutes = i * 60
                        else:
                            # Làm tròn tới phút gần nhất để tránh mất 1 phút do sai số float
                            total_minutes = int(round(num * 60))
                        if total_minutes < 0:
                            total_minutes = 0
                        hours = total_minutes // 60
                        minutes = total_minutes % 60
                        return f"{hours}:{minutes:02d}"
                    except Exception:
                        return '0:00'

                # Tổng giờ: dùng total_hours nếu có, fallback sang total_work_hours
                total_hours_value = getattr(attendance, 'total_hours', None)
                if total_hours_value is None or total_hours_value == "":
                    total_hours_value = getattr(attendance, 'total_work_hours', '')
                
                # Chuyển định dạng số giờ thập phân (vd 16.5) sang H:MM (vd 16:30)
                def to_hhmm_from_decimal(hours_val):
                    try:
                        if hours_val is None or hours_val == '':
                            return ''
                        if isinstance(hours_val, str):
                            if ':' in hours_val:
                                return hours_val
                            hours_float = float(hours_val)
                        else:
                            hours_float = float(hours_val)
                        # Làm tròn tới phút gần nhất để tránh mất 1 phút do sai số float
                        total_minutes = int(round(hours_float * 60))
                        return f"{total_minutes // 60}:{total_minutes % 60:02d}"
                    except Exception:
                        return str(hours_val)
                total_hours_display = to_hhmm_from_decimal(total_hours_value)
                try:
                    used_total_field = 'total_hours' if hasattr(attendance, 'total_hours') else 'total_work_hours'
                    print(f"🧪 ADMIN: Dùng trường '{used_total_field}' cho tổng giờ (hiển thị): {total_hours_display}")
                except Exception:
                    pass

                # Các trường đối ứng/ghi chú/giờ nghỉ (an toàn thuộc tính)
                break_time_value = to_hhmm_smart(getattr(attendance, 'break_time', ''))
                note_value = attendance.note if getattr(attendance, 'note', None) else ''
                # Chuẩn hóa các trường đối ứng về H:MM
                comp_time_regular_value = to_hhmm_smart(getattr(attendance, 'comp_time_regular', ''))
                comp_time_overtime_value = to_hhmm_smart(getattr(attendance, 'comp_time_overtime', ''))
                comp_time_ot_before_22_value = to_hhmm_smart(getattr(attendance, 'comp_time_ot_before_22', ''))
                comp_time_ot_after_22_value = to_hhmm_smart(getattr(attendance, 'comp_time_ot_after_22', ''))
                overtime_comp_time_value = to_hhmm_smart(getattr(attendance, 'overtime_comp_time', ''))
                # Chuẩn hóa OT về H:MM nếu cần
                overtime_before_22_val = to_hhmm_smart(getattr(attendance, 'overtime_before_22', ''))
                overtime_after_22_val = to_hhmm_smart(getattr(attendance, 'overtime_after_22', ''))

                # Tóm tắt đối ứng
                doi_ung_parts = []
                if comp_time_regular_value not in [None, '', 0, '0', '0:00']:
                    doi_ung_parts.append(f"Bù giờ thường: {comp_time_regular_value}")
                if comp_time_overtime_value not in [None, '', 0, '0', '0:00']:
                    doi_ung_parts.append(f"Bù giờ tăng ca: {comp_time_overtime_value}")
                if comp_time_ot_before_22_value not in [None, '', 0, '0', '0:00']:
                    doi_ung_parts.append(f"Bù OT <22h: {comp_time_ot_before_22_value}")
                if comp_time_ot_after_22_value not in [None, '', 0, '0', '0:00']:
                    doi_ung_parts.append(f"Bù OT >22h: {comp_time_ot_after_22_value}")
                if overtime_comp_time_value not in [None, '', 0, '0', '0:00']:
                    doi_ung_parts.append(f"Đối ứng OT: {overtime_comp_time_value}")
                # Tính tổng đối ứng theo HH:MM
                def hhmm_to_minutes_safe(v):
                    try:
                        if not v or v in ['0', '0:00']:
                            return 0
                        if isinstance(v, str) and ':' in v:
                            h, m = v.split(':', 1)
                            return int(h or '0') * 60 + int(m or '0')
                    except Exception:
                        pass
                    return 0
                total_comp_minutes = (
                    hhmm_to_minutes_safe(comp_time_regular_value) +
                    hhmm_to_minutes_safe(comp_time_ot_before_22_value) +
                    hhmm_to_minutes_safe(comp_time_ot_after_22_value) +
                    hhmm_to_minutes_safe(comp_time_overtime_value) +
                    hhmm_to_minutes_safe(overtime_comp_time_value)
                )
                total_comp_display = f"{total_comp_minutes // 60}:{total_comp_minutes % 60:02d}"
                if doi_ung_parts:
                    doi_ung_summary = f"{total_comp_display} [ " + ' | '.join(doi_ung_parts) + " ]"
                else:
                    doi_ung_summary = total_comp_display

                # Tính giờ công thường để hiển thị chính xác (khác với tổng giờ làm)
                regular_work_display = attendance._format_hours_minutes(attendance.calculate_regular_work_hours())

                attendance_data = {
                    'id': attendance.id,
                    'user_name': attendance.user.name if attendance.user else 'Unknown',
                    'date': attendance.date.strftime('%Y-%m-%d') if attendance.date else '',
                    'check_in': attendance.check_in.strftime('%H:%M') if attendance.check_in else '',
                    'check_out': attendance.check_out.strftime('%H:%M') if attendance.check_out else '',
                    'total_hours': total_hours_display,
                    'regular_work_hours': regular_work_display,
                    'break_time': break_time_value,
                    'overtime_before_22': overtime_before_22_val,
                    'overtime_after_22': overtime_after_22_val,
                    'comp_time_regular': comp_time_regular_value,
                    'comp_time_overtime': comp_time_overtime_value,
                    'comp_time_ot_before_22': comp_time_ot_before_22_value,
                    'comp_time_ot_after_22': comp_time_ot_after_22_value,
                    'overtime_comp_time': overtime_comp_time_value,
                    'note': note_value,
                    'doi_ung': doi_ung_summary,
                    'status': attendance.status,
                    'approved_by': user.name,
                    'approved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                print(f"📊 DỮ LIỆU GỬI SANG SELENIUM:")
                print(f"   - Nhân viên: {attendance_data['user_name']}")
                print(f"   - Ngày: {attendance_data['date']}")
                print(f"   - Giờ vào: {attendance_data.get('check_in','')}")
                print(f"   - Giờ ra: {attendance_data.get('check_out','')}")
                print(f"   - Giờ nghỉ: {attendance_data.get('break_time','')}")
                print(f"   - Tổng giờ làm: {attendance_data.get('total_hours','')}")
                print(f"   - Giờ công: {attendance_data.get('regular_work_hours','')}")
                print(f"   - Tăng ca trước 22h: {attendance_data.get('overtime_before_22','')}")
                print(f"   - Tăng ca sau 22h: {attendance_data.get('overtime_after_22','')}")
                print(f"   - Ghi chú: {attendance_data.get('note','')}")
                print(f"   - Đối ứng: {attendance_data.get('doi_ung','-')}")
                print(f"   - Trạng thái: {attendance_data['status']}")
                print(f"   - Người duyệt: {attendance_data['approved_by']}")
                
                open_google_drive_with_selenium(user.name, attendance_data)
                print(f"✅ BACKEND ADMIN: Selenium process completed for admin {user.name}")
            except Exception as e:
                print(f"❌ BACKEND SELENIUM ERROR: Failed to open browser: {str(e)}")
                import traceback
                print(f"❌ BACKEND SELENIUM TRACEBACK: {traceback.format_exc()}")
        # Ghi log phê duyệt
        log_audit_action(
            user_id=user.id,
            action='APPROVE_ATTENDANCE',
            table_name='attendances',
            record_id=attendance_id,
            old_values={'status': old_status},
            new_values={'status': attendance.status, 'approved_by': user.id, 'approved_at': attendance.approved_at.isoformat()}
        )
        
        # Ghi log chữ ký nếu có
        if approver_signature and current_role != 'ADMIN':
            signature_manager.log_signature_action(
                user_id=user.id,
                action='APPROVAL',
                signature_type=signature_type if 'signature_type' in locals() else 'new',
                attendance_id=attendance_id,
                additional_data={
                    'approver_role': current_role,
                    'approver_name': user.name,
                    'approval_status': attendance.status
                }
            )
            print(f"📝 BACKEND SIGNATURE LOG: Logged signature action for {user.name} ({current_role}) - Type: {signature_type}")
        elif current_role == 'ADMIN':
            # Ghi log cho admin không cần chữ ký
            signature_manager.log_signature_action(
                user_id=user.id,
                action='APPROVAL',
                signature_type='admin_no_signature',
                attendance_id=attendance_id,
                additional_data={
                    'approver_role': current_role,
                    'approver_name': user.name,
                    'approval_status': attendance.status,
                    'admin_approval': True
                }
            )
            print(f"📝 BACKEND ADMIN LOG: Admin {user.name} approved without signature")
    else:  # reject
        old_status = attendance.status
        attendance.status = 'rejected'
        attendance.note = f"Bị từ chối bởi {current_role}: {reason}"
        message = 'Từ chối thành công'
        print(f"❌ BACKEND REJECT: {user.name} rejected attendance {attendance_id}, reason: {reason}")
        log_audit_action(
            user_id=user.id,
            action='REJECT_ATTENDANCE',
            table_name='attendances',
            record_id=attendance_id,
            old_values={'status': old_status},
            new_values={'status': attendance.status, 'reason': reason}
        )
    try:
        db.session.commit()
        print(f"✅ BACKEND SUCCESS: {user.name} ({current_role}) successfully processed {action} for attendance {attendance_id}")
        
        # Thêm thông tin chi tiết cho response
        response_data = {'message': message}
        
        # Nếu là admin phê duyệt hoàn tất, thêm thông tin về Selenium
        if action == 'approve' and current_role == 'ADMIN' and attendance.status == 'approved':
            response_data['selenium_status'] = 'started'
            response_data['chrome_opened'] = True
            response_data['attendance_info'] = {
                'employee_name': attendance.user.name if attendance.user else 'Unknown',
                'date': attendance.date.strftime('%Y-%m-%d') if attendance.date else '',
                'approved_by': user.name,
                'approved_at': attendance.approved_at.strftime('%Y-%m-%d %H:%M:%S') if attendance.approved_at else ''
            }
            print(f"🌐 BACKEND RESPONSE: Chrome should be opening for admin {user.name}")
        
        return jsonify(response_data)
    except Exception as e:
        db.session.rollback()
        print(f"❌ BACKEND ERROR: Failed to process {action} for attendance {attendance_id}: {str(e)}")
        return jsonify({'error': 'Đã xảy ra lỗi khi cập nhật trạng thái'}), 500

def convert_overtime_to_hhmm():
    def minutes_to_hhmm(minutes):
        if minutes < 0: minutes = 0
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        return f"{hours}:{mins:02d}"

    attendances = Attendance.query.all()
    for att in attendances:
        # Chuyển đổi overtime_before_22
        if att.overtime_before_22 is None or att.overtime_before_22 == "" or att.overtime_before_22 == "NaN:NaN":
            att.overtime_before_22 = "0:00"
        elif not isinstance(att.overtime_before_22, str):
            try:
                minutes = int(float(att.overtime_before_22) * 60)
                att.overtime_before_22 = minutes_to_hhmm(minutes) if minutes > 0 else "0:00"
            except Exception:
                att.overtime_before_22 = "0:00"
        # Chuyển đổi overtime_after_22
        if att.overtime_after_22 is None or att.overtime_after_22 == "" or att.overtime_after_22 == "NaN:NaN":
            att.overtime_after_22 = "0:00"
        elif not isinstance(att.overtime_after_22, str):
            try:
                minutes = int(float(att.overtime_after_22) * 60)
                att.overtime_after_22 = minutes_to_hhmm(minutes) if minutes > 0 else "0:00"
            except Exception:
                att.overtime_after_22 = "0:00"
    db.session.commit()
    print("Đã làm sạch lại overtime về dạng H:MM cho tất cả bản ghi.")

def format_hours_minutes(hours):
    try:
        if hours is None:
            return "0:00"
        # Nếu là chuỗi số, chuyển sang float
        if isinstance(hours, str):
            hours = float(hours)
        if hours != hours or hours < 0:  # kiểm tra NaN hoặc âm
            return "0:00"
        h = int(hours)
        m = int(round((hours - h) * 60))
        if m == 60:
            h += 1
            m = 0
        return f"{h}:{m:02d}"
    except Exception:
        return "0:00"

def translate_holiday_type(holiday_type_en):
    """Translates holiday type from English to Vietnamese."""
    if not holiday_type_en:
        return '-'
    translations = {
        'normal': 'Ngày thường',
        'weekend': 'Cuối tuần',
        'vietnamese_holiday': 'Lễ Việt Nam',
        'japanese_holiday': 'Lễ Nhật Bản'
    }
    return translations.get(holiday_type_en, holiday_type_en)

@app.route('/api/attendance/pending')
def get_pending_attendance():
    if 'user_id' not in session:
        return jsonify({'total': 0, 'page': 1, 'per_page': 10, 'data': []})
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    user = get_user_from_session()
    if not user:
        return jsonify({'total': 0, 'page': 1, 'per_page': 10, 'data': []})
    current_role = session.get('current_role', user.roles.split(',')[0])
    page = validate_int(request.args.get('page', 1), min_val=1)
    per_page = validate_int(request.args.get('per_page', 10), min_val=1, max_val=100)
    search = validate_input_sanitize(request.args.get('search', '').strip())
    department = validate_input_sanitize(request.args.get('department', '').strip())
    date_from = validate_date(request.args.get('date_from', '').strip()) if request.args.get('date_from') else None
    date_to = validate_date(request.args.get('date_to', '').strip()) if request.args.get('date_to') else None
    if page is None or per_page is None:
        return jsonify({'error': 'Tham số phân trang không hợp lệ'}), 400
    if current_role == 'TEAM_LEADER':
        query = Attendance.query.filter_by(approved=False, status='pending')
        team_users = User.query.filter(User.department == user.department, User.is_deleted == False).all()
        team_user_ids = [u.id for u in team_users]
        query = query.filter(Attendance.user_id.in_(team_user_ids))
    elif current_role == 'MANAGER':
        query = Attendance.query.filter_by(approved=False, status='pending_manager')
        if department:
            query = query.join(Attendance.user).filter(
                User.department == department,
                User.is_deleted == False
            )
    else:  # ADMIN
        query = Attendance.query.filter_by(approved=False, status='pending_admin')
    # Join với User một lần duy nhất
    query = query.join(Attendance.user).filter(User.is_deleted == False)
    
    if search:
        search_lower = search.lower().strip()
        # Tách từ khóa tìm kiếm thành các từ riêng lẻ
        search_words = search_lower.split()
        
        # Tạo điều kiện tìm kiếm đơn giản - tìm theo từng từ riêng lẻ
        name_conditions = []
        for word in search_words:
            name_conditions.append(func.lower(User.name).contains(word))
        
        # Thêm điều kiện tìm kiếm theo mã nhân viên
        name_conditions.append(func.lower(func.cast(User.employee_id, db.String)).contains(search_lower))
        
        # Kết hợp tất cả điều kiện với OR
        query = query.filter(db.or_(*name_conditions))
    if date_from:
        query = query.filter(Attendance.date >= date_from)
    if date_to:
        query = query.filter(Attendance.date <= date_to)
    total = query.count()
    records = query.options(joinedload(Attendance.user)).order_by(Attendance.date.desc()).offset((page-1)*per_page).limit(per_page).all()
    result = []
    for att in records:
        result.append({
            'id': att.id,
            'date': att.date.strftime('%d/%m/%Y'),
            'check_in': att.check_in.strftime('%H:%M') if att.check_in else None,
            'check_out': att.check_out.strftime('%H:%M') if att.check_out else None,
            'break_time': att._format_hours_minutes(att.break_time),
            'comp_time_regular': att._format_hours_minutes(att.comp_time_regular),
            'comp_time_overtime': att._format_hours_minutes(att.comp_time_overtime),
            'comp_time_ot_before_22': att._format_hours_minutes(att.comp_time_ot_before_22),
            'comp_time_ot_after_22': att._format_hours_minutes(att.comp_time_ot_after_22),
            'overtime_comp_time': att._format_hours_minutes(att.overtime_comp_time),  # Giữ lại để tương thích
            'total_work_hours': att._format_hours_minutes(att.total_work_hours) if att.total_work_hours is not None else "0:00",
            'work_hours_display': att._format_hours_minutes(att.calculate_regular_work_hours()),
            'overtime_before_22': att.overtime_before_22,
            'overtime_after_22': att.overtime_after_22,
            'holiday_type': translate_holiday_type(att.holiday_type),
            'user_name': att.user.name if att.user else '',
            'department': att.user.department if att.user else '',
            'note': att.note,
            'status': att.status,
            'approved': att.approved,
            'signature': att.signature,
            'team_leader_signature': att.team_leader_signature,
            'manager_signature': att.manager_signature
        })
    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'data': result
    })

@app.route('/api/attendance/debug/status')
def debug_attendance_status():
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    user = get_user_from_session()
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    current_role = session.get('current_role', user.roles.split(',')[0])
    if current_role != 'ADMIN':
        return jsonify({'error': 'Chỉ ADMIN mới có thể truy cập endpoint này'}), 403
    if not has_role(session['user_id'], 'ADMIN'):
        return jsonify({'error': 'Bạn không có quyền truy cập debug endpoint'}), 403
    all_statuses = db.session.query(Attendance.status).distinct().all()
    status_counts = {}
    for status in ['pending', 'pending_manager', 'pending_admin', 'approved', 'rejected']:
        count = Attendance.query.filter_by(status=status).count()
        status_counts[status] = count
    sample_records = {}
    for status in ['pending', 'pending_manager', 'pending_admin']:
        records = Attendance.query.options(joinedload(Attendance.user)).filter_by(status=status).limit(5).all()
        sample_records[status] = [
            {
                'id': r.id,
                'user_id': r.user_id,
                'date': r.date.strftime('%d/%m/%Y'),
                'status': r.status,
                'approved': r.approved,
                'user_name': r.user.name if r.user else 'Unknown'
            }
            for r in records
        ]
    return jsonify({
        'all_statuses': [s[0] for s in all_statuses],
        'status_counts': status_counts,
        'sample_records': sample_records
    })

@app.route('/api/attendance/debug/search')
def debug_attendance_search():
    """Debug endpoint để kiểm tra tìm kiếm"""
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    user = get_user_from_session()
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    current_role = session.get('current_role', user.roles.split(',')[0])
    if current_role != 'ADMIN':
        return jsonify({'error': 'Chỉ ADMIN mới có thể truy cập endpoint này'}), 403
    
    search = request.args.get('search', '').strip()
    department = request.args.get('department', '').strip()
    
    # Kiểm tra tất cả bản ghi attendance
    query = Attendance.query.join(Attendance.user).filter(User.is_deleted == False)
    
    debug_info = {
        'search_term': search,
        'search_lower': search.lower().strip() if search else '',
        'search_words': search.lower().strip().split() if search else [],
        'department_filter': department,
        'query_before_filter': query.count()
    }
    
    if search:
        search_lower = search.lower().strip()
        # Tách từ khóa tìm kiếm thành các từ riêng lẻ
        search_words = search_lower.split()
        
        debug_info['search_words'] = search_words
        
        # Thử tìm kiếm đơn giản trước
        simple_query = query.filter(func.lower(User.name).contains(search_lower))
        debug_info['simple_search_count'] = simple_query.count()
        
        # Tạo điều kiện tìm kiếm cho từng từ
        name_conditions = []
        for word in search_words:
            name_conditions.append(func.lower(User.name).contains(word))
        
        debug_info['name_conditions'] = [str(cond) for cond in name_conditions]
        
        # Thử từng điều kiện riêng lẻ
        for i, word in enumerate(search_words):
            word_query = query.filter(func.lower(User.name).contains(word))
            debug_info[f'word_{i}_{word}_count'] = word_query.count()
        
        # Tạo điều kiện tìm kiếm đơn giản - tìm theo từng từ riêng lẻ
        name_conditions = []
        for word in search_words:
            name_conditions.append(func.lower(User.name).contains(word))
        
        # Thêm điều kiện tìm kiếm theo mã nhân viên
        name_conditions.append(func.lower(func.cast(User.employee_id, db.String)).contains(search_lower))
        
        # Kết hợp tất cả điều kiện với OR
        query = query.filter(db.or_(*name_conditions))
        
        debug_info['query_after_filter'] = query.count()
    
    if department:
        query = query.filter(User.department == department)
        debug_info['query_after_department'] = query.count()
    
    # Lấy tất cả bản ghi để debug
    records = query.options(joinedload(Attendance.user)).limit(20).all()
    
    debug_data = []
    for att in records:
        debug_data.append({
            'id': att.id,
            'user_id': att.user_id,
            'user_name': att.user.name if att.user else 'Unknown',
            'employee_id': att.user.employee_id if att.user else 'Unknown',
            'department': att.user.department if att.user else 'Unknown',
            'date': att.date.strftime('%d/%m/%Y'),
            'status': att.status,
            'approved': att.approved,
            'check_in': att.check_in.strftime('%H:%M') if att.check_in else None,
            'check_out': att.check_out.strftime('%H:%M') if att.check_out else None
        })
    
    debug_info['total_found'] = len(debug_data)
    debug_info['records'] = debug_data
    
    return jsonify(debug_info)

def validate_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return None

def validate_time(time_str):
    try:
        if not time_str:
            return None
        time_str = str(time_str).strip()
        # Chỉ nhận đúng định dạng HH:MM
        if len(time_str) == 5 and time_str[2] == ':':
            return datetime.strptime(time_str, '%H:%M').time()
        return None
    except Exception:
        return None

def validate_float(val, min_val=None, max_val=None):
    try:
        if val is None:
            return None
        # Hỗ trợ chuỗi H:MM
        if isinstance(val, str) and ':' in val:
            parts = val.split(':', 1)
            hh = int(parts[0] or '0')
            mm = int(parts[1] or '0')
            f = hh + mm / 60.0
        else:
            f = float(val)  # Đã sửa indentation
        
        if min_val is not None and f < min_val:
            return None
        if max_val is not None and f > max_val:
            return None
        return f
    except Exception:
        return None



def validate_note(val):
    return validate_str(val, max_length=1000, allow_empty=True)

def validate_reason(val):
    return validate_str(val, max_length=500, allow_empty=False)

def validate_holiday_type(val):
    allowed = ['normal', 'weekend', 'vietnamese_holiday', 'japanese_holiday']
    return val if val in allowed else None

def validate_role_value(val):
    allowed = ['EMPLOYEE', 'TEAM_LEADER', 'MANAGER', 'ADMIN']
    return val if val in allowed else None

def validate_int(val, min_val=None, max_val=None):
    try:
        i = int(val)
        if min_val is not None and i < min_val:
            return None
        if max_val is not None and i > max_val:
            return None
        return i
    except Exception:
        return None



# Exempt certain API endpoints from CSRF protection if needed
# GET endpoints don't need CSRF protection
try:
    csrf.exempt(app.view_functions['get_attendance'])
    csrf.exempt(app.view_functions['get_attendance_history'])
    csrf.exempt(app.view_functions['get_pending_attendance'])
    csrf.exempt(app.view_functions['debug_attendance_status'])
    # Temporarily exempt signature APIs for testing
    csrf.exempt(app.view_functions['check_signature_status'])
    csrf.exempt(app.view_functions['save_signature_to_session'])
    csrf.exempt(app.view_functions['clear_session_signature'])
except KeyError:
    pass  # Routes might not exist yet

def safe_format_hours_minutes(hours):
    try:
        if hours is None or hours == "" or hours != hours or float(hours) < 0:
            return "01:00"
        if isinstance(hours, str) and ':' in hours:
            return hours
        if isinstance(hours, str):
            hours = float(hours)
        h = int(hours)
        m = int(round((hours - h) * 60))
        if m == 60:
            h += 1
            m = 0
        return f"{h}:{m:02d}"
    except Exception:
        return "01:00"

@app.route('/admin/users/<int:user_id>/soft_delete', methods=['POST'])
@require_admin
def soft_delete_user(user_id):
    """Soft delete user - set is_deleted to True"""
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    
    # Không cho phép xóa chính mình
    if user.id == session['user_id']:
        return jsonify({'error': 'Không thể xóa tài khoản của chính mình'}), 400
    
    try:
        # Soft delete user
        user.soft_delete()
        db.session.commit()
        
        # Log the action
        log_audit_action(
            user_id=session['user_id'],
            action='SOFT_DELETE_USER',
            table_name='users',
            record_id=user_id,
            old_values={'is_deleted': False, 'is_active': True},
            new_values={'is_deleted': True, 'is_active': False}
        )
        
        return jsonify({
            'success': True,
            'message': f'Đã xóa người dùng {user.name} thành công'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error soft deleting user: {str(e)}")
        return jsonify({'error': 'Đã xảy ra lỗi khi xóa người dùng'}), 500

@app.route('/admin/users/<int:user_id>/restore', methods=['POST'])
@require_admin
def restore_user(user_id):
    """Restore soft deleted user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    
    if not user.is_soft_deleted():
        return jsonify({'error': 'Người dùng này chưa bị xóa'}), 400
    
    try:
        # Restore user
        user.restore()
        db.session.commit()
        
        # Log the action
        log_audit_action(
            user_id=session['user_id'],
            action='RESTORE_USER',
            table_name='users',
            record_id=user_id,
            old_values={'is_deleted': True, 'is_active': False},
            new_values={'is_deleted': False, 'is_active': True}
        )
        
        return jsonify({
            'success': True,
            'message': f'Đã khôi phục người dùng {user.name} thành công'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error restoring user: {str(e)}")
        return jsonify({'error': 'Đã xảy ra lỗi khi khôi phục người dùng'}), 500

@app.route('/admin/users/deleted')
@require_admin
def admin_deleted_users():
    """Show soft deleted users"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    search = request.args.get('search', '', type=str).strip()
    department_filter = request.args.get('department', '', type=str).strip()

    query = User.query.filter_by(is_deleted=True)  # Chỉ hiển thị users đã bị soft delete
    if search:
        search_lower = search.lower().strip()
        # Tách từ khóa tìm kiếm thành các từ riêng lẻ
        search_words = search_lower.split()
        
        # Tạo điều kiện tìm kiếm cho từng từ
        name_conditions = []
        for word in search_words:
            name_conditions.append(func.lower(User.name).contains(word))
        
        # Tạo điều kiện tìm kiếm đơn giản - tìm theo từng từ riêng lẻ
        name_conditions = []
        for word in search_words:
            name_conditions.append(func.lower(User.name).contains(word))
        
        # Thêm điều kiện tìm kiếm theo mã nhân viên
        name_conditions.append(func.lower(func.cast(User.employee_id, db.String)).contains(search_lower))
        
        # Kết hợp tất cả điều kiện với OR
        query = query.filter(db.or_(*name_conditions))
    if department_filter:
        query = query.filter(User.department == department_filter)
    query = query.order_by(User.name.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items

    # Danh sách phòng ban duy nhất từ users đã bị xóa
    all_departments = User.query.filter_by(is_deleted=True).with_entities(User.department).distinct().all()
    departments = sorted(set([d[0] for d in all_departments if d[0]]))

    # Calculate statistics
    deleted_count = len(users)
    
    # Tính toán phân trang
    start_page = max(1, pagination.page - 2)
    end_page = min(pagination.pages, pagination.page + 2)
    if end_page - start_page < 4:
        end_page = min(pagination.pages, start_page + 4)
        start_page = max(1, end_page - 4)
    page_range = range(start_page, end_page + 1)

    return render_template(
        'admin/deleted_users.html',
        users=users,
        deleted_count=deleted_count,
        pagination=pagination,
        search=search,
        departments=departments,
        department_filter=department_filter,
        per_page=per_page,
        page_range=page_range
    )

@app.route('/admin/users/<int:user_id>/toggle_active', methods=['POST'])
@require_admin
def toggle_user_active(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if int(user_id) == int(session['user_id']):
        return jsonify({'error': 'Không thể tự khoá tài khoản của mình!'}), 400
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({
        'success': True,
        'is_active': user.is_active,
        'user_name': user.name,
        'status_label': 'Hoạt Động' if user.is_active else 'Đã Khoá',
        'status_class': 'bg-success' if user.is_active else 'bg-secondary'
    })

@app.route('/admin/attendance/<int:attendance_id>/export-overtime-pdf')
@require_admin
def export_overtime_pdf(attendance_id):
    try:
        # Load attendance với tất cả các relationship cần thiết
        attendance = Attendance.query.options(
            joinedload(Attendance.user).load_only(User.name, User.employee_id, User.department),
            joinedload(Attendance.team_leader_signer).load_only(User.name),
            joinedload(Attendance.manager_signer).load_only(User.name)
        ).get_or_404(attendance_id)
        
        buffer = io.BytesIO()
        
        # Sử dụng hàm create_overtime_pdf đã tách riêng
        create_overtime_pdf(attendance, buffer)
        
        # Tạo tên file
        safe_name = remove_vietnamese_accents(attendance.user.name)
        safe_empid = str(attendance.user.employee_id)
        safe_date = attendance.date.strftime('%d%m%Y')
        filename = f"tangca_{safe_name}_{safe_empid}_{safe_date}.pdf"
        
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
        
    except Exception as e:
        print('PDF export error:', e)
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': 'Lỗi khi sinh file PDF', 'detail': str(e)})

@app.route('/admin/attendance/<int:attendance_id>/test-signature-pdf')
@require_admin
def test_signature_on_overtime_pdf(attendance_id):
    """Test hiển thị chữ ký trên form tăng ca thực tế"""
    try:
        # Lấy bản ghi attendance với tất cả các relationship cần thiết
        attendance = Attendance.query.options(
            joinedload(Attendance.user).load_only(User.name, User.employee_id, User.department),
            joinedload(Attendance.team_leader_signer).load_only(User.name),
            joinedload(Attendance.manager_signer).load_only(User.name)
        ).get_or_404(attendance_id)
        
        # Tạo chữ ký mẫu cho test
        sample_signature = create_sample_signature_base64()
        
        # Tạo bản copy của attendance với chữ ký mẫu
        test_attendance = type('TestAttendance', (), {
            'id': attendance.id,
            'date': attendance.date,
            'check_in': attendance.check_in,
            'check_out': attendance.check_out,
            'break_time': attendance.break_time,
            'total_work_hours': attendance.total_work_hours,
            'overtime_before_22': attendance.overtime_before_22,
            'overtime_after_22': attendance.overtime_after_22,
            'note': attendance.note,
            'user': attendance.user,
            'signature': sample_signature,
            'team_leader_signature': sample_signature,
            'manager_signature': sample_signature,
            'team_leader_signer_id': attendance.team_leader_signer_id,
            'manager_signer_id': attendance.manager_signer_id,
            'team_leader_signer': attendance.team_leader_signer,
            'manager_signer': attendance.manager_signer,
            'approved': True,
            'approved_at': datetime.now()
        })()
        
        buffer = io.BytesIO()
        
        # Tạo PDF với chữ ký mẫu
        create_overtime_pdf(test_attendance, buffer)
        
        # Tạo tên file test
        safe_name = remove_vietnamese_accents(attendance.user.name)
        safe_empid = str(attendance.user.employee_id)
        safe_date = attendance.date.strftime('%d%m%Y')
        filename = f"test_chu_ky_tangca_{safe_name}_{safe_empid}_{safe_date}.pdf"
        
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
        
    except Exception as e:
        print('Test signature PDF error:', e)
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': 'Lỗi khi tạo PDF test chữ ký', 'detail': str(e)})

def create_sample_signature_base64():
    """Tạo chữ ký mẫu dạng base64"""
    try:
        # Tạo canvas để vẽ chữ ký mẫu
        from PIL import Image, ImageDraw
        
        # Tạo ảnh trắng
        img = Image.new('RGB', (200, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # Vẽ chữ ký mẫu với màu xanh như bút bi
        draw.line([(20, 50), (40, 30), (60, 70), (80, 40), (100, 60), (120, 35), (140, 65), (160, 45), (180, 55)], fill='blue', width=2)
        
        # Chuyển thành base64
        import io
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        import base64
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
        
    except Exception as e:
        print(f"Error creating sample signature: {e}")
        # Trả về chữ ký mẫu đơn giản nếu có lỗi
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="

# Hàm wrap_text cho phần ghi chú (đặt phía trên đoạn sử dụng)
def wrap_text(text, font_name, font_size, max_width, canvas_obj):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words = text.split(' ')
    lines = []
    current_line = ''
    for word in words:
        test_line = current_line + (' ' if current_line else '') + word
        if stringWidth(test_line, font_name, font_size) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

@app.route('/admin/attendance/export-overtime-bulk')
@require_admin
def export_overtime_bulk():
    try:
        month = request.args.get('month')  # Có thể None nếu xuất theo năm
        year = int(request.args.get('year', 0))
        
        if not (2000 <= year <= 2100):
            return abort(400, 'Tham số năm không hợp lệ')
        
        # Xây dựng query filter
        query_filter = [
            db.extract('year', Attendance.date) == year,
            Attendance.approved == True
        ]
        
        # Thêm filter tháng nếu có
        if month:
            month = int(month)
            if not (1 <= month <= 12):
                return abort(400, 'Tham số tháng không hợp lệ')
            query_filter.append(db.extract('month', Attendance.date) == month)
        
        # Lấy tất cả bản ghi Attendance đã được phê duyệt
        # Tối ưu: chỉ lấy các trường cần thiết
        attendances = Attendance.query.filter(*query_filter).options(
            joinedload(Attendance.user).load_only(User.name, User.employee_id, User.department)
        ).all()
        
        if not attendances:
            if month:
                return abort(404, 'Không có bản ghi nào trong tháng này')
            else:
                return abort(404, 'Không có bản ghi nào trong năm này')
        
        print(f'Creating ZIP for {len(attendances)} records...')
        
        # Tạo file ZIP trong bộ nhớ với compression level cao hơn
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for i, att in enumerate(attendances, 1):
                try:
                    # Tạo PDF cho từng bản ghi
                    pdf_buffer = io.BytesIO()
                    
                    # Gọi hàm tạo PDF (tái sử dụng logic từ export_overtime_pdf)
                    create_overtime_pdf(att, pdf_buffer)
                    
                    # Đặt tên file cho từng PDF (loại bỏ dấu tiếng Việt)
                    
                    safe_name = remove_vietnamese_accents(att.user.name) if att.user and att.user.name else str(att.id)
                    safe_empid = str(att.user.employee_id) if att.user and att.user.employee_id else str(att.id)
                    safe_date = att.date.strftime('%d%m%Y')
                    filename = f"tangca_{safe_name}_{safe_empid}_{safe_date}.pdf"
                    
                    # Đảm bảo buffer ở đầu file
                    pdf_buffer.seek(0)
                    zipf.writestr(filename, pdf_buffer.read())
                    
                    # Log progress mỗi 10 records
                    if i % 10 == 0:
                        print(f'Processed {i}/{len(attendances)} records...')
                    
                except Exception as e:
                    print(f'Error creating PDF for attendance {att.id}: {e}')
                    continue
        
        zip_buffer.seek(0)
        
        # Tạo tên file ZIP
        if month:
            zip_filename = f"tangca_{month:02d}_{year}.zip"
        else:
            zip_filename = f"tangca_{year}.zip"
            
        print(f'ZIP creation completed: {zip_filename}')
        return send_file(zip_buffer, as_attachment=True, download_name=zip_filename, mimetype='application/zip')
        
    except Exception as e:
        print('Bulk export error:', e)
        return jsonify({'error': 'Lỗi khi xuất file ZIP', 'detail': str(e)})

# Cache fonts để tránh đăng ký lại mỗi lần
_fonts_registered = False

def register_pdf_fonts():
    """Đăng ký fonts cho PDF một lần duy nhất"""
    global _fonts_registered
    if _fonts_registered:
        return
    
    try:
        # Thử đăng ký DejaVuSans cho tiếng Việt
        registerFont(TTFont('DejaVuSans', 'static/fonts/DejaVuSans.ttf'))
        registerFont(TTFont('DejaVuSans-Bold', 'static/fonts/DejaVuSans.ttf'))  # Sử dụng cùng font cho bold
        
        # Đăng ký NotoSansJP cho tiếng Nhật
        registerFont(TTFont('NotoSansJP', 'static/fonts/NotoSansJP-Regular.ttf'))
        registerFont(TTFont('NotoSansJP-Bold', 'static/fonts/NotoSansJP-Bold.ttf'))
        registerFont(TTFont('NotoSansJP-Medium', 'static/fonts/NotoSansJP-Medium.ttf'))
        registerFont(TTFont('NotoSansJP-Light', 'static/fonts/NotoSansJP-Light.ttf'))
        registerFont(TTFont('NotoSansJP-Black', 'static/fonts/NotoSansJP-Black.ttf'))
        registerFont(TTFont('NotoSansJP-ExtraBold', 'static/fonts/NotoSansJP-ExtraBold.ttf'))
        registerFont(TTFont('NotoSansJP-ExtraLight', 'static/fonts/NotoSansJP-ExtraLight.ttf'))
        registerFont(TTFont('NotoSansJP-SemiBold', 'static/fonts/NotoSansJP-SemiBold.ttf'))
        registerFont(TTFont('NotoSansJP-Thin', 'static/fonts/NotoSansJP-Thin.ttf'))
        
        _fonts_registered = True
        print('PDF fonts registered successfully')
    except Exception as e:
        print('PDF font register error:', e)
        # Fallback: sử dụng font mặc định
        _fonts_registered = True

def fix_base64_padding(base64_string):
    """
    Sửa lỗi base64 padding để đảm bảo độ dài là bội số của 4
    """
    if not base64_string:
        return base64_string
    
    # Loại bỏ khoảng trắng và ký tự xuống dòng
    base64_string = base64_string.strip()
    
    # Tính số ký tự cần thêm để đạt bội số của 4
    padding_length = len(base64_string) % 4
    if padding_length > 0:
        # Thêm dấu = để đạt bội số của 4
        base64_string += '=' * (4 - padding_length)
        print(f"DEBUG: Fixed base64 padding, added {4 - padding_length} padding characters")
    
    return base64_string

def looks_like_fernet_token(token):
    """
    Nhận diện nhanh chuỗi có khả năng là Fernet token để tránh thử giải mã sai dữ liệu
    """
    try:
        if not isinstance(token, str) or len(token) < 50:
            return False
        normalized = token.strip().replace(' ', '+')
        padding_length = len(normalized) % 4
        if padding_length > 0:
            normalized += '=' * (4 - padding_length)
        raw = base64.urlsafe_b64decode(normalized.encode('utf-8'))
        return len(raw) > 9 and raw[0] == 0x80
    except Exception:
        return False

def process_signature_for_pdf(signature_data):
    """
    Xử lý chữ ký để hiển thị trong PDF - IMPROVED VERSION với xử lý lỗi base64 an toàn
    """
    if not signature_data:
        print("DEBUG: No signature data provided")
        return None
    
    try:
        if isinstance(signature_data, str):
            print(f"DEBUG: Processing signature string, length: {len(signature_data)}")
            
            # Nếu là base64 từ frontend (data:image/png;base64,...)
            if signature_data.startswith('data:image'):
                print("DEBUG: Found data:image format, extracting base64")
                try:
                    # Kiểm tra định dạng data:image
                    if not signature_data.startswith('data:image/png;base64,'):
                        print("DEBUG: Not PNG format, trying to convert")
                        # Thử chuyển đổi từ các định dạng khác
                        if signature_data.startswith('data:image/jpeg;base64,'):
                            signature_data = signature_data.replace('data:image/jpeg;base64,', 'data:image/png;base64,')
                    
                    base64_data = signature_data.split(',')[1]
                    
                    # Sửa lỗi base64 padding
                    base64_data = fix_base64_padding(base64_data)
                    
                    # Kiểm tra base64 có hợp lệ không
                    try:
                        decoded = base64.b64decode(base64_data)
                        print(f"DEBUG: Base64 decode successful, decoded length: {len(decoded)}")
                        
                        # Kiểm tra có phải là ảnh PNG không
                        if len(decoded) >= 8 and decoded.startswith(b'\x89PNG\r\n\x1a\n'):
                            print("DEBUG: Valid PNG image confirmed")
                            return base64_data
                        else:
                            print("DEBUG: Not a valid PNG image")
                            return None
                    except Exception as decode_error:
                        print(f"DEBUG: Base64 decode failed after padding fix: {decode_error}")
                        return None
                        
                except Exception as e:
                    print(f"DEBUG: Base64 decode failed: {e}")
                    return None
                    
            # Nếu là base64 thuần túy
            elif len(signature_data) > 100:
                try:
                    # Sửa lỗi base64 padding trước khi decode
                    fixed_signature = fix_base64_padding(signature_data)
                    
                    # Thử decode để kiểm tra
                    decoded = base64.b64decode(fixed_signature)
                    print(f"DEBUG: Valid base64 signature found, decoded length: {len(decoded)}")
                    
                    # Kiểm tra có phải là ảnh PNG không
                    if len(decoded) >= 8 and decoded.startswith(b'\x89PNG\r\n\x1a\n'):
                        print("DEBUG: Valid PNG image confirmed")
                        return fixed_signature
                    else:
                        print("DEBUG: Not a valid PNG image")
                        return None
                        
                except Exception as base64_error:
                    print(f"DEBUG: Base64 decode failed: {base64_error}")
                    # Chỉ thử giải mã nếu thật sự trông giống Fernet token
                    if looks_like_fernet_token(signature_data):
                        try:
                            decrypted = signature_manager.decrypt_signature(signature_data)
                            print(f"DEBUG: Decrypted signature, length: {len(decrypted) if decrypted else 0}")
                            
                            if decrypted:
                                # Nếu giải mã thành công và có data:image
                                if decrypted.startswith('data:image'):
                                    base64_data = decrypted.split(',')[1]
                                    try:
                                        # Sửa lỗi base64 padding sau khi giải mã
                                        base64_data = fix_base64_padding(base64_data)
                                        
                                        # Kiểm tra base64 sau khi giải mã
                                        decoded = base64.b64decode(base64_data)
                                        print(f"DEBUG: Decrypted base64 decode successful, decoded length: {len(decoded)}")
                                        
                                        # Kiểm tra có phải là ảnh PNG không
                                        if len(decoded) >= 8 and decoded.startswith(b'\x89PNG\r\n\x1a\n'):
                                            print("DEBUG: Valid PNG image confirmed after decryption")
                                            return base64_data
                                        else:
                                            print("DEBUG: Not a valid PNG image after decryption")
                                            return None
                                            
                                    except Exception as e:
                                        print(f"DEBUG: Decrypted base64 decode failed: {e}")
                                        return None
                                # Nếu giải mã thành công và là base64 thuần túy
                                elif len(decrypted) > 100:
                                    try:
                                        # Sửa lỗi base64 padding sau khi giải mã
                                        fixed_decrypted = fix_base64_padding(decrypted)
                                        
                                        decoded = base64.b64decode(fixed_decrypted)
                                        print(f"DEBUG: Decrypted base64 decode successful, decoded length: {len(decoded)}")
                                        
                                        # Kiểm tra có phải là ảnh PNG không
                                        if len(decoded) >= 8 and decoded.startswith(b'\x89PNG\r\n\x1a\n'):
                                            print("DEBUG: Valid PNG image confirmed after decryption")
                                            return fixed_decrypted
                                        else:
                                            print("DEBUG: Not a valid PNG image after decryption")
                                            return None
                                            
                                    except Exception as e:
                                        print(f"DEBUG: Decrypted base64 decode failed: {e}")
                                        return None
                        except Exception:
                            # Silent on decryption failure to avoid noisy logs; logic unchanged
                            return None
                    else:
                        print("DEBUG: Not valid base64 and not a Fernet token, skip decryption")
                        return None
            else:
                print(f"DEBUG: Short signature string: {signature_data}")
                return signature_data
        else:
            print(f"DEBUG: Non-string signature data type: {type(signature_data)}")
            return None
    except Exception as e:
        print(f"Error processing signature: {e}")
        import traceback
        traceback.print_exc()
        return None

def draw_signature_with_proper_scaling(canvas, signature_data, x, y, box_width, box_height):
    """
    Vẽ chữ ký với tỷ lệ đúng và màu xanh như bút bi - SỬ DỤNG SIGNATURE FIT ADAPTER
    """
    if not signature_data:
        print("DEBUG: No signature data provided to draw")
        return False
    
    try:
        # Sử dụng signature fit adapter để điều chỉnh chữ ký vừa khít với ô
        from utils.signature_manager import signature_manager
        
        # Xác định loại ô dựa trên kích thước
        box_type = 'default'
        if box_width >= 140 and box_height >= 70:
            box_type = 'manager'  # Ô quản lý
        elif box_width >= 120 and box_height >= 60:
            box_type = 'supervisor'  # Ô cấp trên
        elif box_width >= 100 and box_height >= 50:
            box_type = 'applicant'  # Ô người xin phép
        
        print(f"DEBUG: Using signature fit adapter for box type: {box_type}")
        
        # Điều chỉnh chữ ký vừa khít với ô
        fitted_signature = signature_manager.fit_signature_to_form_box(
            signature_data, 
            box_type=box_type
        )
        
        if not fitted_signature:
            print("DEBUG: Failed to fit signature to box")
            return False
                
        print(f"DEBUG: Fitted signature length: {len(fitted_signature)}")
        
        # Decode base64
        try:
            if fitted_signature.startswith('data:image'):
                fitted_signature = fitted_signature.split(',')[1]
            
            decoded_data = base64.b64decode(fitted_signature)
            print(f"DEBUG: Successfully decoded fitted signature, length: {len(decoded_data)}")
            
        except Exception as decode_error:
            print(f"DEBUG: Failed to decode fitted signature: {decode_error}")
            return False
        
        # Mở và chuẩn hóa ảnh, đồng thời chuẩn bị để nội suy theo kích thước vẽ thực tế
        try:
            from PIL import Image
            import io
            
            pil_image = Image.open(io.BytesIO(decoded_data))
            if pil_image.mode != 'RGBA':
                pil_image = pil_image.convert('RGBA')
        except Exception as img_open_err:
            print(f"DEBUG: Failed to open image for processing: {img_open_err}")
            return False
        
        # Tính tỷ lệ để giữ nguyên tỷ lệ khung hình và vừa khít với ô
        img_width, img_height = pil_image.size
        print(f"DEBUG: Fitted image size (PIL): {img_width}x{img_height}")
        aspect_ratio = img_width / img_height
        box_aspect_ratio = box_width / box_height
        
        # Tính kích thước thực tế để vẽ - sử dụng 99% kích thước ô để đảm bảo gần như kín mà không tràn
        if aspect_ratio > box_aspect_ratio:
            # Ảnh rộng hơn, căn theo chiều rộng
            draw_width = box_width * 0.99
            draw_height = draw_width / aspect_ratio
        else:
            # Ảnh cao hơn, căn theo chiều cao
            draw_height = box_height * 0.99
            draw_width = draw_height * aspect_ratio
        
        # Kiểm tra kích thước vẽ hợp lệ
        if draw_width <= 0 or draw_height <= 0:
            print(f"DEBUG: Invalid draw dimensions: {draw_width}x{draw_height}")
            return False
        
        # Nội suy ảnh tới độ phân giải mục tiêu dựa trên kích thước vẽ để luôn sắc nét
        try:
            target_dpi = 220  # DPI mục tiêu cho ảnh nhúng vào PDF (MaxFill - chất lượng cao)
            target_px_w = max(1, int(draw_width * target_dpi / 72.0))
            target_px_h = max(1, int(draw_height * target_dpi / 72.0))
            
            if pil_image.size != (target_px_w, target_px_h):
                pil_image = pil_image.resize((target_px_w, target_px_h), Image.Resampling.LANCZOS)
            
            # Chuyển màu chữ ký sang xanh bút bi sau khi đã resize để giữ cạnh mịn
            data = pil_image.getdata()
            blue_pen_color = (0, 0, 255, 255)
            new_data = []
            for item in data:
                if item[0] < 50 and item[1] < 50 and item[2] < 50 and item[3] > 100:
                    new_data.append(blue_pen_color)
                else:
                    new_data.append(item)
            new_image = Image.new('RGBA', pil_image.size)
            new_image.putdata(new_data)
            
            new_image_buffer = io.BytesIO()
            new_image.save(new_image_buffer, format='PNG')
            new_image_buffer.seek(0)
            img = ImageReader(new_image_buffer)
            print("DEBUG: Image prepared and ImageReader created at target DPI")
        except Exception as prep_err:
            print(f"DEBUG: Failed to prepare high-DPI image: {prep_err}")
            try:
                img = ImageReader(io.BytesIO(decoded_data))
            except Exception:
                return False
        
        # Tính vị trí căn giữa
        x_offset = (box_width - draw_width) / 2
        y_offset = (box_height - draw_height) / 2
        
        # Vẽ nền trắng cho ô chữ ký để tránh bị đen
        canvas.setFillColor(colors.white)
        canvas.rect(x, y, box_width, box_height, fill=1, stroke=0)
        canvas.setFillColor(colors.black)  # Reset về màu đen cho text
        
        # Vẽ chữ ký với kích thước đã tính toán
        try:
            final_x = x + x_offset
            final_y = y + y_offset
            
            # Kiểm tra vị trí hợp lệ
            if final_x < 0 or final_y < 0:
                print(f"DEBUG: Invalid position: ({final_x}, {final_y})")
                return False
                
            # Kiểm tra vị trí có vượt quá trang không
            if final_x + draw_width > canvas._pagesize[0] or final_y + draw_height > canvas._pagesize[1]:
                print(f"DEBUG: Position out of page bounds")
                return False
            
            canvas.drawImage(img, final_x, final_y, width=draw_width, height=draw_height)
            print(f"DEBUG: Blue signature drawn successfully with signature fit adapter")
            print(f"DEBUG: Fitted size: {img_width}x{img_height}, Draw size: {draw_width:.1f}x{draw_height:.1f}")
            print(f"DEBUG: Position: ({final_x:.1f}, {final_y:.1f})")
            return True
        except Exception as draw_error:
            print(f"DEBUG: Failed to draw image: {draw_error}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"DEBUG: Error drawing signature with signature fit adapter: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_signature_placeholder(canvas, x, y, box_width, box_height, text="Chữ ký"):
    """Tạo placeholder cho chữ ký khi không thể hiển thị"""
    try:
        # Vẽ nền trắng
        canvas.setFillColor(colors.white)
        canvas.rect(x, y, box_width, box_height, fill=1, stroke=0)
        
        # Vẽ border
        canvas.setStrokeColor(colors.grey)
        canvas.setLineWidth(0.5)
        canvas.rect(x, y, box_width, box_height, stroke=1, fill=0)
        
        # Vẽ text placeholder
        canvas.setFillColor(colors.grey)
        canvas.setFont("DejaVuSans", 8)
        
        # Căn giữa text
        text_width = canvas.stringWidth(text, "DejaVuSans", 8)
        text_x = x + (box_width - text_width) / 2
        text_y = y + box_height / 2 + 3  # +3 để căn giữa theo chiều dọc
        
        canvas.drawString(text_x, text_y, text)
        
        # Reset màu
        canvas.setFillColor(colors.black)
        canvas.setStrokeColor(colors.black)
        
        return True
    except Exception as e:
        print(f"DEBUG: Error creating signature placeholder: {e}")
        return False

def create_overtime_pdf(attendance, buffer):
    """Tạo PDF giấy tăng ca cho một bản ghi attendance"""
    # Đăng ký fonts một lần duy nhất
    register_pdf_fonts()
    
    user = attendance.user
    employee_signature = attendance.signature if attendance.signature else None
    team_leader_signature = attendance.team_leader_signature if attendance.team_leader_signature else None
    manager_signature = attendance.manager_signature if attendance.manager_signature else None
    
    # Lấy thông tin người ký từ database
    from database.models import User
    
    # Thông tin người ký employee (người tạo đơn)
    employee_signer_name = user.name if user else "Không xác định"
    
    # Thông tin người ký team leader và manager - load relationship và xử lý an toàn
    team_leader_signer_name = "Chưa ký"
    manager_signer_name = "Chưa ký"
    
    # Kiểm tra và lấy tên người ký team leader
    if hasattr(attendance, 'team_leader_signer') and attendance.team_leader_signer:
        team_leader_signer_name = attendance.team_leader_signer.name
    elif hasattr(attendance, 'team_leader_signer_id') and attendance.team_leader_signer_id:
        # Nếu có ID nhưng relationship chưa load, query trực tiếp
        team_leader = User.query.get(attendance.team_leader_signer_id)
        if team_leader:
            team_leader_signer_name = team_leader.name
    
    # Kiểm tra và lấy tên người ký manager
    if hasattr(attendance, 'manager_signer') and attendance.manager_signer:
        manager_signer_name = attendance.manager_signer.name
    elif hasattr(attendance, 'manager_signer_id') and attendance.manager_signer_id:
        # Nếu có ID nhưng relationship chưa load, query trực tiếp
        manager = User.query.get(attendance.manager_signer_id)
        if manager:
            manager_signer_name = manager.name
    


    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 30
    y = height - margin

    # Header: Bảng 6 cột như trong hình
    header_data = [
        [
            Paragraph('<b>DMI HUẾ</b>', ParagraphStyle('h', fontName='DejaVuSans', fontSize=9, alignment=1)),
            Paragraph('<b>総務<br/>TỔNG VỤ</b>', ParagraphStyle('h', fontName='NotoSansJP', fontSize=8, alignment=1)),
            Paragraph('<b>分類番号：<br/>Số hiệu phân loại：</b>', ParagraphStyle('h', fontName='NotoSansJP', fontSize=7, alignment=1)),
            Paragraph('', ParagraphStyle('h', fontName='DejaVuSans', fontSize=8, alignment=1)),  # Ô trắng sau ô 3
            Paragraph('<b>記入 FORM<br/>NHẬP FORM</b>', ParagraphStyle('h', fontName='NotoSansJP', fontSize=8, alignment=1)),
            Paragraph('<b>Form作成：<br/>Tác thành：</b>', ParagraphStyle('h', fontName='NotoSansJP', fontSize=7, alignment=1)),
            Paragraph('', ParagraphStyle('h', fontName='DejaVuSans', fontSize=8, alignment=1)),  # Ô trắng sau ô tác thành
            Paragraph('', ParagraphStyle('h', fontName='DejaVuSans', fontSize=8, alignment=1)),  # Ô trắng thứ 2 sau ô tác thành
        ]
    ]
    
    col_widths = [60, 80, 100, 50, 80, 80, 50, 50]  # Tổng = 570, gần bằng width A4
    header_table_width = sum(col_widths)
    x_header = (width - header_table_width) / 2
    header_table = Table(header_data, colWidths=col_widths, rowHeights=25)
    header_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'DejaVuSans'),
    ]))
    header_table.wrapOn(c, width-2*margin, 30)
    header_table.drawOn(c, x_header, y-25)
    y -= 40

    # Thông tin công ty
    c.setFont("DejaVuSans", 10)
    c.drawString(margin, y, "Công ty TNHH DMI HUẾ")
    y -= 12
    c.setFont("DejaVuSans", 8)
    c.drawString(margin, y, "174 Bà Triệu- tòa nhà 4 tầng Phong Phú Plaza, phường Phú Hội, Thành phố Huế, Tỉnh Thừa Thiên Huế,Việt Nam.")
    y -= 25

    # Tiêu đề chính
    c.setFont("DejaVuSans", 14)
    c.drawCentredString(width/2, y, "GIẤY ĐỀ NGHỊ TĂNG CA/ĐI LÀM NGÀY NGHỈ")
    y -= 16
    c.setFont("NotoSansJP", 11)
    c.drawCentredString(width/2, y, "(残業/休日出勤申請書)")
    y -= 20
    c.setFont("DejaVuSans", 9)
    c.drawCentredString(width/2, y, "Nộp tại bộ phận tổng vụ")
    c.setFont("NotoSansJP-Light", 9)
    c.drawCentredString(width/2, y-10, "(総務部署で提出)")
    y -= 30

    # Phần checkbox và thông tin cá nhân
    c.setFont("DejaVuSans", 10)
    
    # Dòng checkbox
    checkbox_y = y
    c.rect(margin, checkbox_y-3, 8, 8)  # Checkbox tăng ca
    c.drawString(margin+15, checkbox_y, "Tăng ca /")
    c.setFont("NotoSansJP", 10)
    c.drawString(margin+70, checkbox_y, "残業")
    
    c.rect(margin+200, checkbox_y-3, 8, 8)  # Checkbox đi làm ngày nghỉ
    c.setFont("DejaVuSans", 10)
    c.drawString(margin+215, checkbox_y, "Đi làm ngày nghỉ /")
    c.setFont("NotoSansJP", 10)
    c.drawString(margin+320, checkbox_y, "休日出勤")
    y -= 20

    # Thông tin nhân viên
    c.setFont("NotoSansJP-Light", 10)
    c.drawString(margin, y, f"Họ tên (氏名)：{user.name}")
    c.drawString(margin+200, y, f"Nhóm (チーム)：{user.department}")
    c.drawString(margin+350, y, f"Mã NV (社員コード): {user.employee_id}")
    y -= 15
    
    c.drawString(margin, y, f"Lý do tăng ca (理由): {attendance.note}")
    y -= 15
    
    c.drawString(margin, y, "Đề nghị công ty chấp thuận cho tôi được tăng ca/đi làm vào ngày nghỉ.")
    y -= 10
    c.setFont("NotoSansJP-Light", 9)
    c.drawString(margin, y, "残業/休日出勤を許可お願いします。")
    y -= 25
    
    # Thêm khoảng cách trước khi vẽ bảng thời gian
    y -= 15

    # Bảng chấm công chi tiết
    table_y = y
    table_width = width - 2*margin
    
    # Định nghĩa style cho tiêu đề
    header_style_vn = ParagraphStyle('header_vn', fontName='DejaVuSans', fontSize=8, alignment=1)
    header_style_jp = ParagraphStyle('header_jp', fontName='NotoSansJP', fontSize=8, alignment=1)
    
    # Tạo chuỗi thời gian làm việc
    time_str = f"{attendance.check_in.strftime('%H:%M') if attendance.check_in else '-'} - {attendance.check_out.strftime('%H:%M') if attendance.check_out else '-'}"
    
    # Xác định hình thức (1 hoặc 2)
    form_type = "1" if getattr(attendance, 'holiday_type', None) == "normal" else "2"
    
    # Hàng 1: Tiếng Việt
    header_row1 = [
        Paragraph('No.', header_style_vn),
        Paragraph('NGÀY THÁNG NĂM', header_style_vn),
        Paragraph('HÌNH THỨC', header_style_vn),
        Paragraph('CA LÀM VIỆC', header_style_vn),
        Paragraph('GIỜ VÀO - GIỜ RA', header_style_vn),
        Paragraph('Thời gian nghỉ đối ứng công việc', header_style_vn),
        Paragraph('XÁC NHẬN', header_style_vn)
    ]
    # Hàng 2: Tiếng Nhật/Hán
    header_row2 = [
        Paragraph('', header_style_jp),
        Paragraph('日付', header_style_jp),
        Paragraph('種類', header_style_jp),
        Paragraph('シフト', header_style_jp),
        Paragraph('出勤時間-退勤時間', header_style_jp),
        Paragraph('業務対応時間', header_style_jp),
        Paragraph('ラボマネ承認', header_style_jp)
    ]
    # Hàng dữ liệu
    # Tách riêng thời gian và đối ứng để dễ đọc
    time_info = f"{attendance.check_in.strftime('%H:%M') if attendance.check_in else '-'} - {attendance.check_out.strftime('%H:%M') if attendance.check_out else '-'}"
    
    # Tính tổng thời gian đối ứng - chỉ hiển thị 1 giá trị duy nhất
    total_comp_time = 0.0
    
    # Cộng tất cả các loại đối ứng
    if attendance.comp_time_regular and attendance.comp_time_regular > 0:
        total_comp_time += attendance.comp_time_regular
    
    if attendance.comp_time_overtime and attendance.comp_time_overtime > 0:
        total_comp_time += attendance.comp_time_overtime
    
    if attendance.comp_time_ot_before_22 and float(attendance.comp_time_ot_before_22 or 0) > 0:
        # Chuyển đổi từ format "H:MM" sang giờ
        if ':' in str(attendance.comp_time_ot_before_22):
            hours, minutes = map(int, str(attendance.comp_time_ot_before_22).split(':'))
            total_comp_time += hours + minutes / 60
        else:
            total_comp_time += float(attendance.comp_time_ot_before_22 or 0)
    
    if attendance.comp_time_ot_after_22 and float(attendance.comp_time_ot_after_22 or 0) > 0:
        # Chuyển đổi từ format "H:MM" sang giờ
        if ':' in str(attendance.comp_time_ot_after_22):
            hours, minutes = map(int, str(attendance.comp_time_ot_after_22).split(':'))
            total_comp_time += hours + minutes / 60
        else:
            total_comp_time += float(attendance.comp_time_ot_after_22 or 0)
    
    # Định dạng tổng thời gian đối ứng
    if total_comp_time > 0:
        comp_time_display = attendance._format_hours_minutes(total_comp_time)
    else:
        comp_time_display = "0:00"
    
    # Tạo dữ liệu hàng với thông tin rõ ràng
    row_data = [
        '1',
        attendance.date.strftime('%d/%m/%Y'),
        form_type,
        attendance.shift_code or '-',
        time_info,
        comp_time_display,  # Chỉ hiển thị 1 giá trị tổng thời gian đối ứng
        ''
    ]
    
    table_data = [header_row1, header_row2, row_data]
    col_widths = [30, 80, 50, 65, 80, 110, 70]  # Tổng nhỏ hơn width, luôn còn margin hai bên
    row_heights = [40, 14, 18]  # Hàng dữ liệu bình thường vì chỉ hiển thị 1 giá trị
    
    detail_table_width = sum(col_widths)
    x_detail = (width - detail_table_width) / 2
    table = Table(table_data, colWidths=col_widths, rowHeights=row_heights)
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'DejaVuSans'),
        ('FONTNAME', (0,1), (-1,1), 'NotoSansJP'),
        ('FONTSIZE', (0,0), (-1,1), 8),
        ('FONTSIZE', (0,2), (-1,2), 9),
        # Xóa dòng kẻ ngang giữa hàng 0 và 1
        ('LINEBELOW', (0,0), (-1,0), 0, colors.white),
    ]))
    table.wrapOn(c, width-2*margin, 50)
    table.drawOn(c, x_detail, table_y - 46)
    y = table_y - 46 - 36  # cập nhật y cho phần tiếp theo
    
    # Ghi chú dưới bảng
    note_sections = [
        ("DejaVuSans", 8, "* Ghi chú: Tại cột Hình thức: Tăng ca ngày bình thường ghi số 1 Đi làm ngày nghỉ, tăng ca ghi số 2"),
        ("NotoSansJP-Light", 8, "備考：平日の残業の場合：1番を記入してください。 休日出勤の場合：2番を記入してください。"),
        ("DejaVuSans", 8, "*Về việc nghỉ giải lao (60 phút) ngày thường trong tuần, trường hợp nếu nghỉ dài hơn vì đối ứng công việc ：Hãy nộp đơn cho bộ phận văn phòng."),
        ("NotoSansJP-Light", 8, "通常（1の場合）の昼休憩（60分）に、休憩途中で業務対応する場合、申請をして下さい。"),
        ("DejaVuSans", 8, "*Trong trường hợp không xin phép trước, thì tăng ca và đi làm ngày nghỉ không được chấp nhận."),
        ("DejaVuSans", 8, "Phải ghi giấy tăng ca sau khi tăng ca (chậm nhất là ngày mai) ,sang ngày mốt ghi tăng ca thì không được chấp nhận."),
        ("NotoSansJP-Light", 8, "※1分単位で申請して下さい。申請をしない限り、残業と休日出勤は反映されません。"),
        ("NotoSansJP-Light", 8, "必ず、残業をした日に申請すること。（次の日までの申請は認めますが、それ以外の申請は認めません）")
    ]
    max_note_width = width - 2*margin - 10
    for i, (font_name, font_size, text) in enumerate(note_sections):
        lines = wrap_text(text, font_name, font_size, max_note_width, c)
        for line in lines:
            c.setFont(font_name, font_size)
            c.drawString(margin, y, line)
            y -= font_size + 1
        # Thêm dòng trắng sau mỗi đoạn bắt đầu bằng * (trừ đoạn cuối)
        if text.startswith('*') and i < len(note_sections)-1:
            y -= font_size + 1
    
    # Thêm khoảng cách giữa phần ghi chú và dòng ngày tháng
    y -= 25
    # Ngày tháng - Đặt ở vị trí cao hơn để không bị đè
    date_y = y + 20  # Đặt dòng ngày tháng cao hơn
    c.setFont("DejaVuSans", 10)
    c.drawRightString(width-margin, date_y, f"Huế, ngày {attendance.date.day} tháng {attendance.date.month} năm {attendance.date.year}")
    y -= 10  # Đẩy dòng ngày tháng xuống thấp hơn
    y -= 95  # Tăng thêm khoảng cách để không bị đè lên phần ghi chú và dòng ngày tháng
    
    # --- Căn chỉnh lại phần chữ ký và tiêu đề phía trên ---
    # Số ô và kích thước - GIẢM KÍCH THƯỚC Ô ĐỂ VỪA TRANG VÀ CÓ BORDER
    num_boxes = 3
    box_width = 140  # Giảm từ 180 xuống 140 để vừa trang
    box_height = 70  # Giảm từ 80 xuống 70 để cân đối
    box_spacing = 30  # Giảm khoảng cách từ 40 xuống 30 để vừa trang
    total_width = num_boxes * box_width + (num_boxes - 1) * box_spacing
    start_x = (width - total_width) / 2
    box_y = y  # y là vị trí đáy các ô
    label_font_size = 10
    sublabel_font_size = 8
    # Tiêu đề các ô
    box_titles = [
        ("Quản lí", "ラボマネジャー"),
        ("Cấp trên trực tiếp", "□室長　□リーダー　□他"),
        ("Người xin phép", "申請者")
    ]
    # Vẽ tiêu đề và sublabel căn giữa trên mỗi ô
    for i, (title, sublabel) in enumerate(box_titles):
        x = start_x + i * (box_width + box_spacing)
        # Căn giữa tiêu đề
        c.setFont("DejaVuSans", label_font_size)
        c.drawCentredString(x + box_width/2, box_y + box_height + 22, title)
        c.setFont("NotoSansJP-Light", sublabel_font_size)
        c.drawCentredString(x + box_width/2, box_y + box_height + 10, sublabel)
    # Vẽ các ô chữ ký với border - SẼ ĐƯỢC VẼ LẠI SAU KHI VẼ CHỮ KÝ
    signature_boxes = []
    for i in range(num_boxes):
        x = start_x + i * (box_width + box_spacing)
        signature_boxes.append((x, box_y, box_width, box_height))
    # Hiển thị chữ ký hoặc (chưa ký) căn giữa trong từng ô
    # Quản lý
    x0 = start_x
    signature_area_height = box_height - 18  # Giảm vùng chữ ký (để lại 18px cho tên)
    signature_y = box_y + 18  # Chữ ký ở phần trên (cách đáy 18px)
    signature_center_y = signature_y + signature_area_height/2 - 8/2  # Căn giữa chữ ký
    name_y = box_y + 8  # Tên người ký ở phần dưới (cách đáy 8px)
    
    if manager_signature:
        print(f"DEBUG: Processing manager signature for PDF")
        debug_signature_data(manager_signature, "manager")
        success = draw_signature_with_proper_scaling(c, manager_signature, x0, signature_y, box_width, signature_area_height)
        if not success:
            print(f"DEBUG: Failed to draw manager signature, creating placeholder")
            create_signature_placeholder(c, x0, signature_y, box_width, signature_area_height, "Lỗi hiển thị")
    else:
        c.setFont("DejaVuSans", 8)
        c.drawCentredString(x0 + box_width/2, signature_center_y, "(chưa ký)")
    
    # Thêm tên người ký quản lý bên trong ô chữ ký (phía dưới chữ ký)
    c.setFont("DejaVuSans", 8)
    c.drawCentredString(x0 + box_width/2, name_y, manager_signer_name)
    
    # Trưởng nhóm
    x1 = start_x + 1 * (box_width + box_spacing)
    
    if team_leader_signature:
        print(f"DEBUG: Processing team leader signature for PDF")
        debug_signature_data(team_leader_signature, "team_leader")
        success = draw_signature_with_proper_scaling(c, team_leader_signature, x1, signature_y, box_width, signature_area_height)
        if not success:
            print(f"DEBUG: Failed to draw team leader signature, creating placeholder")
            create_signature_placeholder(c, x1, signature_y, box_width, signature_area_height, "Lỗi hiển thị")
    else:
        c.setFont("DejaVuSans", 8)
        c.drawCentredString(x1 + box_width/2, signature_center_y, "(chưa ký)")
    
    # Thêm tên người ký trưởng nhóm bên trong ô chữ ký (phía dưới chữ ký)
    c.setFont("DejaVuSans", 8)
    c.drawCentredString(x1 + box_width/2, name_y, team_leader_signer_name)
    
    # Nhân viên
    x2 = start_x + 2 * (box_width + box_spacing)
    
    if employee_signature:
        print(f"DEBUG: Processing employee signature for PDF")
        debug_signature_data(employee_signature, "employee")
        success = draw_signature_with_proper_scaling(c, employee_signature, x2, signature_y, box_width, signature_area_height)
        if not success:
            print(f"DEBUG: Failed to draw employee signature, creating placeholder")
            create_signature_placeholder(c, x2, signature_y, box_width, signature_area_height, "Lỗi hiển thị")
    else:
        c.setFont("DejaVuSans", 8)
        c.drawCentredString(x2 + box_width/2, signature_center_y, "(chưa ký)")
    
    # Thêm tên người ký nhân viên bên trong ô chữ ký (phía dưới chữ ký)
    c.setFont("DejaVuSans", 8)
    c.drawCentredString(x2 + box_width/2, name_y, employee_signer_name)
    
    # Vẽ lại border cho tất cả các ô chữ ký sau khi đã vẽ chữ ký
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    for x, y, w, h in signature_boxes:
        c.rect(x, y, w, h, stroke=1, fill=0)
    
    c.save()

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash('Vui lòng nhập email đã đăng ký!', 'error')
            return render_template('forgot_password.html')
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Không tìm thấy tài khoản với email này!', 'error')
            return render_template('forgot_password.html')
        # Tạo token
        import secrets
        token = secrets.token_urlsafe(48)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
        db.session.add(reset_token)
        db.session.commit()
        # Gửi email
        reset_link = url_for('reset_password', token=token, _external=True)
        email_sent = send_reset_email(user.email, user.name, reset_link)
        if email_sent:
            flash('Đã gửi email hướng dẫn đặt lại mật khẩu. Vui lòng kiểm tra hộp thư!', 'success')
        else:
            flash('Không thể gửi email. Vui lòng liên hệ quản trị viên để được hỗ trợ.', 'error')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if not reset_token or reset_token.is_expired():
        flash('Link đặt lại mật khẩu không hợp lệ hoặc đã hết hạn!', 'error')
        return redirect(url_for('login'))
    user = User.query.get(reset_token.user_id)
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        if not password or not confirm or password != confirm:
            flash('Mật khẩu không khớp hoặc không hợp lệ!', 'error')
            return render_template('reset_password.html', token=token)
        user.set_password(password)
        db.session.commit()
        reset_token.used = True
        db.session.commit()
        flash('Đặt lại mật khẩu thành công! Bạn có thể đăng nhập lại.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)

def send_reset_email(to_email, to_name, reset_link):
    # Cấu hình SMTP từ config
    smtp_server = app.config['SMTP_SERVER']
    smtp_port = app.config['SMTP_PORT']
    smtp_user = app.config['SMTP_USER']
    smtp_password = app.config['SMTP_PASSWORD']
    from_email = app.config['MAIL_FROM']
    
    # Kiểm tra và đặt giá trị mặc định cho from_email nếu không có
    if not from_email:
        from_email = smtp_user if smtp_user else 'noreply@dmi.com'
    
    subject = 'Đặt lại mật khẩu hệ thống chấm công DMI'
    
    # Plain text version
    text_body = f"""Xin chào {to_name},

Bạn vừa yêu cầu đặt lại mật khẩu cho tài khoản hệ thống chấm công DMI.

Vui lòng copy link dưới đây vào trình duyệt để đặt lại mật khẩu (có hiệu lực trong 1 giờ):

{reset_link}

Lưu ý: Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.

Trân trọng,
Hệ thống chấm công DMI"""
    
    # HTML version
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Đặt lại mật khẩu</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #f9f9f9; padding: 30px; border-radius: 10px; border: 1px solid #ddd;">
            <h2 style="color: #1976d2; margin-bottom: 20px;">Đặt lại mật khẩu hệ thống chấm công DMI</h2>
            
            <p>Xin chào <strong>{to_name}</strong>,</p>
            
            <p>Bạn vừa yêu cầu đặt lại mật khẩu cho tài khoản hệ thống chấm công DMI.</p>
            
            <p>Vui lòng nhấn vào link dưới đây để đặt lại mật khẩu (có hiệu lực trong 1 giờ):</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" style="background-color: #1976d2; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Đặt lại mật khẩu</a>
            </div>
            
            <p style="font-size: 14px; color: #666;">Hoặc copy link này vào trình duyệt:</p>
            <p style="word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-size: 12px;">{reset_link}</p>
            
            <p style="color: #d32f2f; font-size: 14px;"><strong>Lưu ý:</strong> Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.</p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            
            <p style="color: #666; font-size: 14px;">Trân trọng,<br>
            <strong>Hệ thống chấm công DMI</strong></p>
        </div>
    </body>
    </html>
    """
    
    # Kiểm tra cấu hình SMTP trước khi gửi email
    if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
        print('SMTP configuration incomplete. Cannot send email.')
        return False
    
    # Create multipart message
    from email.mime.multipart import MIMEMultipart
    msg = MIMEMultipart('alternative')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = formataddr((str(Header('DMI Attendance', 'utf-8')), from_email))
    msg['To'] = to_email
    
    # Attach both plain text and HTML versions
    text_part = MIMEText(text_body, 'plain', 'utf-8')
    html_part = MIMEText(html_body, 'html', 'utf-8')
    
    msg.attach(text_part)
    msg.attach(html_part)
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print('Email send error:', e)
        # Không raise để không lộ thông tin cho user
        return False

# Đổi mật khẩu khi đã đăng nhập
@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user_from_session()
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm = request.form.get('confirm')
        if not user.check_password(old_password):
            flash('Mật khẩu cũ không đúng!', 'error')
            return render_template('change_password.html')
        if not new_password or new_password != confirm:
            flash('Mật khẩu mới không hợp lệ hoặc không khớp!', 'error')
            return render_template('change_password.html')
        user.set_password(new_password)
        db.session.commit()
        flash('Đổi mật khẩu thành công!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('change_password.html')

@app.route('/api/signature/debug/<int:attendance_id>')
@require_admin
def debug_signature(attendance_id):
    """Debug endpoint để kiểm tra chữ ký trong database"""
    try:
        attendance = Attendance.query.get(attendance_id)
        if not attendance:
            return jsonify({'error': 'Attendance not found'}), 404
        
        debug_info = {
            'attendance_id': attendance_id,
            'employee_signature': {
                'exists': bool(attendance.signature),
                'length': len(attendance.signature) if attendance.signature else 0,
                'type': type(attendance.signature).__name__ if attendance.signature else None,
                'starts_with_data_image': attendance.signature.startswith('data:image') if attendance.signature else False,
                'processed': process_signature_for_pdf(attendance.signature) is not None if attendance.signature else False
            },
            'team_leader_signature': {
                'exists': bool(attendance.team_leader_signature),
                'length': len(attendance.team_leader_signature) if attendance.team_leader_signature else 0,
                'type': type(attendance.team_leader_signature).__name__ if attendance.team_leader_signature else None,
                'starts_with_data_image': attendance.team_leader_signature.startswith('data:image') if attendance.team_leader_signature else False,
                'processed': process_signature_for_pdf(attendance.team_leader_signature) is not None if attendance.team_leader_signature else False
            },
            'manager_signature': {
                'exists': bool(attendance.manager_signature),
                'length': len(attendance.manager_signature) if attendance.manager_signature else 0,
                'type': type(attendance.manager_signature).__name__ if attendance.manager_signature else None,
                'starts_with_data_image': attendance.manager_signature.startswith('data:image') if attendance.manager_signature else False,
                'processed': process_signature_for_pdf(attendance.manager_signature) is not None if attendance.manager_signature else False
            }
        }
        
        # Thêm debug chi tiết cho từng chữ ký
        if attendance.signature:
            debug_signature_data(attendance.signature, "employee_debug")
        if attendance.team_leader_signature:
            debug_signature_data(attendance.team_leader_signature, "team_leader_debug")
        if attendance.manager_signature:
            debug_signature_data(attendance.manager_signature, "manager_debug")
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Thêm hàm debug chữ ký
def debug_signature_data(signature_data, source="unknown"):
    """Debug chi tiết dữ liệu chữ ký"""
    print(f"=== DEBUG SIGNATURE DATA ({source}) ===")
    if not signature_data:
        print("Signature data is None or empty")
        return
    
    print(f"Type: {type(signature_data)}")
    print(f"Length: {len(signature_data)}")
    
    if isinstance(signature_data, str):
        print(f"Starts with 'data:image': {signature_data.startswith('data:image')}")
        print(f"First 100 chars: {signature_data[:100]}")
        print(f"Last 100 chars: {signature_data[-100:]}")
        
        # Kiểm tra có phải base64 không
        try:
            decoded = base64.b64decode(signature_data)
            print(f"Valid base64: Yes, decoded length: {len(decoded)}")
        except:
            print("Valid base64: No")
            
            # Thử giải mã nếu có thể
            try:
                decrypted = signature_manager.decrypt_signature(signature_data)
                if decrypted:
                    print(f"Decrypted successfully, length: {len(decrypted)}")
                    print(f"Decrypted starts with 'data:image': {decrypted.startswith('data:image')}")
                else:
                    print("Decryption failed or returned empty")
            except Exception as e:
                print(f"Decryption error: {e}")
    
    print("=== END DEBUG ===")

@app.route('/personal-signature', methods=['GET', 'POST'])
@login_required
def personal_signature():
    """Trang quản lý chữ ký cá nhân"""
    if request.method == 'POST':
        signature = request.form.get('signature')
        if signature:
            # 使用签名处理器优化签名质量
            processed_signature = signature_manager.process_signature_for_display(signature)
            
            user = get_user_from_session()
            user.personal_signature = processed_signature
            db.session.commit()
            
            # 记录签名操作
            signature_manager.log_signature_action(
                user_id=user.id,
                action='UPDATE_PERSONAL',
                signature_type='personal_signature'
            )
            
            flash('Đã cập nhật chữ ký cá nhân thành công! Hệ thống đã tự động tối ưu hóa chất lượng chữ ký.', 'success')
            return redirect(url_for('personal_signature'))
    
    user = get_user_from_session()
    return render_template('personal_signature.html', user=user)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Trang cài đặt thông tin cá nhân và chữ ký"""
    print("DEBUG: Settings route accessed")
    print("DEBUG: Session user_id:", session.get('user_id'))
    print("DEBUG: Session keys:", list(session.keys()))
    
    if 'user_id' not in session:
        print("DEBUG: No user_id in session, redirecting to login")
        return redirect(url_for('login'))
    
    user = get_user_from_session()
    if not user:
        print("DEBUG: User not found, redirecting to login")
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('login'))
    
    # Kiểm tra user có active không
    if not user.is_active:
        session.clear()
        flash('Tài khoản đã bị khóa!', 'error')
        return redirect(url_for('login'))
    
    # Kiểm tra session timeout
    if check_session_timeout():
        flash('Phiên đăng nhập đã hết hạn!', 'error')
        return redirect(url_for('login'))
    
    # Cập nhật thời gian hoạt động cuối
    update_session_activity()
    
    print("DEBUG: User found:", user.name)
    
    if request.method == 'POST':
        # Chỉ xử lý cập nhật chữ ký cá nhân
        signature = request.form.get('signature')
        
        # Cập nhật chữ ký nếu có
        if signature:
            user.personal_signature = signature
            try:
                db.session.commit()
                flash('Lưu chữ ký thành công!', 'success')
                return redirect(url_for('settings'))
            except Exception as e:
                db.session.rollback()
                flash('Đã xảy ra lỗi khi lưu chữ ký', 'error')
        else:
            flash('Chưa có chữ ký để lưu', 'error')
    
    return render_template('settings.html', user=user)

@app.route('/signature-test', methods=['GET', 'POST'])
def signature_test():
    """Trang test hiển thị chữ ký cho cả 3 vai trò"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = get_user_from_session()
    if not user:
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('login'))
    
    # Kiểm tra user có active không
    if not user.is_active:
        session.clear()
        flash('Tài khoản đã bị khóa!', 'error')
        return redirect(url_for('login'))
    
    # Kiểm tra session timeout
    if check_session_timeout():
        flash('Phiên đăng nhập đã hết hạn!', 'error')
        return redirect(url_for('login'))
    
    # Cập nhật thời gian hoạt động cuối
    update_session_activity()
    
    if request.method == 'POST':
        # Xử lý lưu test chữ ký
        employee_signature = request.form.get('employee_signature')
        team_leader_signature = request.form.get('team_leader_signature')
        manager_signature = request.form.get('manager_signature')
        test_date = request.form.get('test_date')
        test_note = request.form.get('test_note', 'Test hiển thị chữ ký')
        
        # Lưu vào session để sử dụng cho PDF
        session['test_signatures'] = {
            'employee': employee_signature,
            'team_leader': team_leader_signature,
            'manager': manager_signature,
            'date': test_date,
            'note': test_note
        }
        
        flash('Đã lưu test chữ ký thành công!', 'success')
        return redirect(url_for('signature_test'))
    
    return render_template('signature_test.html', user=user, today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/signature-test/download-pdf', methods=['POST'])
def download_signature_test_pdf():
    """Tải PDF test chữ ký"""
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    
    user = get_user_from_session()
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    
    # Lấy dữ liệu chữ ký từ form
    employee_signature = request.form.get('employee_signature')
    team_leader_signature = request.form.get('team_leader_signature')
    manager_signature = request.form.get('manager_signature')
    test_date = request.form.get('test_date')
    test_note = request.form.get('test_note', 'Test hiển thị chữ ký')
    
    # Tạo buffer cho PDF
    buffer = io.BytesIO()
    
    # Đăng ký font
    register_pdf_fonts()
    
    # Tạo PDF
    canvas_obj = canvas.Canvas(buffer, pagesize=A4)
    canvas_obj.setTitle('Test Chữ ký - DMI Attendance')
    
    # Header
    canvas_obj.setFont('NotoSansJP-Bold', 18)
    canvas_obj.drawString(50, 800, 'TEST HIỂN THỊ CHỮ KÝ')
    canvas_obj.setFont('NotoSansJP-Regular', 12)
    canvas_obj.drawString(50, 780, f'Ngày test: {test_date}')
    canvas_obj.drawString(50, 760, f'Ghi chú: {test_note}')
    canvas_obj.drawString(50, 740, f'Người tạo: {user.name}')
    
    # Vẽ đường kẻ
    canvas_obj.line(50, 720, 550, 720)
    
    # Chữ ký Nhân viên
    y_position = 680
    canvas_obj.setFont('NotoSansJP-Bold', 14)
    canvas_obj.drawString(50, y_position, '1. Chữ ký Nhân viên:')
    
    if employee_signature:
        try:
            draw_signature_with_proper_scaling(canvas_obj, employee_signature, 50, y_position - 80, 200, 60)
        except Exception as e:
            print(f"Error drawing employee signature: {e}")
            create_signature_placeholder(canvas_obj, 50, y_position - 80, 200, 60, "Lỗi hiển thị")
    else:
        create_signature_placeholder(canvas_obj, 50, y_position - 80, 200, 60, "Chưa có chữ ký")
    
    # Chữ ký Trưởng nhóm
    y_position = 540
    canvas_obj.setFont('NotoSansJP-Bold', 14)
    canvas_obj.drawString(50, y_position, '2. Chữ ký Trưởng nhóm:')
    
    if team_leader_signature:
        try:
            draw_signature_with_proper_scaling(canvas_obj, team_leader_signature, 50, y_position - 80, 200, 60)
        except Exception as e:
            print(f"Error drawing team leader signature: {e}")
            create_signature_placeholder(canvas_obj, 50, y_position - 80, 200, 60, "Lỗi hiển thị")
    else:
        create_signature_placeholder(canvas_obj, 50, y_position - 80, 200, 60, "Chưa có chữ ký")
    
    # Chữ ký Quản lý
    y_position = 400
    canvas_obj.setFont('NotoSansJP-Bold', 14)
    canvas_obj.drawString(50, y_position, '3. Chữ ký Quản lý:')
    
    if manager_signature:
        try:
            draw_signature_with_proper_scaling(canvas_obj, manager_signature, 50, y_position - 80, 200, 60)
        except Exception as e:
            print(f"Error drawing manager signature: {e}")
            create_signature_placeholder(canvas_obj, 50, y_position - 80, 200, 60, "Lỗi hiển thị")
    else:
        create_signature_placeholder(canvas_obj, 50, y_position - 80, 200, 60, "Chưa có chữ ký")
    
    # Footer
    y_position = 200
    canvas_obj.line(50, y_position, 550, y_position)
    canvas_obj.setFont('NotoSansJP-Regular', 10)
    canvas_obj.drawString(50, y_position - 20, f'Được tạo bởi: {user.name} - {user.employee_id}')
    canvas_obj.drawString(50, y_position - 40, f'Thời gian: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')
    
    canvas_obj.save()
    buffer.seek(0)
    
    # Tạo response
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=test_chu_ky_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return response

@app.route('/settings/test-signature-pdf', methods=['POST'])
def test_signature_pdf():
    """Tạo PDF test chữ ký cá nhân trên mẫu phiếu tăng ca thực tế"""
    print("DEBUG: test_signature_pdf route accessed")
    print("DEBUG: Session user_id:", session.get('user_id'))
    print("DEBUG: Form data:", request.form)
    
    if 'user_id' not in session:
        print("DEBUG: No user_id in session")
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    
    user = get_user_from_session()
    if not user:
        print("DEBUG: User not found")
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    
    signature = request.form.get('signature')
    if not signature:
        print("DEBUG: No signature provided")
        return jsonify({'error': 'Chưa có chữ ký'}), 400
    
    print("DEBUG: Signature length:", len(signature) if signature else 0)
    try:
        # Tạo buffer cho PDF
        buffer = io.BytesIO()
        register_pdf_fonts()
        canvas_obj = canvas.Canvas(buffer, pagesize=A4)
        canvas_obj.setTitle('Test Chữ ký trên Phiếu Tăng Ca - DMI Attendance')
        print("DEBUG: PDF canvas created successfully")
        
        # Tạo mẫu phiếu tăng ca với chữ ký test
        create_overtime_test_pdf(canvas_obj, user, signature)
        
        canvas_obj.save()
        buffer.seek(0)
        print("DEBUG: PDF created successfully, size:", len(buffer.getvalue()))
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=test_phieu_tang_ca_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        return response
    except Exception as e:
        print(f"DEBUG: Error creating PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Lỗi tạo PDF: {str(e)}'}), 500

def create_overtime_test_pdf(canvas_obj, user, signature):
    """Tạo PDF test với mẫu phiếu tăng ca thực tế"""
    width, height = A4
    margin = 30
    y = height - margin

    # Header: Bảng 6 cột như trong mẫu thực tế - sử dụng font an toàn
    header_data = [
        [
            Paragraph('<b>DMI HUẾ</b>', ParagraphStyle('h', fontName='DejaVuSans', fontSize=9, alignment=1)),
            Paragraph('<b>総務<br/>TONG VU</b>', ParagraphStyle('h', fontName='NotoSansJP', fontSize=8, alignment=1)),
            Paragraph('<b>分類番号：<br/>So hieu phan loai：</b>', ParagraphStyle('h', fontName='NotoSansJP', fontSize=7, alignment=1)),
            Paragraph('', ParagraphStyle('h', fontName='DejaVuSans', fontSize=8, alignment=1)),
            Paragraph('<b>記入 FORM<br/>NHAP FORM</b>', ParagraphStyle('h', fontName='NotoSansJP', fontSize=8, alignment=1)),
            Paragraph('<b>Form作成：<br/>Tac thanh：</b>', ParagraphStyle('h', fontName='NotoSansJP', fontSize=7, alignment=1)),
            Paragraph('', ParagraphStyle('h', fontName='DejaVuSans', fontSize=8, alignment=1)),
            Paragraph('', ParagraphStyle('h', fontName='DejaVuSans', fontSize=8, alignment=1)),
        ]
    ]
    
    col_widths = [60, 80, 100, 50, 80, 80, 50, 50]
    header_table_width = sum(col_widths)
    x_header = (width - header_table_width) / 2
    header_table = Table(header_data, colWidths=col_widths, rowHeights=25)
    header_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'DejaVuSans'),
    ]))
    header_table.wrapOn(canvas_obj, width-2*margin, 30)
    header_table.drawOn(canvas_obj, x_header, y-25)
    y -= 40

    # Thông tin công ty
    canvas_obj.setFont("DejaVuSans", 10)
    canvas_obj.drawString(margin, y, "Công ty TNHH DMI HUẾ")
    y -= 12
    canvas_obj.setFont("DejaVuSans", 8)
    canvas_obj.drawString(margin, y, "174 Bà Triệu- tòa nhà 4 tầng Phong Phú Plaza, phường Phú Hội, Thành phố Huế, Tỉnh Thừa Thiên Huế,Việt Nam.")
    y -= 25

    # Tiêu đề chính
    canvas_obj.setFont("DejaVuSans", 14)
    canvas_obj.drawCentredString(width/2, y, "GIẤY ĐỀ NGHỊ TĂNG CA/ĐI LÀM NGÀY NGHỈ")
    y -= 16
    canvas_obj.setFont("NotoSansJP", 11)
    canvas_obj.drawCentredString(width/2, y, "(残業/休日出勤申請書)")
    y -= 20
    canvas_obj.setFont("DejaVuSans", 9)
    canvas_obj.drawCentredString(width/2, y, "Nộp tại bộ phận tổng vụ")
    canvas_obj.setFont("NotoSansJP-Light", 9)
    canvas_obj.drawCentredString(width/2, y-10, "(総務部署で提出)")
    y -= 30

    # Phần checkbox và thông tin cá nhân
    canvas_obj.setFont("DejaVuSans", 10)
    
    # Dòng checkbox
    checkbox_y = y
    canvas_obj.rect(margin, checkbox_y-3, 8, 8)  # Checkbox tăng ca
    canvas_obj.drawString(margin+15, checkbox_y, "Tăng ca /")
    canvas_obj.setFont("NotoSansJP", 10)
    canvas_obj.drawString(margin+70, checkbox_y, "残業")
    
    canvas_obj.rect(margin+200, checkbox_y-3, 8, 8)  # Checkbox đi làm ngày nghỉ
    canvas_obj.setFont("DejaVuSans", 10)
    canvas_obj.drawString(margin+215, checkbox_y, "Đi làm ngày nghỉ /")
    canvas_obj.setFont("NotoSansJP", 10)
    canvas_obj.drawString(margin+320, checkbox_y, "休日出勤")
    y -= 20

    # Thông tin nhân viên
    canvas_obj.setFont("DejaVuSans", 10)
    canvas_obj.drawString(margin, y, f"Họ tên: {user.name}")
    canvas_obj.drawString(margin+200, y, f"Nhóm: {user.department}")
    canvas_obj.drawString(margin+350, y, f"Mã NV: {user.employee_id}")
    y -= 15
    canvas_obj.drawString(margin, y, f"Lý do tăng ca: Test hiển thị chữ ký trên phiếu tăng ca")
    y -= 15
    canvas_obj.drawString(margin, y, "Đề nghị công ty chấp thuận cho tôi được tăng ca/đi làm vào ngày nghỉ.")
    y -= 10
    canvas_obj.setFont("NotoSansJP-Light", 9)
    canvas_obj.drawString(margin, y, "残業/休日出勤を許可お願いします。")
    y -= 25
    
    # Thêm khoảng cách trước khi vẽ bảng thời gian
    y -= 15

    # Bảng chấm công chi tiết
    table_y = y
    table_width = width - 2*margin
    
    # Định nghĩa style cho tiêu đề
    header_style_vn = ParagraphStyle('header_vn', fontName='DejaVuSans', fontSize=8, alignment=1)
    header_style_jp = ParagraphStyle('header_jp', fontName='NotoSansJP', fontSize=8, alignment=1)
    
    # Tạo chuỗi thời gian làm việc mẫu
    time_str = "18:00 - 22:00"
    
    # Hàng 1: Tiếng Việt
    header_row1 = [
        Paragraph('No.', header_style_vn),
        Paragraph('NGÀY THÁNG NĂM', header_style_vn),
        Paragraph('HÌNH THỨC', header_style_vn),
        Paragraph('CA LÀM VIỆC', header_style_vn),
        Paragraph('GIỜ VÀO - GIỜ RA', header_style_vn),
        Paragraph('Thời gian nghỉ đối ứng công việc', header_style_vn),
        Paragraph('XÁC NHẬN', header_style_vn)
    ]
    # Hàng 2: Tiếng Nhật/Hán
    header_row2 = [
        Paragraph('', header_style_jp),
        Paragraph('日付', header_style_jp),
        Paragraph('種類', header_style_jp),
        Paragraph('シフト', header_style_jp),
        Paragraph('出勤時間-退勤時間', header_style_jp),
        Paragraph('業務対応時間', header_style_jp),
        Paragraph('ラボマネ承認', header_style_jp)
    ]
    # Hàng dữ liệu mẫu - chỉ hiển thị giá trị thời gian
    row_data = [
        '1',
        '15/07/2025',
        '1',
        'Tăng ca',
        time_str,
        '3:30',  # Chỉ hiển thị 1 giá trị tổng thời gian đối ứng (0:30 + 2:00 + 1:00 = 3:30)
        ''
    ]
    
    table_data = [header_row1, header_row2, row_data]
    col_widths = [30, 80, 50, 65, 80, 110, 70]
    row_heights = [40, 14, 18]  # Hàng dữ liệu bình thường vì chỉ hiển thị 1 giá trị
    
    detail_table_width = sum(col_widths)
    x_detail = (width - detail_table_width) / 2
    table = Table(table_data, colWidths=col_widths, rowHeights=row_heights)
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'DejaVuSans'),
        ('FONTNAME', (0,1), (-1,1), 'NotoSansJP'),
        ('FONTSIZE', (0,0), (-1,1), 8),
        ('FONTSIZE', (0,2), (-1,2), 9),
        ('LINEBELOW', (0,0), (-1,0), 0, colors.white),
    ]))
    table.wrapOn(canvas_obj, width-2*margin, 50)
    table.drawOn(canvas_obj, x_detail, table_y - 46)
    y = table_y - 46 - 36
    
    # Ghi chú dưới bảng
    note_sections = [
        ("DejaVuSans", 8, "* Ghi chú: Tại cột Hình thức: Tăng ca ngày bình thường ghi số 1 Đi làm ngày nghỉ, tăng ca ghi số 2"),
        ("NotoSansJP-Light", 8, "備考：平日の残業の場合：1番を記入してください。 休日出勤の場合：2番を記入してください。"),
        ("DejaVuSans", 8, "*Về việc nghỉ giải lao (60 phút) ngày thường trong tuần, trường hợp nếu nghỉ dài hơn vì đối ứng công việc ：Hãy nộp đơn cho bộ phận văn phòng."),
        ("NotoSansJP-Light", 8, "通常（1の場合）の昼休憩（60分）に、休憩途中で業務対応する場合、申請をして下さい。"),
        ("DejaVuSans", 8, "*Trong trường hợp không xin phép trước, thì tăng ca và đi làm ngày nghỉ không được chấp nhận."),
        ("DejaVuSans", 8, "Phải ghi giấy tăng ca sau khi tăng ca (chậm nhất là ngày mai) ,sang ngày mốt ghi tăng ca thì không được chấp nhận."),
        ("NotoSansJP-Light", 8, "※1分単位で申請して下さい。申請をしない限り、残業と休日出勤は反映されません。"),
        ("NotoSansJP-Light", 8, "必ず、残業をした日に申請すること。（次の日までの申請は認めますが、それ以外の申請は認めません）")
    ]
    max_note_width = width - 2*margin - 10
    for i, (font_name, font_size, text) in enumerate(note_sections):
        lines = wrap_text(text, font_name, font_size, max_note_width, canvas_obj)
        for line in lines:
            canvas_obj.setFont(font_name, font_size)
            canvas_obj.drawString(margin, y, line)
            y -= font_size + 1
        if text.startswith('*') and i < len(note_sections)-1:
            y -= font_size + 1
    
    # Thêm khoảng cách giữa phần ghi chú và dòng ngày tháng
    y -= 25
    # Ngày tháng - Đặt ở vị trí cao hơn để không bị đè
    date_y = y + 20  # Đặt dòng ngày tháng cao hơn
    canvas_obj.setFont("DejaVuSans", 10)
    canvas_obj.drawRightString(width-margin, date_y, f"Huế, ngày 15 tháng 07 năm 2025")
    y -= 10
    y -= 95  # Tăng thêm khoảng cách để không bị đè lên phần ghi chú và dòng ngày tháng
    
    # Số ô và kích thước chữ ký - GIẢM KÍCH THƯỚC Ô ĐỂ VỪA TRANG VÀ CÓ BORDER
    num_boxes = 3
    box_width = 140  # Giảm từ 180 xuống 140 để vừa trang
    box_height = 70  # Giảm từ 80 xuống 70 để cân đối
    box_spacing = 30  # Giảm khoảng cách từ 40 xuống 30 để vừa trang
    total_width = num_boxes * box_width + (num_boxes - 1) * box_spacing
    start_x = (width - total_width) / 2
    box_y = y
    label_font_size = 10
    sublabel_font_size = 8
    
    # Tiêu đề các ô
    box_titles = [
        ("Quản lí", "ラボマネジャー"),
        ("Cấp trên trực tiếp", "□室長　□リーダー　□他"),
        ("Người xin phép", "申請者")
    ]
    
    # Vẽ tiêu đề và sublabel căn giữa trên mỗi ô
    for i, (title, sublabel) in enumerate(box_titles):
        x = start_x + i * (box_width + box_spacing)
        canvas_obj.setFont("DejaVuSans", label_font_size)
        canvas_obj.drawCentredString(x + box_width/2, box_y + box_height + 22, title)
        canvas_obj.setFont("NotoSansJP-Light", sublabel_font_size)
        canvas_obj.drawCentredString(x + box_width/2, box_y + box_height + 10, sublabel)
    
    # Vẽ các ô chữ ký với border
    signature_boxes = []
    for i in range(num_boxes):
        x = start_x + i * (box_width + box_spacing)
        signature_boxes.append((x, box_y, box_width, box_height))
    
    # Hiển thị chữ ký trong từng ô
    signature_area_height = box_height - 18  # Giảm vùng chữ ký (để lại 18px cho tên)
    signature_y = box_y + 18  # Chữ ký ở phần trên (cách đáy 18px)
    signature_center_y = signature_y + signature_area_height/2 - 8/2  # Căn giữa chữ ký
    name_y = box_y + 8  # Tên người ký ở phần dưới (cách đáy 8px)
    
    # Quản lý
    x0 = start_x
    
    print("DEBUG: Processing manager signature for PDF")
    try:
        success = draw_signature_with_proper_scaling(canvas_obj, signature, x0, signature_y, box_width, signature_area_height)
        if not success:
            print("DEBUG: Failed to draw manager signature, creating placeholder")
            create_signature_placeholder(canvas_obj, x0, signature_y, box_width, signature_area_height, "Lỗi hiển thị")
    except Exception as e:
        print(f"Error drawing manager signature: {e}")
        create_signature_placeholder(canvas_obj, x0, signature_y, box_width, signature_area_height, "Lỗi")
    
    # Thêm tên người ký quản lý bên trong ô chữ ký (phía dưới chữ ký)
    canvas_obj.setFont("DejaVuSans", 8)
    canvas_obj.drawCentredString(x0 + box_width/2, name_y, "Test Quản lý")
    
    # Trưởng nhóm
    x1 = start_x + 1 * (box_width + box_spacing)
    
    print("DEBUG: Processing team leader signature for PDF")
    try:
        success = draw_signature_with_proper_scaling(canvas_obj, signature, x1, signature_y, box_width, signature_area_height)
        if not success:
            print("DEBUG: Failed to draw team leader signature, creating placeholder")
            create_signature_placeholder(canvas_obj, x1, signature_y, box_width, signature_area_height, "Lỗi hiển thị")
    except Exception as e:
        print(f"Error drawing team leader signature: {e}")
        create_signature_placeholder(canvas_obj, x1, signature_y, box_width, signature_area_height, "Lỗi")
    
    # Thêm tên người ký trưởng nhóm bên trong ô chữ ký (phía dưới chữ ký)
    canvas_obj.setFont("DejaVuSans", 8)
    canvas_obj.drawCentredString(x1 + box_width/2, name_y, "Test Trưởng nhóm")
    
    # Nhân viên
    x2 = start_x + 2 * (box_width + box_spacing)
    
    print("DEBUG: Processing employee signature for PDF")
    try:
        success = draw_signature_with_proper_scaling(canvas_obj, signature, x2, signature_y, box_width, signature_area_height)
        if not success:
            print("DEBUG: Failed to draw employee signature, creating placeholder")
            create_signature_placeholder(canvas_obj, x2, signature_y, box_width, signature_area_height, "Lỗi hiển thị")
    except Exception as e:
        print(f"Error drawing employee signature: {e}")
        create_signature_placeholder(canvas_obj, x2, signature_y, box_width, signature_area_height, "Lỗi")
    
    # Thêm tên người ký nhân viên bên trong ô chữ ký (phía dưới chữ ký)
    canvas_obj.setFont("DejaVuSans", 8)
    canvas_obj.drawCentredString(x2 + box_width/2, name_y, user.name)
    
    # Vẽ lại border cho tất cả các ô chữ ký sau khi đã vẽ chữ ký
    canvas_obj.setStrokeColor(colors.black)
    canvas_obj.setLineWidth(0.5)
    for x, y, w, h in signature_boxes:
        canvas_obj.rect(x, y, w, h, stroke=1, fill=0)
    
    # Thêm ghi chú test ở cuối
    canvas_obj.setFont("DejaVuSans", 8)
    canvas_obj.drawString(margin, 50, "*** Đây là PDF test để kiểm tra hiển thị chữ ký cá nhân trên mẫu phiếu tăng ca thực tế ***")
    canvas_obj.drawString(margin, 35, f"Được tạo bởi: {user.name} - {user.employee_id} - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    canvas_obj.drawString(margin, 20, "Phiếu này chỉ dùng để test hiển thị chữ ký, không có giá trị pháp lý.")

def remove_vietnamese_accents(text):
    """Loại bỏ dấu tiếng Việt và chuyển thành chữ thường, loại bỏ khoảng trắng"""
    if not text:
        return ""
    
    # Mapping dấu tiếng Việt
    vietnamese_map = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        'đ': 'd',
        'À': 'A', 'Á': 'A', 'Ả': 'A', 'Ã': 'A', 'Ạ': 'A',
        'Ă': 'A', 'Ằ': 'A', 'Ắ': 'A', 'Ẳ': 'A', 'Ẵ': 'A', 'Ặ': 'A',
        'Â': 'A', 'Ầ': 'A', 'Ấ': 'A', 'Ẩ': 'A', 'Ẫ': 'A', 'Ậ': 'A',
        'È': 'E', 'É': 'E', 'Ẻ': 'E', 'Ẽ': 'E', 'Ẹ': 'E',
        'Ê': 'E', 'Ề': 'E', 'Ế': 'E', 'Ể': 'E', 'Ễ': 'E', 'Ệ': 'E',
        'Ì': 'I', 'Í': 'I', 'Ỉ': 'I', 'Ĩ': 'I', 'Ị': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ỏ': 'O', 'Õ': 'O', 'Ọ': 'O',
        'Ô': 'O', 'Ồ': 'O', 'Ố': 'O', 'Ổ': 'O', 'Ỗ': 'O', 'Ộ': 'O',
        'Ơ': 'O', 'Ờ': 'O', 'Ớ': 'O', 'Ở': 'O', 'Ỡ': 'O', 'Ợ': 'O',
        'Ù': 'U', 'Ú': 'U', 'Ủ': 'U', 'Ũ': 'U', 'Ụ': 'U',
        'Ư': 'U', 'Ừ': 'U', 'Ứ': 'U', 'Ử': 'U', 'Ữ': 'U', 'Ự': 'U',
        'Ỳ': 'Y', 'Ý': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y', 'Ỵ': 'Y',
        'Đ': 'D'
    }
    
    result = ""
    for char in text:
        result += vietnamese_map.get(char, char)
    
    # Chuyển thành chữ thường và loại bỏ khoảng trắng
    result = result.lower().replace(' ', '')
    
    # Loại bỏ các ký tự đặc biệt khác, chỉ giữ lại chữ cái và số
    import re
    result = re.sub(r'[^a-z0-9]', '', result)
    
    return result

# API endpoint để phê duyệt tất cả attendance records
@app.route('/api/attendance/approve-all', methods=['POST'])
@rate_limit(max_requests=10, window_seconds=60)  # Giới hạn 10 lần gọi API trong 1 phút
def approve_all_attendances():
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    
    update_session_activity()
    
    user = get_user_from_session()
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    
    current_role = session.get('current_role', user.roles.split(',')[0])
    if current_role not in ['TEAM_LEADER', 'MANAGER', 'ADMIN']:
        return jsonify({'error': 'Bạn không có quyền phê duyệt hàng loạt'}), 403
    
    data = request.get_json()
    action = data.get('action')  # 'approve' hoặc 'reject'
    reason = validate_reason(data.get('reason', '')) if data.get('action') == 'reject' else ''
    
    if action not in ['approve', 'reject']:
        return jsonify({'error': 'Hành động không hợp lệ'}), 400
    
    if action == 'reject' and not reason:
        return jsonify({'error': 'Lý do từ chối không hợp lệ'}), 400
    
    try:
        # Xác định phạm vi attendance records cần phê duyệt
        if current_role == 'ADMIN':
            # Admin có thể phê duyệt tất cả
            attendances_query = Attendance.query.filter(
                Attendance.approved == False
            )
        elif current_role == 'MANAGER':
            # Manager có thể phê duyệt tất cả nhân viên (không phân biệt phòng ban)
            # Bao gồm cả nhân viên từ các phòng ban khác
            attendances_query = Attendance.query.filter(
                Attendance.approved == False
            )
        else:  # TEAM_LEADER
            # Team leader chỉ có thể phê duyệt nhân viên cùng phòng ban
            attendances_query = Attendance.query.join(User, Attendance.user_id == User.id).filter(
                Attendance.approved == False,
                User.department == user.department
            )
        
        # Lọc theo trạng thái hiện tại
        if current_role == 'TEAM_LEADER':
            attendances_query = attendances_query.filter(Attendance.status == 'pending')
        elif current_role == 'MANAGER':
            # Manager chỉ có thể phê duyệt pending và pending_manager
            attendances_query = attendances_query.filter(
                Attendance.status.in_(['pending', 'pending_manager'])
            )
        elif current_role == 'ADMIN':
            # Admin có thể phê duyệt tất cả trạng thái chờ duyệt
            attendances_query = attendances_query.filter(
                Attendance.status.in_(['pending', 'pending_manager', 'pending_admin'])
            )
        
        attendances = attendances_query.all()
        
        if not attendances:
            return jsonify({'message': 'Không có bản ghi nào cần phê duyệt', 'count': 0}), 200
        
        approved_count = 0
        rejected_count = 0
        
        for attendance in attendances:
            # Kiểm tra quyền phê duyệt từng record
            has_permission, error_message = check_approval_permission(user.id, attendance.id, current_role)
            if not has_permission:
                continue
            
            if action == 'approve':
                # Xử lý phê duyệt
                if current_role == 'TEAM_LEADER':
                    attendance.status = 'pending_manager'
                    attendance.approved_by = user.id
                    attendance.approved_at = datetime.now()
                    # Lưu chữ ký và ID người ký nếu có
                    if user.has_personal_signature():
                        attendance.team_leader_signature = user.personal_signature
                    attendance.team_leader_signer_id = user.id  # Cập nhật ID người ký trưởng nhóm
                elif current_role == 'MANAGER':
                    # Manager chuyển lên QUẢN TRỊ VIÊN để kiểm tra cuối cùng
                    # Nếu trạng thái là pending, cần lưu chữ ký trưởng nhóm (nếu có)
                    if attendance.status == 'pending' and user.has_personal_signature():
                        attendance.team_leader_signature = user.personal_signature
                        # Cập nhật ID người ký trưởng nhóm nếu chưa có
                        if not attendance.team_leader_signer_id:
                            attendance.team_leader_signer_id = user.id
                    
                    attendance.status = 'pending_admin'
                    attendance.approved_by = user.id
                    attendance.approved_at = datetime.now()
                    # Lưu chữ ký quản lý nếu có
                    if user.has_personal_signature():
                        attendance.manager_signature = user.personal_signature
                    attendance.manager_signer_id = user.id  # Cập nhật ID người ký quản lý
                elif current_role == 'ADMIN':
                    # Admin có thể phê duyệt trực tiếp lên trạng thái cuối cùng
                    # Lưu chữ ký trưởng nhóm nếu trạng thái là pending và có chữ ký
                    if attendance.status == 'pending' and user.has_personal_signature():
                        attendance.team_leader_signature = user.personal_signature
                        attendance.team_leader_signer_id = user.id  # Cập nhật ID người ký trưởng nhóm
                    
                    # Lưu chữ ký quản lý nếu trạng thái là pending_manager và có chữ ký
                    if attendance.status == 'pending_manager' and user.has_personal_signature():
                        attendance.manager_signature = user.personal_signature
                        attendance.manager_signer_id = user.id  # Cập nhật ID người ký quản lý
                    
                    # Lưu chữ ký quản lý nếu trạng thái là pending_admin và có chữ ký
                    if attendance.status == 'pending_admin' and user.has_personal_signature():
                        attendance.manager_signature = user.personal_signature
                        attendance.manager_signer_id = user.id  # Cập nhật ID người ký quản lý
                    
                    attendance.status = 'approved'
                    attendance.approved = True
                    attendance.approved_by = user.id
                    attendance.approved_at = datetime.now()
                
                approved_count += 1
                
                # Log audit action
                log_audit_action(
                    user_id=user.id,
                    action='BULK_APPROVE_ATTENDANCE',
                    table_name='attendances',
                    record_id=attendance.id,
                    old_values={'status': attendance.status},
                    new_values={
                        'status': attendance.status, 
                        'approved_by': user.id,
                        'team_leader_signer_id': getattr(attendance, 'team_leader_signer_id', None),
                        'manager_signer_id': getattr(attendance, 'manager_signer_id', None)
                    }
                )
                
            else:  # reject
                attendance.status = 'rejected'
                attendance.reject_reason = reason
                attendance.approved_by = user.id
                attendance.approved_at = datetime.now()
                rejected_count += 1
                
                # Log audit action
                log_audit_action(
                    user_id=user.id,
                    action='BULK_REJECT_ATTENDANCE',
                    table_name='attendances',
                    record_id=attendance.id,
                    old_values={'status': attendance.status},
                    new_values={'status': 'rejected', 'reject_reason': reason, 'approved_by': user.id}
                )
        
        db.session.commit()
        
        total_processed = approved_count + rejected_count
        message = f'Đã xử lý {total_processed} bản ghi: {approved_count} phê duyệt, {rejected_count} từ chối'
        
        return jsonify({
            'success': True,
            'message': message,
            'total_processed': total_processed,
            'approved_count': approved_count,
            'rejected_count': rejected_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in bulk approval: {e}")
        return jsonify({'error': f'Lỗi khi xử lý hàng loạt: {str(e)}'}), 500

# ============================================================================
# LEAVE REQUEST ROUTES
# ============================================================================

@app.route('/test-auth')
def test_auth():
    """Test route để kiểm tra authentication"""
    if 'user_id' not in session:
        return jsonify({'authenticated': False, 'error': 'Not logged in'}), 401
    
    user = get_user_from_session()
    if not user:
        return jsonify({'authenticated': False, 'error': 'Invalid user'}), 401
    
    return jsonify({
        'authenticated': True,
        'user_id': user.id,
        'user_name': user.name,
        'roles': user.roles
    })

@app.route('/leave-request', methods=['GET'])
def leave_request_form():
    """Hiển thị form xin nghỉ phép - TỐI ƯU CỰC NHANH"""
    try:
        # Kiểm tra user đã đăng nhập
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
            return redirect(url_for('login'))
        
        # TỐI ƯU: Sử dụng session data thay vì query database
        user_id = session['user_id']
        user_name = session.get('user_name', 'Nhân viên')
        user_department = session.get('user_department', 'Chưa xác định')
        user_roles = session.get('user_roles', 'EMPLOYEE')
        
        # Tạo user object giả từ session data
        class FastUser:
            def __init__(self, user_id, user_name, user_department, user_roles):
                self.id = user_id
                self.name = user_name
                self.department = user_department
                self.roles = user_roles
        
        user = FastUser(user_id, user_name, user_department, user_roles)
        
        # Lấy vai trò hiện tại từ session
        current_role = session.get('current_role', user_roles.split(',')[0])
        work_shift = '08:00 - 17:00'
        
        return render_template('leave_request_form.html', user=user, current_role=current_role, work_shift=work_shift)
    except Exception as e:
        print(f"Error in leave_request_form: {e}")
        flash('Có lỗi xảy ra, vui lòng thử lại', 'error')
        return redirect(url_for('dashboard'))

@app.route('/leave-request', methods=['POST'])
def submit_leave_request():
    """Xử lý đơn xin nghỉ phép"""
    try:
        print("[Leave][Create] submit_leave_request called")
        # Kiểm tra user đã đăng nhập
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
            return redirect(url_for('login'))
        
        user = get_user_from_session()
        if not user:
            session.clear()
            flash('Phiên đăng nhập không hợp lệ!', 'error')
            return redirect(url_for('login'))
        
        # Lấy dữ liệu từ form
        data = request.form
        
        # Xử lý file upload
        attachments_info = []
        if 'attachments' in request.files:
            files = request.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    # Tạo tên file unique
                    filename = f"{uuid.uuid4()}_{file.filename}"
                    
                    # Tạo thư mục uploads nếu chưa có
                    upload_dir = os.path.join(app.root_path, 'uploads', 'leave_requests')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Lưu file
                    file_path = os.path.join(upload_dir, filename)
                    file.save(file_path)
                    
                    attachments_info.append({
                        'original_name': file.filename,
                        'saved_name': filename,
                        'size': file.content_length or 0
                    })
        
        # Parse trước một số trường ngày để ràng buộc hợp lệ
        from_date_str = data.get('leave_from_date', '2024-01-01')
        to_date_str = data.get('leave_to_date', '2024-01-01')
        try:
            from_date_dt = datetime.strptime(from_date_str, '%Y-%m-%d')
            to_date_dt = datetime.strptime(to_date_str, '%Y-%m-%d')
        except Exception:
            flash('Định dạng ngày không hợp lệ', 'error')
            return redirect(url_for('leave_request_form'))

        requested_annual = float(data.get('annual_leave_days', 0) or 0)
        requested_unpaid = float(data.get('unpaid_leave_days', 0) or 0)
        requested_special = float(data.get('special_leave_days', 0) or 0)
        total_requested_days = requested_annual + requested_unpaid + requested_special
        # Sử dụng kết quả tính toán từ frontend (đã tính đúng theo ca làm việc)
        # Frontend đã tính toán chính xác theo ca làm việc và giờ nghỉ trưa
        from_time_str = data.get('leave_from_time') or '00:00'
        to_time_str = data.get('leave_to_time') or '00:00'
        
        # Lấy kết quả tính toán từ frontend nếu có
        frontend_calculated_days = data.get('calculated_leave_days')
        if frontend_calculated_days is not None:
            available_units = float(frontend_calculated_days)
        else:
            # Fallback: tính theo logic cũ (không chính xác cho tất cả ca)
            available_units = _compute_leave_units_generic(from_date_dt, from_time_str, to_date_dt, to_time_str)
        
        if total_requested_days > available_units + 1e-9:
            flash('Tổng số ngày xin nghỉ vượt quá số ngày có thể xin trong khoảng thời gian đã chọn (theo ca làm việc).', 'error')
            return redirect(url_for('leave_request_form'))

        # Tạo đơn xin nghỉ phép mới
        leave_request = LeaveRequest(
            user_id=user.id,
            employee_name=data.get('employee_name'),
            team=data.get('team'),
            employee_code=data.get('employee_code'),
            leave_reason=data.get('leave_reason'),
            attachments=json.dumps(attachments_info) if attachments_info else None,
            reason_sick_child=bool(data.get('reason_sick_child')),
            reason_sick=bool(data.get('reason_sick')),
            reason_death_anniversary=bool(data.get('reason_death_anniversary')),
            reason_other=bool(data.get('reason_other')),
            reason_other_detail=data.get('reason_other_detail'),
            hospital_confirmation=bool(data.get('hospital_confirmation')),
            wedding_invitation=bool(data.get('wedding_invitation')),
            death_birth_certificate=bool(data.get('death_birth_certificate')),
            leave_from_hour=int(data.get('leave_from_time', '00:00').split(':')[0]),
            leave_from_minute=int(data.get('leave_from_time', '00:00').split(':')[1]),
            leave_from_day=int(data.get('leave_from_date', '2024-01-01').split('-')[2]),
            leave_from_month=int(data.get('leave_from_date', '2024-01-01').split('-')[1]),
            leave_from_year=int(data.get('leave_from_date', '2024-01-01').split('-')[0]),
            leave_to_hour=int(data.get('leave_to_time', '00:00').split(':')[0]),
            leave_to_minute=int(data.get('leave_to_time', '00:00').split(':')[1]),
            leave_to_day=int(data.get('leave_to_date', '2024-01-01').split('-')[2]),
            leave_to_month=int(data.get('leave_to_date', '2024-01-01').split('-')[1]),
            leave_to_year=int(data.get('leave_to_date', '2024-01-01').split('-')[0]),
            annual_leave_days=float(data.get('annual_leave_days', 0) or 0),
            unpaid_leave_days=float(data.get('unpaid_leave_days', 0) or 0),
            special_leave_days=float(data.get('special_leave_days', 0) or 0),
            special_leave_type=data.get('special_leave_type'),
            substitute_name=data.get('substitute_name'),
            substitute_employee_id=data.get('substitute_employee_id'),
            notes=data.get('notes'),
            # Lưu ca áp dụng khi xin nghỉ (tùy chọn)
            # Tương thích: nếu không có, giữ None
            shift_code=data.get('leave_shift_code') if data.get('leave_shift_code') in ['1','2','3','4'] else None,
            status='pending'
        )
        
        # Ràng buộc: các số ngày phải là bội số 0.5
        def ensure_half_step(x):
            return (int(round(x * 2)) / 2.0)
        leave_request.annual_leave_days = ensure_half_step(leave_request.annual_leave_days or 0.0)
        leave_request.unpaid_leave_days = ensure_half_step(leave_request.unpaid_leave_days or 0.0)
        leave_request.special_leave_days = ensure_half_step(leave_request.special_leave_days or 0.0)

        # Kiểm tra lần nữa sau chuẩn hóa: tổng không vượt quá đơn vị nghỉ tính được
        if (leave_request.annual_leave_days + leave_request.unpaid_leave_days + leave_request.special_leave_days) > available_units + 1e-9:
            flash('Tổng số ngày xin nghỉ vượt quá số ngày có thể xin trong khoảng thời gian đã chọn (theo ca làm việc).', 'error')
            return redirect(url_for('leave_request_form'))

        # Lưu vào cơ sở dữ liệu
        db.session.add(leave_request)
        db.session.commit()
        
        # Gửi email thông báo đến HR (bất đồng bộ)
        try:
            print(f"[Mail] Attempting to send create email for leave_request #{leave_request.id} by user #{user.id} ({user.name})")
            send_leave_request_email_async(leave_request, user, action='create')
            # Persist 'sending' immediately
            upsert_email_status(leave_request.id, 'sending', 'Đang gửi email thông báo...')
            # Lưu trạng thái email vào session cho tất cả vai trò
            session['email_status'] = {
                'request_id': leave_request.id,
                'status': 'sending',
                'message': 'Đang gửi email thông báo...'
            }
            # Chỉ thông báo về đơn; tiến trình email sẽ do toast hiển thị
            flash('Đơn xin nghỉ phép đã được gửi thành công!', 'success')
        except Exception as e:
            print(f"[Mail] Error scheduling leave create email: {e}")
            # Lưu trạng thái email vào session cho tất cả vai trò
            session['email_status'] = {
                'request_id': leave_request.id,
                'status': 'error',
                'message': f'Lỗi khi gửi email: {str(e)}'
            }
            flash('Đơn đã gửi thành công, nhưng có lỗi khi gửi email thông báo.', 'warning')
        print(f"[DEBUG] Redirecting to leave_requests_list with request_id={leave_request.id}")
        print(f"[DEBUG] Session email_status before redirect: {session.get('email_status')}")
        return redirect(url_for('leave_requests_list', request_id=leave_request.id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in submit_leave_request: {e}")
        flash(f'Lỗi khi gửi đơn xin nghỉ phép: {str(e)}', 'error')
        return redirect(url_for('leave_request_form'))

@app.route('/leave-request/<int:request_id>/attachment/<filename>')
def download_leave_attachment(request_id, filename):
    """Download attachment file for leave request"""
    try:
        # Kiểm tra user đã đăng nhập
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
            return redirect(url_for('login'))
        
        user = get_user_from_session()
        if not user:
            session.clear()
            flash('Phiên đăng nhập không hợp lệ!', 'error')
            return redirect(url_for('login'))
        
        # Lấy leave request
        leave_request = LeaveRequest.query.get_or_404(request_id)
        
        # Kiểm tra quyền truy cập (chỉ user tạo đơn hoặc admin/manager mới xem được)
        current_role = session.get('current_role', user.roles.split(',')[0])
        if not (user.id == leave_request.user_id or 
                current_role in ['ADMIN', 'MANAGER', 'TEAM_LEADER']):
            flash('Bạn không có quyền truy cập file này', 'error')
            return redirect(url_for('leave_requests_list'))
        
        # Kiểm tra file có trong attachments không
        if not leave_request.attachments:
            flash('Không tìm thấy file đính kèm', 'error')
            return redirect(url_for('view_leave_request', request_id=request_id))
        
        attachments = json.loads(leave_request.attachments)
        file_info = None
        for att in attachments:
            if att['saved_name'] == filename:
                file_info = att
                break
        
        if not file_info:
            flash('File không tồn tại', 'error')
            return redirect(url_for('view_leave_request', request_id=request_id))
        
        # Đường dẫn file
        file_path = os.path.join(app.root_path, 'uploads', 'leave_requests', filename)
        
        if not os.path.exists(file_path):
            flash('File không tồn tại trên server', 'error')
            return redirect(url_for('view_leave_request', request_id=request_id))
        
        return send_file(file_path, as_attachment=True, download_name=file_info['original_name'])
        
    except Exception as e:
        print(f"Error in download_leave_attachment: {e}")
        flash('Có lỗi xảy ra khi tải file', 'error')
        return redirect(url_for('leave_requests_list'))

@app.route('/leave-requests')
def leave_requests_list():
    """Hiển thị danh sách đơn xin nghỉ phép"""
    try:
        # Kiểm tra user đã đăng nhập
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
            return redirect(url_for('login'))
        
        user = get_user_from_session()
        if not user:
            session.clear()
            flash('Phiên đăng nhập không hợp lệ!', 'error')
            return redirect(url_for('login'))
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        request_id = request.args.get('request_id', type=int)
        
        # Tối ưu: Sử dụng raw SQL để tránh ORM overhead
        from sqlalchemy import text
        
        # Xây dựng base SQL query
        base_sql = """
        SELECT lr.id, lr.user_id, lr.employee_name, lr.team, lr.employee_code,
               lr.leave_reason, lr.leave_from_hour, lr.leave_from_minute,
               lr.leave_from_day, lr.leave_from_month, lr.leave_from_year,
               lr.leave_to_hour, lr.leave_to_minute, lr.leave_to_day,
               lr.leave_to_month, lr.leave_to_year, lr.annual_leave_days,
               lr.unpaid_leave_days, lr.special_leave_days, lr.special_leave_type,
               lr.substitute_name, lr.substitute_employee_id, lr.status,
               lr.created_at, lr.updated_at, lr.shift_code, lr.attachments,
               u.id as user_id, u.name as user_name, u.department as user_department
        FROM leave_requests lr
        LEFT JOIN users u ON u.id = lr.user_id
        WHERE 1=1
        """
        
        # Xây dựng điều kiện WHERE
        where_conditions = []
        params = {}
        
        # Lọc theo trạng thái
        status = request.args.get('status')
        if status:
            where_conditions.append("lr.status = :status")
            params['status'] = status
        
        # Lọc theo nhân viên
        employee = request.args.get('employee')
        if employee:
            where_conditions.append("(lr.employee_name LIKE :employee OR lr.employee_code LIKE :employee)")
            params['employee'] = f'%{employee}%'
        
        # Lọc theo ngày
        date_from = request.args.get('date_from')
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                where_conditions.append("lr.created_at >= :date_from")
                params['date_from'] = from_date
            except ValueError:
                pass
        
        date_to = request.args.get('date_to')
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                where_conditions.append("lr.created_at < :date_to")
                params['date_to'] = to_date
            except ValueError:
                pass
        
        # Phân quyền: Nhân viên chỉ xem đơn của mình
        user_roles = user.get_roles_list()
        is_approver = any(role in ['ADMIN', 'MANAGER', 'TEAM_LEADER'] for role in user_roles)
        
        if not is_approver:
            where_conditions.append("lr.user_id = :user_id")
            params['user_id'] = user.id
        
        # Xây dựng SQL hoàn chỉnh
        if where_conditions:
            base_sql += " AND " + " AND ".join(where_conditions)
        
        # Sắp xếp
        sort_by = request.args.get('sort_by', 'created_at')
        sort_dir = request.args.get('sort_dir', 'desc')
        if sort_by == 'status':
            base_sql += f" ORDER BY lr.status {sort_dir.upper()}"
        else:
            base_sql += f" ORDER BY lr.created_at {sort_dir.upper()}"
        
        # Thực hiện query với raw SQL
        import time as _t
        _t0 = _t.perf_counter()
        
        # Đếm tổng số bản ghi
        count_sql = f"SELECT COUNT(*) FROM ({base_sql}) as count_query"
        total_count = db.session.execute(text(count_sql), params).scalar()
        
        # Lấy dữ liệu với phân trang
        offset = (page - 1) * per_page
        paginated_sql = f"{base_sql} LIMIT {per_page} OFFSET {offset}"
        result = db.session.execute(text(paginated_sql), params)
        
        # Chuyển đổi kết quả thành objects giả với pre-computed values
        leave_requests = []
        for row in result:
            # Tạo object giả với pre-computed values
            class FastLeaveRequest:
                def __init__(self, row):
                    self.id = row.id
                    self.user_id = row.user_id
                    self.employee_name = row.employee_name
                    self.team = row.team
                    self.employee_code = row.employee_code
                    self.leave_reason = row.leave_reason
                    self.status = row.status
                    self.created_at = row.created_at
                    self.updated_at = row.updated_at
                    self.shift_code = row.shift_code
                    self.attachments = row.attachments
                    self.substitute_name = row.substitute_name
                    self.substitute_employee_id = row.substitute_employee_id
                    self.annual_leave_days = row.annual_leave_days
                    self.unpaid_leave_days = row.unpaid_leave_days
                    self.special_leave_days = row.special_leave_days
                    self.special_leave_type = row.special_leave_type
                    
                    # Pre-compute datetime objects (chỉ tạo 1 lần)
                    self._cached_from_datetime = datetime(
                        row.leave_from_year, row.leave_from_month, row.leave_from_day,
                        row.leave_from_hour, row.leave_from_minute
                    )
                    self._cached_to_datetime = datetime(
                        row.leave_to_year, row.leave_to_month, row.leave_to_day,
                        row.leave_to_hour, row.leave_to_minute
                    )
                    
                    # Pre-compute text values
                    self._cached_reason_text = row.leave_reason or 'Không có lý do'
                    
                    # Pre-compute leave type text
                    leave_types = []
                    if row.annual_leave_days and row.annual_leave_days > 0:
                        leave_types.append(f'Phép năm: {row.annual_leave_days} ngày')
                    if row.unpaid_leave_days and row.unpaid_leave_days > 0:
                        leave_types.append(f'Không lương: {row.unpaid_leave_days} ngày')
                    if row.special_leave_days and row.special_leave_days > 0:
                        leave_types.append(f'Đặc biệt: {row.special_leave_days} ngày')
                    if row.special_leave_type:
                        leave_types.append(f'({row.special_leave_type})')
                    self._cached_leave_type_text = ', '.join(leave_types) if leave_types else 'Không xác định'
                    
                    # Tạo user object giả
                    class FastUser:
                        def __init__(self, user_id, user_name, user_department):
                            self.id = user_id
                            self.name = user_name
                            self.department = user_department
                    
                    self.user = FastUser(row.user_id, row.user_name, row.user_department)
            
            leave_requests.append(FastLeaveRequest(row))
        
        _elapsed = (_t.perf_counter() - _t0) * 1000
        
        # Tạo pagination object giả
        class FastPagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None
        
        pagination = FastPagination(leave_requests, page, per_page, total_count)
        
        try:
            print(f"[PERF] leave_requests_list raw SQL: {len(pagination.items)} items, page={page}, total={total_count}, ms={_elapsed:.1f}")
        except Exception:
            pass
        
        # Lấy vai trò hiện tại từ session
        current_role = session.get('current_role', user.roles.split(',')[0])
        
        print(f"[DEBUG] leave_requests_list called with request_id={request_id}")
        print(f"[DEBUG] Session email_status: {session.get('email_status')}")
        print(f"[DEBUG] Global email_status: {dict(email_status)}")
        
        # Template helper functions cho cached values
        def get_cached_from_datetime(request):
            return request._cached_from_datetime
        
        def get_cached_to_datetime(request):
            return request._cached_to_datetime
        
        def get_cached_reason_text(request):
            return request._cached_reason_text
        
        def get_cached_leave_type_text(request):
            return request._cached_leave_type_text
        
        return render_template('leave_requests_list.html', 
                             leave_requests=pagination.items,
                             pagination=pagination,
                             user=user,
                             current_role=current_role,
                             request_id=request_id,
                             get_cached_from_datetime=get_cached_from_datetime,
                             get_cached_to_datetime=get_cached_to_datetime,
                             get_cached_reason_text=get_cached_reason_text,
                             get_cached_leave_type_text=get_cached_leave_type_text)
    except Exception as e:
        print(f"Error in leave_requests_list: {e}")
        flash('Có lỗi xảy ra, vui lòng thử lại', 'error')
        return redirect(url_for('dashboard'))

@app.route('/leave-request/<int:request_id>')
def view_leave_request(request_id):
    """Xem chi tiết đơn xin nghỉ phép"""
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
        return redirect(url_for('login'))
    
    user = get_user_from_session()
    if not user:
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('login'))
    
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Kiểm tra quyền truy cập
    user_roles = user.get_roles_list()
    if not (any(role in ['ADMIN', 'MANAGER', 'TEAM_LEADER'] for role in user_roles) or 
            user.id == leave_request.user_id):
        abort(403)
    
    # Lấy vai trò hiện tại từ session
    current_role = session.get('current_role', user.roles.split(',')[0])
    return render_template('view_leave_request.html', leave_request=leave_request, user=user, current_role=current_role, request_id=request_id)

@app.route('/api/email-status/<int:request_id>')
def get_email_status(request_id):
    """API để kiểm tra trạng thái gửi email"""
    print(f"[API] Email status request for request_id: {request_id}")
    
    if 'user_id' not in session:
        print("[API] Unauthorized - no user_id in session")
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = get_user_from_session()
    if not user:
        print("[API] User not found")
        return jsonify({'error': 'User not found'}), 401
    
    print(f"[API] User: {user.name}, Role: {user.roles}")
    
    # Trả về email status cho tất cả vai trò
    # (Đã loại bỏ giới hạn chỉ cho nhân viên)
    
    # Ưu tiên trạng thái trong DB trước
    db_rec = get_email_status_record(request_id)
    if db_rec:
        resp = {'request_id': request_id, 'status': db_rec.status, 'message': db_rec.message}
        print(f"[API] DB status: {resp}")
        # Nếu là kết quả cuối cùng, dọn trạng thái để không lặp lại
        if db_rec.status in ['success', 'error']:
            try:
                db.session.delete(db_rec)
                db.session.commit()
            except Exception as _:
                db.session.rollback()
            session.pop('email_status', None)
        return jsonify(resp)
    
    # Nếu không có global status, kiểm tra session
    if 'email_status' in session and session['email_status'].get('request_id') == request_id:
        session_status = session['email_status']
        print(f"[API] Found session status: {session_status}")
        # Nếu là kết quả cuối cùng, dọn session
        if session_status.get('status') in ['success', 'error']:
            session.pop('email_status', None)
        return jsonify(session_status)
    
    # Fallback về unknown
    status = {'status': 'unknown', 'message': 'Không có thông tin'}
    print(f"[API] No status found, returning unknown: {status}")
    return jsonify(status)

@app.route('/api/email-status/latest')
def get_latest_email_status():
    """API: lấy trạng thái email gần nhất từ session, không cần request_id trên URL.
    Nếu session đang là 'sending' và có request_id, sẽ đối chiếu với global email_status
    để trả về kết quả cuối cùng khi có (success/error).
    """
    print("[API] Latest email status requested")
    if 'user_id' not in session:
        print("[API] Latest: Unauthorized - no user_id in session")
        return jsonify({'error': 'Unauthorized'}), 401

    # Lấy từ session nếu có
    sess = session.get('email_status')
    print(f"[API] Latest: session email_status = {sess}")
    if not sess:
        return jsonify({'status': 'unknown', 'message': 'Không có thông tin'})

    request_id = sess.get('request_id')
    if request_id:
        # Kiểm tra DB trước
        db_rec = get_email_status_record(request_id)
        print(f"[API] Latest: DB status = {db_rec.status if db_rec else None}")
        if db_rec and db_rec.status in ['success', 'error']:
            response_payload = {
                'request_id': request_id,
                'status': db_rec.status,
                'message': db_rec.message
            }
            # Dọn DB và session để không lặp lại
            try:
                db.session.delete(db_rec)
                db.session.commit()
            except Exception:
                db.session.rollback()
            session.pop('email_status', None)
            return jsonify(response_payload)

    # Ngược lại trả về session hiện tại
    # Nếu sess đã là kết quả cuối cùng thì dọn luôn và trả một lần
    if sess and sess.get('status') in ['success', 'error']:
        payload = sess
        session.pop('email_status', None)
        return jsonify(payload)
    return jsonify(sess)

# ===================== SSE: Email Status Push =====================
# In-memory subscribers per user_id
_email_sse_subscribers = defaultdict(list)

def _sse_subscribe(user_id: int) -> Queue:
    q = Queue()
    _email_sse_subscribers[user_id].append(q)
    return q

def _sse_unsubscribe(user_id: int, q: Queue) -> None:
    try:
        if q in _email_sse_subscribers.get(user_id, []):
            _email_sse_subscribers[user_id].remove(q)
    except Exception:
        pass

def publish_email_status(user_id: int, request_id: int, status: str, message: str) -> None:
    """Publish an email status event to all live SSE subscribers of the user."""
    payload = {
        'request_id': request_id,
        'status': status,
        'message': message,
    }
    for q in list(_email_sse_subscribers.get(user_id, [])):
        try:
            q.put_nowait(payload)
        except Exception:
            # if queue full/broken, ignore
            pass

@app.route('/sse/email-status')
def sse_email_status():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    q = _sse_subscribe(user_id)

    def stream():
        # advise client reconnection delay
        yield 'retry: 3000\n\n'
        try:
            # send a heartbeat every 15s if idle
            import time
            last = time.time()
            while True:
                try:
                    item = q.get(timeout=1.0)
                    import json as _json
                    data = _json.dumps(item, ensure_ascii=False)
                    yield f"event: email_status\ndata: {data}\n\n"
                    last = time.time()
                except Exception:
                    now = time.time()
                    if now - last > 15:
                        # comment heartbeat to keep connection alive
                        yield ": keep-alive\n\n"
                        last = now
        finally:
            _sse_unsubscribe(user_id, q)

    from flask import Response
    return Response(stream(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@app.route('/api/test-email-status')
def test_email_status():
    """Test endpoint để kiểm tra email status"""
    return jsonify({
        'global_status': dict(email_status),
        'session_status': session.get('email_status'),
        'message': 'Test endpoint for debugging'
    })

@app.route('/api/set-test-email-status/<int:request_id>')
def set_test_email_status(request_id):
    """Test endpoint để set email status manually"""
    # Set global status
    email_status[request_id] = {
        'status': 'success',
        'message': 'Test email sent successfully!',
        'timestamp': time.time()
    }
    
    # Set session status
    session['email_status'] = {
        'request_id': request_id,
        'status': 'success',
        'message': 'Test email sent successfully!'
    }
    
    return jsonify({
        'message': f'Set test email status for request {request_id}',
        'status': 'success'
    })

@app.route('/leave-request/<int:request_id>/edit', methods=['GET', 'POST'])
def edit_leave_request(request_id):
    """Sửa đơn xin nghỉ phép"""
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
        return redirect(url_for('login'))
    
    user = get_user_from_session()
    if not user:
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('login'))
    
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Chỉ người tạo đơn mới có thể sửa
    if user.id != leave_request.user_id:
        abort(403)
    
    # Chỉ có thể sửa khi đơn đang ở trạng thái chờ phê duyệt
    if leave_request.status != 'pending':
        flash('Chỉ có thể sửa đơn khi đang chờ phê duyệt', 'error')
        return redirect(url_for('view_leave_request', request_id=request_id))
    
    if request.method == 'POST':
        try:
            data = request.form
            
            # Cập nhật thông tin nhân viên và lý do
            leave_request.employee_name = data.get('employee_name')
            leave_request.team = data.get('team')
            leave_request.employee_code = data.get('employee_code')
            leave_request.leave_reason = data.get('leave_reason')

            # Cập nhật thời gian từ các trường date/time hiện có trên form
            from_time = (data.get('leave_from_time') or '00:00').split(':')
            to_time = (data.get('leave_to_time') or '00:00').split(':')
            from_date_parts = (data.get('leave_from_date') or '2024-01-01').split('-')
            to_date_parts = (data.get('leave_to_date') or '2024-01-01').split('-')

            leave_request.leave_from_hour = int(from_time[0])
            leave_request.leave_from_minute = int(from_time[1])
            leave_request.leave_from_year = int(from_date_parts[0])
            leave_request.leave_from_month = int(from_date_parts[1])
            leave_request.leave_from_day = int(from_date_parts[2])

            leave_request.leave_to_hour = int(to_time[0])
            leave_request.leave_to_minute = int(to_time[1])
            leave_request.leave_to_year = int(to_date_parts[0])
            leave_request.leave_to_month = int(to_date_parts[1])
            leave_request.leave_to_day = int(to_date_parts[2])

            # Cập nhật hình thức nghỉ
            leave_request.annual_leave_days = float(data.get('annual_leave_days', 0) or 0)
            leave_request.unpaid_leave_days = float(data.get('unpaid_leave_days', 0) or 0)
            leave_request.special_leave_days = float(data.get('special_leave_days', 0) or 0)
            leave_request.special_leave_type = data.get('special_leave_type')
            # Cập nhật ca làm việc áp dụng khi xin nghỉ (nếu có chọn)
            sel_shift = data.get('leave_shift_code')
            if sel_shift in ['1','2','3','4']:
                leave_request.shift_code = sel_shift

            # Chuẩn hóa bội số 0.5 cho số ngày
            def ensure_half_step(x):
                return (int(round((x or 0.0) * 2)) / 2.0)
            leave_request.annual_leave_days = ensure_half_step(leave_request.annual_leave_days)
            leave_request.unpaid_leave_days = ensure_half_step(leave_request.unpaid_leave_days)
            leave_request.special_leave_days = ensure_half_step(leave_request.special_leave_days)

            # Ràng buộc: tổng ngày xin nghỉ không vượt quá số ngày trong khoảng từ ngày-đến ngày
            try:
                from_date_dt = datetime.strptime(data.get('leave_from_date', '2024-01-01'), '%Y-%m-%d')
                to_date_dt = datetime.strptime(data.get('leave_to_date', '2024-01-01'), '%Y-%m-%d')
                from_time_str = data.get('leave_from_time') or '00:00'
                to_time_str = data.get('leave_to_time') or '00:00'
                available_units = _compute_leave_units_generic(from_date_dt, from_time_str, to_date_dt, to_time_str)
            except Exception:
                available_units = None
            if available_units is not None:
                if (leave_request.annual_leave_days + leave_request.unpaid_leave_days + leave_request.special_leave_days) > available_units + 1e-9:
                    flash('Tổng số ngày xin nghỉ vượt quá số ngày có thể xin trong khoảng thời gian đã chọn (theo ca làm việc).', 'error')
                    return redirect(url_for('edit_leave_request', request_id=request_id))

            leave_request.substitute_name = data.get('substitute_name')
            leave_request.substitute_employee_id = data.get('substitute_employee_id')
            leave_request.notes = data.get('notes')
            
            db.session.commit()
            try:
                print(f"[Mail] Attempting to send update email for leave_request #{leave_request.id} by user #{user.id} ({user.name})")
                send_leave_request_email_async(leave_request, user, action='update')
                # Lưu trạng thái email vào session cho tất cả vai trò
                session['email_status'] = {
                    'request_id': leave_request.id,
                    'status': 'sending',
                    'message': 'Đang gửi email thông báo...'
                }
                # Chỉ thông báo về cập nhật; tiến trình email sẽ do toast hiển thị
                flash('Đã cập nhật đơn thành công!', 'success')
            except Exception as e:
                print(f"[Mail] Error scheduling leave update email: {e}")
                # Lưu trạng thái email vào session cho tất cả vai trò
                session['email_status'] = {
                    'request_id': leave_request.id,
                    'status': 'error',
                    'message': f'Lỗi khi gửi email: {str(e)}'
                }
                flash('Đơn đã cập nhật thành công, nhưng có lỗi khi gửi email thông báo.', 'warning')
            return redirect(url_for('leave_requests_list', status='pending'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật đơn xin nghỉ phép: {str(e)}', 'error')
    
    # Xử lý GET request - hiển thị form sửa
    work_shift = '08:00 - 17:00'
    current_role = session.get('current_role', user.roles.split(',')[0])
    return render_template('leave_request_form.html', 
                         leave_request=leave_request, 
                         is_edit=True, 
                         user=user, 
                         current_role=current_role, 
                         work_shift=work_shift)


@app.route('/leave-request/<int:request_id>/approve', methods=['POST'])
def approve_leave_request(request_id):
    """Phê duyệt hoặc từ chối đơn xin nghỉ phép"""
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
        return redirect(url_for('login'))
    
    user = get_user_from_session()
    if not user:
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('login'))
    
    # Vai trò hiện tại trong session
    current_role = session.get('current_role', user.roles.split(',')[0])
    # Kiểm tra quyền phê duyệt theo phòng ban/vai trò (tương tự chấm công)
    has_perm, err_msg = check_leave_approval_permission(user.id, request_id, current_role)
    if not has_perm:
        flash(err_msg, 'error')
        return redirect(url_for('view_leave_request', request_id=request_id))
    
    leave_request = LeaveRequest.query.get_or_404(request_id)
    action = request.form.get('action')
    
    try:
        if action == 'approve':
            # Logic phê duyệt 3 cấp giống chấm công
            if current_role == 'TEAM_LEADER':
                if leave_request.status != 'pending':
                    flash('Đơn không ở trạng thái chờ duyệt', 'warning')
                    return redirect(url_for('view_leave_request', request_id=request_id))
                leave_request.status = 'pending_manager'
                leave_request.approved_by = user.id
                leave_request.approved_at = datetime.now()
                leave_request.team_leader_signer_id = user.id
                flash('Đã chuyển lên Quản lý phê duyệt', 'success')
                
            elif current_role == 'MANAGER':
                if leave_request.status != 'pending_manager':
                    flash('Đơn chưa được Trưởng nhóm phê duyệt', 'warning')
                    return redirect(url_for('view_leave_request', request_id=request_id))
                leave_request.status = 'pending_admin'
                leave_request.approved_by = user.id
                leave_request.approved_at = datetime.now()
                leave_request.manager_signer_id = user.id
                flash('Đã chuyển lên Admin phê duyệt', 'success')
                
            elif current_role == 'ADMIN':
                if leave_request.status not in ['pending_manager', 'pending_admin']:
                    flash('Đơn chưa được cấp trước phê duyệt', 'warning')
                    return redirect(url_for('view_leave_request', request_id=request_id))
            leave_request.status = 'approved'
            leave_request.approved = True
            leave_request.approved_by = user.id
            leave_request.approved_at = datetime.now()
            # Nếu chưa có chữ ký manager thì set luôn
            if not leave_request.manager_signer_id:
                leave_request.manager_signer_id = user.id
            flash('Đơn xin nghỉ phép đã được phê duyệt hoàn tất!', 'success')
            
        elif action == 'reject':
            old_status = leave_request.status
            leave_request.status = 'rejected'
            leave_request.approved = False
            rejection_reason = request.form.get('rejection_reason')
            if rejection_reason:
                # Lưu lý do vào notes, bảo toàn ghi chú cũ nếu có
                sep = '\n' if leave_request.notes else ''
                leave_request.notes = f"{leave_request.notes or ''}{sep}Lý do từ chối: {rejection_reason}"
            # Ghi nhận người từ chối theo vai trò
            if current_role == 'TEAM_LEADER':
                leave_request.team_leader_signer_id = user.id
            elif current_role == 'MANAGER':
                leave_request.manager_signer_id = user.id
            flash('Đơn xin nghỉ phép đã bị từ chối!', 'warning')
        else:
            flash('Hành động không hợp lệ!', 'error')
            return redirect(url_for('view_leave_request', request_id=request_id))
        
        db.session.commit()
        upsert_email_status(request_id, 'sending', 'Đang gửi email thông báo...')
        return redirect(url_for('view_leave_request', request_id=request_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xử lý đơn xin nghỉ phép: {str(e)}', 'error')
        return redirect(url_for('view_leave_request', request_id=request_id))

@app.route('/leave-request/<int:request_id>/delete')
def delete_leave_request(request_id):
    """Xóa đơn xin nghỉ phép"""
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
        return redirect(url_for('login'))
    
    user = get_user_from_session()
    if not user:
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('login'))
    
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Chỉ người tạo đơn mới có thể xóa
    if user.id != leave_request.user_id:
        abort(403)
    
    # Chỉ có thể xóa khi đơn đang ở trạng thái chờ phê duyệt
    if leave_request.status != 'pending':
        flash('Chỉ có thể xóa đơn khi đang chờ phê duyệt', 'error')
        return redirect(url_for('view_leave_request', request_id=request_id))
    
    try:
        db.session.delete(leave_request)
        db.session.commit()
        flash('Đơn xin nghỉ phép đã được xóa thành công!', 'success')
        return redirect(url_for('leave_requests_list'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xóa đơn xin nghỉ phép: {str(e)}', 'error')
        return redirect(url_for('view_leave_request', request_id=request_id))

@app.route('/leave-history')
def leave_history():
    """Hiển thị lịch sử nghỉ phép: chỉ các đơn đã được phê duyệt của chính người dùng"""
    try:
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
            return redirect(url_for('login'))

        user = get_user_from_session()
        if not user:
            session.clear()
            flash('Phiên đăng nhập không hợp lệ!', 'error')
            return redirect(url_for('login'))

        current_role = session.get('current_role', user.roles.split(',')[0])

        page = request.args.get('page', 1, type=int)
        per_page = 20

        # Tối ưu query để chỉ load cột cần thiết
        query = (
            LeaveRequest.query
            .options(
                joinedload(LeaveRequest.user).load_only(User.id, User.name, User.department),
                defer(LeaveRequest.notes),
                defer(LeaveRequest.attachments),
                defer(LeaveRequest.applicant_signature),
                defer(LeaveRequest.manager_signature),
                defer(LeaveRequest.team_leader_signature),
                defer(LeaveRequest.direct_superior_signature)
            )
            .filter(
            LeaveRequest.user_id == user.id,
            LeaveRequest.status == 'approved'
            )
            .order_by(LeaveRequest.created_at.desc())
        )

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return render_template('leave_history.html',
                               leave_requests=pagination.items,
                               pagination=pagination,
                               user=user,
                               current_role=current_role)
    except Exception as e:
        print(f"Error in leave_history: {e}")
        flash('Có lỗi xảy ra, vui lòng thử lại', 'error')
        return redirect(url_for('dashboard'))
@app.route('/leave-request/back-to-dashboard')
def back_to_dashboard():
    """Quay về dashboard với vai trò hiện tại"""
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
        return redirect(url_for('login'))
    
    # Lấy vai trò hiện tại từ session
    current_role = session.get('current_role', 'EMPLOYEE')
    print(f"DEBUG back_to_dashboard: current_role from session: {current_role}")
    print(f"DEBUG back_to_dashboard: session keys: {list(session.keys())}")
    print(f"DEBUG back_to_dashboard: redirecting to dashboard?role={current_role}")
    
    # Chuyển hướng về dashboard với vai trò hiện tại
    return redirect(url_for('dashboard', role=current_role))

@app.route('/api/pending-leave-count')
def api_pending_leave_count():
    """API để lấy số lượng đơn nghỉ phép cần phê duyệt"""
    try:
        # Kiểm tra user đã đăng nhập
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Chỉ trưởng nhóm, quản lý và quản trị viên mới có quyền xem
        user_roles = user.get_roles_list()
        if not any(role in ['TEAM_LEADER', 'MANAGER', 'ADMIN'] for role in user_roles):
            return jsonify({'error': 'Forbidden'}), 403
        
        # Đếm số đơn nghỉ phép đang chờ phê duyệt
        pending_count = LeaveRequest.query.filter(LeaveRequest.status == 'pending').count()
        
        return jsonify({'count': pending_count})
        
    except Exception as e:
        print(f"Error in api_pending_leave_count: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def open_google_drive_with_selenium(admin_name, attendance_data=None):
    """
    Mở Google Drive với Selenium để tương tác với elements
    """
    try:
        print(f"🚪 VÀO HÀM open_google_drive_with_selenium(admin_name={admin_name}, co_du_lieu={'có' if bool(attendance_data) else 'không'})", flush=True)
        # In dữ liệu càng sớm càng tốt để không phụ thuộc việc chờ trang
        if attendance_data:
            print(f"📊 DỮ LIỆU (EARLY) GỬI SANG SELENIUM:", flush=True)
            print(f"   - Nhân viên: {attendance_data.get('user_name', 'N/A')}", flush=True)
            print(f"   - Ngày: {attendance_data.get('date', 'N/A')}", flush=True)
            print(f"   - Giờ vào: {attendance_data.get('check_in', 'N/A')}", flush=True)
            print(f"   - Giờ ra: {attendance_data.get('check_out', 'N/A')}", flush=True)
            print(f"   - Giờ nghỉ: {attendance_data.get('break_time', 'N/A')}", flush=True)
            print(f"   - Tổng giờ làm: {attendance_data.get('total_hours', 'N/A')}", flush=True)
            print(f"   - Giờ công: {attendance_data.get('regular_work_hours', 'N/A')}", flush=True)
            print(f"   - Tăng ca trước 22h: {attendance_data.get('overtime_before_22', 'N/A')}", flush=True)
            print(f"   - Tăng ca sau 22h: {attendance_data.get('overtime_after_22', 'N/A')}", flush=True)
            print(f"   - Ghi chú: {attendance_data.get('note', '-')}", flush=True)
            print(f"   - Đối ứng: {attendance_data.get('doi_ung', '-')}", flush=True)
            print(f"   - Trạng thái: {attendance_data.get('status', 'N/A')}", flush=True)
            print(f"   - Người duyệt: {attendance_data.get('approved_by', 'N/A')}", flush=True)
            print(f"   - Thời điểm duyệt: {attendance_data.get('approved_at', 'N/A')}", flush=True)
    except Exception:
        pass
    driver = None
    try:
        # Cấu hình Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--remote-debugging-port=9222")
        # chrome_options.add_argument("--headless")  # Chạy ẩn (uncomment nếu muốn)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        if platform.system() == "Windows":
            chrome_paths = [
                os.path.join(current_dir, "browsers", "chrome.exe"),
                os.path.join(current_dir, "chrome", "chrome.exe"),
                os.path.join(current_dir, "chrome.exe"),
                "C:/Program Files/Google/Chrome/Application/chrome.exe",
                "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"
            ]
        else:
            chrome_paths = [
                os.path.join(current_dir, "browsers", "chrome"),
                os.path.join(current_dir, "chrome", "chrome"),
                os.path.join(current_dir, "chrome"),
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser"
            ]
        
        chrome_found = False
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                chrome_options.binary_location = chrome_path
                print(f"✅ BACKEND SELENIUM: Found Chrome at {chrome_path}")
                chrome_found = True
                break
        
        if not chrome_found:
            print(f"⚠️ BACKEND SELENIUM: Chrome not found in project folder, using system default")

        driver_path = None
        driver_source = "webdriver-manager"
        
        try:
            print(f"📥 BACKEND SELENIUM: Installing latest Chrome driver for admin {admin_name}")
            driver_path = ChromeDriverManager(version="latest").install()
            print(f"✅ BACKEND SELENIUM: Latest driver installed at: {driver_path}")
            
        except Exception as e:
            print(f"⚠️ BACKEND SELENIUM: Latest driver failed: {str(e)}")
            print(f"🔄 BACKEND SELENIUM: Falling back to local drivers...")
            if platform.system() == "Windows":
                local_driver_paths = [
                    os.path.join(current_dir, "browsers", "chromedriver.exe"),
                    os.path.join(current_dir, "chrome", "chromedriver.exe"),
                    os.path.join(current_dir, "chromedriver.exe")
                ]
            else:
                local_driver_paths = [
                    os.path.join(current_dir, "browsers", "chromedriver"),
                    os.path.join(current_dir, "chrome", "chromedriver"),
                    os.path.join(current_dir, "chromedriver")
                ]

            for local_path in local_driver_paths:
                if os.path.exists(local_path):
                    driver_path = local_path
                    driver_source = "local"
                    print(f"✅ BACKEND SELENIUM: Using local driver: {driver_path}")
                    break
            if not driver_path:
                print(f"❌ BACKEND SELENIUM: No local driver found!")
                print(f"🚫 BACKEND SELENIUM: Manual download required!")
                print(f"💡 Please download chromedriver from: https://chromedriver.chromium.org/")
                print(f"💡 Place it in: {os.path.join(current_dir, 'browsers')} or {os.path.join(current_dir, 'chrome')}")
                raise Exception("Chrome driver not found. Please download manually.")
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(10)
        
        # Mở Google Drive
        drive_url = "https://drive.google.com/drive/folders/1dHF_x6fCJEs9krtmaZPabBIWiTr5xpB3"
        driver.get(drive_url)
        print(f"🌐 BACKEND SELENIUM: Opened Chrome to Google Drive for admin {admin_name}")
        wait = WebDriverWait(driver, 15)
        
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Nếu có dữ liệu attendance, in ra console và tương tác với Google Drive
            if attendance_data:
                print(f"\n{'='*80}")
                print(f"📝 BACKEND SELENIUM: Processing attendance data for admin {admin_name}")
                print(f"{'='*80}")
                print(f"📊 BACKEND SELENIUM: ATTENDANCE APPROVAL DATA:")
                print(f"   🆔 ID: {attendance_data.get('id', 'N/A')}")
                print(f"   👤 Employee: {attendance_data.get('user_name', 'N/A')}")
                print(f"   📅 Date: {attendance_data.get('date', 'N/A')}")
                print(f"   ⏰ Check In: {attendance_data.get('check_in', 'N/A')}")
                print(f"   ⏰ Check Out: {attendance_data.get('check_out', 'N/A')}")
                print(f"   ☕ Break Time: {attendance_data.get('break_time', 'N/A')}")
                print(f"   ⏱️  Total Hours: {attendance_data.get('total_hours', 'N/A')}")
                print(f"   🌅 Overtime Before 22:00: {attendance_data.get('overtime_before_22', 'N/A')}")
                print(f"   🌙 Overtime After 22:00: {attendance_data.get('overtime_after_22', 'N/A')}")
                print(f"   💼 Comp Time Regular: {attendance_data.get('comp_time_regular', 'N/A')}")
                print(f"   💼 Comp Time Overtime: {attendance_data.get('comp_time_overtime', 'N/A')}")
                print(f"   ✅ Status: {attendance_data.get('status', 'N/A')}")
                print(f"   👑 Approved By: {attendance_data.get('approved_by', 'N/A')}")
                print(f"   🕐 Approved At: {attendance_data.get('approved_at', 'N/A')}")
                print(f"{'='*80}")
                
                # Chỉ mở Google Drive, không tự động tạo Sheets
                print(f"🌐 BACKEND SELENIUM: Google Drive opened successfully for admin {admin_name}")
                print(f"📋 BACKEND SELENIUM: Admin can now manually create Google Sheets if needed")
                print(f"{'='*80}\n")
                    
            else:
                # Nếu không có dữ liệu, chỉ mở Google Drive
                print(f"📁 BACKEND SELENIUM: No attendance data provided, just opened Drive for admin {admin_name}")
                
                # Tương tác cơ bản với Google Drive
                try:
                    # Chờ trang load hoàn toàn
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-target='docs-chrome']")))
                    
                    # Scroll xuống để load thêm content
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    print(f"📜 BACKEND SELENIUM: Scrolled to bottom for admin {admin_name}")
                    
                    # Lấy tên các folder/files hiện có
                    try:
                        file_elements = driver.find_elements(By.CSS_SELECTOR, "[data-target='docs-chrome'] [role='gridcell']")
                        if file_elements:
                            print(f"📋 BACKEND SELENIUM: Found {len(file_elements)} items in Drive for admin {admin_name}")
                        else:
                            print(f"📋 BACKEND SELENIUM: No items found in Drive for admin {admin_name}")
                    except Exception as e:
                        print(f"⚠️ BACKEND SELENIUM: Could not count items: {str(e)}")
                        
                except TimeoutException:
                    print(f"⚠️ BACKEND SELENIUM: Timeout waiting for Drive elements for admin {admin_name}")
                except Exception as e:
                    print(f"⚠️ BACKEND SELENIUM: Error interacting with Drive: {str(e)}")
            
            print(f"✅ BACKEND SELENIUM: Successfully processed Google Drive for admin {admin_name}")
            
            # Giữ browser mở một thời gian ngắn để admin có thể tương tác (không yêu cầu input)
            import time
            print("⏳ SELENIUM: Giữ trình duyệt mở 10 giây để bạn tương tác thủ công...")
            time.sleep(10)
            
        except TimeoutException:
            print(f"⚠️ BACKEND SELENIUM: Timeout waiting for page to load for admin {admin_name}")
        except Exception as e:
            print(f"⚠️ BACKEND SELENIUM: Error interacting with page: {str(e)}")
            
    except WebDriverException as e:
        print(f"❌ BACKEND SELENIUM: WebDriver error for admin {admin_name}: {str(e)}")
        print(f"🚫 BACKEND SELENIUM: Cannot open Google Drive automatically for admin {admin_name}")
    except Exception as e:
        print(f"❌ BACKEND SELENIUM: Unexpected error for admin {admin_name}: {str(e)}")
        print(f"🚫 BACKEND SELENIUM: Cannot open Google Drive automatically for admin {admin_name}")
    finally:
        # Đóng browser sau khi hoàn thành
        if driver:
            try:
                driver.quit()
                print(f"🔒 BACKEND SELENIUM: Closed browser for admin {admin_name}")
            except Exception as e:
                print(f"⚠️ BACKEND SELENIUM: Error closing browser: {str(e)}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        convert_overtime_to_hhmm()
    
    # Production-ready settings
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    app.run(debug=debug_mode, host=host, port=port) 