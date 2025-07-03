from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from functools import wraps
from config import config

app = Flask(__name__)

# Load configuration
config_name = os.environ.get('FLASK_CONFIG') or 'default'
app.config.from_object(config[config_name])

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password_hash = db.Column(db.String(120), nullable=False)
    original_password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    employee_id = db.Column(db.Integer, unique=True, nullable=False)
    roles = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.original_password = password

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role):
        return role in self.roles.split(',')

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    check_in = db.Column(db.DateTime, nullable=True)
    check_out = db.Column(db.DateTime, nullable=True)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected
    note = db.Column(db.Text, nullable=True)
    break_time = db.Column(db.Float, nullable=False, default=1.0)  # Break time in hours
    is_holiday = db.Column(db.Boolean, nullable=False, default=False)  # Is it a holiday
    holiday_type = db.Column(db.String(20), nullable=True)  # Type of holiday (weekend, vietnamese_holiday, etc)
    total_work_hours = db.Column(db.Float, nullable=True)  # Total work hours for the day
    overtime_before_22 = db.Column(db.String(5), nullable=True)  # Overtime hours before 22:00
    overtime_after_22 = db.Column(db.String(5), nullable=True)  # Overtime hours after 22:00
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)  # True: đã phê duyệt, False: chưa phê duyệt

    user = db.relationship('User', backref=db.backref('attendances', lazy=True))

    def update_work_hours(self):
        if not self.check_in or not self.check_out:
            self.total_work_hours = None
            self.overtime_before_22 = "0:00"
            self.overtime_after_22 = "0:00"
            return

        def minutes_to_hhmm(minutes):
            if minutes < 0: minutes = 0
            hours = int(minutes // 60)
            mins = int(minutes % 60)
            return f"{hours}:{mins:02d}"

        # Tổng giờ làm thực tế (đã trừ giờ nghỉ)
        total_work_duration_hours = (self.check_out - self.check_in).total_seconds() / 3600 - self.break_time
        self.total_work_hours = round(max(0, total_work_duration_hours), 2)
        
        # Logic cho ngày cuối tuần và ngày lễ
        if self.holiday_type in ['weekend', 'vietnamese_holiday']:
            twenty_two_oclock = self.check_in.replace(hour=22, minute=0, second=0, microsecond=0)
            
            # Tính tăng ca sau 22h
            ot_after_22_minutes = 0
            if self.check_out > twenty_two_oclock:
                ot_after_22_start = max(self.check_in, twenty_two_oclock)
                ot_after_22_minutes = (self.check_out - ot_after_22_start).total_seconds() / 60
            
            # Tính tổng giờ làm (đã trừ nghỉ)
            total_work_minutes = max(0, total_work_duration_hours * 60)
            
            # Tăng ca trước 22h là tổng giờ trừ đi tăng ca sau 22h
            ot_before_22_minutes = total_work_minutes - ot_after_22_minutes

            self.overtime_before_22 = minutes_to_hhmm(ot_before_22_minutes)
            self.overtime_after_22 = minutes_to_hhmm(ot_after_22_minutes)
        else:
            # Logic cho ngày thường
            ca_gio = [
                (7, 30, 16, 30), (8, 0, 17, 0), (9, 0, 18, 0), (11, 0, 22, 0)
            ]
            ca_batdau = self.check_in.replace(hour=7, minute=30, second=0, microsecond=0)
            ca_ketthuc = self.check_in.replace(hour=16, minute=30, second=0, microsecond=0)
            for h_in, m_in, h_out, m_out in ca_gio:
                ca_start = self.check_in.replace(hour=h_in, minute=m_in, second=0, microsecond=0)
                if abs((self.check_in - ca_start).total_seconds()) <= 3600:
                    ca_batdau = ca_start
                    ca_ketthuc = self.check_in.replace(hour=h_out, minute=m_out, second=0, microsecond=0)
                    break

            # Tăng ca trước 22h: từ sau giờ kết thúc ca đến 22:00
            overtime_start = max(self.check_in, ca_ketthuc)
            overtime_end = min(self.check_out, self.check_in.replace(hour=22, minute=0, second=0, microsecond=0))
            overtime_before_22 = (overtime_end - overtime_start).total_seconds() / 60 if overtime_end > overtime_start else 0

            # Tăng ca sau 22h
            after_22 = self.check_in.replace(hour=22, minute=0, second=0, microsecond=0)
            overtime_after_22 = (self.check_out - after_22).total_seconds() / 60 if self.check_out > after_22 else 0
            
            self.overtime_before_22 = minutes_to_hhmm(overtime_before_22)
            self.overtime_after_22 = minutes_to_hhmm(overtime_after_22)

    def calculate_regular_work_hours(self):
        if not self.check_in or not self.check_out:
            return 0.0

        # Nếu là ngày lễ hoặc cuối tuần, giờ công = 0
        if self.holiday_type in ['weekend', 'vietnamese_holiday']:
            return 0.0

        # Logic cho ngày thường: tính giờ làm việc trong ca chuẩn
        ca_gio = [
            (7, 30, 16, 30), (8, 0, 17, 0), (9, 0, 18, 0), (11, 0, 22, 0)
        ]
        
        # Xác định ca làm việc
        ca_batdau = self.check_in.replace(hour=7, minute=30, second=0, microsecond=0)
        ca_ketthuc = self.check_in.replace(hour=16, minute=30, second=0, microsecond=0)
        for h_in, m_in, h_out, m_out in ca_gio:
            ca_start = self.check_in.replace(hour=h_in, minute=m_in, second=0, microsecond=0)
            if abs((self.check_in - ca_start).total_seconds()) <= 3600: # Tìm ca dựa trên giờ vào
                ca_batdau = ca_start
                ca_ketthuc = self.check_in.replace(hour=h_out, minute=m_out, second=0, microsecond=0)
                break
        
        # Tính thời gian làm việc thực tế trong ca
        overlap_start = max(self.check_in, ca_batdau)
        overlap_end = min(self.check_out, ca_ketthuc)
        
        in_shift_duration_hours = 0
        if overlap_end > overlap_start:
            in_shift_duration_hours = (overlap_end - overlap_start).total_seconds() / 3600
        
        # Trừ giờ nghỉ khỏi thời gian làm trong ca
        regular_hours = max(0, in_shift_duration_hours - self.break_time)
        
        return round(regular_hours, 2)

    def to_dict(self):
        # Tính toán giờ công trước khi chuyển đổi
        work_hours_val = self.calculate_regular_work_hours()

        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d'),
            'check_in': self.check_in.strftime('%H:%M:%S') if self.check_in else None,
            'check_out': self.check_out.strftime('%H:%M:%S') if self.check_out else None,
            'status': self.status,
            'break_time': format_hours_minutes(self.break_time) if self.break_time is not None else "0:00",
            'is_holiday': self.is_holiday,
            'holiday_type': translate_holiday_type(self.holiday_type),
            'total_work_hours': format_hours_minutes(self.total_work_hours) if self.total_work_hours is not None else "0:00",
            'work_hours_display': format_hours_minutes(work_hours_val),
            'overtime_before_22': self.overtime_before_22,
            'overtime_after_22': self.overtime_after_22,
            'note': self.note,
            'approved': self.approved
        }

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    request_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    current_approver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    step = db.Column(db.String(20), nullable=False, default='leader')
    reject_reason = db.Column(db.Text, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('requests', lazy=True))
    current_approver = db.relationship('User', foreign_keys=[current_approver_id], backref=db.backref('approvals', lazy=True))

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
def login():
    if request.method == 'POST':
        employee_id = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        try:
            employee_id = int(employee_id)
            user = User.query.filter_by(employee_id=employee_id).first()
            
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['name'] = user.name
                session['employee_id'] = user.employee_id
                session['roles'] = user.roles.split(',')
                session['current_role'] = user.roles.split(',')[0]
                response = redirect(url_for('dashboard'))
                
                if remember:
                    # Set cookies to expire in 30 days
                    response.set_cookie('remembered_username', str(employee_id), max_age=30*24*60*60)
                    response.set_cookie('remembered_password', password, max_age=30*24*60*60)
                else:
                    # Clear any existing cookies
                    response.delete_cookie('remembered_username')
                    response.delete_cookie('remembered_password')
                
                flash('Đăng nhập thành công!', 'success')
                return response
            
            flash('Mã nhân viên hoặc mật khẩu không đúng!', 'error')
        except ValueError:
            flash('Mã nhân viên không hợp lệ!', 'error')
    
    return render_template('login.html', messages=get_flashed_messages(with_categories=False))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        print("No user_id in session, redirecting to login")  # Debug log
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        print("User not found, clearing session")  # Debug log
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('login'))
    
    # Đảm bảo session có đầy đủ thông tin
    if 'roles' not in session:
        session['roles'] = user.roles.split(',')
    if 'current_role' not in session:
        session['current_role'] = user.roles.split(',')[0]
    if 'name' not in session:
        session['name'] = user.name
    if 'employee_id' not in session:
        session['employee_id'] = user.employee_id
    
    print("Rendering dashboard for user:", user.name)  # Debug log
    return render_template('dashboard.html', user=user)

@app.route('/api/attendance', methods=['POST'])
def record_attendance():
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    data = request.get_json()
    date = data.get('date')
    check_in = data.get('check_in')
    check_out = data.get('check_out')
    note = data.get('note', '')
    break_time = data.get('break_time', 1.0)
    is_holiday = data.get('is_holiday', False)
    holiday_type = data.get('holiday_type')
    print("Received data:", data)  # Debug log
    if not date or date.strip() == '':
        return jsonify({'error': 'Vui lòng chọn ngày chấm công'}), 400
    if not holiday_type:
        return jsonify({'error': 'Vui lòng chọn loại ngày'}), 400
    if not check_in or not check_out:
        return jsonify({'error': 'Vui lòng nhập đầy đủ giờ vào và giờ ra'}), 400
    try:
        # Parse date and times
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()
        check_in_time = datetime.strptime(f"{date}T{check_in}", '%Y-%m-%dT%H:%M')
        check_out_time = datetime.strptime(f"{date}T{check_out}", '%Y-%m-%dT%H:%M')
        print(f"Parsed times - Check in: {check_in_time}, Check out: {check_out_time}")  # Debug log
        now = datetime.now()
        if check_in_time > now:
            return jsonify({'error': 'Không thể chấm công giờ vào sau thời gian thực!'}), 400
        if check_out_time > now:
            return jsonify({'error': 'Không thể chấm công giờ ra sau thời gian thực!'}), 400
        if check_out_time <= check_in_time:
            return jsonify({'error': 'Giờ ra phải sau giờ vào!'}), 400
        
        work_duration_seconds = (check_out_time - check_in_time).total_seconds()
        break_time_seconds = break_time * 3600
        if break_time_seconds >= work_duration_seconds:
            return jsonify({'error': 'Giờ nghỉ không thể lớn hơn hoặc bằng tổng thời gian làm việc!'}), 400
            
    except ValueError as e:
        print(f"ValueError: {str(e)}")  # Debug log
        return jsonify({'error': 'Định dạng ngày hoặc giờ không hợp lệ'}), 400
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    # Kiểm tra đã có bản ghi chấm công cho ngày này chưa
    existing_attendance = Attendance.query.filter_by(user_id=user.id, date=selected_date).first()
    if existing_attendance:
        return jsonify({'error': 'Bạn đã chấm công cho ngày này rồi, không thể chấm công 2 lần trong 1 ngày.'}), 400
    
    # Kiểm tra ngày không được trong tương lai
    if selected_date > datetime.now().date():
        return jsonify({'error': 'Không thể chấm công cho ngày trong tương lai!'}), 400
    attendance = Attendance(
        user_id=user.id,
        date=selected_date,
        break_time=break_time,
        is_holiday=is_holiday,
        holiday_type=holiday_type,
        status='pending',
        overtime_before_22="0:00",
        overtime_after_22="0:00"
    )
    db.session.add(attendance)
    attendance.check_in = check_in_time
    attendance.check_out = check_out_time
    attendance.note = note
    attendance.update_work_hours()
    try:
        db.session.commit()
        return jsonify({
            'message': 'Chấm công thành công',
            'work_hours': attendance.total_work_hours,
            'overtime_before_22': attendance.overtime_before_22,
            'overtime_after_22': attendance.overtime_after_22
        })
    except Exception as e:
        print(f"Database error: {str(e)}")  # Debug log
        db.session.rollback()
        return jsonify({'error': 'Đã xảy ra lỗi khi lưu dữ liệu'}), 500

@app.route('/api/attendance/history')
def get_attendance_history():
    print("Session data:", session)  # Debug log
    if 'user_id' not in session:
        print("No user_id in session")  # Debug log
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    try:
        user = User.query.get(session['user_id'])
        print("User found:", user)  # Debug log
        if not user:
            return jsonify({'error': 'Không tìm thấy người dùng'}), 404
        
        # Kiểm tra quyền truy cập
        current_role = session.get('current_role', user.roles.split(',')[0])
        
        # Nếu có ?all=1 thì chỉ ADMIN mới được truy cập
        if request.args.get('all') == '1':
            if current_role != 'ADMIN':
                return jsonify({'error': 'Chỉ quản trị viên mới có thể xem lịch sử chấm công toàn bộ'}), 403
            
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 10))
            month = request.args.get('month')
            year = request.args.get('year')
            
            # ADMIN có thể xem tất cả records đã được phê duyệt
            # Sửa lỗi: Hiển thị của tất cả user, không chỉ của admin
            q = Attendance.query.filter_by(approved=True)

            if month and year:
                q = q.filter(db.extract('month', Attendance.date) == int(month), db.extract('year', Attendance.date) == int(year))
            elif month:
                q = q.filter(db.extract('month', Attendance.date) == int(month))
            elif year:
                q = q.filter(db.extract('year', Attendance.date) == int(year))

            total = q.count()
            attendances = q.order_by(Attendance.date.desc()).offset((page-1)*per_page).limit(per_page).all()
            
            history = []
            for att in attendances:
                att_user = User.query.get(att.user_id)
                att_dict = att.to_dict()
                att_dict['user_name'] = att_user.name if att_user else '-'
                att_dict['department'] = att_user.department if att_user else '-'
                history.append(att_dict)

            return jsonify({
                'total': total,
                'page': page,
                'per_page': per_page,
                'data': history
            })
        else:
            # Lấy lịch sử chấm công của tháng hiện tại (tất cả records để nhân viên thấy trạng thái)
            current_month = datetime.now().month
            current_year = datetime.now().year
            attendances = Attendance.query.filter_by(user_id=user.id)\
                .filter(db.extract('month', Attendance.date) == current_month)\
                .filter(db.extract('year', Attendance.date) == current_year)\
                .order_by(Attendance.date.desc())\
                .all()
        print("Found attendances:", len(attendances))  # Debug log
        history = []
        for att in attendances:
            history.append(att.to_dict())
        return jsonify(history)
    except Exception as e:
        print(f"Error in get_attendance_history: {str(e)}")  # Debug log
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
    
    attendance = Attendance.query.get(attendance_id)
    if not attendance:
        return False, "Không tìm thấy bản ghi chấm công"
    
    # ADMIN và MANAGER có thể duyệt tất cả
    if current_role in ['ADMIN', 'MANAGER']:
        return True, ""
    
    # TEAM_LEADER có thể duyệt nhân viên cùng phòng ban (bao gồm cả bản thân)
    if current_role == 'TEAM_LEADER':
        attendance_user = User.query.get(attendance.user_id)
        if not attendance_user or attendance_user.department != user.department:
            return False, "Bạn chỉ có thể phê duyệt chấm công của nhân viên cùng phòng ban"
        
        return True, ""
    
    return False, "Bạn không có quyền phê duyệt chấm công"

def require_role(required_role):
    """Decorator to require specific role for route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                return redirect(url_for('login'))
            if not has_role(session['user_id'], required_role):
                flash('Bạn không có quyền truy cập trang này', 'error')
                return redirect(url_for('index'))
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
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@require_admin
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            user.name = request.form['name']
            user.roles = request.form['role']
            user.department = request.form['department']
            
            db.session.commit()
            flash('Cập nhật người dùng thành công', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('edit_user', user_id=user_id))
    
    return render_template('admin/edit_user.html', user=user)

@app.route('/switch-role', methods=['POST'])
def switch_role():
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    
    data = request.get_json()
    role = data.get('role')
    if not role:
        return jsonify({'error': 'Thiếu vai trò'}), 400
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    
    # Kiểm tra xem user có role này không
    if role not in user.roles.split(','):
        return jsonify({'error': 'Vai trò không hợp lệ'}), 400
    
    # Cập nhật session
    session['current_role'] = role
    
    return jsonify({'message': 'Đã chuyển vai trò thành công'}), 200

# API endpoint để submit request
@app.route('/api/request/submit', methods=['POST'])
def submit_request():
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    
    data = request.get_json()
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    
    # Tìm leader của phòng ban
    leader = User.query.filter_by(department=user.department, roles='TEAM_LEADER').first()
    if not leader:
        return jsonify({'error': 'Không tìm thấy trưởng nhóm cho phòng ban này'}), 400
    
    new_request = Request(
        user_id=user.id,
        request_type=data.get('request_type'),
        start_date=datetime.strptime(data.get('start_date'), '%Y-%m-%d').date(),
        end_date=datetime.strptime(data.get('end_date'), '%Y-%m-%d').date(),
        reason=data.get('reason'),
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
    
    data = request.get_json()
    action = data.get('action')  # 'approve' hoặc 'reject'
    reason = data.get('reason', '')
    
    req = Request.query.get_or_404(request_id)
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
    att = Attendance.query.get(attendance_id)
    if not att or att.user_id != session['user_id']:
        return jsonify({'error': 'Không tìm thấy bản ghi hoặc không có quyền xóa'}), 404
    if att.approved:
        return jsonify({'error': 'Bản ghi đã được phê duyệt, không thể xóa!'}), 400
    try:
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
    
    attendance = Attendance.query.get(attendance_id)
    if not attendance or attendance.user_id != session['user_id']:
        return jsonify({'error': 'Không tìm thấy bản ghi hoặc không có quyền truy cập'}), 404
    
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
        'status': attendance.status
    })

@app.route('/api/attendance/<int:attendance_id>', methods=['PUT'])
def update_attendance(attendance_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    
    attendance = Attendance.query.get(attendance_id)
    if not attendance or attendance.user_id != session['user_id']:
        return jsonify({'error': 'Không tìm thấy bản ghi hoặc không có quyền truy cập'}), 404
    
    if attendance.approved:
        return jsonify({'error': 'Bản ghi đã được phê duyệt, không thể sửa!'}), 400
    
    data = request.get_json()
    date = data.get('date')
    check_in = data.get('check_in')
    check_out = data.get('check_out')
    note = data.get('note', '')
    break_time = data.get('break_time', 1.0)
    is_holiday = data.get('is_holiday', False)
    holiday_type = data.get('holiday_type')
    
    print("Updating attendance with data:", data)  # Debug log
    
    if not date or date.strip() == '':
        return jsonify({'error': 'Vui lòng chọn ngày chấm công'}), 400
    if not holiday_type:
        return jsonify({'error': 'Vui lòng chọn loại ngày'}), 400
    if not check_in or not check_out:
        return jsonify({'error': 'Vui lòng nhập đầy đủ giờ vào và giờ ra'}), 400
    
    try:
        # Parse date and times
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()
        check_in_time = datetime.strptime(f"{date}T{check_in}", '%Y-%m-%dT%H:%M')
        check_out_time = datetime.strptime(f"{date}T{check_out}", '%Y-%m-%dT%H:%M')
        
        # Validate time
        now = datetime.now()
        if check_out_time <= check_in_time:
            return jsonify({'error': 'Giờ ra phải sau giờ vào!'}), 400
            
        work_duration_seconds = (check_out_time - check_in_time).total_seconds()
        break_time_seconds = break_time * 3600
        if break_time_seconds >= work_duration_seconds:
            return jsonify({'error': 'Giờ nghỉ không thể lớn hơn hoặc bằng tổng thời gian làm việc!'}), 400
            
    except ValueError as e:
        print(f"ValueError: {str(e)}")  # Debug log
        return jsonify({'error': 'Định dạng ngày hoặc giờ không hợp lệ'}), 400
    
    # Update attendance record
    attendance.date = selected_date
    attendance.check_in = check_in_time
    attendance.check_out = check_out_time
    attendance.note = note
    attendance.break_time = break_time
    attendance.is_holiday = is_holiday
    attendance.holiday_type = holiday_type
    
    # Reset trạng thái về pending nếu record bị từ chối
    if attendance.status == 'rejected':
        attendance.status = 'pending'
    
    # Kiểm tra ngày không được trong tương lai
    if selected_date > datetime.now().date():
        return jsonify({'error': 'Không thể chấm công cho ngày trong tương lai!'}), 400
    
    attendance.update_work_hours()
    
    try:
        db.session.commit()
        message = 'Cập nhật chấm công thành công'
        
        return jsonify({
            'message': message,
            'work_hours': attendance.total_work_hours,
            'overtime_before_22': attendance.overtime_before_22,
            'overtime_after_22': attendance.overtime_after_22
        })
    except Exception as e:
        print(f"Database error: {str(e)}")  # Debug log
        db.session.rollback()
        return jsonify({'error': 'Đã xảy ra lỗi khi cập nhật dữ liệu'}), 500

@app.route('/api/attendance/<int:attendance_id>/approve', methods=['POST'])
def approve_attendance(attendance_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
        
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    
    # Kiểm tra quyền phê duyệt
    current_role = session.get('current_role', user.roles.split(',')[0])
    if current_role not in ['TEAM_LEADER', 'MANAGER', 'ADMIN']:
        return jsonify({'error': 'Bạn không có quyền phê duyệt chấm công'}), 403
    
    # Kiểm tra permission chi tiết
    has_permission, error_message = check_approval_permission(user.id, attendance_id, current_role)
    if not has_permission:
        return jsonify({'error': error_message}), 403
        
    data = request.get_json()
    action = data.get('action')  # 'approve' hoặc 'reject'
    reason = data.get('reason', '')
    
    attendance = Attendance.query.get(attendance_id)
    if not attendance:
        return jsonify({'error': 'Không tìm thấy bản ghi chấm công'}), 404
        
    if attendance.approved:
        return jsonify({'error': 'Bản ghi đã được phê duyệt hoàn tất'}), 400
        
    if action == 'approve':
        if current_role == 'TEAM_LEADER':
            # Trưởng nhóm duyệt -> chuyển cho Manager, không thông báo cho nhân viên
            if attendance.status != 'pending':
                return jsonify({'error': 'Bản ghi không ở trạng thái chờ duyệt'}), 400
            attendance.status = 'pending_manager'
            message = 'Đã chuyển lên Quản lý phê duyệt'
            print(f"TEAM_LEADER approved attendance {attendance_id}, status changed to: {attendance.status}")
        elif current_role == 'MANAGER':
            # Manager duyệt -> chuyển cho Admin
            if attendance.status != 'pending_manager':
                return jsonify({'error': 'Bản ghi chưa được Trưởng nhóm phê duyệt'}), 400
            attendance.status = 'pending_admin'
            message = 'Đã chuyển lên Admin phê duyệt'
            print(f"MANAGER approved attendance {attendance_id}, status changed to: {attendance.status}")
        elif current_role == 'ADMIN':
            # Admin duyệt -> hoàn tất
            if attendance.status not in ['pending_manager', 'pending_admin']:
                return jsonify({'error': 'Bản ghi chưa được cấp dưới phê duyệt'}), 400
            attendance.status = 'approved'
            attendance.approved = True
            message = 'Phê duyệt hoàn tất'
            print(f"ADMIN approved attendance {attendance_id}, status changed to: {attendance.status}, approved: {attendance.approved}")
    else:  # reject
        attendance.status = 'rejected'
        # Ghi đè ghi chú cũ bằng lý do từ chối mới
        attendance.note = f"Bị từ chối bởi {current_role}: {reason}"
        message = 'Từ chối thành công'
        print(f"{current_role} rejected attendance {attendance_id}, status changed to: {attendance.status}")
        
    try:
        db.session.commit()
        return jsonify({
            'message': message
        })
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
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'total': 0, 'page': 1, 'per_page': 10, 'data': []})
    current_role = session.get('current_role', user.roles.split(',')[0])
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    search = request.args.get('search', '').strip()
    department = request.args.get('department', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    if current_role == 'TEAM_LEADER':
        # TEAM_LEADER chỉ thấy bản ghi pending ban đầu
        query = Attendance.query.filter_by(approved=False, status='pending')
        # Cho phép leader duyệt nhân viên trong cùng phòng ban (bao gồm cả bản thân)
        team_users = User.query.filter(User.department == user.department).all()
        team_user_ids = [u.id for u in team_users]
        query = query.filter(Attendance.user_id.in_(team_user_ids))
    elif current_role == 'MANAGER':
        # MANAGER chỉ thấy bản ghi đã được TEAM_LEADER duyệt
        query = Attendance.query.filter_by(approved=False, status='pending_manager')
        # Bỏ điều kiện lọc user_id để MANAGER thấy tất cả bản ghi
        if department:
            user_ids = [u.id for u in User.query.filter_by(department=department)]
            query = query.filter(Attendance.user_id.in_(user_ids))
    else:  # ADMIN
        # ADMIN chỉ thấy các bản ghi đã được MANAGER duyệt và chờ mình
        query = Attendance.query.filter_by(approved=False, status='pending_admin')
        
        # Debug: In ra tất cả các status có trong database
        all_statuses = db.session.query(Attendance.status).distinct().all()
        print(f"All statuses in database: {[s[0] for s in all_statuses]}")
        
        # Debug: In ra số lượng bản ghi cho mỗi status
        for status in ['pending', 'pending_manager', 'pending_admin', 'approved', 'rejected']:
            count = Attendance.query.filter_by(status=status, approved=False).count()
            print(f"Status '{status}': {count} records")

    # Áp dụng các bộ lọc chung
    if search:
        user_ids = [u.id for u in User.query.filter(User.name.ilike(f'%{search}%'))]
        query = query.filter(Attendance.user_id.in_(user_ids))
    if date_from:
        query = query.filter(Attendance.date >= date_from)
    if date_to:
        query = query.filter(Attendance.date <= date_to)
    
    print(f"Current role: {current_role}")  # Debug log
    print(f"Query SQL: {query}")  # Debug log
    
    total = query.count()
    records = query.order_by(Attendance.date.desc()).offset((page-1)*per_page).limit(per_page).all()
    
    print(f"Found {total} records")  # Debug log
    
    result = []
    for att in records:
        emp = User.query.get(att.user_id)
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
            'user_name': emp.name if emp else '',
            'department': emp.department if emp else '',
            'note': att.note,
            'status': att.status
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
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    
    current_role = session.get('current_role', user.roles.split(',')[0])
    if current_role != 'ADMIN':
        return jsonify({'error': 'Chỉ ADMIN mới có thể truy cập endpoint này'}), 403
    
    # Lấy tất cả các status có trong database
    all_statuses = db.session.query(Attendance.status).distinct().all()
    status_counts = {}
    
    for status in ['pending', 'pending_manager', 'pending_admin', 'approved', 'rejected']:
        count = Attendance.query.filter_by(status=status).count()
        status_counts[status] = count
    
    # Lấy một số bản ghi mẫu cho mỗi status
    sample_records = {}
    for status in ['pending', 'pending_manager', 'pending_admin']:
        records = Attendance.query.filter_by(status=status).limit(5).all()
        sample_records[status] = [
            {
                'id': r.id,
                'user_id': r.user_id,
                'date': r.date.strftime('%Y-%m-%d'),
                'status': r.status,
                'approved': r.approved,
                'user_name': User.query.get(r.user_id).name if User.query.get(r.user_id) else 'Unknown'
            }
            for r in records
        ]
    
    return jsonify({
        'all_statuses': [s[0] for s in all_statuses],
        'status_counts': status_counts,
        'sample_records': sample_records
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        convert_overtime_to_hhmm()
    app.run(debug=True) 