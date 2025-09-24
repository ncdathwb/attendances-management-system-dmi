# Hướng dẫn sử dụng chức năng xin nghỉ phép

## Tổng quan

Chức năng xin nghỉ phép cho phép nhân viên tạo và quản lý các đơn xin nghỉ phép theo mẫu chuẩn của công ty DMI HUẾ. Hệ thống hỗ trợ đầy đủ quy trình từ tạo đơn, phê duyệt đến lưu trữ.

## Các tính năng chính

### 1. Tạo đơn xin nghỉ phép
- Form nhập liệu đầy đủ theo mẫu đơn chuẩn
- Hỗ trợ tiếng Việt và tiếng Nhật
- Tự động điền thông tin nhân viên
- Validation dữ liệu đầu vào

### 2. Quản lý đơn xin nghỉ phép
- Xem danh sách tất cả đơn
- Lọc theo trạng thái, nhân viên, ngày tháng
- Phân trang kết quả
- Tìm kiếm nhanh

### 3. Phê duyệt đơn
- Quy trình phê duyệt nhiều cấp
- Chữ ký số cho từng cấp phê duyệt
- Lưu trữ lịch sử phê duyệt

### 4. Báo cáo và thống kê
- Thống kê theo trạng thái
- Báo cáo theo thời gian
- Export dữ liệu

## Cách sử dụng

### Đối với nhân viên

#### 1. Tạo đơn xin nghỉ phép
1. Đăng nhập vào hệ thống
2. Vào menu "Đăng ký nghỉ phép"
3. Điền đầy đủ thông tin theo form
4. Chọn lý do nghỉ phép
5. Chọn chứng từ đính kèm (nếu có)
6. Nhập thời gian nghỉ phép
7. Chọn hình thức nghỉ phép
8. Điền thông tin người thay thế
9. Ký đơn và gửi

#### 2. Xem danh sách đơn
1. Vào menu "Danh sách đơn nghỉ phép"
2. Sử dụng bộ lọc để tìm kiếm
3. Xem chi tiết đơn bằng cách nhấn "Xem"

#### 3. Sửa/xóa đơn
- Chỉ có thể sửa/xóa đơn khi đang ở trạng thái "Chờ phê duyệt"
- Sử dụng nút "Sửa" hoặc "Xóa" trong trang chi tiết

### Đối với quản lý/trưởng nhóm

#### 1. Phê duyệt đơn
1. Vào "Danh sách đơn nghỉ phép"
2. Chọn đơn cần phê duyệt
3. Nhấn "Xem" để xem chi tiết
4. Sử dụng nút "Phê duyệt" hoặc "Từ chối"
5. Ký đơn bằng chữ ký số

#### 2. Quản lý đơn
- Xem tất cả đơn trong phòng ban
- Lọc theo trạng thái, nhân viên
- Theo dõi tiến độ phê duyệt

### Đối với admin

#### 1. Quản lý toàn bộ hệ thống
- Xem tất cả đơn trong công ty
- Phê duyệt đơn ở mọi cấp
- Quản lý cấu hình hệ thống

## Cấu trúc dữ liệu

### Bảng `leave_requests`

| Trường | Kiểu dữ liệu | Mô tả |
|--------|---------------|-------|
| id | Integer | ID duy nhất |
| user_id | Integer | ID người tạo đơn |
| employee_name | String | Tên nhân viên |
| team | String | Nhóm/phòng ban |
| employee_code | String | Mã nhân viên |
| reason_sick_child | Boolean | Lý do: Con ốm |
| reason_sick | Boolean | Lý do: Bị ốm |
| reason_death_anniversary | Boolean | Lý do: Đám giỗ |
| reason_other | Boolean | Lý do khác |
| reason_other_detail | Text | Chi tiết lý do khác |
| hospital_confirmation | Boolean | Giấy xác nhận bệnh viện |
| wedding_invitation | Boolean | Thiệp mời đám cưới |
| death_birth_certificate | Boolean | Giấy chứng tử/sinh |
| leave_from_* | Integer | Thời gian bắt đầu nghỉ |
| leave_to_* | Integer | Thời gian kết thúc nghỉ |
| annual_leave_days | Integer | Số ngày phép năm |
| unpaid_leave_days | Integer | Số ngày nghỉ không lương |
| special_leave_days | Integer | Số ngày nghỉ đặc biệt |
| special_leave_type | String | Loại nghỉ đặc biệt |
| substitute_name | String | Tên người thay thế |
| substitute_employee_id | String | Mã nhân viên thay thế |
| status | String | Trạng thái: pending/approved/rejected |
| manager_approval | Boolean | Phê duyệt quản lý |
| manager_signature | Text | Chữ ký quản lý |
| direct_superior_approval | Boolean | Phê duyệt cấp trên |
| direct_superior_signature | Text | Chữ ký cấp trên |
| applicant_signature | Text | Chữ ký người xin phép |
| created_at | DateTime | Thời gian tạo |
| updated_at | DateTime | Thời gian cập nhật |
| notes | Text | Ghi chú |

## Quy trình phê duyệt

### 1. Trạng thái đơn
- **pending**: Chờ phê duyệt
- **approved**: Đã phê duyệt
- **rejected**: Bị từ chối

### 2. Luồng phê duyệt
```
Nhân viên tạo đơn → Trưởng nhóm phê duyệt → Quản lý phê duyệt → Hoàn tất
```

### 3. Quyền phê duyệt
- **Trưởng nhóm**: Phê duyệt đơn của nhóm mình
- **Quản lý**: Phê duyệt đơn của phòng ban
- **Admin**: Phê duyệt tất cả đơn

## Cài đặt và triển khai

### 1. Tạo bảng cơ sở dữ liệu
```bash
python scripts/create_leave_request_table.py
```

### 2. Kiểm tra quyền truy cập
- Đảm bảo user có role phù hợp
- Kiểm tra CSRF token
- Kiểm tra session timeout

### 3. Tích hợp với hệ thống hiện tại
- Sử dụng chung hệ thống authentication
- Tích hợp với hệ thống chữ ký số
- Sử dụng chung audit log

## Xử lý lỗi thường gặp

### 1. Lỗi validation
- Kiểm tra dữ liệu đầu vào
- Đảm bảo các trường bắt buộc được điền
- Validate định dạng ngày tháng

### 2. Lỗi quyền truy cập
- Kiểm tra role của user
- Kiểm tra quyền phê duyệt
- Kiểm tra quyền sửa/xóa

### 3. Lỗi cơ sở dữ liệu
- Kiểm tra kết nối database
- Kiểm tra cấu trúc bảng
- Kiểm tra foreign key constraints

## Bảo mật

### 1. Xác thực và phân quyền
- Sử dụng Flask-Login
- Kiểm tra role-based access control
- Validate session timeout

### 2. Bảo vệ dữ liệu
- Sử dụng CSRF protection
- Validate input data
- Sanitize output data

### 3. Audit logging
- Ghi log tất cả thao tác
- Lưu trữ lịch sử thay đổi
- Theo dõi quyền truy cập

## Tương lai

### 1. Tính năng dự kiến
- Tích hợp với hệ thống lương
- Tự động tính toán ngày nghỉ
- Gửi email thông báo
- Mobile app

### 2. Cải tiến hiệu suất
- Caching dữ liệu
- Pagination tối ưu
- Index database
- Background jobs

### 3. Tích hợp hệ thống
- ERP system
- HR system
- Payroll system
- Time tracking system
