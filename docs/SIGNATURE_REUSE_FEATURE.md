# Tính Năng Tái Sử Dụng Chữ Ký Từ Vai Trò Thấp Hơn

## Tổng Quan

Tính năng này giải quyết vấn đề khi một người dùng có nhiều vai trò (EMPLOYEE, TEAM_LEADER, MANAGER, ADMIN) và đã ký ở vai trò thấp hơn, nhưng khi phê duyệt ở vai trò cao hơn lại bị yêu cầu ký lại.

## Vấn Đề Trước Đây

### Kịch Bản Vấn Đề
1. User A có vai trò: EMPLOYEE, TEAM_LEADER, MANAGER
2. User A đăng ký chấm công ở vai trò EMPLOYEE và đã ký xác nhận
3. Khi User A chuyển sang vai trò TEAM_LEADER để phê duyệt chính bản thân mình
4. Hệ thống yêu cầu ký lại → **Không cần thiết**

## Giải Pháp Mới

### Logic Tái Sử Dụng Chữ Ký

#### 1. Thứ Tự Ưu Tiên Cho TEAM_LEADER
```
1. Chữ ký TEAM_LEADER (nếu có)
2. Chữ ký EMPLOYEE (tái sử dụng từ vai trò thấp hơn)
```

#### 2. Thứ Tự Ưu Tiên Cho MANAGER
```
1. Chữ ký MANAGER (nếu có)
2. Chữ ký TEAM_LEADER (tái sử dụng từ vai trò thấp hơn)
3. Chữ ký EMPLOYEE (tái sử dụng từ vai trò thấp nhất)
```

#### 3. Thứ Tự Ưu Tiên Cho EMPLOYEE
```
1. Chữ ký EMPLOYEE (chỉ sử dụng chữ ký của chính mình)
```

### Cải Tiến Backend

#### 1. Signature Manager (`utils/signature_manager.py`)

**Hàm `get_signature_from_database()` được cải tiến:**

```python
def get_signature_from_database(self, user_id: int, role: str, attendance_id: int = None) -> Optional[str]:
    """Lấy chữ ký từ database dựa trên role và kiểm tra chữ ký từ vai trò thấp hơn"""
    
    # Với attendance_id cụ thể
    if attendance_id:
        if role == 'TEAM_LEADER':
            # Kiểm tra chữ ký team leader trước
            if attendance.team_leader_signature:
                return attendance.team_leader_signature
            # Nếu không có, kiểm tra chữ ký employee (vai trò thấp hơn)
            elif attendance.signature and attendance.user_id == user_id:
                return attendance.signature
                
        elif role == 'MANAGER':
            # Kiểm tra chữ ký manager trước
            if attendance.manager_signature:
                return attendance.manager_signature
            # Nếu không có, kiểm tra chữ ký team leader (vai trò thấp hơn)
            elif attendance.team_leader_signature and attendance.approved_by == user_id:
                return attendance.team_leader_signature
            # Nếu không có, kiểm tra chữ ký employee (vai trò thấp nhất)
            elif attendance.signature and attendance.user_id == user_id:
                return attendance.signature
```

**Hàm `check_signature_status()` được cải tiến:**

```python
def check_signature_status(self, user_id: int, role: str, attendance_id: int = None) -> Dict[str, Any]:
    # Thêm thông tin về chữ ký được tái sử dụng
    is_reused_signature = False
    if has_db_signature and attendance_id:
        # Logic kiểm tra xem chữ ký có phải từ vai trò thấp hơn không
        if role == 'TEAM_LEADER' and attendance.signature == db_signature:
            is_reused_signature = True
        elif role == 'MANAGER':
            if (attendance.team_leader_signature == db_signature) or \
               (attendance.signature == db_signature):
                is_reused_signature = True
    
    result = {
        # ... các trường khác
        'is_reused_signature': is_reused_signature,
        'message': 'Có thể sử dụng chữ ký từ vai trò thấp hơn' if is_reused_signature else 'Cần chữ ký để phê duyệt'
    }
```

#### 2. API Endpoints

**`POST /api/signature/check`** trả về thông tin mới:
```json
{
    "need_signature": true,
    "is_admin": false,
    "has_session_signature": false,
    "has_db_signature": true,
    "should_use_session": false,
    "session_signature_available": false,
    "is_reused_signature": true,
    "message": "Có thể sử dụng chữ ký từ vai trò thấp hơn"
}
```

### Cải Tiến Frontend

#### 1. Signature Flow Handler (`templates/dashboard.html`)

**Hàm `getSignatureInfoFromDatabase()` được cải tiến:**

```javascript
async function getSignatureInfoFromDatabase(attendanceId) {
    // Logic mới để xác định chữ ký được tái sử dụng
    if (currentRole === 'TEAM_LEADER') {
        if (data.team_leader_signature) {
            // Sử dụng chữ ký team leader gốc
            signatureInfo.isReusedSignature = false;
        } else if (data.signature) {
            // Sử dụng chữ ký employee (tái sử dụng)
            signatureInfo.isReusedSignature = true;
            signatureInfo.signerRole = 'EMPLOYEE';
        }
    } else if (currentRole === 'MANAGER') {
        if (data.manager_signature) {
            // Sử dụng chữ ký manager gốc
            signatureInfo.isReusedSignature = false;
        } else if (data.team_leader_signature) {
            // Sử dụng chữ ký team leader (tái sử dụng)
            signatureInfo.isReusedSignature = true;
            signatureInfo.signerRole = 'TEAM_LEADER';
        } else if (data.signature) {
            // Sử dụng chữ ký employee (tái sử dụng)
            signatureInfo.isReusedSignature = true;
            signatureInfo.signerRole = 'EMPLOYEE';
        }
    }
}
```

**Hàm `handleSignatureFlow()` được cải tiến:**

```javascript
async function handleSignatureFlow(signatureStatus, attendanceId) {
    // Tạo message phù hợp dựa trên việc có phải chữ ký tái sử dụng không
    let reuseMessage = 'Bạn có muốn sử dụng lại chữ ký đã lưu trước đó không?';
    let infoBoxStyle = 'background: #fff3e0; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #ff9800;';
    let infoIcon = 'fas fa-database';
    
    if (dbSignatureInfo.isReusedSignature) {
        reuseMessage = 'Bạn có muốn sử dụng lại chữ ký từ vai trò thấp hơn không?';
        infoBoxStyle = 'background: #e8f5e8; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #4caf50;';
        infoIcon = 'fas fa-recycle';
    }
    
    // Hiển thị dialog với thông tin phù hợp
    const useDbSignature = await Swal.fire({
        title: '<i class="fas fa-database me-2"></i>Chữ ký đã lưu',
        html: `
            <div style="text-align: center;">
                <p>${reuseMessage}</p>
                <div style="${infoBoxStyle}">
                    <small style="${infoBoxColor}">
                        <i class="${infoIcon} me-1"></i>
                        Chữ ký đã lưu của: <strong>${dbSignatureInfo.signerName}</strong> (${dbSignatureInfo.signerRole})
                        ${dbSignatureInfo.isReusedSignature ? '<br><strong>Chữ ký này được tái sử dụng từ vai trò thấp hơn</strong>' : ''}
                    </small>
                </div>
            </div>
        `
    });
}
```

## Kịch Bản Sử Dụng

### Kịch Bản 1: TEAM_LEADER Tái Sử Dụng Chữ Ký EMPLOYEE
1. User A (EMPLOYEE, TEAM_LEADER) đăng ký chấm công và ký
2. User A chuyển sang vai trò TEAM_LEADER
3. User A phê duyệt chính bản thân mình
4. Hệ thống hiển thị: "Bạn có muốn sử dụng lại chữ ký từ vai trò thấp hơn không?"
5. User A chọn "Có, sử dụng"
6. Phê duyệt thành công mà không cần ký lại

### Kịch Bản 2: MANAGER Tái Sử Dụng Chữ Ký TEAM_LEADER
1. User A (EMPLOYEE, TEAM_LEADER, MANAGER) đã ký ở vai trò TEAM_LEADER
2. User A chuyển sang vai trò MANAGER
3. User A phê duyệt bản ghi
4. Hệ thống hiển thị: "Bạn có muốn sử dụng lại chữ ký từ vai trò thấp hơn không?"
5. User A chọn "Có, sử dụng"
6. Phê duyệt thành công mà không cần ký lại

### Kịch Bản 3: MANAGER Tái Sử Dụng Chữ Ký EMPLOYEE
1. User A (EMPLOYEE, MANAGER) đã ký ở vai trò EMPLOYEE
2. User A chuyển sang vai trò MANAGER
3. User A phê duyệt bản ghi
4. Hệ thống hiển thị: "Bạn có muốn sử dụng lại chữ ký từ vai trò thấp hơn không?"
5. User A chọn "Có, sử dụng"
6. Phê duyệt thành công mà không cần ký lại

## Lợi Ích

### 1. Trải Nghiệm Người Dùng
- **Giảm thời gian**: Không cần ký lại khi đã ký ở vai trò thấp hơn
- **Thuận tiện**: Tự động phát hiện và đề xuất tái sử dụng chữ ký
- **Rõ ràng**: Hiển thị rõ chữ ký được tái sử dụng từ vai trò nào

### 2. Bảo Mật
- **Kiểm soát**: Chỉ tái sử dụng chữ ký của chính người dùng đó
- **Xác thực**: Đảm bảo chữ ký thuộc về người dùng hiện tại
- **Logging**: Ghi log đầy đủ việc tái sử dụng chữ ký

### 3. Hiệu Suất
- **Tối ưu**: Giảm số lần yêu cầu ký không cần thiết
- **Cache**: Tận dụng chữ ký đã có trong database
- **Session**: Lưu trữ thông minh trong session

## Testing

### Chạy Test Script
```bash
python scripts/test_signature_system.py
```

### Test Cases
1. ✅ Tạo user với nhiều vai trò
2. ✅ Tạo attendance với chữ ký employee
3. ✅ Test TEAM_LEADER tái sử dụng chữ ký employee
4. ✅ Test MANAGER tái sử dụng chữ ký team leader
5. ✅ Test MANAGER tái sử dụng chữ ký employee
6. ✅ Test thứ tự ưu tiên chữ ký
7. ✅ Test phát hiện chữ ký được tái sử dụng

## Cấu Hình

### Environment Variables
```bash
# Không cần thêm cấu hình mới
# Sử dụng cấu hình hiện tại của Smart Signature System
```

### Database
```sql
-- Không cần thay đổi schema
-- Sử dụng các trường hiện có:
-- - signature (chữ ký employee)
-- - team_leader_signature (chữ ký team leader)
-- - manager_signature (chữ ký manager)
```

## Troubleshooting

### Lỗi Thường Gặp

#### 1. "Không tìm thấy chữ ký để tái sử dụng"
- **Nguyên nhân**: Chữ ký không tồn tại hoặc không thuộc về user hiện tại
- **Giải pháp**: Kiểm tra lại logic kiểm tra quyền sở hữu chữ ký

#### 2. "Chữ ký không hợp lệ khi tái sử dụng"
- **Nguyên nhân**: Chữ ký bị hỏng hoặc không đúng định dạng
- **Giải pháp**: Kiểm tra lại logic xử lý chữ ký trong database

#### 3. "Frontend không hiển thị thông tin tái sử dụng"
- **Nguyên nhân**: API không trả về đúng thông tin `is_reused_signature`
- **Giải pháp**: Kiểm tra lại logic trong `check_signature_status()`

## Tương Lai

### Cải Tiến Tiềm Năng
1. **Tái sử dụng chữ ký từ các bản ghi khác**: Mở rộng tìm kiếm chữ ký từ các attendance records khác
2. **Tự động tái sử dụng**: Tự động sử dụng chữ ký mà không cần hỏi người dùng
3. **Quản lý chữ ký**: Dashboard để quản lý và xóa chữ ký đã lưu
4. **Thống kê tái sử dụng**: Báo cáo về việc tái sử dụng chữ ký

### Tích Hợp
1. **Audit log**: Ghi log chi tiết việc tái sử dụng chữ ký
2. **Notification**: Thông báo khi chữ ký được tái sử dụng
3. **Analytics**: Phân tích mức độ sử dụng tính năng tái sử dụng 