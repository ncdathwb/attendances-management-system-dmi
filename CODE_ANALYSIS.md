# PHÂN TÍCH HỆ THỐNG QUẢN LY CHẤM CÔNG DMI

## 📋 TỔNG QUAN HỆ THỐNG

Đây là một hệ thống quản lý chấm công hiện đại được phát triển bằng Flask (Python) với các tính năng bảo mật cao và giao diện thân thiện người dùng. Hệ thống hỗ trợ đa cấp phê duyệt và có đầy đủ các chức năng quản lý nhân sự.

## 🏗️ KIẾN TRÚC TỔNG THỂ

### Cấu Trúc Thư Mục
```
├── app.py                 # Ứng dụng Flask chính (1870 dòng)
├── config.py              # Cấu hình môi trường và bảo mật
├── database/              # Tầng dữ liệu
│   ├── models.py          # Định nghĩa các model SQLAlchemy
│   ├── init_db.py         # Khởi tạo database
│   └── schema-sqlite.sql  # Schema database
├── routes/                # Tầng routing
│   └── auth.py            # Routes xác thực
├── utils/                 # Tiện ích chung
│   ├── decorators.py      # Rate limiting và decorators
│   ├── validators.py      # Validation và sanitization
│   ├── session.py         # Quản lý session
│   └── logger.py          # Logging system
├── templates/             # Giao diện người dùng
│   ├── dashboard.html     # Dashboard chính
│   ├── login.html         # Trang đăng nhập
│   └── admin/             # Templates admin
├── static/                # File tĩnh (CSS, JS, images)
└── requirements.txt       # Dependencies Python
```

## 💾 THIẾT KẾ DATABASE

### Model Chính

#### 1. User Model
```python
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    password_hash = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    employee_id = db.Column(db.Integer, unique=True, nullable=False)
    roles = db.Column(db.String(100), nullable=False)  # EMPLOYEE,TEAM_LEADER,MANAGER,ADMIN
    department = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    remember_token = db.Column(db.String(255), nullable=True)
    remember_token_expires = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
```

**Điểm đặc biệt:**
- Hỗ trợ nhiều vai trò cho một user (comma-separated)
- Remember token bảo mật thay vì lưu password
- Soft delete với `is_active`

#### 2. Attendance Model
```python
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    check_in = db.Column(db.DateTime, nullable=True)
    check_out = db.Column(db.DateTime, nullable=True)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='pending')
    break_time = db.Column(db.Float, default=1.0)
    is_holiday = db.Column(db.Boolean, default=False)
    holiday_type = db.Column(db.String(20))  # normal, weekend, vietnamese_holiday, japanese_holiday
    total_work_hours = db.Column(db.Float)
    regular_work_hours = db.Column(db.Float)
    overtime_before_22 = db.Column(db.String(5))
    overtime_after_22 = db.Column(db.String(5))
    shift_code = db.Column(db.String(10))  # 1,2,3,4
    shift_start = db.Column(db.Time)
    shift_end = db.Column(db.Time)
    signature = db.Column(db.Text)  # Chữ ký base64
    team_leader_signature = db.Column(db.Text)
    manager_signature = db.Column(db.Text)
```

**Logic tính toán phức tạp:**
- 4 ca làm việc cố định với thời gian khác nhau
- Tự động tính overtime trước/sau 22h
- Xử lý đặc biệt cho ngày lễ và cuối tuần
- Hỗ trợ chữ ký điện tử đa cấp

#### 3. Request Model
```python
class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    request_type = db.Column(db.String(50))  # leave, overtime, etc.
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    current_approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    step = db.Column(db.String(20), default='leader')  # leader -> manager -> admin
```

#### 4. AuditLog Model
```python
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(50))  # LOGIN, CREATE_ATTENDANCE, etc.
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## 🔐 PHÂN QUYỀN VÀ BẢO MẬT

### Hệ Thống Phân Quyền 4 Cấp

#### 1. EMPLOYEE (Nhân viên)
- Chấm công hàng ngày
- Xem lịch sử chấm công cá nhân
- Tạo yêu cầu nghỉ phép/làm thêm

#### 2. TEAM_LEADER (Trưởng nhóm)
- Tất cả quyền EMPLOYEE
- Phê duyệt chấm công nhân viên cùng phòng ban
- Quản lý yêu cầu của nhóm

#### 3. MANAGER (Quản lý)
- Tất cả quyền TEAM_LEADER
- Phê duyệt chấm công toàn phòng ban
- Xem báo cáo phòng ban
- Xuất PDF báo cáo

#### 4. ADMIN (Quản trị viên)
- Toàn quyền hệ thống
- Quản lý user (tạo/sửa/khóa/mở khóa)
- Xem audit logs
- Truy cập tất cả dữ liệu

### Tính Năng Bảo Mật

#### 1. Input Validation & Sanitization
```python
def validate_input_sanitize(text):
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove script tags  
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    # Remove SQL injection patterns
    text = re.sub(r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)', '', text, flags=re.IGNORECASE)
    return text.strip()
```

#### 2. Rate Limiting
```python
@rate_limit(max_requests=10, window_seconds=300)  # 10 attempts per 5 minutes
def login():
    # Login logic
```

#### 3. Session Security
- Session timeout sau 30 phút
- CSRF protection
- Secure cookies với HttpOnly
- Remember token thay vì lưu password

#### 4. Audit Logging
Ghi lại tất cả hành động quan trọng:
- Đăng nhập/đăng xuất
- Tạo/sửa/xóa chấm công
- Phê duyệt
- Thay đổi user

## ⚙️ LOGIC NGHIỆP VỤ CHÍNH

### 1. Tính Toán Giờ Làm Việc

Hệ thống có logic tính toán rất phức tạp trong `update_work_hours()`:

#### Ca Làm Việc
```python
shift_map = {
    '1': (time(7,30), time(16,30)),   # Ca 1: 7:30-16:30
    '2': (time(8,0), time(17,0)),     # Ca 2: 8:00-17:00  
    '3': (time(9,0), time(18,0)),     # Ca 3: 9:00-18:00
    '4': (time(11,0), time(22,0)),    # Ca 4: 11:00-22:00
}
```

#### Xử Lý Theo Loại Ngày
1. **Ngày thường**: Giờ công tối đa 8h, tính overtime ngoài ca
2. **Cuối tuần**: Không có giờ công chính thức, toàn bộ là overtime
3. **Ngày lễ VN**: Được tặng 8h công chính thức + overtime
4. **Ngày lễ Nhật**: Xử lý tương tự ngày lễ VN

#### Tính Overtime
- **Trước 22h**: Thời gian ngoài ca làm việc đến 22:00
- **Sau 22h**: Thời gian từ 22:00 đến khi ra về

### 2. Quy Trình Phê Duyệt

#### Luồng Phê Duyệt Chấm Công
1. Nhân viên tạo chấm công → `status: 'pending'`
2. Team Leader phê duyệt (cùng phòng ban)
3. Manager phê duyệt (nếu cần)
4. Admin có thể phê duyệt mọi lúc

#### Permission Check
```python
def check_approval_permission(user_id, attendance_id, current_role):
    # ADMIN và MANAGER có thể duyệt tất cả
    if current_role in ['ADMIN', 'MANAGER']:
        return True, ""
    
    # TEAM_LEADER chỉ duyệt cùng phòng ban
    if current_role == 'TEAM_LEADER':
        if attendance.user.department != user.department:
            return False, "Chỉ có thể phê duyệt nhân viên cùng phòng ban"
        return True, ""
```

### 3. Chữ Ký Điện Tử

Hệ thống hỗ trợ 3 loại chữ ký:
- `signature`: Chữ ký nhân viên (base64)
- `team_leader_signature`: Chữ ký trưởng nhóm
- `manager_signature`: Chữ ký quản lý

```python
# Tự động lưu chữ ký theo role
if 'TEAM_LEADER' in user.roles.split(','):
    attendance.team_leader_signature = signature
if 'MANAGER' in user.roles.split(','):
    attendance.manager_signature = signature
```

## 📊 TÍNH NĂNG NÂNG CAO

### 1. Xuất PDF Báo Cáo

Sử dụng ReportLab để tạo PDF với:
- Font tiếng Việt
- Bảng dữ liệu formatted
- Logo và header
- Chữ ký điện tử

### 2. Bulk Export

Xuất nhiều báo cáo thành file ZIP:
```python
@app.route('/admin/attendance/export-overtime-bulk')
@require_admin
def export_overtime_bulk():
    # Tạo multiple PDF files
    # Nén thành ZIP
    # Return download link
```

### 3. Dashboard Thống Kê

Dashboard hiển thị:
- Chấm công hôm nay
- Pending approvals
- Thống kê tháng
- Quick actions

### 4. Real-time Validation

Frontend có validation real-time:
- Kiểm tra overlap thời gian
- Validation format HH:MM
- Tính toán overtime ngay lập tức

## 🚨 ĐIỂM CẦN LƯU Ý

### 1. Performance Issues
- File `app.py` quá lớn (1870 dòng) - nên refactor
- Một số query có thể gây N+1 problem
- Thiếu indexing cho các trường search

### 2. Code Organization
- Logic business nên tách riêng khỏi routes
- Validation logic lặp lại nhiều chỗ
- Config có thể module hóa tốt hơn

### 3. Security Considerations
- Rate limiting còn basic (memory-based)
- Audit log không có retention policy
- Session storage có thể cải thiện

### 4. Scalability Concerns
- SQLite không phù hợp production lớn
- In-memory rate limiting không scale
- File upload/signature cần cloud storage

## 🔧 CÔNG NGHỆ SỬ DỤNG

### Backend Stack
- **Flask 2.3.3**: Web framework
- **SQLAlchemy 3.0.5**: ORM
- **Flask-Login 0.6.3**: Authentication
- **Flask-WTF 1.2.1**: CSRF protection
- **Flask-Limiter 3.5.0**: Rate limiting

### Security Libraries
- **Flask-Talisman**: Security headers
- **cryptography**: Enhanced encryption
- **Werkzeug**: Password hashing

### PDF Generation
- **ReportLab**: PDF creation
- **Vietnamese fonts**: NotoSans support

### Frontend
- **Vanilla JavaScript**: No heavy frameworks
- **Bootstrap**: UI components
- **Chart.js**: Dashboards charts

## 📈 KẾT LUẬN

Đây là một hệ thống được thiết kế rất kỹ lưỡng với:

**Điểm mạnh:**
- Bảo mật tốt với nhiều lớp protection
- Logic business phức tạp được handle đầy đủ
- UI/UX thân thiện người dùng Việt
- Audit trail đầy đủ
- Hỗ trợ workflow phê duyệt linh hoạt

**Điểm cần cải thiện:**
- Refactor code structure cho maintainability
- Performance optimization
- Scalability improvements
- Testing coverage

Hệ thống phù hợp cho doanh nghiệp vừa và nhỏ với nhu cầu quản lý chấm công chuyên nghiệp.