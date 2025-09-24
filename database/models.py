"""
Database models for the attendance management system
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, time
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
    personal_signature = db.Column(db.Text, nullable=True)  # Chữ ký cá nhân duy nhất
    is_deleted = db.Column(db.Boolean, default=False)  # Soft delete flag

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

    def has_personal_signature(self):
        """Check if user has personal signature"""
        return bool(self.personal_signature and self.personal_signature.strip())

    def soft_delete(self):
        """Soft delete user by setting is_deleted to True"""
        self.is_deleted = True
        self.is_active = False

    def restore(self):
        """Restore soft deleted user"""
        self.is_deleted = False
        self.is_active = True

    def is_soft_deleted(self):
        """Check if user is soft deleted"""
        return self.is_deleted

    @classmethod
    def get_active_users(cls):
        """Get all non-deleted users"""
        return cls.query.filter_by(is_deleted=False).all()

    @classmethod
    def get_deleted_users(cls):
        """Get all soft deleted users"""
        return cls.query.filter_by(is_deleted=True).all()

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
    # Giờ đối ứng trong ca làm việc: trừ vào giờ công thường
    comp_time_regular = db.Column(db.Float, nullable=False, default=0.0)
    # Giờ đối ứng tăng ca: tổng (giữ tương thích nhưng không dùng để trừ trực tiếp)
    comp_time_overtime = db.Column(db.Float, nullable=False, default=0.0)
    # Giờ đối ứng tăng ca trước 22h
    comp_time_ot_before_22 = db.Column(db.Float, nullable=False, default=0.0)
    # Giờ đối ứng tăng ca sau 22h
    comp_time_ot_after_22 = db.Column(db.Float, nullable=False, default=0.0)
    # Giờ đối ứng tăng ca cũ (để tương thích ngược)
    overtime_comp_time = db.Column(db.Float, nullable=False, default=0.0)
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
    
    # Thêm các trường để lưu ID người ký cho từng vai trò
    team_leader_signer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # ID người ký trưởng nhóm
    manager_signer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # ID người ký quản lý

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('attendances', lazy=True))
    approver = db.relationship('User', foreign_keys=[approved_by], backref=db.backref('approved_attendances', lazy=True))
    team_leader_signer = db.relationship('User', foreign_keys=[team_leader_signer_id], backref=db.backref('team_leader_signed_attendances', lazy=True))
    manager_signer = db.relationship('User', foreign_keys=[manager_signer_id], backref=db.backref('manager_signed_attendances', lazy=True))

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

        # Định nghĩa 5 ca chuẩn (bao gồm ca đặc biệt cho ngày nghỉ)
        shift_map = {
            '1': (time(7,30), time(16,30)),
            '2': (time(9,0), time(18,0)),
            '3': (time(11,0), time(20,0)),
            '4': (time(8,0), time(17,0)),
            '5': (time(0,0), time(23,59)),  # Ca đặc biệt: tự do giờ giấc cho ngày nghỉ
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
            handler = logging.FileHandler("attendance_debug.log", encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            logger.addHandler(handler)

        # Log giá trị đầu vào
        logger.debug(f"check_in: {self.check_in} ({type(self.check_in)})")
        logger.debug(f"check_out: {self.check_out} ({type(self.check_out)})")
        logger.debug(f"break_time: {self.break_time}")

        # Tính duration thực tế theo phút để tránh sai số float
        duration_minutes = int(round((self.check_out - self.check_in).total_seconds() / 60))
        logger.debug(f"duration_minutes (check_in to check_out): {duration_minutes}")
        break_minutes = int(round((self.break_time or 0.0) * 60))
        # Tổng phút làm = thời gian thực làm việc - phút nghỉ
        total_work_minutes = max(0, duration_minutes - break_minutes)
        logger.debug(f"total_work_minutes (after break deduction): {total_work_minutes}")
        self.total_work_hours = round(total_work_minutes / 60.0, 2)
        
        # Import helper function từ validators
        from utils.validators import safe_convert_to_minutes
        
        # Trừ giờ đối ứng vào tổng giờ làm (cho phép chọn nhiều loại)
        try:
            total_comp_time_minutes = 0
            
            # Cuối tuần và Lễ Việt Nam: KHÔNG trừ đối ứng trong ca (comp_time_regular)
            # Chỉ trừ đối ứng tăng ca chi tiết (trước/sau 22h). Legacy tổng tăng ca xử lý riêng bên dưới.
            if self.holiday_type in ['weekend', 'vietnamese_holiday']:
                if (self.comp_time_ot_before_22 or 0) > 0:
                    total_comp_time_minutes += safe_convert_to_minutes(self.comp_time_ot_before_22)
                if (self.comp_time_ot_after_22 or 0) > 0:
                    total_comp_time_minutes += safe_convert_to_minutes(self.comp_time_ot_after_22)
            else:
                # Ngày thường và lễ Nhật: trừ tất cả loại đối ứng
                if (self.comp_time_regular or 0) > 0:
                    total_comp_time_minutes += safe_convert_to_minutes(self.comp_time_regular)
                if (self.comp_time_overtime or 0) > 0:
                    total_comp_time_minutes += safe_convert_to_minutes(self.comp_time_overtime)
                if (self.comp_time_ot_before_22 or 0) > 0:
                    total_comp_time_minutes += safe_convert_to_minutes(self.comp_time_ot_before_22)
                if (self.comp_time_ot_after_22 or 0) > 0:
                    total_comp_time_minutes += safe_convert_to_minutes(self.comp_time_ot_after_22)
            
            if total_comp_time_minutes > 0:
                total_after_comp_minutes = max(0, int(round(self.total_work_hours * 60)) - total_comp_time_minutes)
                self.total_work_hours = round(total_after_comp_minutes / 60.0, 2)
        except Exception:
            # An toàn: nếu parse lỗi, giữ nguyên total_work_hours
            pass

        if self.shift_start and self.shift_end:
            ca_start = datetime.combine(self.date, self.shift_start)
            if self.shift_end > self.shift_start:
                ca_end = datetime.combine(self.date, self.shift_end)
            else:
                ca_end = datetime.combine(self.date, self.shift_end) + timedelta(days=1)
            
            # Xử lý 22:00 - 22:00 luôn là của ngày check_in
            twenty_two = datetime.combine(self.date, time(22, 0))

            # 2. Giờ công thường: xử lý theo loại ngày
            overlap_start = max(self.check_in, ca_start)
            overlap_end = min(self.check_out, ca_end)
            # Xử lý trường hợp ca qua đêm: nếu overlap_end <= overlap_start có thể là do ca qua đêm
            if overlap_end <= overlap_start and self.check_out.time() < self.check_in.time():
                # Trường hợp ca qua đêm: tính từ check_in đến ca_end
                time_in_shift = round(max(0, (ca_end - self.check_in).total_seconds() / 3600), 2)
            else:
                time_in_shift = round(max(0, (overlap_end - overlap_start).total_seconds() / 3600), 2) if overlap_end > overlap_start else 0
            
            # Xử lý giờ công chính thức theo loại ngày
            if self.holiday_type == 'vietnamese_holiday':
                # Ngày lễ Việt Nam: được 8h giờ công thường (ngày nghỉ có lương)
                self.regular_work_hours = 8.0
                break_time_for_overtime = self.break_time
            elif self.holiday_type == 'weekend':
                # Cuối tuần: giờ công thường = 0, tất cả thời gian làm việc tính vào tăng ca
                self.regular_work_hours = 0.0
                break_time_for_overtime = self.break_time
            elif self.holiday_type == 'japanese_holiday':
                # Lễ Nhật: Giờ công = total_work_hours (đã trừ giờ nghỉ), trừ tất cả loại đối ứng
                # Giới hạn tối đa 8h cho giờ công thường
                regular_base = min(self.total_work_hours or 0.0, 8.0)
                # Trừ tất cả loại đối ứng (giống ngày thường)
                total_comp_regular = (self.comp_time_regular or 0.0) + (self.comp_time_overtime or 0.0)
                regular_hours = round(max(0.0, regular_base - total_comp_regular), 2)
                self.regular_work_hours = regular_hours
                break_time_for_overtime = 0
            else:
                # Ngày thường: giờ nghỉ và đối ứng trong ca trừ vào giờ công thường, tối đa 8 giờ
                effective_break_regular = self.break_time + self.comp_time_regular
                regular_hours = round(max(0, time_in_shift - effective_break_regular), 2)
                self.regular_work_hours = min(regular_hours, 8.0)  # Giới hạn tối đa 8 giờ cho ngày thường
                break_time_for_overtime = 0

            # 3. Tăng ca: tính thô hai phần trước/sau 22h
            # Sau đó trừ "giờ nghỉ hiệu lực" theo từng phần:
            # - phần trước 22h: trừ comp_time_ot_before_22
            # - phần sau 22h: trừ comp_time_ot_after_22
            if self.holiday_type in ['vietnamese_holiday', 'weekend']:
                # Ngày lễ và cuối tuần: tính thời gian từ check_in đến 22:00
                check_in_time = self.check_in.time()
                check_out_time = self.check_out.time()
                
                # Tính tăng ca trước 22h
                if self.holiday_type == 'vietnamese_holiday':
                    # Lễ Việt Nam: giới hạn đến 22:00
                    if self.check_out <= twenty_two:
                        # Toàn bộ thời gian làm việc trước 22h
                        overtime_before_22 = (self.check_out - self.check_in).total_seconds() / 3600
                    else:
                        # Tính thời gian từ check_in đến 22:00
                        if self.check_in < twenty_two:
                            # Có thời gian trước 22h
                            overtime_before_22 = (twenty_two - self.check_in).total_seconds() / 3600
                        else:
                            # Không có thời gian trước 22h
                            overtime_before_22 = 0
                else:
                    # Cuối tuần: vẫn phân biệt tăng ca trước và sau 22h
                    # Tăng ca trước 22h: từ check_in đến min(22:00, check_out) (đã trừ giờ nghỉ)
                    if self.check_in < twenty_two:
                        # Giới hạn bởi thời gian làm việc thực tế
                        actual_end = min(self.check_out, twenty_two)
                        overtime_before_22 = (actual_end - self.check_in).total_seconds() / 3600
                        # Trừ giờ nghỉ ngay từ đầu cho cuối tuần
                        overtime_before_22 = max(0.0, overtime_before_22 - self.break_time)
                    else:
                        overtime_before_22 = 0
            elif self.holiday_type == 'japanese_holiday':
                # Lễ Nhật: tăng ca = tổng giờ làm - giờ công
                # Phân bổ ưu tiên phần sau 22h trước, phần còn lại cho trước 22h để phản ánh đúng mốc thời gian thực tế
                overtime_total = max(0.0, (self.total_work_hours or 0.0) - (self.regular_work_hours or 0.0))
                overtime_before_22 = 0.0
                overtime_after_22 = 0.0
                if overtime_total > 0.0:
                    regular_end = self.check_in + timedelta(hours=self.regular_work_hours or 0.0)
                    # Dung lượng trước 22h (và trước giờ ra)
                    before_window_end = min(self.check_out, twenty_two)
                    capacity_before = 0.0
                    if before_window_end > regular_end:
                        capacity_before = max(0.0, (before_window_end - regular_end).total_seconds() / 3600)
                    # Dung lượng sau 22h (sau max(regular_end, 22:00) tới check_out)
                    after_window_start = max(regular_end, twenty_two)
                    capacity_after = 0.0
                    if self.check_out > after_window_start:
                        capacity_after = max(0.0, (self.check_out - after_window_start).total_seconds() / 3600)
                    # Phân bổ: sau 22h trước
                    overtime_after_22 = min(overtime_total, capacity_after)
                    remaining = max(0.0, overtime_total - overtime_after_22)
                    overtime_before_22 = min(capacity_before, remaining)
            else:
                # Ngày thường: Tính OT trước 22h
                # Kiểm tra shift_code để quyết định có tính đi làm sớm không
                if self.shift_code == '5':
                    # Ca 5 (tự do): tính cả đi làm sớm và về muộn
                    # 1) Trước giờ vào ca
                    pre_start = self.check_in
                    pre_end = min(self.check_out, ca_start, twenty_two)
                    pre_shift_ot = max(0, (pre_end - pre_start).total_seconds() / 3600) if pre_end > pre_start and self.check_in < ca_start else 0

                    # 2) Sau giờ ra ca nhưng trước 22h
                    post_start = max(self.check_in, ca_end)
                    post_end = min(self.check_out, twenty_two)
                    # Điều kiện: phải có thời gian sau ca và trước 22h
                    logger.debug(f"Post shift OT: post_start={post_start}, post_end={post_end}, ca_end={ca_end}, check_out={self.check_out}")
                    post_shift_ot = max(0, (post_end - post_start).total_seconds() / 3600) if post_end > post_start and self.check_out > ca_end else 0
                    logger.debug(f"Post shift OT result: {post_shift_ot}")

                    overtime_before_22 = pre_shift_ot + post_shift_ot
                else:
                    # Ca 1-4: chỉ tính về muộn, không tính đi làm sớm
                    # Chỉ tính phần sau giờ ra ca nhưng trước 22h
                    post_start = max(self.check_in, ca_end)
                    post_end = min(self.check_out, twenty_two)
                    # Điều kiện: phải có thời gian sau ca và trước 22h
                    logger.debug(f"Post shift OT: post_start={post_start}, post_end={post_end}, ca_end={ca_end}, check_out={self.check_out}")
                    post_shift_ot = max(0, (post_end - post_start).total_seconds() / 3600) if post_end > post_start and self.check_out > ca_end else 0
                    logger.debug(f"Post shift OT result: {post_shift_ot}")

                    overtime_before_22 = post_shift_ot
            
            # 4. Tăng ca sau 22h: thời gian từ 22:00 (ngày check_in) đến khi ra (kể cả qua đêm)
            if self.holiday_type in ['vietnamese_holiday', 'weekend']:
                if self.holiday_type == 'vietnamese_holiday':
                    # Lễ Việt Nam: hợp nhất xử lý, tính cả phần qua đêm
                    ot2_start = max(self.check_in, twenty_two)
                    if self.check_out > ot2_start:
                        overtime_after_22 = (self.check_out - ot2_start).total_seconds() / 3600
                    else:
                        overtime_after_22 = 0
                else:
                    # Cuối tuần: tăng ca sau 22h từ 22:00 đến check_out
                    if self.check_out > twenty_two:
                        overtime_after_22 = (self.check_out - twenty_two).total_seconds() / 3600
                    else:
                        overtime_after_22 = 0
            elif self.holiday_type == 'japanese_holiday':
                # Nếu trước đó đã phân bổ rồi thì giữ nguyên; nếu chưa (trường hợp hiếm), fallback về tính toán an toàn
                if 'overtime_after_22' not in locals():
                    overtime_total = max(0.0, (self.total_work_hours or 0.0) - (self.regular_work_hours or 0.0))
                    regular_end = self.check_in + timedelta(hours=self.regular_work_hours or 0.0)
                    after_window_start = max(regular_end, twenty_two)
                    if self.check_out > after_window_start:
                        raw_capacity_after = (self.check_out - after_window_start).total_seconds() / 3600
                        overtime_after_22 = min(overtime_total, max(0.0, raw_capacity_after))
                    else:
                        overtime_after_22 = 0.0
            else:
                # Ngày thường: hợp nhất xử lý, tính cả phần qua đêm
                ot2_start = max(self.check_in, twenty_two)
                if self.check_out > ot2_start:
                    overtime_after_22 = (self.check_out - ot2_start).total_seconds() / 3600
                else:
                    overtime_after_22 = 0

            # 5. Trừ giờ nghỉ hiệu lực vào từng phần OT
            overtime_before_22 = max(0.0, overtime_before_22)
            overtime_after_22 = max(0.0, overtime_after_22)
            
            # Trừ giờ đối ứng theo từng loại tăng ca
            # Đối ứng tăng ca trước 22h
            if (self.comp_time_ot_before_22 or 0) > 0:
                comp_minutes_before_22 = safe_convert_to_minutes(self.comp_time_ot_before_22)
                overtime_before_22 = max(0.0, overtime_before_22 - (comp_minutes_before_22 / 60.0))
            
            # Đối ứng tăng ca sau 22h  
            if (self.comp_time_ot_after_22 or 0) > 0:
                comp_minutes_after_22 = safe_convert_to_minutes(self.comp_time_ot_after_22)
                overtime_after_22 = max(0.0, overtime_after_22 - (comp_minutes_after_22 / 60.0))
            
            # Legacy: trừ comp_time_overtime (tổng tăng ca)
            if (self.comp_time_overtime or 0) > 0:
                total_overtime = overtime_before_22 + overtime_after_22
                comp_minutes_overtime = safe_convert_to_minutes(self.comp_time_overtime)
                deduction = min(comp_minutes_overtime / 60.0, total_overtime)
                if deduction > 0:
                    deduct_before = min(overtime_before_22, deduction)
                    overtime_before_22 -= deduct_before
                    deduction -= deduct_before
                    if deduction > 0:
                        overtime_after_22 = max(0.0, overtime_after_22 - deduction)
            
            # Xử lý giờ nghỉ theo loại ngày
            if self.holiday_type == 'vietnamese_holiday':
                # Ngày lễ Việt Nam: giờ nghỉ trừ vào tăng ca trước 22h
                if overtime_before_22 > 0:
                    overtime_before_22 = max(0.0, overtime_before_22 - self.break_time)
            # Cuối tuần: giờ nghỉ đã được trừ ngay từ đầu khi tính tăng ca trước 22h
            # Ngày thường và lễ Nhật: giờ nghỉ đã được trừ vào giờ công thường rồi, không trừ vào OT

            # Gán chuỗi H:MM
            self.overtime_before_22 = minutes_to_hhmm(overtime_before_22 * 60)
            self.overtime_after_22 = minutes_to_hhmm(overtime_after_22 * 60)
        else:
            # Nếu không có ca chuẩn, xử lý theo loại ngày
            if self.holiday_type == 'vietnamese_holiday':
                # Ngày lễ Việt Nam: được 8h giờ công thường (ngày nghỉ có lương)
                self.regular_work_hours = 8.0
                self.overtime_before_22 = "0:00"
                self.overtime_after_22 = "0:00"
            elif self.holiday_type == 'weekend':
                # Cuối tuần: giờ công thường = 0 (ngày nghỉ không lương)
                self.regular_work_hours = 0.0
                # Tính tăng ca cho cuối tuần khi không có ca chuẩn
                if self.check_in and self.check_out:
                    # Tăng ca trước 22h: từ check_in đến 22:00 (trừ giờ nghỉ)
                    check_in_time = self.check_in.time()
                    check_out_time = self.check_out.time()
                    twenty_two = time(22, 0)
                    
                    if check_in_time < twenty_two:
                        overtime_before_22 = (twenty_two - check_in_time).total_seconds() / 3600
                        # Trừ giờ nghỉ
                        overtime_before_22 = max(0.0, overtime_before_22 - self.break_time)
                    else:
                        overtime_before_22 = 0.0
                    
                    # Tăng ca sau 22h: từ 22:00 đến check_out
                    if check_out_time > twenty_two:
                        overtime_after_22 = (check_out_time - twenty_two).total_seconds() / 3600
                    else:
                        overtime_after_22 = 0.0
                    
                    self.overtime_before_22 = minutes_to_hhmm(overtime_before_22 * 60)
                    self.overtime_after_22 = minutes_to_hhmm(overtime_after_22 * 60)
                else:
                    self.overtime_before_22 = "0:00"
                    self.overtime_after_22 = "0:00"
            elif self.holiday_type == 'japanese_holiday':
                # Lễ Nhật: xử lý đặc biệt theo thời gian làm việc (khi không có ca chuẩn)
                total_work_duration = (self.check_out - self.check_in).total_seconds() / 3600 if self.check_in and self.check_out else 0.0
                
                # Lễ Nhật: Giờ công = total_work_hours (đã trừ giờ nghỉ), trừ tất cả loại đối ứng
                # Giới hạn tối đa 8h cho giờ công thường
                regular_base = min(self.total_work_hours or 0.0, 8.0)
                # Trừ tất cả loại đối ứng (giống ngày thường)
                total_comp_regular = (self.comp_time_regular or 0.0) + (self.comp_time_overtime or 0.0)
                self.regular_work_hours = round(max(0.0, regular_base - total_comp_regular), 2)
                # Tính tăng ca cho lễ Nhật khi không có ca chuẩn (giống ngày thường)
                if self.check_in and self.check_out:
                    # Lễ Nhật: tính tăng ca giống ngày thường - trừ giờ công thường trước
                    # Tăng ca trước 22h: từ (check_in + giờ công thường) đến 22:00
                    check_in_time = self.check_in.time()
                    check_out_time = self.check_out.time()
                    twenty_two = time(22, 0)
                    
                    # Tính thời điểm bắt đầu tăng ca (sau khi đã làm đủ giờ công thường + giờ nghỉ)
                    regular_start = datetime.combine(self.date, check_in_time)
                    overtime_start = regular_start + timedelta(hours=self.regular_work_hours + self.break_time)
                    
                    # Xử lý trường hợp ca qua đêm
                    if self.check_out < self.check_in:
                        # Ca qua đêm: check_out thuộc ngày hôm sau
                        overtime_start_date = overtime_start.date()
                        twenty_two_datetime = datetime.combine(overtime_start_date, twenty_two)
                        
                        if overtime_start < twenty_two_datetime:
                            # Có thời gian tăng ca trước 22h
                            overtime_before_22 = (twenty_two_datetime - overtime_start).total_seconds() / 3600
                        else:
                            overtime_before_22 = 0.0
                    else:
                        # Ca trong cùng ngày
                        if overtime_start.time() < twenty_two:
                            # Có thời gian tăng ca trước 22h
                            overtime_before_22 = (twenty_two - overtime_start.time()).total_seconds() / 3600
                        else:
                            overtime_before_22 = 0.0
                    
                    # Tăng ca sau 22h: từ 22:00 đến check_out
                    if self.check_out < self.check_in:
                        # Ca qua đêm: check_out thuộc ngày hôm sau
                        check_out_date = self.check_out.date()
                        twenty_two_datetime = datetime.combine(check_out_date, twenty_two)
                        if self.check_out > twenty_two_datetime:
                            overtime_after_22 = (self.check_out - twenty_two_datetime).total_seconds() / 3600
                        else:
                            overtime_after_22 = 0.0
                    else:
                        # Ca trong cùng ngày
                        if check_out_time > twenty_two:
                            overtime_after_22 = (check_out_time - twenty_two).total_seconds() / 3600
                        else:
                            overtime_after_22 = 0.0
                    
                    self.overtime_before_22 = minutes_to_hhmm(overtime_before_22 * 60)
                    self.overtime_after_22 = minutes_to_hhmm(overtime_after_22 * 60)
                else:
                    self.overtime_before_22 = "0:00"
                    self.overtime_after_22 = "0:00"
            else:
                # Ngày thường: tối đa 8 giờ
                self.regular_work_hours = min(self.total_work_hours, 8.0) if self.total_work_hours else 0.0
                # Tính tăng ca cho ngày thường khi không có ca chuẩn
                if self.check_in and self.check_out:
                    # Ngày thường: tính tăng ca sau khi đã làm đủ giờ công thường
                    # Tăng ca trước 22h: từ (check_in + giờ công thường + giờ nghỉ) đến 22:00
                    check_in_time = self.check_in.time()
                    check_out_time = self.check_out.time()
                    twenty_two = time(22, 0)
                    
                    # Tính thời điểm bắt đầu tăng ca (sau khi đã làm đủ giờ công thường)
                    effective_break_regular = self.break_time + self.comp_time_regular
                    regular_start = datetime.combine(self.date, check_in_time)
                    overtime_start = regular_start + timedelta(hours=self.regular_work_hours + effective_break_regular)
                    
                    # Xử lý trường hợp ca qua đêm
                    if self.check_out < self.check_in:
                        # Ca qua đêm: check_out thuộc ngày hôm sau
                        overtime_start_date = overtime_start.date()
                        twenty_two_datetime = datetime.combine(overtime_start_date, twenty_two)
                        
                        if overtime_start < twenty_two_datetime:
                            # Có thời gian tăng ca trước 22h
                            overtime_before_22 = (twenty_two_datetime - overtime_start).total_seconds() / 3600
                        else:
                            overtime_before_22 = 0.0
                    else:
                        # Ca trong cùng ngày
                        if overtime_start.time() < twenty_two:
                            # Có thời gian tăng ca trước 22h
                            overtime_before_22 = (twenty_two - overtime_start.time()).total_seconds() / 3600
                        else:
                            overtime_before_22 = 0.0
                    
                    # Tăng ca sau 22h: từ 22:00 đến check_out
                    if self.check_out < self.check_in:
                        # Ca qua đêm: check_out thuộc ngày hôm sau
                        check_out_date = self.check_out.date()
                        twenty_two_datetime = datetime.combine(check_out_date, twenty_two)
                        if self.check_out > twenty_two_datetime:
                            overtime_after_22 = (self.check_out - twenty_two_datetime).total_seconds() / 3600
                        else:
                            overtime_after_22 = 0.0
                    else:
                        # Ca trong cùng ngày
                        if check_out_time > twenty_two:
                            overtime_after_22 = (check_out_time - twenty_two).total_seconds() / 3600
                        else:
                            overtime_after_22 = 0.0
                    
                    self.overtime_before_22 = minutes_to_hhmm(overtime_before_22 * 60)
                    self.overtime_after_22 = minutes_to_hhmm(overtime_after_22 * 60)
                else:
                    self.overtime_before_22 = "0:00"
                    self.overtime_after_22 = "0:00"

    def calculate_regular_work_hours(self):
        """Calculate regular work hours (excluding overtime)"""
        if not self.check_in or not self.check_out:
            return 0.0

        if self.holiday_type == 'vietnamese_holiday':
            return 8.0  # Ngày lễ Việt Nam: được 8h giờ công thường (ngày nghỉ có lương)
        if self.holiday_type == 'weekend':
            return 0.0  # Cuối tuần: giờ công thường = 0 (ngày nghỉ không lương)
        if self.holiday_type == 'japanese_holiday':
            # Lễ Nhật: Giờ công = total_work_hours (đã trừ giờ nghỉ), trừ tất cả loại đối ứng
            # Giới hạn tối đa 8h cho giờ công thường
            if self.total_work_hours is not None:
                base = min(self.total_work_hours, 8.0)
            else:
                # Fallback: tính theo thời gian thực tế trừ giờ nghỉ
                duration_hours = (self.check_out - self.check_in).total_seconds() / 3600
                base = min(max(0.0, duration_hours - self.break_time), 8.0)
            # Trừ tất cả loại đối ứng (giống ngày thường)
            total_comp_regular = (self.comp_time_regular or 0.0) + (self.comp_time_overtime or 0.0)
            return round(max(0.0, base - total_comp_regular), 2)

        # Ngày thường và lễ Nhật: tính giờ công và giới hạn tối đa 8 giờ
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
            # Giờ công chính thức = thời gian trong ca - giờ nghỉ - đối ứng trong ca, tối đa 8 giờ
            effective_break_regular = self.break_time + self.comp_time_regular
            regular_hours = round(max(0, time_in_shift - effective_break_regular), 2)
            return min(regular_hours, 8.0)  # Giới hạn tối đa 8 giờ cho ngày thường
        else:
            # Nếu không có ca chuẩn, tính theo cách cũ
            effective_break_regular = self.break_time + self.comp_time_regular
            actual_work_duration_hours = (self.check_out - self.check_in).total_seconds() / 3600 - effective_break_regular
            regular_hours = round(max(0, actual_work_duration_hours), 2)
            return min(regular_hours, 8.0)  # Giới hạn tối đa 8 giờ cho ngày thường và lễ Nhật

    def to_dict(self):
        """Convert attendance record to dictionary"""
        work_hours_val = self.calculate_regular_work_hours()
        return {
            'id': self.id,
            'date': self.date.strftime('%d/%m/%Y'),
            'check_in': self.check_in.strftime('%H:%M') if self.check_in else None,
            'check_out': self.check_out.strftime('%H:%M') if self.check_out else None,
            'break_time': self._format_hours_minutes(self.break_time),
            'comp_time_regular': self._format_hours_minutes(self.comp_time_regular),
            'comp_time_overtime': self._format_hours_minutes(self.comp_time_overtime),
            'comp_time_ot_before_22': self._format_hours_minutes(self.comp_time_ot_before_22),
            'comp_time_ot_after_22': self._format_hours_minutes(self.comp_time_ot_after_22),
            'overtime_comp_time': self._format_hours_minutes(self.overtime_comp_time),  # Giữ lại để tương thích
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

class PasswordResetToken(db.Model):
    """Password reset token model"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('password_reset_tokens', lazy=True))
    
    def is_expired(self):
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid (not expired and not used)"""
        return not self.is_expired() and not self.used
    
    def __repr__(self):
        return f'<PasswordResetToken {self.token[:10]}...>' 

class LeaveRequest(db.Model):
    """Leave request model for employees"""
    __tablename__ = 'leave_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Thông tin nhân viên
    employee_name = db.Column(db.String(100), nullable=False)
    team = db.Column(db.String(50), nullable=False)
    employee_code = db.Column(db.String(20), nullable=False)
    
    # Lý do nghỉ phép
    leave_reason = db.Column(db.Text, nullable=False)         # Lý do nghỉ phép chi tiết
    reason_sick_child = db.Column(db.Boolean, default=False)  # Con ốm (deprecated)
    reason_sick = db.Column(db.Boolean, default=False)        # Bị ốm (deprecated)
    reason_death_anniversary = db.Column(db.Boolean, default=False)  # Đám giỗ (deprecated)
    reason_other = db.Column(db.Boolean, default=False)       # Lý do khác (deprecated)
    reason_other_detail = db.Column(db.Text, nullable=True)   # Chi tiết lý do khác (deprecated)
    
    # Chứng từ đính kèm
    attachments = db.Column(db.Text, nullable=True)                  # Danh sách file đính kèm (JSON)
    hospital_confirmation = db.Column(db.Boolean, default=False)      # Giấy xác nhận bệnh viện (deprecated)
    wedding_invitation = db.Column(db.Boolean, default=False)        # Thiệp mời đám cưới (deprecated)
    death_birth_certificate = db.Column(db.Boolean, default=False)   # Giấy chứng tử, chứng sinh (deprecated)
    
    # Thời gian nghỉ phép
    leave_from_hour = db.Column(db.Integer, nullable=False)          # Giờ bắt đầu
    leave_from_minute = db.Column(db.Integer, nullable=False)        # Phút bắt đầu
    leave_from_day = db.Column(db.Integer, nullable=False)           # Ngày bắt đầu
    leave_from_month = db.Column(db.Integer, nullable=False)         # Tháng bắt đầu
    leave_from_year = db.Column(db.Integer, nullable=False)          # Năm bắt đầu
    
    leave_to_hour = db.Column(db.Integer, nullable=False)            # Giờ kết thúc
    leave_to_minute = db.Column(db.Integer, nullable=False)          # Phút kết thúc
    leave_to_day = db.Column(db.Integer, nullable=False)             # Ngày kết thúc
    leave_to_month = db.Column(db.Integer, nullable=False)           # Tháng kết thúc
    leave_to_year = db.Column(db.Integer, nullable=False)            # Năm kết thúc
    
    # Hình thức nghỉ phép
    annual_leave_days = db.Column(db.Float, default=0.0)             # Số ngày phép năm (hỗ trợ 0.5)
    unpaid_leave_days = db.Column(db.Float, default=0.0)             # Số ngày nghỉ không lương (hỗ trợ 0.5)
    special_leave_days = db.Column(db.Float, default=0.0)            # Số ngày nghỉ đặc biệt (hỗ trợ 0.5)
    special_leave_type = db.Column(db.String(50), nullable=True)     # Loại nghỉ đặc biệt (kết hôn, đám tang)
    
    # Người đảm trách công việc thay thế
    substitute_name = db.Column(db.String(100), nullable=True)       # Tên người thay thế
    substitute_employee_id = db.Column(db.String(20), nullable=True) # Mã nhân viên thay thế
    
    # Trạng thái và phê duyệt (giống chấm công: pending → pending_manager → pending_admin → approved)
    status = db.Column(db.String(20), default='pending')             # pending, pending_manager, pending_admin, approved, rejected
    approved = db.Column(db.Boolean, default=False)                  # Đã phê duyệt hoàn tất
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Người phê duyệt cuối cùng
    approved_at = db.Column(db.DateTime, nullable=True)              # Thời gian phê duyệt cuối cùng
    
    # Chữ ký và ID người ký cho từng cấp (giống chấm công)
    team_leader_signature = db.Column(db.Text, nullable=True)        # Chữ ký trưởng nhóm
    team_leader_signer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    manager_signature = db.Column(db.Text, nullable=True)            # Chữ ký quản lý
    manager_signer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Giữ tương thích ngược với các trường cũ
    manager_approval = db.Column(db.Boolean, default=False)          # Phê duyệt của quản lý (deprecated)
    direct_superior_approval = db.Column(db.Boolean, default=False)  # Phê duyệt cấp trên trực tiếp (deprecated)
    direct_superior_type = db.Column(db.String(20), nullable=True)   # Loại cấp trên (deprecated)
    direct_superior_signature = db.Column(db.Text, nullable=True)    # Chữ ký cấp trên (deprecated)
    direct_superior_signer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    applicant_signature = db.Column(db.Text, nullable=True)          # Chữ ký người xin phép
    
    # Thời gian tạo và cập nhật
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ghi chú
    notes = db.Column(db.Text, nullable=True)
    
    # Ca làm việc áp dụng khi xin nghỉ
    shift_code = db.Column(db.String(10), nullable=True)  # Mã ca: 1,2,3,4
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('leave_requests', lazy=True))
    approver = db.relationship('User', foreign_keys=[approved_by], backref=db.backref('approved_leave_requests', lazy=True))
    team_leader_signer = db.relationship('User', foreign_keys=[team_leader_signer_id], backref=db.backref('team_leader_signed_leaves', lazy=True))
    manager_signer = db.relationship('User', foreign_keys=[manager_signer_id], backref=db.backref('manager_signed_leaves', lazy=True))
    # Giữ tương thích ngược
    direct_superior_signer = db.relationship('User', foreign_keys=[direct_superior_signer_id], backref=db.backref('superior_approved_leaves', lazy=True))
    
    def get_leave_from_datetime(self):
        """Get leave start datetime"""
        return datetime(self.leave_from_year, self.leave_from_month, self.leave_from_day, 
                       self.leave_from_hour, self.leave_from_minute)
    
    def get_leave_to_datetime(self):
        """Get leave end datetime"""
        return datetime(self.leave_to_year, self.leave_to_month, self.leave_to_day,
                       self.leave_to_hour, self.leave_to_minute)
    
    def get_total_leave_days(self):
        """Calculate total leave days"""
        start = self.get_leave_from_datetime()
        end = self.get_leave_to_datetime()
        delta = end - start
        return delta.days + 1  # Include both start and end day
    
    def get_reason_text(self):
        """Get human readable reason text.
        Ưu tiên dùng trường mô tả tự do `leave_reason` từ form "Lý do nghỉ phép *".
        Giữ tương thích ngược với các cờ lý do cũ nếu `leave_reason` trống.
        """
        if self.leave_reason and self.leave_reason.strip():
            return self.leave_reason.strip()

        reasons = []
        if self.reason_sick_child:
            reasons.append("Con ốm")
        if self.reason_sick:
            reasons.append("Bị ốm")
        if self.reason_death_anniversary:
            reasons.append("Đám giỗ")
        if self.reason_other and self.reason_other_detail:
            reasons.append(f"Khác: {self.reason_other_detail}")
        return ", ".join(reasons) if reasons else "Không xác định"
    
    def get_leave_type_text(self):
        """Get human readable leave type text"""
        types = []
        if self.annual_leave_days > 0:
            types.append(f"Phép năm: {self.annual_leave_days} ngày")
        if self.unpaid_leave_days > 0:
            types.append(f"Nghỉ không lương: {self.unpaid_leave_days} ngày")
        if self.special_leave_days > 0:
            types.append(f"Nghỉ đặc biệt: {self.special_leave_days} ngày")
            if self.special_leave_type:
                types[-1] += f" ({self.special_leave_type})"
        return ", ".join(types) if types else "Không xác định"
    
    def __repr__(self):
        return f'<LeaveRequest {self.employee_name} ({self.get_leave_from_datetime().strftime("%d/%m/%Y")} - {self.get_leave_to_datetime().strftime("%d/%m/%Y")})>' 