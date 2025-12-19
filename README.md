# Attendance Management System DMI

## Mục tiêu dự án

Hệ thống quản lý chấm công, phê duyệt tăng ca/nghỉ phép, quản lý người dùng, phân quyền, và đặc biệt là hệ thống phê duyệt thông minh với chữ ký số (ký tay trên web, mã hóa, lưu session, tái sử dụng, audit log).

---

## 1. Kiến trúc tổng quan

- **Backend:** Python (Flask), SQLAlchemy ORM, SQLite (có thể mở rộng PostgreSQL/MySQL), Flask-Login, Flask-WTF, Flask-Migrate, cryptography (Fernet)
- **Frontend:** HTML5, Bootstrap, JavaScript (ES6+), SweetAlert2, SignaturePad.js
- **Session:** Flask session (server-side hoặc client-side signed cookie)
- **Audit:** Audit log chi tiết mọi hành động quan trọng
- **Security:** CSRF, rate limit, mã hóa chữ ký, session timeout, phân quyền rõ ràng

---

## 2. Các flow nghiệp vụ chính

### 2.1 Đăng nhập/Đăng xuất
- Người dùng đăng nhập bằng mã nhân viên + mật khẩu (hash bcrypt)
- Session lưu thông tin user, roles, last activity
- Có chức năng "remember me" (token an toàn, không lưu mật khẩu)

### 2.2 Chấm công
- Nhân viên đăng ký chấm công (ngày, giờ vào/ra, ca, ghi chú, loại ngày, chữ ký)
- Kiểm tra trùng ngày, không cho phép chấm công tương lai, validate dữ liệu
- Lưu chữ ký (base64, mã hóa)

### 2.3 Phê duyệt chấm công/tăng ca/nghỉ phép
- Phân quyền: EMPLOYEE, TEAM_LEADER, MANAGER, ADMIN
- Quy trình phê duyệt nhiều cấp: NV → Trưởng nhóm → Quản lý → Admin
- Mỗi cấp có thể ký xác nhận (ký tay trên web, lưu session, tái sử dụng, timeout)
- ADMIN có thể phê duyệt không cần ký
- Ghi log chi tiết mỗi lần phê duyệt (người, vai trò, loại chữ ký, thời điểm, IP, user-agent)

### 2.4 Quản lý người dùng
- CRUD user, phân quyền, reset mật khẩu, đổi mật khẩu, khóa/mở tài khoản
- Tìm kiếm, lọc theo phòng ban, phân trang

### 2.5 Báo cáo, xuất PDF/ZIP
- Xuất giấy tăng ca PDF (theo mẫu song ngữ, có chữ ký)
- Xuất hàng loạt (ZIP nhiều PDF)
- Lọc theo tháng/năm, phòng ban

### 2.6 Audit log
- Ghi lại mọi thay đổi dữ liệu quan trọng (ai, khi nào, thay đổi gì, IP, user-agent)
- Có thể mở rộng dashboard audit

---

## 3. Hệ thống chữ ký thông minh (Smart Signature System)

### 3.1 Logic tổng quát
- Khi phê duyệt, kiểm tra session có chữ ký hợp lệ không (và flag "không hỏi lại")
- Nếu có, hỏi dùng lại (có thể tick "không hỏi lại")
- Nếu không, kiểm tra database có chữ ký cũ không, hỏi dùng lại
- **MỚI**: Tự động phát hiện và đề xuất tái sử dụng chữ ký từ vai trò thấp hơn
- Nếu không, yêu cầu ký mới
- Chữ ký session hết hạn sau 30 phút (hoặc cấu hình)
- ADMIN không cần ký
- Mọi chữ ký đều mã hóa (Fernet/AES)
- Có API kiểm tra trạng thái chữ ký, lưu/xóa chữ ký session
- Ghi log mọi hành động liên quan chữ ký

### 3.2 API endpoints
- `POST /api/signature/check` — Kiểm tra trạng thái chữ ký (session/db/flag)
- `POST /api/signature/save-session` — Lưu chữ ký vào session (và flag nếu có)
- `POST /api/signature/clear-session` — Xóa chữ ký khỏi session
- `POST /api/attendance/<id>/approve` — Phê duyệt (logic chữ ký thông minh)

### 3.3 Frontend
- Khi nhấn "Phê duyệt":
  - Gọi `/api/signature/check` lấy trạng thái
  - Nếu ADMIN: gửi phê duyệt luôn
  - Nếu có chữ ký session + flag: hỏi dùng lại, nếu đồng ý thì gửi phê duyệt luôn
  - Nếu có chữ ký database: hỏi dùng lại, nếu đồng ý thì lưu vào session và gửi phê duyệt
  - **MỚI**: Nếu có chữ ký từ vai trò thấp hơn: hiển thị thông báo đặc biệt và đề xuất tái sử dụng
  - Nếu không có hoặc chọn ký mới: mở popup ký, lưu vào session, gửi phê duyệt
  - Có checkbox "Không hỏi lại trong phiên này"
  - Cho phép xóa chữ ký session (gọi `/api/signature/clear-session`)
- Chữ ký luôn được mã hóa khi lưu session/database

### 3.4 Bảo mật
- Chữ ký mã hóa Fernet (AES-128)
- Session timeout, metadata (IP, user-agent, thời gian tạo)
- Log mọi hành động ký/phê duyệt
- **MỚI**: Kiểm soát chặt chẽ việc tái sử dụng chữ ký (chỉ của chính user đó)

---

## 4. Database schema (SQLite, có thể migrate sang RDBMS khác)

### 4.1 attendances
- id, user_id, check_in, check_out, date, status, note, break_time, is_holiday, holiday_type, ...
- signature (TEXT, base64, mã hóa)
- team_leader_signature (TEXT)
- manager_signature (TEXT)
- approved, approved_by, approved_at

### 4.2 users
- id, name, employee_id, roles, department, password_hash, is_active, email, ...

### 4.3 requests
- id, user_id, request_type, start_date, end_date, reason, status, current_approver_id, step, reject_reason

### 4.4 audit_logs
- id, user_id, action, table_name, record_id, old_values, new_values, ip_address, user_agent, created_at

---

## 5. Hướng dẫn cài đặt & phát triển

### 5.1 Cài đặt
```bash
# Clone repo
# Tạo virtualenv, activate
pip install -r requirements.txt
# Khởi tạo DB
python app.py  # hoặc flask db upgrade
```

### 5.2 Chạy dev
```bash
python app.py
# hoặc flask run
```

### 5.3 Testing
```bash
python scripts/test_signature_system.py
```

### 5.4 Migrate DB
```bash
flask db migrate -m "msg"
flask db upgrade
```

---

## 6. Mở rộng & tối ưu

- Có thể chuyển sang PostgreSQL/MySQL dễ dàng (chỉ đổi URI SQLAlchemy)
- Có thể tích hợp OAuth2, SSO, LDAP cho login
- Có thể mở rộng chữ ký số (digital signature, PKI)
- Có thể tích hợp gửi email, thông báo
- Có thể thêm dashboard audit, thống kê
- Có thể tách microservice cho phê duyệt hoặc chữ ký
- Có thể dùng Redis/Memcached cho session lớn
- Có thể tích hợp CI/CD, Docker hóa

---

## 7. Lưu ý cho AI/dev khi tái tạo hoặc tối ưu

- **Luôn mã hóa chữ ký khi lưu (dù là base64 image hay vector)**
- **Session chữ ký phải timeout, không dùng vĩnh viễn**
- **Luôn log mọi hành động quan trọng (audit log)**
- **Phân quyền rõ ràng, không để lộ API cho user không hợp lệ**
- **Kiểm tra kỹ input, chống injection, XSS, CSRF**
- **Tách biệt rõ logic nghiệp vụ, logic bảo mật, logic UI**
- **Có thể refactor thành service layer, repository pattern nếu codebase lớn**
- **Có thể dùng queue (Celery, RQ) cho các tác vụ nặng (xuất PDF hàng loạt, gửi mail)**
- **Có thể mở rộng sang mobile app, desktop app với API REST**

---

## 8. Tài liệu tham khảo
- [docs/SMART_SIGNATURE_SYSTEM.md](docs/SMART_SIGNATURE_SYSTEM.md) — Chi tiết hệ thống chữ ký thông minh
- [Flask](https://flask.palletsprojects.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [cryptography](https://cryptography.io/)
- [SignaturePad.js](https://github.com/szimek/signature_pad)
- [SweetAlert2](https://sweetalert2.github.io/)

---

## 9. Roadmap
- [ ] Hỗ trợ chữ ký cho request/phê duyệt nghỉ phép
- [ ] Tích hợp chữ ký số PKI
- [ ] Dashboard audit nâng cao
- [ ] Tối ưu performance, caching
- [ ] CI/CD, Docker hóa

---

**Mọi AI hoặc dev đọc README này có thể tái tạo, mở rộng, hoặc tối ưu hệ thống mà vẫn đảm bảo logic nghiệp vụ, bảo mật, và trải nghiệm người dùng như bản gốc.**
