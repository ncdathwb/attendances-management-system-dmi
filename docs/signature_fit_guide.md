# Hướng dẫn sử dụng chức năng điều chỉnh chữ ký vừa khít với ô ký

## Tổng quan

Chức năng **Signature Fit Adapter** tự động điều chỉnh chữ ký để vừa khít với các ô ký trong biểu mẫu, giải quyết vấn đề chữ ký quá nhỏ hoặc quá lớn so với kích thước ô.

## Các loại ô ký được hỗ trợ

### 1. Ô Quản lý (Manager)
- **Kích thước**: 120x40 pixel
- **Màu nền**: Xanh nhạt (#e3f2fd)
- **Sử dụng cho**: Quản lý phê duyệt

### 2. Ô Cấp trên trực tiếp (Supervisor)
- **Kích thước**: 120x40 pixel
- **Màu nền**: Tím nhạt (#f3e5f5)
- **Sử dụng cho**: Cấp trên trực tiếp phê duyệt

### 3. Ô Người xin phép (Applicant)
- **Kích thước**: 120x40 pixel
- **Màu nền**: Xanh lá nhạt (#e8f5e8)
- **Sử dụng cho**: Người xin phép ký

### 4. Ô Trưởng nhóm (Team Leader)
- **Kích thước**: 100x35 pixel
- **Màu nền**: Cam nhạt (#fff3e0)
- **Sử dụng cho**: Trưởng nhóm phê duyệt

### 5. Ô Nhân viên (Employee)
- **Kích thước**: 100x35 pixel
- **Màu nền**: Hồng nhạt (#fce4ec)
- **Sử dụng cho**: Nhân viên ký

## Cách sử dụng

### 1. Điều chỉnh chữ ký cho một ô cụ thể

```python
from utils.signature_manager import signature_manager

# Điều chỉnh chữ ký vừa khít với ô quản lý
fitted_signature = signature_manager.fit_signature_to_form_box(
    signature_data, 
    box_type='manager'
)

# Điều chỉnh chữ ký vừa khít với ô cấp trên
fitted_signature = signature_manager.fit_signature_to_form_box(
    signature_data, 
    box_type='supervisor'
)

# Điều chỉnh chữ ký vừa khít với ô người xin phép
fitted_signature = signature_manager.fit_signature_to_form_box(
    signature_data, 
    box_type='applicant'
)
```

### 2. Tạo chữ ký cho toàn bộ biểu mẫu

```python
# Chuẩn bị dữ liệu chữ ký
signatures = {
    'manager': manager_signature_data,
    'supervisor': supervisor_signature_data,
    'applicant': applicant_signature_data,
    'team_leader': team_leader_signature_data,
    'employee': employee_signature_data
}

# Tạo chữ ký cho toàn bộ biểu mẫu
form_signatures = signature_manager.create_form_signatures(signatures)

# Kết quả
print(form_signatures)
# {
#     'manager': 'fitted_manager_signature_base64',
#     'supervisor': 'fitted_supervisor_signature_base64',
#     'applicant': 'fitted_applicant_signature_base64',
#     'team_leader': 'fitted_team_leader_signature_base64',
#     'employee': 'fitted_employee_signature_base64'
# }
```

### 3. Kiểm tra chữ ký có vừa khít không

```python
# Kiểm tra chữ ký có vừa khít với ô quản lý không
validation_result = signature_manager.validate_signature_fit(
    signature_data, 
    box_type='manager'
)

if validation_result['fits']:
    print("Chữ ký vừa khít với ô")
else:
    print("Chữ ký cần điều chỉnh:")
    for rec in validation_result.get('recommendations', []):
        print(f"- {rec}")
```

## API Endpoints

### 1. Điều chỉnh chữ ký vừa khít với ô

**POST** `/api/signature/fit-to-form`

**Request Body:**
```json
{
    "signature": "base64_signature_data",
    "box_type": "manager"
}
```

**Response:**
```json
{
    "success": true,
    "fitted_signature": "fitted_signature_base64",
    "fit_result": {
        "fits": true,
        "signature_size": [100, 30],
        "box_size": [120, 40],
        "available_size": [112, 32],
        "message": "Chữ ký vừa khít với ô"
    }
}
```

### 2. Tạo chữ ký cho toàn bộ biểu mẫu

**POST** `/api/signature/create-form-signatures`

**Request Body:**
```json
{
    "signatures": {
        "manager": "manager_signature_base64",
        "supervisor": "supervisor_signature_base64",
        "applicant": "applicant_signature_base64",
        "team_leader": "team_leader_signature_base64",
        "employee": "employee_signature_base64"
    }
}
```

**Response:**
```json
{
    "success": true,
    "form_signatures": {
        "manager": "fitted_manager_signature_base64",
        "supervisor": "fitted_supervisor_signature_base64",
        "applicant": "fitted_applicant_signature_base64",
        "team_leader": "fitted_team_leader_signature_base64",
        "employee": "fitted_employee_signature_base64"
    }
}
```

## Tùy chỉnh kích thước ô

### Thiết lập kích thước tùy chỉnh

```python
from utils.signature_fit_adapter import signature_fit_adapter

# Thiết lập kích thước tùy chỉnh cho ô mới
signature_fit_adapter.set_custom_box_size('custom_box', (150, 50))

# Sử dụng ô tùy chỉnh
fitted_signature = signature_fit_adapter.fit_signature_to_box(
    signature_data, 
    box_type='custom_box'
)
```

### Lấy kích thước ô hiện tại

```python
# Lấy kích thước ô quản lý
manager_size = signature_fit_adapter.get_box_size('manager')
print(f"Ô quản lý: {manager_size}")  # (120, 40)

# Lấy kích thước ô nhân viên
employee_size = signature_fit_adapter.get_box_size('employee')
print(f"Ô nhân viên: {employee_size}")  # (100, 35)
```

## Ví dụ sử dụng trong biểu mẫu

### Biểu mẫu "GIẤY ĐỀ NGHỊ TĂNG CA/ĐI LÀM NGÀY NGHỈ"

```python
# Xử lý chữ ký cho biểu mẫu tăng ca
def process_overtime_form_signatures(user_signature):
    # Tạo chữ ký cho các ô trong biểu mẫu
    form_signatures = {
        'manager': user_signature,      # Ô Quản lý
        'supervisor': user_signature,   # Ô Cấp trên trực tiếp
        'applicant': user_signature     # Ô Người xin phép
    }
    
    # Điều chỉnh chữ ký vừa khít với từng ô
    fitted_signatures = signature_manager.create_form_signatures(form_signatures)
    
    return fitted_signatures

# Sử dụng
user_signature = "base64_signature_data"
overtime_signatures = process_overtime_form_signatures(user_signature)

# Kết quả có thể sử dụng trực tiếp trong PDF
manager_signature = overtime_signatures['manager']
supervisor_signature = overtime_signatures['supervisor']
applicant_signature = overtime_signatures['applicant']
```

## Xử lý trường hợp đặc biệt

### 1. Chữ ký trống

Nếu không có chữ ký, hệ thống sẽ tự động tạo ô trống với:
- Đường kẻ ngang để ký
- Chữ "Ký tên" ở giữa
- Màu nền phù hợp với loại ô

### 2. Chữ ký quá lớn

Hệ thống sẽ tự động:
- Thu nhỏ chữ ký để vừa khít với ô
- Giữ nguyên tỷ lệ khung hình
- Thêm padding để không sát viền

### 3. Chữ ký quá nhỏ

Hệ thống sẽ tự động:
- Phóng to chữ ký để vừa khít với ô
- Giữ nguyên tỷ lệ khung hình
- Đảm bảo chất lượng không bị giảm

## Cấu hình nâng cao

### Thay đổi tỷ lệ padding

```python
# Thay đổi padding từ 10% thành 15%
signature_fit_adapter.padding_ratio = 0.15
```

### Thay đổi màu sắc ô

```python
# Thay đổi màu ô quản lý
signature_fit_adapter.box_colors['manager'] = '#ffebee'  # Đỏ nhạt
```

### Thêm loại ô mới

```python
# Thêm loại ô mới
signature_fit_adapter.signature_box_sizes['director'] = (140, 45)
signature_fit_adapter.box_colors['director'] = '#e8eaf6'  # Tím nhạt
```

## Lưu ý quan trọng

1. **Kích thước tối ưu**: Các kích thước ô đã được tối ưu cho biểu mẫu A4
2. **Chất lượng**: Chữ ký được xử lý để đảm bảo chất lượng tốt nhất
3. **Tương thích**: Hỗ trợ tất cả định dạng chữ ký Base64
4. **Hiệu suất**: Xử lý nhanh, phù hợp cho ứng dụng web
5. **Bảo mật**: Không lưu trữ chữ ký, chỉ xử lý tạm thời

## Troubleshooting

### Lỗi thường gặp

1. **Chữ ký không hiển thị**
   - Kiểm tra định dạng Base64
   - Đảm bảo dữ liệu chữ ký không rỗng

2. **Chữ ký bị méo**
   - Kiểm tra tỷ lệ khung hình gốc
   - Điều chỉnh padding_ratio nếu cần

3. **Ô ký quá nhỏ**
   - Tăng kích thước ô bằng set_custom_box_size
   - Hoặc giảm padding_ratio

### Debug

```python
# Bật debug logging
import logging
logging.getLogger('utils.signature_fit_adapter').setLevel(logging.DEBUG)

# Kiểm tra chi tiết
validation = signature_manager.validate_signature_fit(signature_data, 'manager')
print(f"Validation details: {validation}")
```

---

*Hướng dẫn này giúp bạn sử dụng hiệu quả chức năng điều chỉnh chữ ký vừa khít với ô ký trong biểu mẫu.*
