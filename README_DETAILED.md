# Hệ thống Quản lý Chấm công DMI - Tài liệu chi tiết

> Tài liệu chi tiết về các tính năng chính và logic xử lý phức tạp của hệ thống

---

## Tính năng chính & Logic xử lý chi tiết

### 1) Xác thực & Phân quyền (Authentication & Authorization)

#### **Đầu vào**
- `employee_id`: Mã nhân viên (format: chuỗi, không rỗng)
- `password`: Mật khẩu (độ dài tối thiểu 6 ký tự)

#### **Xử lý chi tiết**
1. **Input Validation**:
   - Kiểm tra `employee_id` không rỗng và đúng format
   - Kiểm tra `password` có độ dài hợp lệ
   - Sanitize input để tránh injection

2. **User Lookup**:
   - Tra cứu user trong database theo `employee_id`
   - Kiểm tra tài khoản có `is_active = True` không
   - Kiểm tra tài khoản có bị khóa (`is_deleted = False`) không

3. **Password Verification**:
   - So sánh password hash với `werkzeug.security.check_password_hash()`
   - Sử dụng bcrypt algorithm cho bảo mật

4. **Session Creation**:
   - Tạo session với `user_id`, `roles`, `name`, `employee_id`
   - Set session timeout (mặc định 8 giờ)
   - Ghi log đăng nhập thành công

5. **Rate Limiting**:
   - Giới hạn 100 lần đăng nhập/5 phút theo IP
   - Block IP nếu vượt quá giới hạn

#### **Đầu ra**
- **Thành công**: Redirect đến dashboard với session cookie
- **Thất bại**: Error message với HTTP status code

#### **Lỗi & Ngoại lệ**
- `401 Unauthorized`: Sai thông tin đăng nhập
- `429 Too Many Requests`: Vượt rate limit
- `403 Forbidden`: Tài khoản bị khóa
- `500 Internal Server Error`: Lỗi database

#### **Bảo mật**
- Password được hash với bcrypt
- Session timeout tự động
- CSRF protection cho tất cả forms
- Rate limiting theo IP
- Audit log cho mọi lần đăng nhập

#### **Edge Cases**
- Tài khoản bị khóa sau nhiều lần đăng nhập sai
- Session hết hạn giữa chừng
- Đăng nhập từ nhiều thiết bị khác nhau
- IP thay đổi trong session

---

### 2) Chấm công hàng ngày (Daily Attendance Recording)

#### **Đầu vào**
```json
{
  "date": "2024-01-15",
  "check_in": "08:00",
  "check_out": "17:30",
  "shift_code": "1",
  "break_time": "01:00",            // [MỚI] gửi dạng HH:MM
  "comp_time_regular": "00:00",     // [MỚI] gửi dạng HH:MM
  "comp_time_ot_before_22": "00:00",// [MỚI] gửi dạng HH:MM
  "comp_time_ot_after_22": "00:00", // [MỚI] gửi dạng HH:MM
  "holiday_type": "normal",
  "note": "Ghi chú tùy chọn",
  "signature": "base64_encoded_signature"
}
```

> [MỚI] Chuẩn thời lượng: Backend parse `HH:MM` → PHÚT (int) và tính toán hoàn toàn theo phút. Chỉ khi trả về/hiển thị mới chuyển sang `HH:MM`. Điều này loại bỏ sai số làm tròn khi dùng số thực.

#### **Xử lý chi tiết**

1. **Input Validation**:
   - Validate date format và không cho phép ngày tương lai
   - Validate time format (HH:MM)
   - [MỚI] Các trường thời lượng nhận dạng `HH:MM`; backend tự parse về giờ (0-8h)
   - Kiểm tra `check_out > check_in`
   - Validate `shift_code` (1-5)
   - Validate `break_time` (0-8 giờ)
   - Validate compensation times (0-8 giờ mỗi loại)

2. **Duplicate Check**:
   - Kiểm tra đã chấm công cho ngày này chưa
   - Nếu có, chỉ cho phép update nếu status = 'rejected'

3. **Holiday Type Detection**:
   - `normal`: Ngày làm việc bình thường
   - `weekend`: Cuối tuần
   - `vietnamese_holiday`: Lễ Việt Nam
   - `japanese_holiday`: Lễ Nhật

4. **Work Hours Calculation**:
   - Gọi `update_work_hours()` để tính toán chi tiết
   - Tính `total_work_hours`, `regular_work_hours`
   - Tính `overtime_before_22`, `overtime_after_22`

5. **Signature Processing**:
   - Validate signature format (base64)
   - Mã hóa signature trước khi lưu
   - Lưu vào database với encryption

6. **Database Transaction**:
   - Tạo attendance record với status = 'pending'
   - Lưu tất cả thông tin vào database
   - Commit transaction

#### **Đầu ra**
```json
{
  "message": "Chấm công thành công",
  "work_hours": 8.5,
  "overtime_before_22": "0:30",
  "overtime_after_22": "0:00",
  "signature_info": {
    "has_signature": true,
    "signature_type": "manual"
  }
}
```

#### **Lỗi & Ngoại lệ**
- `400 Bad Request`: Dữ liệu không hợp lệ
- `409 Conflict`: Đã chấm công cho ngày này
- `401 Unauthorized`: Chưa đăng nhập
- `500 Internal Server Error`: Lỗi database

#### **Bảo mật**
- Validate tất cả input
- Mã hóa signature
- Kiểm tra quyền truy cập
- CSRF protection

#### **Edge Cases**
- Tăng ca qua ngày (next_day_checkout = true)
- Ca làm việc qua đêm
- Ngày lễ đặc biệt
- Chữ ký không hợp lệ

---

### 3) Tính toán giờ công và tăng ca (Work Hours & Overtime Calculation)

#### **Logic phức tạp theo loại ngày**

##### **A. Ngày thường (normal)**

**Giờ công thường (regular_work_hours)**:
- Tối đa 8 giờ
- Tính trong khoảng thời gian ca làm việc
- Trừ thời gian nghỉ và đối ứng trong ca

**Tăng ca trước 22h (overtime_before_22)**:
- **Ca 1-4**: Chỉ tính về muộn (sau giờ ra ca nhưng trước 22h)
- **Ca 5 (tự do)**: Tính cả đi làm sớm + về muộn

**Tăng ca sau 22h (overtime_after_22)**:
- Từ 22:00 đến giờ ra
- Tính cả trường hợp qua đêm

**Ví dụ cụ thể**:
```
Ca 1 (8:00-17:00):
- Làm việc: 7:30 - 18:30
- Giờ công thường: 8h (8:00-17:00, trừ 1h nghỉ)
- Tăng ca trước 22h: 1h (17:00-18:00) - KHÔNG tính 7:30-8:00
- Tăng ca sau 22h: 0h

Ca 5 (tự do):
- Làm việc: 7:30 - 18:30  
- Giờ công thường: 8h
- Tăng ca trước 22h: 1.5h (7:30-8:00 + 17:00-18:00)
- Tăng ca sau 22h: 0h
```

##### **B. Ngày lễ Việt Nam (vietnamese_holiday)**

**Giờ công thường**: 8 giờ (ngày nghỉ có lương, không trừ vào thời gian làm)

**Nguyên tắc**: Toàn bộ thời gian làm việc được tính là tăng ca và phân bổ theo mốc 22:00

**Tăng ca trước 22h**: Từ giờ vào đến 22:00 (trừ giờ nghỉ)

**Tăng ca sau 22h**: Từ 22:00 đến giờ ra

**Đối ứng (Comp Time)**:
- UI: disable "Đối ứng trong ca" và chỉ bật "Trước 22h"/"Sau 22h"
- Backend: chặn `comp_time_regular`, `comp_time_overtime` cho Lễ VN; chỉ nhận `comp_time_ot_before_22`, `comp_time_ot_after_22`

##### **C. Cuối tuần (weekend)**

**Giờ công thường**: 0 giờ (ngày nghỉ không lương)

**Tăng ca trước 22h**:
- Từ giờ vào đến **min(22:00, giờ ra)** (giới hạn bởi thời gian làm việc thực tế)
- **Trừ thời gian nghỉ ngay từ đầu** (không trừ 2 lần)
- **Quan trọng**: Tăng ca trước 22h không được vượt quá tổng giờ làm thực tế

**Tăng ca sau 22h**:
- Từ 22:00 đến giờ ra

**Ví dụ cụ thể**:
```
Cuối tuần: 07:30 - 19:30, nghỉ 1h
- Giờ công thường: 0h (cuối tuần)
- Tổng giờ làm: 12h - 1h nghỉ = 11h
- Tăng ca trước 22h: min(22:00, 19:30) - 07:30 - 1h = 19:30 - 07:30 - 1h = 11h ✅
- Tăng ca sau 22h: 0h (không có)
```

##### **D. Lễ Nhật (japanese_holiday)**

**Giờ công thường**: Tối đa 8 giờ
- **Giờ công = total_work_hours** (đã trừ giờ nghỉ), trừ **tất cả loại đối ứng**
- **Giới hạn tối đa 8h** cho giờ công thường
- **Hỗ trợ chọn nhiều loại đối ứng**: `comp_time_regular`, `comp_time_overtime`, `comp_time_ot_before_22`, `comp_time_ot_after_22`

**Tăng ca**: Tổng giờ làm - giờ công thường
- Phân bổ ưu tiên phần sau 22h trước

#### **Compensation Time Logic**

**Các loại đối ứng**:
1. `comp_time_regular`: Đối ứng trong ca
2. `comp_time_ot_before_22`: Đối ứng tăng ca trước 22h
3. `comp_time_ot_after_22`: Đối ứng tăng ca sau 22h
4. `comp_time_overtime`: Đối ứng tăng ca tổng (legacy)

**Quy tắc**:
- **Có thể chọn nhiều loại đối ứng cùng lúc** (linh hoạt hơn)
- Đối ứng không được vượt quá thời gian thực tế
- **Đối ứng trong ca**: trừ vào `regular_work_hours` và `total_work_hours`
- **Đối ứng tăng ca trước 22h**: trừ vào `overtime_before_22` và `total_work_hours`
- **Đối ứng tăng ca sau 22h**: trừ vào `overtime_after_22` và `total_work_hours`
- **Đối ứng tăng ca tổng (legacy)**: trừ vào tổng tăng ca và `total_work_hours`
- **Tổng đối ứng**: Tất cả loại đối ứng được cộng lại và trừ vào `total_work_hours`
- **Validation**: Tổng đối ứng không được vượt quá tổng giờ làm thực tế (đã trừ giờ nghỉ)
- **Hiển thị**: Cột "Đối ứng" trong bảng hiển thị tổng thời gian của tất cả các loại đối ứng được chọn

**Quy tắc enable/disable đối ứng mới**:
1. **< 8h**: Chỉ cho phép `comp_time_regular` (đối ứng trong ca)
2. **≥ 8h và có tăng ca < 22h**: Chỉ cho phép `comp_time_regular` và `comp_time_ot_before_22`
3. **≥ 8h và có tăng ca ≥ 22h**: Cho phép tất cả loại đối ứng
4. **Cuối tuần/Lễ VN**: Chỉ cho phép đối ứng tăng ca (không có đối ứng trong ca)

**Đặc biệt cho cuối tuần**:
- **KHÔNG áp dụng** đối ứng trong ca (`comp_time_regular`, `comp_time_overtime`)
- **CHỈ áp dụng** đối ứng tăng ca (`comp_time_ot_before_22`, `comp_time_ot_after_22`)
- **Lý do**: Cuối tuần không có giờ công thường, chỉ có tăng ca

#### **Validation Logic**

```python
# Kiểm tra có tăng ca không
has_overtime = overtime_before_22_hours > 0.1 or overtime_after_22_hours > 0.1

# Nếu không có tăng ca: chỉ cho phép đối ứng trong ca
if not has_overtime:
    if comp_time_ot_before_22 > 0 or comp_time_ot_after_22 > 0:
        return "Không có tăng ca, chỉ được đối ứng trong ca"

# LOGIC MỚI: Kiểm tra quy tắc đối ứng dựa trên giờ làm việc
if has_overtime:
    # Nếu < 8h: chỉ cho phép đối ứng trong ca
    if actual_work_hours < 8.0:
        if comp_time_ot_before_22 > 0 or comp_time_ot_after_22 > 0:
            return f"Giờ làm việc ({actual_work_hours:.1f}h) < 8h. Chỉ được đối ứng trong ca"
    
    # Nếu ≥ 8h và chỉ có tăng ca trước 22h: chỉ cho phép đối ứng trong ca và trước 22h
    elif actual_work_hours >= 8.0 and overtime_before_22_hours > 0.1 and overtime_after_22_hours <= 0.1:
        if comp_time_ot_after_22 > 0:
            return f"Giờ làm việc ({actual_work_hours:.1f}h) ≥ 8h và chỉ có tăng ca trước 22h. Chỉ được đối ứng trong ca và trước 22h"

# Kiểm tra không vượt quá thực tế cho từng loại đối ứng
if comp_time_ot_before_22 > overtime_before_22_hours:
    return "Đối ứng trước 22h vượt quá thực tế"

if comp_time_ot_after_22 > overtime_after_22_hours:
    return "Đối ứng sau 22h vượt quá thực tế"

# Tổng đối ứng không được vượt quá tổng giờ làm thực tế
# Cuối tuần: chỉ tính đối ứng tăng ca
if holiday_type == 'weekend':
    total_comp_time = (comp_time_ot_before_22 or 0) + (comp_time_ot_after_22 or 0)
else:
    total_comp_time = (comp_time_regular or 0) + (comp_time_ot_before_22 or 0) + (comp_time_ot_after_22 or 0) + (comp_time_overtime or 0)

if total_comp_time > actual_work_hours:
    return f"Tổng đối ứng ({total_comp_time:.1f}h) vượt quá tổng giờ làm thực tế ({actual_work_hours:.1f}h)"
```

#### **Frontend UI Logic**

**Tự động enable/disable các input đối ứng**:
- **Khi thay đổi giờ vào/ra, ca làm việc, giờ nghỉ**: Tự động cập nhật UI
- **Khi < 8h**: Disable `comp_time_ot_before_22` và `comp_time_ot_after_22`
- **Khi ≥ 8h và chỉ có tăng ca trước 22h**: Disable `comp_time_ot_after_22`
- **Khi ≥ 8h và có tăng ca sau 22h**: Enable tất cả
- **Tự động clear giá trị không hợp lệ** khi disable input
- **Toast notification** khi clear giá trị
```

#### **Code Implementation**

```python
def calculate_overtime_before_22(self, shift_code, holiday_type):
    """Tính tăng ca trước 22h theo logic phức tạp"""
    
    if holiday_type in ['vietnamese_holiday', 'weekend']:
        # Ngày lễ và cuối tuần: tính từ check_in đến min(22:00, check_out)
        if self.check_in < twenty_two:
            actual_end = min(self.check_out, twenty_two)
            return (actual_end - self.check_in).total_seconds() / 3600
        return 0.0
    
    else:
        # Ngày thường: phân biệt theo ca
        if shift_code == '5':
            # Ca 5: tính cả đi làm sớm và về muộn
            pre_shift_ot = max(0, (min(self.check_out, shift_start, twenty_two) - self.check_in).total_seconds() / 3600)
            post_shift_ot = max(0, (min(self.check_out, twenty_two) - max(self.check_in, shift_end)).total_seconds() / 3600)
            return pre_shift_ot + post_shift_ot
        else:
            # Ca 1-4: chỉ tính về muộn
            post_shift_ot = max(0, (min(self.check_out, twenty_two) - max(self.check_in, shift_end)).total_seconds() / 3600)
            return post_shift_ot
```

---

### 4) Phê duyệt chấm công (Attendance Approval)

#### **Phân quyền chi tiết**

**Hierarchy**: `EMPLOYEE < TEAM_LEADER < MANAGER < ADMIN`

**Quyền phê duyệt**:
- **ADMIN**: Phê duyệt tất cả, không cần chữ ký
- **MANAGER**: Phê duyệt nhân viên cùng phòng ban
- **TEAM_LEADER**: Phê duyệt nhân viên cùng phòng ban
- **EMPLOYEE**: Chỉ xem bản ghi của mình

#### **Đầu vào**
```json
{
  "action": "approve", // hoặc "reject"
  "signature": "base64_encoded_signature", // tùy chọn
  "note": "Ghi chú phê duyệt" // tùy chọn
}
```

#### **Xử lý chi tiết**

1. **Permission Check**:
   - Kiểm tra user có quyền phê duyệt attendance này không
   - Validate role hierarchy
   - Kiểm tra cùng phòng ban (nếu cần)

2. **Signature Validation** (nếu không phải ADMIN):
   - Kiểm tra có chữ ký hợp lệ không
   - Validate signature format và encryption
   - Kiểm tra signature không quá cũ

3. **Status Update**:
   - Cập nhật `status` = 'approved' hoặc 'rejected'
   - Lưu `approved_by`, `approved_at`
   - Lưu chữ ký người phê duyệt (nếu có)

4. **Notification**:
   - Gửi email thông báo cho nhân viên
   - Ghi audit log chi tiết

#### **Smart Signature System**

**Logic chữ ký thông minh**:
1. Kiểm tra session có chữ ký không
2. Nếu có, hỏi dùng lại
3. Kiểm tra database có chữ ký cũ không
4. Nếu có, đề xuất tái sử dụng
5. Nếu không, yêu cầu ký mới

**API Endpoints**:
- `POST /api/signature/check`: Kiểm tra trạng thái chữ ký
- `POST /api/signature/save-session`: Lưu chữ ký vào session
- `POST /api/signature/clear-session`: Xóa chữ ký khỏi session

#### **Đầu ra**
```json
{
  "message": "Phê duyệt thành công",
  "attendance_id": 123,
  "status": "approved",
  "approved_by": "user_name",
  "approved_at": "2024-01-15T10:30:00"
}
```

#### **Tính năng mở trình duyệt tự động với Selenium (Auto Browser Opening with Selenium)**

**Kích hoạt**: Chỉ khi ADMIN phê duyệt thành công

**URL đích**: `https://drive.google.com/drive/folders/1dHF_x6fCJEs9krtmaZPabBIWiTr5xpB3`

**Công nghệ**: Selenium WebDriver + Chrome + webdriver-manager

**Logic xử lý**:
1. **Khởi tạo**: Sử dụng webdriver-manager để tự động quản lý Chrome driver
2. **Cấu hình**: Chrome options với các flags tối ưu
3. **Tương tác**: Điều hướng và tương tác với Google Drive elements
4. **Fallback**: Sử dụng webbrowser nếu Selenium lỗi

**Code implementation**:
```python
def open_google_drive_with_selenium(admin_name):
    """
    Mở Google Drive với Selenium để tương tác với elements
    """
    driver = None
    try:
        # Cấu hình Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Khởi tạo WebDriver với webdriver-manager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(10)
        
        # Mở Google Drive
        drive_url = "https://drive.google.com/drive/folders/1dHF_x6fCJEs9krtmaZPabBIWiTr5xpB3"
        driver.get(drive_url)
        
        # Tương tác với elements
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-target='docs-chrome']")))
        
        # Scroll và đếm files
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        file_elements = driver.find_elements(By.CSS_SELECTOR, "[data-target='docs-chrome'] [role='gridcell']")
        
        # Giữ browser mở 30 giây
        time.sleep(30)
        
    except Exception as e:
        # Error handling: Thông báo lỗi khi Selenium không thể hoạt động
        print(f"❌ BACKEND SELENIUM: Error: {str(e)}")
        print(f"🚫 BACKEND SELENIUM: Cannot open Google Drive automatically")
    finally:
        if driver:
            driver.quit()
```

**Tính năng tương tác**:
- **Điều hướng**: Tự động mở Google Drive folder
- **Scroll**: Scroll xuống để load thêm content
- **Đếm files**: Đếm số lượng items trong folder
- **Click elements**: Có thể click vào nút "New", folder cụ thể
- **Upload files**: Có thể upload files tự động (cần thêm code)

**Logging**: Ghi log chi tiết quá trình
- `🌐 BACKEND SELENIUM`: Khi mở Chrome thành công
- `✅ BACKEND SELENIUM`: Khi load trang thành công
- `📜 BACKEND SELENIUM`: Khi scroll thành công
- `📋 BACKEND SELENIUM`: Khi đếm files thành công
- `❌ BACKEND SELENIUM ERROR`: Khi có lỗi
- `🌐 BACKEND FALLBACK`: Khi sử dụng fallback

#### **Lỗi & Ngoại lệ**
- `403 Forbidden`: Không có quyền phê duyệt
- `400 Bad Request`: Thiếu chữ ký (nếu cần)
- `404 Not Found`: Không tìm thấy attendance
- `409 Conflict`: Đã được phê duyệt rồi

#### **Bảo mật**
- Role-based access control
- Signature encryption
- Audit logging
- Session timeout cho chữ ký

---

### 5) Báo cáo và xuất dữ liệu (Reporting & Export)

#### **Các loại báo cáo**

##### **A. Báo cáo chấm công**
- **Theo ngày**: Tổng hợp chấm công trong ngày
- **Theo tuần**: Thống kê tuần làm việc
- **Theo tháng**: Báo cáo tháng chi tiết
- **Theo quý**: Tổng hợp quý

##### **B. Báo cáo tăng ca**
- Tăng ca theo từng nhân viên
- Tăng ca theo phòng ban
- Tăng ca theo loại ngày
- So sánh tăng ca các tháng

##### **C. Báo cáo phê duyệt**
- Thời gian phê duyệt trung bình
- Tỷ lệ phê duyệt/từ chối
- Người phê duyệt nhiều nhất

#### **Filter Options**
```json
{
  "date_from": "2024-01-01",
  "date_to": "2024-01-31",
  "department": "IT",
  "user_id": 123,
  "status": "approved",
  "holiday_type": "normal"
}
```

#### **Xuất dữ liệu**

##### **A. PDF Export**
- **Công nghệ**: ReportLab
- **Nội dung**: 
  - Thông tin nhân viên
  - Bảng chấm công chi tiết
  - Tổng hợp giờ công và tăng ca
  - Chữ ký số (nếu có)
- **Format**: A4, song ngữ (Việt-Anh)

##### **B. Excel Export**
- **Format**: CSV
- **Encoding**: UTF-8
- **Nội dung**: Dữ liệu thô để phân tích

##### **C. Bulk Export**
- **ZIP nhiều PDF**: Xuất hàng loạt cho nhiều nhân viên
- **Batch processing**: Xử lý theo lô để tránh timeout

#### **Performance Optimization**
- **Pagination**: Giới hạn 100 records/page
- **Caching**: Cache kết quả báo cáo 5 phút
- **Background processing**: Xuất file lớn trong background
- **Database indexing**: Index cho các cột filter

#### **Đầu ra**
```json
{
  "report_data": {
    "total_records": 150,
    "total_work_hours": 1200,
    "total_overtime": 45.5,
    "approval_rate": 95.2
  },
  "export_url": "/download/report_202401.pdf",
  "generated_at": "2024-01-15T10:30:00"
}
```

---

### 6) Quản lý người dùng (User Management)

#### **CRUD Operations**

##### **A. Tạo người dùng**
```json
{
  "name": "Nguyễn Văn A",
  "employee_id": "NV001",
  "email": "nguyenvana@company.com",
  "department": "IT",
  "roles": "EMPLOYEE,TEAM_LEADER",
  "password": "secure_password"
}
```

##### **B. Cập nhật thông tin**
- Thông tin cá nhân
- Phân quyền
- Trạng thái tài khoản

##### **C. Xóa mềm (Soft Delete)**
- Set `is_deleted = True`
- Không xóa dữ liệu thực
- Ẩn khỏi danh sách

#### **Phân quyền chi tiết**

**EMPLOYEE**:
- Xem và chấm công của mình
- Cập nhật thông tin cá nhân

**TEAM_LEADER**:
- Tất cả quyền của EMPLOYEE
- Phê duyệt nhân viên cùng phòng ban
- Xem báo cáo phòng ban

**MANAGER**:
- Tất cả quyền của TEAM_LEADER
- Quản lý nhân viên trong phòng ban
- Báo cáo toàn phòng ban

**ADMIN**:
- Tất cả quyền
- Quản lý toàn bộ hệ thống
- Cấu hình hệ thống

#### **Security Features**
- Password complexity validation
- Account lockout sau nhiều lần đăng nhập sai
- Session management
- Audit logging cho mọi thay đổi

---

### 7) Hệ thống chữ ký số (Digital Signature System)

#### **Signature Types**
1. **Manual Signature**: Ký tay trên web
2. **Database Signature**: Chữ ký đã lưu trước đó
3. **Session Signature**: Chữ ký trong session hiện tại

#### **Signature Lifecycle**
1. **Creation**: User ký trên SignaturePad
2. **Encryption**: Mã hóa với Fernet (AES-128)
3. **Storage**: Lưu vào database hoặc session
4. **Validation**: Kiểm tra khi sử dụng
5. **Expiration**: Tự động hết hạn sau 30 phút

#### **Smart Reuse Logic**
```python
def get_signature_status(user_id, role):
    # 1. Kiểm tra session signature
    if session_signature_exists():
        return "session_available"
    
    # 2. Kiểm tra database signature
    if db_signature_exists(user_id, role):
        return "database_available"
    
    # 3. Kiểm tra signature từ role thấp hơn
    if lower_role_signature_exists(user_id):
        return "lower_role_available"
    
    return "no_signature"
```

#### **Security Measures**
- **Encryption**: Tất cả chữ ký được mã hóa
- **Session Timeout**: 30 phút tự động hết hạn
- **Role-based Access**: Chỉ dùng chữ ký của chính mình
- **Audit Logging**: Ghi log mọi thao tác chữ ký

---

### 8) Audit Logging (Ghi log kiểm toán)

#### **Logged Actions**
- Đăng nhập/đăng xuất
- Tạo/cập nhật/xóa attendance
- Phê duyệt/từ chối
- Thay đổi thông tin user
- Sử dụng chữ ký

#### **Log Data Structure**
```json
{
  "user_id": 123,
  "action": "APPROVE_ATTENDANCE",
  "table_name": "attendances",
  "record_id": 456,
  "old_values": {"status": "pending"},
  "new_values": {"status": "approved"},
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "created_at": "2024-01-15T10:30:00"
}
```

#### **Audit Features**
- **Immutable Logs**: Không thể sửa/xóa
- **Search & Filter**: Tìm kiếm theo nhiều tiêu chí
- **Export**: Xuất log để phân tích
- **Retention**: Lưu trữ theo policy

---

### 9) Email Notifications

#### **Notification Types**
1. **Approval Notification**: Thông báo khi được phê duyệt
2. **Rejection Notification**: Thông báo khi bị từ chối
3. **Password Reset**: Link reset mật khẩu
4. **System Alerts**: Cảnh báo hệ thống

#### **Email Templates**
- **HTML Format**: Template đẹp, responsive
- **Multi-language**: Hỗ trợ tiếng Việt và tiếng Anh
- **Dynamic Content**: Thông tin động từ database

#### **SMTP Configuration**
```python
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'noreply@company.com'
MAIL_PASSWORD = 'app_password'
```

---

### 10) Performance & Optimization

#### **Database Optimization**
- **Indexing**: Index cho các cột thường query
- **Query Optimization**: Sử dụng SQLAlchemy efficiently
- **Connection Pooling**: Quản lý connection database
- **Caching**: Cache dữ liệu tĩnh

#### **Frontend Optimization**
- **Lazy Loading**: Load dữ liệu theo nhu cầu
- **Pagination**: Phân trang cho danh sách dài
- **Compression**: Nén CSS/JS
- **CDN**: Sử dụng CDN cho static files

#### **Background Processing**
- **PDF Generation**: Xử lý trong background
- **Email Sending**: Queue email để gửi
- **Data Export**: Export file lớn trong background
- **Cleanup Tasks**: Dọn dẹp dữ liệu cũ

---

## Lưu ý quan trọng

### **Logic tính toán phức tạp**
- Hệ thống có logic tính toán giờ công và tăng ca rất phức tạp
- Cần test kỹ lưỡng trước khi deploy production
- Mọi thay đổi logic cần được review và test đầy đủ

### **Bảo mật**
- Tất cả chữ ký đều được mã hóa
- Session timeout tự động
- Audit logging cho mọi thao tác quan trọng
- Input validation nghiêm ngặt

### **Performance**
- Database indexing cho queries thường dùng
- Pagination cho danh sách dài
- Background processing cho tác vụ nặng
- Caching cho dữ liệu tĩnh

---

> **Lưu ý**: Đây là tài liệu chi tiết về logic xử lý. Để hiểu rõ hơn, hãy xem code implementation trong các file tương ứng.

> [MỚI] Về làm tròn:
>
>- Mọi giá trị giờ công/đối ứng/tăng ca đều quy về phút nguyên bằng `int(round(hours*60))` trước khi tính.
>- Phân bổ OT trước/sau 22h cũng theo phút, bảo toàn tổng phút.
>- Khi xuất số giờ (ví dụ `total_work_hours` dạng số) thì lấy `minutes/60` và làm tròn 2 chữ số; khi xuất cho UI thì dùng `HH:MM`.
