# Hệ Thống Quản Lý Chấm Công - DMI

Hệ thống quản lý chấm công toàn diện được xây dựng bằng Flask cho công ty DMI. Hệ thống này cho phép nhân viên ghi lại chấm công, quản lý phê duyệt hồ sơ và quản trị viên quản lý toàn bộ hệ thống.

## Tính Năng

### Cho Nhân Viên
- Ghi lại chấm công hàng ngày (giờ vào/giờ ra)
- Xem lịch sử chấm công
- Gửi yêu cầu nghỉ phép
- Chỉnh sửa hồ sơ chấm công trước khi phê duyệt
- Xem trạng thái phê duyệt

### Cho Trưởng Nhóm
- Phê duyệt hồ sơ chấm công cho thành viên nhóm
- Xem lịch sử chấm công của nhóm
- Quản lý thành viên nhóm

### Cho Quản Lý
- Phê duyệt hồ sơ chấm công sau khi trưởng nhóm phê duyệt
- Xem chấm công toàn phòng ban
- Quản lý thành viên phòng ban

### Cho Quản Trị Viên
- Truy cập toàn bộ hệ thống
- Quản lý người dùng
- Xem tất cả hồ sơ chấm công
- Cấu hình hệ thống

## Công Nghệ Sử Dụng

- **Backend**: Flask (Python)
- **Database**: PostgreSQL với SQLAlchemy ORM
- **Frontend**: HTML, CSS, JavaScript
- **Xác thực**: Flask-Login
- **Di chuyển Database**: Flask-Migrate

## Cài Đặt

1. **Clone repository**
   ```bash
   git clone https://github.com/ncdathwb/attendance-management-system-dmi.git
   cd attendance-management-system-dmi
   ```

2. **Cài đặt dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Cấu hình PostgreSQL**
   - Tạo database PostgreSQL
   - Cập nhật thông tin kết nối trong `app.py`

4. **Khởi tạo database**
   ```bash
   python init_db.py
   ```

5. **Chạy ứng dụng**
   ```bash
   python app.py
   ```

6. **Truy cập ứng dụng**
   Mở trình duyệt và truy cập `http://localhost:5000`

## Cài Đặt Database

Hệ thống đi kèm với danh sách người dùng được cấu hình sẵn trong `danhsach.txt`. Để khởi tạo database với những người dùng này:

```bash
python init_db.py
```

### Tài Khoản Admin Mặc Định
- **Mã nhân viên**: 1395
- **Mật khẩu**: dat123
- **Vai trò**: ADMIN

## Hướng Dẫn Sử Dụng

### Đăng Nhập
- Sử dụng mã nhân viên và mật khẩu để đăng nhập
- Hệ thống hỗ trợ kiểm soát truy cập dựa trên vai trò

### Ghi Chấm Công
1. Chọn ngày
2. Chọn loại ngày (thường, cuối tuần, lễ)
3. Nhập giờ vào và giờ ra
4. Thêm thời gian nghỉ và ghi chú nếu cần
5. Gửi hồ sơ

### Quy Trình Phê Duyệt
1. **Trưởng nhóm** phê duyệt hồ sơ ban đầu
2. **Quản lý** xem xét phê duyệt của trưởng nhóm
3. **Quản trị viên** đưa ra phê duyệt cuối cùng

## Cấu Trúc Tệp

```
DMI-CHAMCONG/
├── app.py                 # Ứng dụng Flask chính
├── init_db.py            # Script khởi tạo database
├── fake_attendance_data.py # Script tạo dữ liệu thử nghiệm
├── requirements.txt      # Dependencies Python
├── danhsach.txt         # Danh sách người dùng để khởi tạo
├── static/              # Tệp tĩnh (CSS, JS)
├── templates/           # Template HTML
└── migrations/          # Tệp di chuyển database
```

## API Endpoints

### Xác Thực
- `POST /login` - Đăng nhập người dùng
- `GET /logout` - Đăng xuất người dùng

### Chấm Công
- `POST /api/attendance` - Ghi chấm công mới
- `GET /api/attendance/history` - Lấy lịch sử chấm công
- `PUT /api/attendance/<id>` - Cập nhật hồ sơ chấm công
- `DELETE /api/attendance/<id>` - Xóa hồ sơ chấm công
- `POST /api/attendance/<id>/approve` - Phê duyệt/từ chối chấm công

### Quản Lý Người Dùng
- `POST /switch-role` - Chuyển đổi vai trò người dùng
- `GET /admin/users` - Quản lý người dùng cho admin

## Cấu Hình

Ứng dụng sử dụng cấu hình sau:

- **Database**: PostgreSQL
- **Secret Key**: Được cấu hình trong `app.py`
- **Quản lý Session**: Flask session

## Đóng Góp

1. Fork repository
2. Tạo feature branch
3. Thực hiện thay đổi
4. Gửi pull request

## Giấy Phép

Dự án này là phần mềm độc quyền của công ty DMI.

## Hỗ Trợ

Để được hỗ trợ và giải đáp thắc mắc, vui lòng liên hệ nhóm phát triển. 