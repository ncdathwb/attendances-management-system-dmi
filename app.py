import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, get_flashed_messages, abort, send_file, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from functools import wraps
from config import config
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import func
import re
from collections import defaultdict
import time
import secrets
from flask_migrate import Migrate
from jinja2 import Template
import io
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import base64
import traceback
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import registerFont
import zipfile


# Import database models
from database.models import db, User, Attendance, Request, Department, AuditLog

app = Flask(__name__)

# Load configuration
config_name = os.environ.get('FLASK_CONFIG') or 'default'
app.config.from_object(config[config_name])

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import rate limiting from utils
from utils.decorators import rate_limit

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=10, window_seconds=300)  # 10 attempts per 5 minutes
def login():
    if request.method == 'POST':
        employee_id_str = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        # Validate input
        if not employee_id_str or not password:
            flash('Vui lòng nhập đầy đủ mã nhân viên và mật khẩu!', 'error')
            return render_template('login.html', messages=get_flashed_messages(with_categories=False))
        
        employee_id = validate_employee_id(employee_id_str)
        if not employee_id:
            flash('Mã nhân viên không hợp lệ!', 'error')
            return render_template('login.html', messages=get_flashed_messages(with_categories=False))
        
        if not validate_str(password, max_length=100):
            flash('Mật khẩu không hợp lệ!', 'error')
            return render_template('login.html', messages=get_flashed_messages(with_categories=False))
        
        try:
            user = User.query.filter_by(employee_id=employee_id).first()
            
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['name'] = user.name
                session['employee_id'] = user.employee_id
                session['roles'] = user.roles.split(',')
                session['current_role'] = user.roles.split(',')[0]
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
                    # Generate secure remember token instead of storing password
                    remember_token = secrets.token_urlsafe(32)
                    user.remember_token = remember_token
                    user.remember_token_expires = datetime.now() + timedelta(days=30)
                    db.session.commit()
                    response.set_cookie('remember_token', remember_token, max_age=30*24*60*60, httponly=True, secure=app.config.get('SESSION_COOKIE_SECURE', False))
                else:
                    response.delete_cookie('remember_username')
                    response.delete_cookie('remember_password')
                
                flash('Đăng nhập thành công!', 'success')
                return response
            
            flash('Mã nhân viên hoặc mật khẩu không đúng!', 'error')
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash('Đã xảy ra lỗi khi đăng nhập!', 'error')
    
    return render_template('login.html', messages=get_flashed_messages(with_categories=False))

@app.route('/logout')
def logout():
    # Log logout if user was logged in
    if 'user_id' in session:
        log_audit_action(
            user_id=session['user_id'],
            action='LOGOUT',
            table_name='users',
            record_id=session['user_id'],
            new_values={'logout_time': datetime.now().isoformat()}
        )
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
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
    
    # Đảm bảo session có đầy đủ thông tin
    if 'roles' not in session:
        session['roles'] = user.roles.split(',')
    if 'current_role' not in session:
        session['current_role'] = user.roles.split(',')[0]
    if 'name' not in session:
        session['name'] = user.name
    if 'employee_id' not in session:
        session['employee_id'] = user.employee_id
    
    # Validate current_role có trong user roles không
    if session['current_role'] not in user.roles.split(','):
        session['current_role'] = user.roles.split(',')[0]
    
    return render_template('dashboard.html', user=user)

@app.route('/api/attendance', methods=['POST'])
@rate_limit(max_requests=100, window_seconds=60)  # 20 requests per minute
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
    break_time = validate_float(data.get('break_time', 1.0), min_val=0, max_val=8)
    is_holiday = bool(data.get('is_holiday', False))
    holiday_type = validate_holiday_type(data.get('holiday_type'))
    shift_code = data.get('shift_code')
    shift_start = validate_time(data.get('shift_start'))
    shift_end = validate_time(data.get('shift_end'))
    print('DEBUG validated:', 'shift_code:', shift_code, 'shift_start:', shift_start, 'shift_end:', shift_end)
    if not date:
        return jsonify({'error': 'Vui lòng chọn ngày chấm công hợp lệ'}), 400
    if not holiday_type:
        return jsonify({'error': 'Vui lòng chọn loại ngày hợp lệ'}), 400
    if not check_in or not check_out:
        return jsonify({'error': 'Vui lòng nhập đầy đủ giờ vào và giờ ra hợp lệ'}), 400
    if break_time is None:
        return jsonify({'error': 'Thời gian nghỉ không hợp lệ!'}), 400
    if not shift_code or not shift_start or not shift_end:
        return jsonify({'error': 'Vui lòng chọn ca làm việc hợp lệ!'}), 400
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    existing_attendance = Attendance.query.filter_by(user_id=user.id, date=date).first()
    if existing_attendance:
        if existing_attendance.status != 'rejected':
            return jsonify({'error': 'Bạn đã chấm công cho ngày này rồi, không thể chấm công 2 lần trong 1 ngày.'}), 400
        else:
            db.session.delete(existing_attendance)
            db.session.commit()
    if date > datetime.now().date():
        return jsonify({'error': 'Không thể chấm công cho ngày trong tương lai!'}), 400
    signature = data.get('signature')
    attendance = Attendance(
        user_id=user.id,
        date=date,
        break_time=break_time,
        is_holiday=is_holiday,
        holiday_type=holiday_type,
        status='pending',
        overtime_before_22="0:00",
        overtime_after_22="0:00",
        shift_code=shift_code,
        signature=signature
    )
    # Nếu user là TEAM_LEADER thì lưu luôn vào team_leader_signature
    if 'TEAM_LEADER' in user.roles.split(','):
        attendance.team_leader_signature = signature
    # Nếu user là MANAGER thì lưu luôn vào manager_signature
    if 'MANAGER' in user.roles.split(','):
        attendance.manager_signature = signature
    db.session.add(attendance)
    attendance.check_in = datetime.combine(date, check_in)
    attendance.check_out = datetime.combine(date, check_out)
    attendance.shift_start = shift_start
    attendance.shift_end = shift_end
    attendance.note = note
    attendance.update_work_hours()
    try:
        db.session.commit()
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
        return jsonify({
            'message': 'Chấm công thành công',
            'work_hours': attendance.total_work_hours,
            'overtime_before_22': attendance.overtime_before_22,
            'overtime_after_22': attendance.overtime_after_22
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
        user = User.query.get(session['user_id'])
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
                
            q = Attendance.query.filter_by(approved=True)
            
            # Filter theo tên nhân viên
            if search:
                search_lower = search.lower().strip()
                q = q.join(Attendance.user).filter(func.lower(User.name).contains(search_lower))
            
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
    user = User.query.get(user_id)
    if not user:
        return []
    return user.roles.split(',')

def has_role(user_id, required_role):
    """Check if user has a specific role"""
    user = User.query.get(user_id)
    if not user:
        return False
    return required_role in user.roles.split(',')

def check_approval_permission(user_id, attendance_id, current_role):
    """Check if user has permission to approve specific attendance"""
    user = User.query.get(user_id)
    if not user:
        return False, "Không tìm thấy người dùng"
    
    attendance = Attendance.query.options(joinedload(Attendance.user)).get(attendance_id)
    if not attendance:
        return False, "Không tìm thấy bản ghi chấm công"
    
    # ADMIN và MANAGER có thể duyệt tất cả
    if current_role in ['ADMIN', 'MANAGER']:
        return True, ""
    
    # TEAM_LEADER có thể duyệt nhân viên cùng phòng ban (bao gồm cả bản thân)
    if current_role == 'TEAM_LEADER':
        if not attendance.user or attendance.user.department != user.department:
            return False, "Bạn chỉ có thể phê duyệt chấm công của nhân viên cùng phòng ban"
        return True, ""
    
    return False, "Bạn không có quyền phê duyệt chấm công"

def check_attendance_access_permission(user_id, attendance_id, action='read'):
    """Check if user has permission to access specific attendance record"""
    user = User.query.get(user_id)
    if not user:
        return False, "Không tìm thấy người dùng"
    
    attendance = Attendance.query.options(joinedload(Attendance.user)).get(attendance_id)
    if not attendance:
        return False, "Không tìm thấy bản ghi chấm công"
    
    current_role = session.get('current_role', user.roles.split(',')[0])
    
    # ADMIN có thể truy cập tất cả
    if current_role == 'ADMIN':
        return True, ""
    
    # MANAGER có thể truy cập nhân viên cùng phòng ban
    if current_role == 'MANAGER':
        if not attendance.user or attendance.user.department != user.department:
            return False, "Bạn chỉ có thể truy cập chấm công của nhân viên cùng phòng ban"
        return True, ""
    
    # TEAM_LEADER có thể truy cập nhân viên cùng phòng ban
    if current_role == 'TEAM_LEADER':
        if not attendance.user or attendance.user.department != user.department:
            return False, "Bạn chỉ có thể truy cập chấm công của nhân viên cùng phòng ban"
        return True, ""
    
    # EMPLOYEE chỉ có thể truy cập bản ghi của chính mình
    if current_role == 'EMPLOYEE':
        if attendance.user_id != user_id:
            return False, "Bạn chỉ có thể truy cập bản ghi chấm công của chính mình"
        return True, ""
    
    return False, "Bạn không có quyền truy cập bản ghi này"

def check_request_access_permission(user_id, request_id, action='read'):
    """Check if user has permission to access specific request record"""
    user = User.query.get(user_id)
    if not user:
        return False, "Không tìm thấy người dùng"
    
    req = Request.query.options(joinedload(Request.user)).get(request_id)
    if not req:
        return False, "Không tìm thấy yêu cầu"
    
    current_role = session.get('current_role', user.roles.split(',')[0])
    
    # ADMIN có thể truy cập tất cả
    if current_role == 'ADMIN':
        return True, ""
    
    # MANAGER có thể truy cập yêu cầu của nhân viên cùng phòng ban
    if current_role == 'MANAGER':
        if not req.user or req.user.department != user.department:
            return False, "Bạn chỉ có thể truy cập yêu cầu của nhân viên cùng phòng ban"
        return True, ""
    
    # TEAM_LEADER có thể truy cập yêu cầu của nhân viên cùng phòng ban
    if current_role == 'TEAM_LEADER':
        if not req.user or req.user.department != user.department:
            return False, "Bạn chỉ có thể truy cập yêu cầu của nhân viên cùng phòng ban"
        return True, ""
    
    # EMPLOYEE chỉ có thể truy cập yêu cầu của chính mình
    if current_role == 'EMPLOYEE':
        if req.user_id != user_id:
            return False, "Bạn chỉ có thể truy cập yêu cầu của chính mình"
        return True, ""
    
    return False, "Bạn không có quyền truy cập yêu cầu này"

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
                flash(f'Bạn cần chuyển sang vai trò {required_role} để truy cập trang này', 'error')
                return redirect(url_for('dashboard'))
            
            # Kiểm tra user có role này trong database không
            if not has_role(session['user_id'], required_role):
                flash('Bạn không có quyền truy cập trang này', 'error')
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

    query = User.query
    if search:
        # Cải thiện tìm kiếm: chuyển về lowercase và sử dụng func.lower() để đảm bảo không phân biệt hoa thường
        search_lower = search.lower().strip()
        query = query.filter(
            (func.lower(User.name).contains(search_lower)) | 
            (func.lower(User.employee_id).contains(search_lower))
        )
    if department_filter:
        query = query.filter(User.department == department_filter)
    query = query.order_by(User.name.asc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items

    # Danh sách phòng ban duy nhất, sắp xếp theo tên
    all_departments = User.query.with_entities(User.department).distinct().all()
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
    # Danh sách phòng ban duy nhất, sắp xếp theo tên
    all_departments = User.query.with_entities(User.department).distinct().all()
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
            
            # Check if employee_id already exists
            existing_user = User.query.filter_by(employee_id=employee_id).first()
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
    
    # Danh sách phòng ban duy nhất, sắp xếp theo tên
    all_departments = User.query.with_entities(User.department).distinct().all()
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
    user = User.query.get(session['user_id'])
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
    user = User.query.get(session['user_id'])
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
    leader = User.query.filter_by(department=user.department, roles='TEAM_LEADER').first()
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
    approver = User.query.get(session['user_id'])
    if req.current_approver_id != approver.id:
        return jsonify({'error': 'Bạn không có quyền phê duyệt yêu cầu này'}), 403
    if action == 'approve':
        if req.step == 'leader':
            manager = User.query.filter_by(department=req.user.department, roles='MANAGER').first()
            if not manager:
                return jsonify({'error': 'Không tìm thấy quản lý cho phòng ban này'}), 400
            req.current_approver_id = manager.id
            req.step = 'manager'
        elif req.step == 'manager':
            admin = User.query.filter_by(roles='ADMIN').first()
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
    
    attendance = Attendance.query.get(attendance_id)
    if not attendance:
        return jsonify({'error': 'Không tìm thấy bản ghi'}), 404
    
    return jsonify({
        'id': attendance.id,
        'date': attendance.date.strftime('%d/%m/%Y'),
        'check_in': attendance.check_in.strftime('%d/%m/%Y %H:%M:%S') if attendance.check_in else None,
        'check_out': attendance.check_out.strftime('%d/%m/%Y %H:%M:%S') if attendance.check_out else None,
        'break_time': attendance._format_hours_minutes(attendance.break_time),
        'is_holiday': attendance.is_holiday,
        'holiday_type': attendance.holiday_type,
        'note': attendance.note,
        'approved': attendance.approved,
        'status': attendance.status,
        'shift_code': attendance.shift_code,
        'shift_start': attendance.shift_start.strftime('%H:%M') if attendance.shift_start else None,
        'shift_end': attendance.shift_end.strftime('%H:%M') if attendance.shift_end else None
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
    is_holiday = bool(data.get('is_holiday', False))
    holiday_type = validate_holiday_type(data.get('holiday_type'))
    shift_code = data.get('shift_code')
    shift_start = validate_time(data.get('shift_start'))
    shift_end = validate_time(data.get('shift_end'))
    # Xử lý signature: nếu không có trường signature hoặc rỗng thì giữ nguyên chữ ký cũ, nếu có thì cập nhật
    if 'signature' in data and data.get('signature'):
        attendance.signature = data.get('signature')
    # Nếu không có trường signature hoặc rỗng thì giữ nguyên chữ ký cũ
    if not date:
        return jsonify({'error': 'Vui lòng chọn ngày chấm công hợp lệ'}), 400
    if not holiday_type:
        return jsonify({'error': 'Vui lòng chọn loại ngày hợp lệ'}), 400
    if not check_in or not check_out:
        return jsonify({'error': 'Vui lòng nhập đầy đủ giờ vào và giờ ra hợp lệ'}), 400
    if break_time is None:
        return jsonify({'error': 'Thời gian nghỉ không hợp lệ!'}), 400
    if not shift_code or not shift_start or not shift_end:
        return jsonify({'error': 'Vui lòng chọn ca làm việc hợp lệ!'}), 400
    attendance.date = date
    attendance.check_in = datetime.combine(date, check_in)
    attendance.check_out = datetime.combine(date, check_out)
    attendance.note = note
    attendance.break_time = break_time
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
                'check_out': datetime.combine(date, check_out).isoformat(),
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

@app.route('/api/attendance/<int:attendance_id>/approve', methods=['POST'])
@rate_limit(max_requests=30, window_seconds=60)  # 30 approvals per minute
def approve_attendance(attendance_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    current_role = session.get('current_role', user.roles.split(',')[0])
    if current_role not in ['TEAM_LEADER', 'MANAGER', 'ADMIN']:
        return jsonify({'error': 'Bạn không có quyền phê duyệt chấm công'}), 403
    has_permission, error_message = check_approval_permission(user.id, attendance_id, current_role)
    if not has_permission:
        return jsonify({'error': error_message}), 403
    data = request.get_json()
    action = data.get('action')  # 'approve' hoặc 'reject'
    reason = validate_reason(data.get('reason', '')) if data.get('action') == 'reject' else ''
    approver_signature = data.get('signature')  # Chữ ký người phê duyệt
    
    if action not in ['approve', 'reject']:
        return jsonify({'error': 'Hành động không hợp lệ'}), 400
    
    # Lấy thông tin attendance để kiểm tra
    attendance = Attendance.query.get(attendance_id)
    if not attendance:
        return jsonify({'error': 'Không tìm thấy bản ghi chấm công'}), 404
    
    # Kiểm tra chữ ký bắt buộc khi phê duyệt
    if action == 'approve':
        # Nếu người phê duyệt chính là người tạo attendance và đã có chữ ký cũ
        if user.id == attendance.user_id and attendance.signature:
            # Tái sử dụng chữ ký cũ
            approver_signature = attendance.signature
        elif not approver_signature:
            # Nếu không phải tự phê duyệt hoặc chưa có chữ ký cũ thì yêu cầu chữ ký mới
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
            # Chỉ lưu chữ ký vào field tương ứng với vai trò hiện tại
            if approver_signature:
                attendance.team_leader_signature = approver_signature
            message = 'Đã chuyển lên Quản lý phê duyệt'
        elif current_role == 'MANAGER':
            if attendance.status != 'pending_manager':
                return jsonify({'error': 'Bản ghi chưa được Trưởng nhóm phê duyệt'}), 400
            attendance.status = 'pending_admin'
            attendance.approved_by = user.id
            attendance.approved_at = datetime.now()
            # Chỉ lưu chữ ký vào field tương ứng với vai trò hiện tại
            if approver_signature:
                attendance.manager_signature = approver_signature
            message = 'Đã chuyển lên Admin phê duyệt'
        elif current_role == 'ADMIN':
            if attendance.status not in ['pending_manager', 'pending_admin']:
                return jsonify({'error': 'Bản ghi chưa được cấp dưới phê duyệt'}), 400
            attendance.status = 'approved'
            attendance.approved = True
            attendance.approved_by = user.id
            attendance.approved_at = datetime.now()
            message = 'Phê duyệt hoàn tất'
        log_audit_action(
            user_id=user.id,
            action='APPROVE_ATTENDANCE',
            table_name='attendances',
            record_id=attendance_id,
            old_values={'status': old_status},
            new_values={'status': attendance.status, 'approved_by': user.id, 'approved_at': attendance.approved_at.isoformat()}
        )
    else:  # reject
        old_status = attendance.status
        attendance.status = 'rejected'
        attendance.note = f"Bị từ chối bởi {current_role}: {reason}"
        message = 'Từ chối thành công'
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
        return jsonify({'message': message})
    except Exception as e:
        db.session.rollback()
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
    user = User.query.get(session['user_id'])
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
        team_users = User.query.filter(User.department == user.department).all()
        team_user_ids = [u.id for u in team_users]
        query = query.filter(Attendance.user_id.in_(team_user_ids))
    elif current_role == 'MANAGER':
        query = Attendance.query.filter_by(approved=False, status='pending_manager')
        if department:
            query = query.join(Attendance.user).filter(User.department == department)
    else:  # ADMIN
        query = Attendance.query.filter_by(approved=False, status='pending_admin')
    if search:
        search_lower = search.lower().strip()
        query = query.join(Attendance.user).filter(func.lower(User.name).contains(search_lower))
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
    user = User.query.get(session['user_id'])
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
        f = float(val)
        if min_val is not None and f < min_val:
            return None
        if max_val is not None and f > max_val:
            return None
        return f
    except Exception:
        return None

def validate_str(val, max_length=255, allow_empty=False):
    if not isinstance(val, str):
        return None
    if not allow_empty and not val.strip():
        return None
    if len(val) > max_length:
        return None
    return val.strip()

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

# Import validation functions from utils
from utils.validators import validate_input_sanitize, validate_employee_id

# Exempt certain API endpoints from CSRF protection if needed
# GET endpoints don't need CSRF protection
try:
    csrf.exempt(app.view_functions['get_attendance'])
    csrf.exempt(app.view_functions['get_attendance_history'])
    csrf.exempt(app.view_functions['get_pending_attendance'])
    csrf.exempt(app.view_functions['debug_attendance_status'])
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
        'status_label': 'Hoạt Động' if user.is_active else 'Đã Khoá',
        'status_class': 'bg-success' if user.is_active else 'bg-secondary'
    })

@app.route('/admin/attendance/<int:attendance_id>/export-overtime-pdf')
@require_admin
def export_overtime_pdf(attendance_id):
    try:
        # Tối ưu: chỉ load các trường cần thiết
        attendance = Attendance.query.options(
            joinedload(Attendance.user).load_only(User.name, User.employee_id, User.department)
        ).get_or_404(attendance_id)
        
        buffer = io.BytesIO()
        
        # Sử dụng hàm create_overtime_pdf đã tách riêng
        create_overtime_pdf(attendance, buffer)
        
        # Tạo tên file
        import re
        def make_safe_filename(s):
            s = s.lower()
            s = re.sub(r'[^a-z0-9]+', '', re.sub(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', lambda m: {
                'à':'a','á':'a','ạ':'a','ả':'a','ã':'a','â':'a','ầ':'a','ấ':'a','ậ':'a','ẩ':'a','ẫ':'a','ă':'a','ằ':'a','ắ':'a','ặ':'a','ẳ':'a','ẵ':'a',
                'è':'e','é':'e','ẹ':'e','ẻ':'e','ẽ':'e','ê':'e','ề':'e','ế':'e','ệ':'e','ể':'e','ễ':'e',
                'ì':'i','í':'i','ị':'i','ỉ':'i','ĩ':'i',
                'ò':'o','ó':'o','ọ':'o','ỏ':'o','õ':'o','ô':'o','ồ':'o','ố':'o','ộ':'o','ổ':'o','ỗ':'o','ơ':'o','ờ':'o','ớ':'o','ợ':'o','ở':'o','ỡ':'o',
                'ù':'u','ú':'u','ụ':'u','ủ':'u','ũ':'u','ư':'u','ừ':'u','ứ':'u','ự':'u','ử':'u','ữ':'u',
                'ỳ':'y','ý':'y','ỵ':'y','ỷ':'y','ỹ':'y','đ':'d'
            }[m.group(0)], s, flags=re.IGNORECASE))
            return s
        
        safe_name = make_safe_filename(attendance.user.name)
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
                    
                    # Đặt tên file cho từng PDF
                    safe_name = att.user.name.lower().replace(' ', '_') if att.user and att.user.name else str(att.id)
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
        registerFont(TTFont('DejaVuSans', 'static/fonts/DejaVuSans.ttf'))
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
    except Exception as e:
        print('PDF font register error:', e)

def create_overtime_pdf(attendance, buffer):
    """Tạo PDF giấy tăng ca cho một bản ghi attendance"""
    # Đăng ký fonts một lần duy nhất
    register_pdf_fonts()
    
    user = attendance.user
    employee_signature = attendance.signature if attendance.signature else None
    team_leader_signature = attendance.team_leader_signature if attendance.team_leader_signature else None
    manager_signature = attendance.manager_signature if attendance.manager_signature else None

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
        Paragraph('THỜI GIAN', header_style_vn),
        Paragraph('Nghỉ giải lao bị gián đoạn do đối ứng công việc', header_style_vn),
        Paragraph('XÁC NHẬN', header_style_vn)
    ]
    # Hàng 2: Tiếng Nhật/Hán
    header_row2 = [
        Paragraph('', header_style_jp),
        Paragraph('日付', header_style_jp),
        Paragraph('種類', header_style_jp),
        Paragraph('シフト', header_style_jp),
        Paragraph('何時から何時まで', header_style_jp),
        Paragraph('休憩途中勤務', header_style_jp),
        Paragraph('ラボマネ承認', header_style_jp)
    ]
    # Hàng dữ liệu
    row_data = [
        '1',
        attendance.date.strftime('%d/%m/%Y'),
        form_type,
        attendance.shift_code or '-',
        time_str,
        attendance._format_hours_minutes(attendance.break_time) if attendance.break_time else '0:00',
        ''
    ]
    
    table_data = [header_row1, header_row2, row_data]
    col_widths = [30, 80, 50, 65, 80, 110, 70]  # Tổng nhỏ hơn width, luôn còn margin hai bên
    row_heights = [40, 14, 18]  # Hàng 1 cao hơn nữa
    
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
    # Ngày tháng
    c.setFont("DejaVuSans", 10)
    c.drawRightString(width-margin, y, f"Huế, ngày {attendance.date.day} tháng {attendance.date.month} năm {attendance.date.year}")
    y -= 10  # Đẩy dòng ngày tháng xuống thấp hơn
    y -= 75  # Tăng thêm khoảng cách để không bị đè lên phần ghi chú
    
    # --- Căn chỉnh lại phần chữ ký và tiêu đề phía trên ---
    # Số ô và kích thước
    num_boxes = 3
    box_width = 150
    box_height = 50
    box_spacing = 45  # khoảng cách giữa các ô
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
    # Vẽ các ô chữ ký
    for i in range(num_boxes):
        x = start_x + i * (box_width + box_spacing)
        c.rect(x, box_y, box_width, box_height)
    # Hiển thị chữ ký hoặc (chưa ký) căn giữa trong từng ô
    # Quản lý
    x0 = start_x
    center_y = box_y + box_height/2 - 8/2  # 8 là font size
    if manager_signature:
        try:
            if isinstance(manager_signature, str) and manager_signature.startswith('data:image'):
                manager_signature = manager_signature.split(',')[1]
            img = ImageReader(io.BytesIO(base64.b64decode(manager_signature)))
            c.drawImage(img, x0, box_y, width=box_width, height=box_height, mask='auto')
        except Exception as e:
            print('PDF manager signature error:', e)
            c.setFont("DejaVuSans", 8)
            c.drawCentredString(x0 + box_width/2, center_y, "(lỗi hiển thị chữ ký)")
    else:
        c.setFont("DejaVuSans", 8)
        c.drawCentredString(x0 + box_width/2, center_y, "(chưa ký)")
    # Trưởng nhóm
    x1 = start_x + 1 * (box_width + box_spacing)
    if team_leader_signature:
        try:
            if isinstance(team_leader_signature, str) and team_leader_signature.startswith('data:image'):
                team_leader_signature = team_leader_signature.split(',')[1]
            img = ImageReader(io.BytesIO(base64.b64decode(team_leader_signature)))
            c.drawImage(img, x1, box_y, width=box_width, height=box_height, mask='auto')
        except Exception as e:
            print('PDF team leader signature error:', e)
            c.setFont("DejaVuSans", 8)
            c.drawCentredString(x1 + box_width/2, center_y, "(lỗi hiển thị chữ ký)")
    else:
        c.setFont("DejaVuSans", 8)
        c.drawCentredString(x1 + box_width/2, center_y, "(chưa ký)")
    # Nhân viên
    x2 = start_x + 2 * (box_width + box_spacing)
    if employee_signature:
        try:
            if isinstance(employee_signature, str) and employee_signature.startswith('data:image'):
                employee_signature = employee_signature.split(',')[1]
            img = ImageReader(io.BytesIO(base64.b64decode(employee_signature)))
            c.drawImage(img, x2, box_y, width=box_width, height=box_height, mask='auto')
        except Exception as e:
            print('PDF employee signature error:', e)
            c.setFont("DejaVuSans", 8)
            c.drawCentredString(x2 + box_width/2, center_y, "(lỗi hiển thị chữ ký)")
    else:
        c.setFont("DejaVuSans", 8)
        c.drawCentredString(x2 + box_width/2, center_y, "(chưa ký)")
    
    c.save()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        convert_overtime_to_hhmm()
    
    # Production-ready settings
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    app.run(debug=debug_mode, host=host, port=port) 