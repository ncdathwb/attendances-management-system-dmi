"""
Database models for the attendance management system
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, time, timedelta
import logging

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """User model for employees, managers, and admins"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    password_hash = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    employee_id = db.Column(db.Integer, unique=True, nullable=False)
    roles = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    remember_token = db.Column(db.String(255), nullable=True)
    remember_token_expires = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        """Set password with hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)

    def has_role(self, role):
        """Check if user has specific role"""
        return role in self.roles.split(',')

    def get_roles_list(self):
        """Get list of user roles"""
        return [role.strip() for role in self.roles.split(',')]

    def __repr__(self):
        return f'<User {self.name} ({self.employee_id})>'

class Attendance(db.Model):
    """Attendance records model"""
    __tablename__ = 'attendances'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    check_in = db.Column(db.DateTime, nullable=True)
    check_out = db.Column(db.DateTime, nullable=True)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    note = db.Column(db.Text, nullable=True)
    break_time = db.Column(db.Float, nullable=False, default=1.0)
    is_holiday = db.Column(db.Boolean, nullable=False, default=False)
    holiday_type = db.Column(db.String(20), nullable=True)
    total_work_hours = db.Column(db.Float, nullable=True)
    regular_work_hours = db.Column(db.Float, nullable=True)
    overtime_before_22 = db.Column(db.String(5), nullable=True)
    overtime_after_22 = db.Column(db.String(5), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    shift_code = db.Column(db.String(10), nullable=True)  # Mã ca: 1,2,3,4
    shift_start = db.Column(db.Time, nullable=True)       # Giờ vào ca chuẩn
    shift_end = db.Column(db.Time, nullable=True)         # Giờ ra ca chuẩn
    signature = db.Column(db.Text, nullable=True)  # Lưu chữ ký base64
    team_leader_signature = db.Column(db.Text, nullable=True)  # Chữ ký trưởng nhóm
    manager_signature = db.Column(db.Text, nullable=True)  # Chữ ký quản lý

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('attendances', lazy=True))
    approver = db.relationship('User', foreign_keys=[approved_by], backref=db.backref('approved_attendances', lazy=True))

    def update_work_hours(self):
        """Calculate and update work hours and overtime"""
        if not self.check_in or not self.check_out:
            self.total_work_hours = None
            self.overtime_before_22 = "0:00"
            self.overtime_after_22 = "0:00"
            self.regular_work_hours = None
            return

        def minutes_to_hhmm(minutes):
            if minutes < 0: minutes = 0
            hours = int(minutes // 60)
            mins = int(minutes % 60)
            return f"{hours}:{mins:02d}"

        # Định nghĩa 4 ca chuẩn
        shift_map = {
            '1': (time(7,30), time(16,30)),
            '2': (time(8,0), time(17,0)),
            '3': (time(9,0), time(18,0)),
            '4': (time(11,0), time(22,0)),
        }
        
        # Nếu có mã ca, chỉ tự động gán giờ vào/ra ca chuẩn nếu chưa có giá trị
        if self.shift_code in shift_map:
            if not self.shift_start:
                self.shift_start = shift_map[self.shift_code][0]
            if not self.shift_end:
                self.shift_end = shift_map[self.shift_code][1]

        # 1. Tổng giờ làm: thời gian thực tế trừ giờ nghỉ
        # Đảm bảo check_in và check_out là datetime, cùng ngày hoặc check_out > check_in
        logger = logging.getLogger("attendance_logic")
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            handler = logging.FileHandler("attendance_debug.log")
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            logger.addHandler(handler)

        # Log giá trị đầu vào
        logger.debug(f"check_in: {self.check_in} ({type(self.check_in)})")
        logger.debug(f"check_out: {self.check_out} ({type(self.check_out)})")
        logger.debug(f"break_time: {self.break_time}")

        # Tính duration thực tế
        duration = (self.check_out - self.check_in).total_seconds() / 3600
        logger.debug(f"duration (giờ vào đến giờ ra): {duration}")
        total_work = duration - self.break_time
        logger.debug(f"total_work_hours (sau khi trừ nghỉ): {total_work}")
        self.total_work_hours = round(max(0, total_work), 2)

        if self.shift_start and self.shift_end:
            ca_start = datetime.combine(self.date, self.shift_start)
            if self.shift_end > self.shift_start:
                ca_end = datetime.combine(self.date, self.shift_end)
            else:
                ca_end = datetime.combine(self.date, self.shift_end) + timedelta(days=1)
            twenty_two = datetime.combine(self.date, time(22, 0))
            if self.shift_end <= time(22, 0) and self.shift_end < self.shift_start:
                twenty_two += timedelta(days=1)

            # 2. Giờ công thường: xử lý theo loại ngày
            overlap_start = max(self.check_in, ca_start)
            overlap_end = min(self.check_out, ca_end)
            time_in_shift = round(max(0, (overlap_end - overlap_start).total_seconds() / 3600), 2) if overlap_end > overlap_start else 0
            
            # Xử lý giờ công chính thức theo loại ngày
            if self.holiday_type == 'vietnamese_holiday':
                # Ngày lễ Việt Nam: luôn được tặng 8 giờ công chính thức
                self.regular_work_hours = 8.0
                break_time_for_overtime = self.break_time
            elif self.holiday_type == 'weekend':
                # Cuối tuần: giờ công chính thức = 0, giờ nghỉ trừ vào tăng ca
                self.regular_work_hours = 0.0
                break_time_for_overtime = self.break_time
            else:
                # Ngày thường: giờ nghỉ trừ vào giờ công thường, tối đa 8 giờ
                regular_hours = round(max(0, time_in_shift - self.break_time), 2)
                self.regular_work_hours = min(regular_hours, 8.0)  # Giới hạn tối đa 8 giờ cho ngày thường
                break_time_for_overtime = 0

            # 3. Tăng ca trước 22h: thời gian từ check_in đến 22:00 trừ giờ nghỉ
            if self.holiday_type in ['vietnamese_holiday', 'weekend']:
                # Ngày lễ và cuối tuần: tính thời gian từ check_in đến 22:00
                check_in_time = self.check_in.time()
                check_out_time = self.check_out.time()
                
                # Tính tăng ca trước 22h
                if check_out_time <= time(22, 0):
                    # Toàn bộ thời gian làm việc trước 22h
                    overtime_before_22 = (self.check_out - self.check_in).total_seconds() / 3600
                else:
                    # Tính thời gian từ check_in đến 22:00
                    if check_in_time < time(22, 0):
                        # Có thời gian trước 22h
                        end_time = time(22, 0)
                        start_time = check_in_time
                        overtime_before_22 = (end_time.hour - start_time.hour) + (end_time.minute - start_time.minute) / 60
                    else:
                        # Không có thời gian trước 22h
                        overtime_before_22 = 0
                
                # Trừ giờ nghỉ vào tăng ca trước 22h
                overtime_before_22 = max(0, overtime_before_22 - self.break_time)
            else:
                # Ngày thường: tính theo logic cũ
                ot1_start = max(self.check_in, ca_end)
                ot1_end = min(self.check_out, twenty_two)
                overtime_before_22 = max(0, (ot1_end - ot1_start).total_seconds() / 3600) if ot1_end > ot1_start else 0
            
            self.overtime_before_22 = minutes_to_hhmm(overtime_before_22 * 60)

            # 4. Tăng ca sau 22h: thời gian từ 22:00 đến khi ra
            if self.holiday_type in ['vietnamese_holiday', 'weekend']:
                # Ngày lễ và cuối tuần: tính thời gian sau 22h
                if check_out_time > time(22, 0):
                    # Có thời gian sau 22h
                    start_time = time(22, 0)
                    overtime_after_22 = (check_out_time.hour - start_time.hour) + (check_out_time.minute - start_time.minute) / 60
                else:
                    # Không có thời gian sau 22h
                    overtime_after_22 = 0
            else:
                # Ngày thường: tính theo logic cũ
                ot2_start = max(self.check_in, twenty_two)
                ot2_end = self.check_out
                overtime_after_22 = max(0, (ot2_end - ot2_start).total_seconds() / 3600) if ot2_end > ot2_start else 0
            
            self.overtime_after_22 = minutes_to_hhmm(overtime_after_22 * 60)
        else:
            # Nếu không có ca chuẩn, coi toàn bộ là giờ công thường (tối đa 8 giờ cho ngày thường)
            if self.holiday_type == 'vietnamese_holiday':
                self.regular_work_hours = 8.0
            elif self.holiday_type == 'weekend':
                self.regular_work_hours = 0.0
            else:
                # Ngày thường: tối đa 8 giờ
                self.regular_work_hours = min(self.total_work_hours, 8.0) if self.total_work_hours else 0.0
            self.overtime_before_22 = "0:00"
            self.overtime_after_22 = "0:00"

    def calculate_regular_work_hours(self):
        """Calculate regular work hours (excluding overtime)"""
        if not self.check_in or not self.check_out:
            return 0.0

        if self.holiday_type == 'vietnamese_holiday':
            return 8.0  # Ngày lễ Việt Nam luôn được tặng 8 giờ công chính thức
        if self.holiday_type == 'weekend':
            return 0.0  # Cuối tuần không có giờ công chính thức

        # Ngày thường: tính giờ công và giới hạn tối đa 8 giờ
        if self.shift_start and self.shift_end:
            ca_start = datetime.combine(self.date, self.shift_start)
            if self.shift_end > self.shift_start:
                ca_end = datetime.combine(self.date, self.shift_end)
            else:
                ca_end = datetime.combine(self.date, self.shift_end) + timedelta(days=1)
            # Lấy phần giao nhau giữa [check_in, check_out] và [shift_start, shift_end]
            overlap_start = max(self.check_in, ca_start)
            overlap_end = min(self.check_out, ca_end)
            time_in_shift = round(max(0, (overlap_end - overlap_start).total_seconds() / 3600), 2) if overlap_end > overlap_start else 0
            # Giờ công chính thức = thời gian trong ca - giờ nghỉ, tối đa 8 giờ
            regular_hours = round(max(0, time_in_shift - self.break_time), 2)
            return min(regular_hours, 8.0)  # Giới hạn tối đa 8 giờ cho ngày thường
        else:
            # Nếu không có ca chuẩn, tính theo cách cũ
            actual_work_duration_hours = (self.check_out - self.check_in).total_seconds() / 3600 - self.break_time
            regular_hours = round(max(0, actual_work_duration_hours), 2)
            return min(regular_hours, 8.0)  # Giới hạn tối đa 8 giờ cho ngày thường

    def to_dict(self):
        """Convert attendance record to dictionary"""
        work_hours_val = self.calculate_regular_work_hours()
        return {
            'id': self.id,
            'date': self.date.strftime('%d/%m/%Y'),
            'check_in': self.check_in.strftime('%H:%M') if self.check_in else None,
            'check_out': self.check_out.strftime('%H:%M') if self.check_out else None,
            'break_time': self._format_hours_minutes(self.break_time),
            'is_holiday': self.is_holiday,
            'holiday_type': self._translate_holiday_type(self.holiday_type),
            'total_work_hours': self._format_hours_minutes(self.total_work_hours) if self.total_work_hours is not None else "0:00",
            'work_hours_display': self._format_hours_minutes(work_hours_val),
            'overtime_before_22': self.overtime_before_22,
            'overtime_after_22': self.overtime_after_22,
            'note': self.note,
            'status': self.status,
            'approved': self.approved,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.strftime('%d/%m/%Y %H:%M:%S') if self.approved_at else None,
            'approver_name': self.approver.name if self.approver else None,
            'shift_code': self.shift_code,
            'shift_start': self.shift_start.strftime('%H:%M') if self.shift_start else None,
            'shift_end': self.shift_end.strftime('%H:%M') if self.shift_end else None,
            'signature': self.signature,
            'team_leader_signature': self.team_leader_signature,
            'manager_signature': self.manager_signature
        }

    @staticmethod
    def _format_hours_minutes(hours):
        """Format hours to HH:MM format"""
        try:
            if hours is None:
                return "0:00"
            if isinstance(hours, str):
                hours = float(hours)
            if hours != hours or hours < 0:  # Check for NaN or negative
                return "0:00"
            h = int(hours)
            m = int(round((hours - h) * 60))
            if m == 60:
                h += 1
                m = 0
            return f"{h}:{m:02d}"
        except Exception:
            return "0:00"

    @staticmethod
    def _translate_holiday_type(holiday_type_en):
        """Translate holiday type from English to Vietnamese"""
        if not holiday_type_en:
            return '-'
        translations = {
            'normal': 'Ngày thường',
            'weekend': 'Cuối tuần',
            'vietnamese_holiday': 'Lễ Việt Nam',
            'japanese_holiday': 'Lễ Nhật Bản'
        }
        return translations.get(holiday_type_en, holiday_type_en)

    def __repr__(self):
        return f'<Attendance {self.user.name if self.user else "Unknown"} - {self.date}>'

class Request(db.Model):
    """Request model for leave, overtime requests, etc."""
    __tablename__ = 'requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    current_approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    step = db.Column(db.String(20), nullable=False, default='leader')
    reject_reason = db.Column(db.Text, nullable=True)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('requests', lazy=True))
    current_approver = db.relationship('User', foreign_keys=[current_approver_id], backref=db.backref('approvals', lazy=True))

    def __repr__(self):
        return f'<Request {self.request_type} - {self.user.name if self.user else "Unknown"}>'

class Department(db.Model):
    """Department model for organizational structure"""
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    manager = db.relationship('User', foreign_keys=[manager_id], backref=db.backref('managed_departments', lazy=True))
    # Note: employees relationship removed to avoid conflict with User.department field

    def __repr__(self):
        return f'<Department {self.name}>'

class AuditLog(db.Model):
    """Audit log for tracking changes"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=True)
    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))

    def __repr__(self):
        return f'<AuditLog {self.action} on {self.table_name}>' 