"""
Database models for the attendance management system
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

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
    overtime_before_22 = db.Column(db.String(5), nullable=True)
    overtime_after_22 = db.Column(db.String(5), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('attendances', lazy=True))
    approver = db.relationship('User', foreign_keys=[approved_by], backref=db.backref('approved_attendances', lazy=True))

    def update_work_hours(self):
        """Calculate and update work hours and overtime"""
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

        # Total work duration (minus break time)
        total_work_duration_hours = (self.check_out - self.check_in).total_seconds() / 3600 - self.break_time
        self.total_work_hours = round(max(0, total_work_duration_hours), 2)
        
        # Logic for weekends and holidays
        if self.holiday_type in ['weekend', 'vietnamese_holiday']:
            # Tất cả thời gian làm việc trong ngày nghỉ/lễ đều là overtime
            total_work_minutes = max(0, total_work_duration_hours * 60)
            
            # Chia overtime thành trước và sau 22:00
            twenty_two_oclock = self.check_in.replace(hour=22, minute=0, second=0, microsecond=0)
            
            # Overtime after 22:00
            ot_after_22_minutes = 0
            if self.check_out > twenty_two_oclock:
                ot_after_22_start = max(self.check_in, twenty_two_oclock)
                ot_after_22_minutes = (self.check_out - ot_after_22_start).total_seconds() / 60
            
            # Overtime before 22:00
            ot_before_22_minutes = total_work_minutes - ot_after_22_minutes

            self.overtime_before_22 = minutes_to_hhmm(ot_before_22_minutes)
            self.overtime_after_22 = minutes_to_hhmm(ot_after_22_minutes)
        else:
            # Logic for regular days - Simplified and more accurate
            # Standard work hours: 8 hours (9:00-18:00 with 1 hour break)
            standard_start = self.check_in.replace(hour=9, minute=0, second=0, microsecond=0)
            standard_end = self.check_in.replace(hour=18, minute=0, second=0, microsecond=0)
            
            # Calculate overtime before 22:00 (from 18:00 to 22:00)
            overtime_start = max(self.check_in, standard_end)
            overtime_end_22 = min(self.check_out, self.check_in.replace(hour=22, minute=0, second=0, microsecond=0))
            overtime_before_22 = (overtime_end_22 - overtime_start).total_seconds() / 60 if overtime_end_22 > overtime_start else 0

            # Calculate overtime after 22:00
            after_22 = self.check_in.replace(hour=22, minute=0, second=0, microsecond=0)
            overtime_after_22 = (self.check_out - after_22).total_seconds() / 60 if self.check_out > after_22 else 0
            
            self.overtime_before_22 = minutes_to_hhmm(overtime_before_22)
            self.overtime_after_22 = minutes_to_hhmm(overtime_after_22)

    def calculate_regular_work_hours(self):
        """Calculate regular work hours (excluding overtime)"""
        if not self.check_in or not self.check_out:
            return 0.0

        # If holiday or weekend, regular hours = 0
        if self.holiday_type in ['weekend', 'vietnamese_holiday']:
            return 0.0

        # Logic for regular days: calculate work hours within standard shift (9:00-18:00)
        standard_start = self.check_in.replace(hour=9, minute=0, second=0, microsecond=0)
        standard_end = self.check_in.replace(hour=18, minute=0, second=0, microsecond=0)
        
        # Calculate actual work time within standard hours
        overlap_start = max(self.check_in, standard_start)
        overlap_end = min(self.check_out, standard_end)
        
        in_shift_duration_hours = 0
        if overlap_end > overlap_start:
            in_shift_duration_hours = (overlap_end - overlap_start).total_seconds() / 3600
        
        # Subtract break time from shift work time
        regular_hours = max(0, in_shift_duration_hours - self.break_time)
        
        return round(regular_hours, 2)

    def to_dict(self):
        """Convert attendance record to dictionary"""
        work_hours_val = self.calculate_regular_work_hours()

        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d'),
            'check_in': self.check_in.strftime('%H:%M:%S') if self.check_in else None,
            'check_out': self.check_out.strftime('%H:%M:%S') if self.check_out else None,
            'status': self.status,
            'break_time': self._format_hours_minutes(self.break_time) if self.break_time is not None else "0:00",
            'is_holiday': self.is_holiday,
            'holiday_type': self._translate_holiday_type(self.holiday_type),
            'total_work_hours': self._format_hours_minutes(self.total_work_hours) if self.total_work_hours is not None else "0:00",
            'work_hours_display': self._format_hours_minutes(work_hours_val),
            'overtime_before_22': self.overtime_before_22,
            'overtime_after_22': self.overtime_after_22,
            'note': self.note,
            'approved': self.approved
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