# Hệ Thống Quản Lý Chấm Công DMI

Hệ thống quản lý chấm công hiện đại với các tính năng bảo mật cao và giao diện thân thiện.

## 🚀 Tính Năng Chính

- **Quản lý chấm công**: Ghi nhận giờ vào/ra, tính toán giờ làm việc và overtime
- **Phân quyền đa cấp**: EMPLOYEE → TEAM_LEADER → MANAGER → ADMIN
- **Phê duyệt chấm công**: Quy trình phê duyệt từng cấp
- **Quản lý yêu cầu**: Hệ thống xin nghỉ phép, overtime
- **Báo cáo và thống kê**: Xuất báo cáo chi tiết
- **Audit log**: Ghi nhận mọi hoạt động của người dùng
- **Bảo mật cao**: CSRF protection, rate limiting, input validation

## 🔒 Cải Thiện Bảo Mật

### ✅ Đã Cải Thiện
- **Xóa lưu trữ mật khẩu plain text** trong cookies
- **Thêm input sanitization** để ngăn XSS và SQL injection
- **Cải thiện validation** cho tất cả user inputs
- **Thêm security headers** (X-Frame-Options, X-XSS-Protection, etc.)
- **Rate limiting** cho tất cả API endpoints
- **Session timeout** và automatic logout
- **Audit logging** cho mọi hoạt động

### 🛡️ Bảo Mật Hiện Tại
- CSRF protection cho tất cả forms
- Input validation và sanitization
- Rate limiting (5 login attempts/5 minutes)
- Session management với timeout
- Secure cookie settings
- SQL injection prevention
- XSS protection

## 📋 Yêu Cầu Hệ Thống

- Python 3.8+
- SQLite (mặc định)
- Modern web browser

## 🛠️ Cài Đặt

### 1. Clone Repository
```bash
git clone <repository-url>
cd attendance-management-system-dmi
```

### 2. Tạo Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate     # Windows
```

### 3. Cài Đặt Dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu Hình Environment
```bash
cp .env.example .env
# Chỉnh sửa file .env theo nhu cầu
```

### 5. Khởi Tạo Database
```bash
python setup.py
```

### 6. Chạy Ứng Dụng
```bash
python app.py
```

Ứng dụng sẽ chạy tại: http://localhost:5000

## 🗄️ Cấu Trúc Database

### Bảng Users
- Thông tin nhân viên
- Phân quyền đa cấp
- Remember token cho auto-login

### Bảng Attendances
- Ghi nhận chấm công
- Tính toán giờ làm việc và overtime
- Trạng thái phê duyệt

### Bảng Requests
- Yêu cầu nghỉ phép, overtime
- Quy trình phê duyệt

### Bảng AuditLogs
- Ghi nhận mọi hoạt động
- Tracking thay đổi dữ liệu

## 🔐 Phân Quyền

### EMPLOYEE
- Chấm công hàng ngày
- Xem lịch sử cá nhân
- Tạo yêu cầu nghỉ phép

### TEAM_LEADER
- Tất cả quyền EMPLOYEE
- Phê duyệt chấm công nhóm
- Quản lý nhân viên trong nhóm

### MANAGER
- Tất cả quyền TEAM_LEADER
- Phê duyệt chấm công phòng ban
- Xem báo cáo phòng ban

### ADMIN
- Tất cả quyền
- Quản lý người dùng
- Cấu hình hệ thống
- Xem báo cáo toàn bộ

## 📊 API Endpoints

### Authentication
- `POST /login` - Đăng nhập
- `GET /logout` - Đăng xuất

### Attendance
- `POST /api/attendance` - Tạo chấm công
- `GET /api/attendance/history` - Lịch sử chấm công
- `PUT /api/attendance/<id>` - Cập nhật chấm công
- `DELETE /api/attendance/<id>` - Xóa chấm công
- `POST /api/attendance/<id>/approve` - Phê duyệt chấm công

### Requests
- `POST /api/request/submit` - Tạo yêu cầu
- `POST /api/request/<id>/approve` - Phê duyệt yêu cầu

## 🧪 Testing

```bash
# Chạy tests
pytest

# Chạy tests với coverage
pytest --cov=app tests/
```

## 📝 Logging

Hệ thống có 3 loại log:
- `logs/attendance.log` - Log chung
- `logs/error.log` - Log lỗi
- `logs/security.log` - Log bảo mật

## 🚀 Deployment

### Development
```bash
python app.py
```

### Production
```bash
export FLASK_CONFIG=production
export SECRET_KEY=your-secret-key
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 🔧 Cấu Hình Nâng Cao

### Database (SQLite)
```bash
# SQLite được sử dụng mặc định (không cần cài đặt thêm)
# Database file: attendance.db

# Cấu hình trong .env
DATABASE_URL=sqlite:///attendance.db
```

### Redis (cho caching và rate limiting)
```bash
# Cài đặt Redis
pip install redis

# Cấu hình trong .env
REDIS_URL=redis://localhost:6379/0
```

## 📈 Performance

### Tối Ưu Hóa
- Eager loading để tránh N+1 queries
- Database connection pooling
- Rate limiting để tránh spam
- Caching cho các truy vấn thường xuyên

### Monitoring
- Log rotation (10MB per file, keep 10 files)
- Error tracking và alerting
- Performance metrics

## 🤝 Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 📄 License

MIT License - xem file LICENSE để biết thêm chi tiết.

## 🆘 Support

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra logs trong thư mục `logs/`
2. Xem documentation
3. Tạo issue trên GitHub

## 🔄 Changelog

### Version 2.1.0 (Latest)
- ✅ Dọn dẹp code và xóa file dư thừa
- ✅ Sửa logic tính toán giờ làm việc
- ✅ Tái cấu trúc modules và imports
- ✅ Cải thiện performance và maintainability

### Version 2.0.0
- ✅ Cải thiện bảo mật toàn diện
- ✅ Tối ưu hóa performance
- ✅ Cải thiện UX/UI
- ✅ Thêm comprehensive logging
- ✅ Cải thiện error handling
- ✅ Tái cấu trúc code architecture
