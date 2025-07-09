from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, get_flashed_messages
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from functools import wraps
from config import config
from sqlalchemy.orm import joinedload, selectinload
import re
from collections import defaultdict
import time
import secrets
from flask_migrate import Migrate


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
@rate_limit(max_requests=20, window_seconds=60)  # 20 requests per minute
def record_attendance():
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    if check_session_timeout():
        return jsonify({'error': 'Phiên đăng nhập đã hết hạn'}), 401
    update_session_activity()
    data = request.get_json()
    print('DEBUG raw:', data)
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
    attendance = Attendance(
        user_id=user.id,
        date=date,
        break_time=break_time,
        is_holiday=is_holiday,
        holiday_type=holiday_type,
        status='pending',
        overtime_before_22="0:00",
        overtime_after_22="0:00",
        shift_code=shift_code
    )
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
            month = validate_int(request.args.get('month'), min_val=1, max_val=12) if request.args.get('month') else None
            year = validate_int(request.args.get('year'), min_val=2000, max_val=2100) if request.args.get('year') else None
            if page is None or per_page is None:
                return jsonify({'error': 'Tham số phân trang không hợp lệ'}), 400
            q = Attendance.query.filter_by(approved=True)
            if month and year:
                q = q.filter(db.extract('month', Attendance.date) == month, db.extract('year', Attendance.date) == year)
            elif month:
                q = q.filter(db.extract('month', Attendance.date) == month)
            elif year:
                q = q.filter(db.extract('year', Attendance.date) == year)
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
    
    # ADMIN có thể duyệt tất cả
    if current_role == 'ADMIN':
        return True, ""
    
    # MANAGER có thể duyệt nhân viên cùng phòng ban
    if current_role == 'MANAGER':
        if not attendance.user or attendance.user.department != user.department:
            return False, "Bạn chỉ có thể phê duyệt chấm công của nhân viên cùng phòng ban"
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
    users = User.query.all()
    # Calculate statistics
    admin_count = sum(1 for user in users if 'ADMIN' in user.roles.split(','))
    active_count = sum(1 for user in users if user.is_active)
    department_count = len(set(user.department for user in users))
    return render_template('admin/users.html', users=users, admin_count=admin_count, active_count=active_count, department_count=department_count)

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
    return render_template('admin/edit_user.html', user=user)

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
            return render_template('admin/create_user.html')
    
    return render_template('admin/create_user.html')

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
        'date': attendance.date.strftime('%Y-%m-%d'),
        'check_in': attendance.check_in.strftime('%Y-%m-%d %H:%M:%S') if attendance.check_in else None,
        'check_out': attendance.check_out.strftime('%Y-%m-%d %H:%M:%S') if attendance.check_out else None,
        'break_time': attendance.break_time,
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
    if action not in ['approve', 'reject']:
        return jsonify({'error': 'Hành động không hợp lệ'}), 400
    if action == 'reject' and not reason:
        return jsonify({'error': 'Lý do từ chối không hợp lệ'}), 400
    attendance = Attendance.query.get(attendance_id)
    if not attendance:
        return jsonify({'error': 'Không tìm thấy bản ghi chấm công'}), 404
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
            message = 'Đã chuyển lên Quản lý phê duyệt'
        elif current_role == 'MANAGER':
            if attendance.status != 'pending_manager':
                return jsonify({'error': 'Bản ghi chưa được Trưởng nhóm phê duyệt'}), 400
            attendance.status = 'pending_admin'
            attendance.approved_by = user.id
            attendance.approved_at = datetime.now()
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
        query = query.join(Attendance.user).filter(User.name.ilike(f'%{search}%'))
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
            'date': att.date.strftime('%Y-%m-%d'),
            'check_in': att.check_in.strftime('%H:%M') if att.check_in else None,
            'check_out': att.check_out.strftime('%H:%M') if att.check_out else None,
            'break_time': format_hours_minutes(att.break_time),
            'total_work_hours': format_hours_minutes(att.total_work_hours),
            'work_hours_display': format_hours_minutes(att.calculate_regular_work_hours()),
            'overtime_before_22': att.overtime_before_22,
            'overtime_after_22': att.overtime_after_22,
            'holiday_type': translate_holiday_type(att.holiday_type),
            'user_name': att.user.name if att.user else '',
            'department': att.user.department if att.user else '',
            'note': att.note,
            'status': att.status,
            'approved': att.approved
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
                'date': r.date.strftime('%Y-%m-%d'),
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        convert_overtime_to_hhmm()
    
    # Production-ready settings
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    app.run(debug=debug_mode, host=host, port=port) 