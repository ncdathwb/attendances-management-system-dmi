# REFACTORING PLAN - Attendance Management System

## Mục tiêu
- Tái cấu trúc templates sử dụng Jinja2 inheritance
- Giảm code duplication
- Tách CSS/JS thành static files
- **KHÔNG thay đổi UI hiện tại**

---

## PHASE 1: CHUẨN BỊ

### 1.1 Backup & Branch
- [x] Tạo branch mới: `refactor/templates`
- [ ] Backup database hiện tại
- [x] Document các templates hiện có

### 1.2 Audit hiện trạng
- [x] Liệt kê tất cả templates và dependencies
- [x] Xác định inline CSS/JS cần extract
- [x] Xác định common components (sidebar, toast, flash)

---

## PHASE 2: TẠO SHARED COMPONENTS

### 2.1 CSS Variables & Design System ✅ DONE
```
static/css/
├── design-system.css    # CSS variables, typography, colors (đã có)
├── components.css       # Buttons, forms, cards (đã có)
├── sidebar.css          # Sidebar styles ✅ MỚI TẠO
├── toast.css            # Toast notification styles ✅ MỚI TẠO
└── animations.css       # Shared animations (đã có)
```

### 2.2 JavaScript Utilities
```
static/js/
├── utils.js             # Common utilities (đã có)
├── toast.js             # Toast functions (cần tạo)
├── notifications.js     # Notification handling (đã có)
└── api.js               # API helper functions (cần tạo)
```

---

## PHASE 3: REFACTOR TEMPLATES

### 3.1 Tạo cấu trúc base templates ✅ DONE

```
templates/
├── base/
│   ├── base.html                   ✅ MỚI TẠO - Layout chung (auth pages)
│   └── base_with_sidebar.html      ✅ MỚI TẠO - Layout với sidebar (main app)
├── includes/
│   ├── sidebar.html                ✅ MỚI TẠO - Navigation menu
│   └── flash_messages.html         ✅ MỚI TẠO - Flash message display
```

### 3.2 Template Refactoring Progress

| Template | Status | Notes |
|----------|--------|-------|
| `login.html` | ✅ DONE | Sử dụng base.html |
| `forgot_password.html` | ✅ DONE | Sử dụng base.html |
| `reset_password.html` | ✅ DONE | Sử dụng base.html |
| `activate.html` | ✅ DONE | Sử dụng base.html |
| `change_password.html` | ✅ DONE | Sử dụng base.html |
| `admin/holidays.html` | ✅ DONE | Sử dụng base_admin.html |
| `admin/departments.html` | ✅ DONE | Sử dụng base_admin.html |
| `admin/create_user.html` | ✅ DONE | Sử dụng base_admin.html |
| `admin/edit_user.html` | ✅ DONE | Sử dụng base_admin.html |
| `admin/deleted_users.html` | ✅ DONE | Sử dụng base_admin.html |
| `leave_history.html` | ✅ DONE | Sử dụng base_leave.html |
| `view_leave_request.html` | ✅ DONE | Sử dụng base_leave.html |
| `leave_requests_list.html` | ✅ DONE | Sử dụng base_leave.html + external CSS/JS |
| `leave_request_form.html` | ✅ DONE | Sử dụng base_leave.html + external CSS |
| `dashboard.html` | ✅ PARTIAL | CSS extracted, data bridges created (xem DASHBOARD_REFACTOR_PLAN.md) |
| `settings.html` | ✅ DONE | CSS extracted to settings.css |
| `personal_signature.html` | ✅ DONE | Sử dụng base.html + external CSS/JS |
| `admin/users.html` | ✅ DONE | CSS extracted to admin-users.css |

### 3.3 Block Structure
```html
{% extends "base/base_with_sidebar.html" %}

{% block title %}Page Title{% endblock %}
{% block extra_css %}<!-- Page-specific CSS -->{% endblock %}
{% block content %}<!-- Main content -->{% endblock %}
{% block extra_js %}<!-- Page-specific JS -->{% endblock %}
```

---

## PRIORITY ORDER

| # | Task | Risk | Effort | Status |
|---|------|------|--------|--------|
| 1 | Phase 1.2 - Audit hiện trạng | NONE | LOW | ✅ DONE |
| 2 | Phase 2.1 - Extract CSS (sidebar, toast, admin, leave) | LOW | MEDIUM | ✅ DONE |
| 3 | Phase 3.1 - Base templates | LOW | HIGH | ✅ DONE |
| 4 | Refactor auth templates (login, forgot, reset, activate, change_password) | LOW | LOW | ✅ DONE |
| 5 | Refactor admin templates (holidays, departments, create_user, edit_user, deleted_users) | MEDIUM | HIGH | ✅ DONE |
| 6 | Refactor leave templates | MEDIUM | HIGH | ✅ DONE |
| 7 | Refactor dashboard.html | HIGH | HIGH | ✅ PARTIAL (CSS + data bridges) |
| 8 | Refactor admin/users.html | MEDIUM | HIGH | ✅ DONE |
| 9 | Testing & QA | LOW | MEDIUM | ⬜ TODO |

---

## FILES CREATED

### Templates
- `templates/base/base.html` - Base layout cho auth pages
- `templates/base/base_with_sidebar.html` - Base layout với sidebar
- `templates/base/base_admin.html` - Base layout cho admin pages (sidebar 260px)
- `templates/base/base_leave.html` - Base layout cho leave pages
- `templates/includes/sidebar.html` - Shared sidebar component
- `templates/includes/admin_sidebar.html` - Admin sidebar component
- `templates/includes/leave_sidebar.html` - Leave sidebar component
- `templates/includes/flash_messages.html` - Flash messages component

### CSS
- `static/css/sidebar.css` - Sidebar styles
- `static/css/toast.css` - Toast notification styles
- `static/css/admin.css` - Admin pages styles
- `static/css/leave.css` - Leave pages common styles
- `static/css/leave-history.css` - Leave history page styles
- `static/css/leave-requests-list.css` - Leave requests list styles
- `static/css/leave-request-form.css` - Leave request form styles
- `static/css/view-leave-request.css` - View leave request styles

### JavaScript
- `static/js/leave-requests-list.js` - Leave requests list page scripts
- `static/js/personal-signature.js` - Personal signature page scripts

---

## ROLLBACK PLAN

Nếu gặp vấn đề:
1. `git stash` các thay đổi hiện tại
2. `git checkout main` để quay về branch chính
3. Kiểm tra và fix issues trên branch refactor
4. Merge lại khi đã ổn định

---

## TESTING CHECKLIST

### Functional Tests
- [ ] Tất cả routes hoạt động bình thường
- [ ] Login/logout hoạt động
- [ ] CRUD operations cho attendance/leave
- [ ] Email gửi thành công
- [ ] File upload/download hoạt động

### UI Tests
- [ ] UI không thay đổi (visual regression)
- [ ] Toast notifications hiển thị đúng
- [ ] Flash messages hiển thị đúng
- [ ] Sidebar navigation hoạt động
- [ ] Responsive trên mobile/tablet

### Performance
- [ ] Page load time không tăng
- [ ] CSS/JS được cache properly
- [ ] No console errors

---

## DEFINITION OF DONE

Mỗi task được coi là hoàn thành khi:
1. Code được commit với message rõ ràng
2. Không có linting errors
3. Test checklist tương ứng PASS
4. Code review (nếu có team member)

---

## NOTES

- Luôn test trên localhost trước khi deploy
- Commit thường xuyên với message chi tiết
- Nếu thay đổi lớn, tạo PR để review
- **Dashboard.html rất lớn (270KB) - cần refactor cẩn thận từng phần**

---
---

# PHASE 4: TỐI ƯU HÓA LEAVE BULK APPROVE - GOOGLE SHEET SYNC

## Mục tiêu
Tối ưu hóa logic phê duyệt hàng loạt đơn nghỉ phép (`/api/leave/approve-all`) theo pattern đã có của Attendance bulk approve để:
1. **Giảm số lần gọi Google Sheets API** - tránh rate limit
2. **Đảm bảo data integrity** - rollback nếu sync thất bại
3. **Tăng tốc độ xử lý** - batch update thay vì từng record
4. **Không bao giờ mất dữ liệu** - sync thành công mới commit

---

## Phân tích hiện trạng

### Attendance Bulk Approve (ĐÃ TỐI ƯU) ✅
```
Records → Gom theo (dept, month) → Gom theo employee → batchUpdate API → Commit DB
                                                            ↓
                                                    Nếu fail → Rollback
```

### Leave Bulk Approve (CHƯA TỐI ƯU) ❌
```
Records → Commit DB trước → Từng record tạo thread riêng → Gọi API riêng lẻ
                                        ↓
                                Dễ hit rate limit, không rollback được
```

---

## Giải pháp đề xuất

### Bước 1: Tạo function `batch_update_multi_leave_requests_sync()`
**File**: `app.py` (sau function `batch_update_multi_attendances_sync` ~ line 865)

**Logic**:
1. Nhận list các leave requests đã được approve
2. Gom theo (department, month) → cùng spreadsheet
3. Gom theo employee_id → cùng sheet
4. Chuẩn bị batch updates cho cột P (leave_summary)
5. Gọi `batch_update_values_with_formatting()` một lần cho mỗi employee
6. Trả về `{success_ids: [], failed: [], total_api_calls: N}`

### Bước 2: Tạo function `_prepare_batch_updates_for_leave()`
**File**: `app.py` (sau `_prepare_batch_updates_for_attendance` ~ line 942)

**Logic**:
1. Nhận (sheet_name, row_index, leave_data)
2. Chuẩn bị update cho cột P với leave summary
3. Xử lý các loại đơn khác nhau (full_day, half_day, 30min_break, late_early)
4. Trả về list updates `[{range: 'Sheet!P5', values: [['Nghỉ phép: 1 ngày']]}]`

### Bước 3: Refactor `approve_all_leave_requests()`
**File**: `app.py` (line ~16309)

**Thay đổi**:
1. **ADMIN flow**: Gom records vào `admin_records_for_batch` (giống attendance)
2. **Gọi batch update**: `batch_update_multi_leave_requests_sync(batch_data)`
3. **Xử lý kết quả**:
   - Success → Mark as approved, commit
   - Fail → Rollback status, không approve
4. **Commit DB SAU khi sync thành công**

### Bước 4: Xử lý các loại leave request đặc biệt
- `full_day` / `half_day`: Cập nhật cột P với số ngày nghỉ
- `30min_break`: Chỉ memo vào cột P
- `late_early`: Cập nhật cột P + điều chỉnh cột G/K

### Bước 5: Thêm Rate Limit và Retry Logic
- Exponential backoff cho lỗi 429 (quota exceeded)
- Max 3 retries per batch
- Delay 1s → 2s → 4s giữa các retries

---

## Chi tiết Implementation

### 4.1. Function `batch_update_multi_leave_requests_sync()`

```python
def batch_update_multi_leave_requests_sync(leave_requests_with_data, timeout_seconds=120):
    """
    BATCH UPDATE nhiều leave request records trong 1 lần gọi API.
    Gom các records theo spreadsheet (department + month) để giảm số lần gọi API.

    Args:
        leave_requests_with_data: List of dicts with keys:
            - leave_request: LeaveRequest object
            - employee_team: department name
            - employee_id: employee ID string
            - leave_data: dict with date, leave_summary, etc.
            - original_status: status before approval attempt
        timeout_seconds: Timeout cho toàn bộ quá trình

    Returns:
        dict: {
            'success_ids': list of leave_request IDs được cập nhật thành công,
            'failed': list of {'id': id, 'error': error_message},
            'total_api_calls': số lần gọi Google Sheets API
        }
    """
    # Logic tương tự batch_update_multi_attendances_sync
    # 1. Gom theo (dept, month)
    # 2. Gom theo employee
    # 3. Batch update per employee
```

### 4.2. Function `_prepare_batch_updates_for_leave()`

```python
def _prepare_batch_updates_for_leave(sheet_name, row_index, leave_data):
    """
    Chuẩn bị danh sách updates cho một leave request record.
    Trả về list of {'range': 'Sheet!P5', 'values': [['value']]}
    """
    updates = []

    # Column P = Leave summary/memo
    leave_summary = leave_data.get('leave_summary', '')
    if leave_summary:
        a1 = f"{sheet_name}!P{row_index}"
        updates.append({'range': a1, 'values': [[leave_summary]]})

    # Xử lý late_early: cần điều chỉnh cột G hoặc K
    if leave_data.get('late_early_type'):
        late_early_type = leave_data['late_early_type']
        late_early_minutes = leave_data.get('late_early_minutes', 0)
        # Logic điều chỉnh giờ vào/ra...

    return updates
```

### 4.3. Refactored `approve_all_leave_requests()` flow

```python
# ADMIN flow - thay đổi chính:
admin_records_for_batch = []

for leave_request in leave_requests:
    if current_role == 'ADMIN' and action == 'approve':
        # Lưu original status để rollback nếu cần
        original_status = leave_request.status

        # Chuẩn bị data cho batch
        employee = leave_request.user
        employee_team = employee.department or 'Unknown'
        employee_id = employee.employee_id

        # Tính leave_summary dựa trên loại đơn
        leave_data = prepare_leave_data_for_sheet(leave_request)

        admin_records_for_batch.append({
            'leave_request': leave_request,
            'employee_team': employee_team,
            'employee_id': employee_id,
            'leave_data': leave_data,
            'original_status': original_status
        })

# ===== BATCH UPDATE GOOGLE SHEETS =====
if current_role == 'ADMIN' and action == 'approve' and admin_records_for_batch:
    batch_result = batch_update_multi_leave_requests_sync(admin_records_for_batch)

    # Xử lý kết quả
    for record in admin_records_for_batch:
        lr = record['leave_request']
        if lr.id in batch_result['success_ids']:
            # Success - mark as approved
            lr.status = 'approved'
            lr.step = 'done'
            lr.google_sheet_synced = True
            lr.google_sheet_sync_at = datetime.now()
            approved_count += 1
            approved_leave_ids.append(lr.id)
        else:
            # Fail - rollback to original status
            lr.status = record['original_status']
            lr.google_sheet_synced = False
            # Find error message
            error_msg = next((f['error'] for f in batch_result['failed'] if f['id'] == lr.id), 'Unknown')
            lr.google_sheet_sync_error = error_msg
            google_sheet_errors.append({
                'id': lr.id,
                'employee_name': lr.employee_name,
                'error': error_msg
            })

# ===== COMMIT SAU KHI BATCH UPDATE =====
db.session.commit()
```

---

## Files cần sửa đổi

| File | Thay đổi | Line |
|------|----------|------|
| `app.py` | Thêm `batch_update_multi_leave_requests_sync()` | ~866 |
| `app.py` | Thêm `_prepare_batch_updates_for_leave()` | ~943 |
| `app.py` | Refactor `approve_all_leave_requests()` | ~16309 |

---

## Ước tính cải thiện

| Metric | Trước | Sau |
|--------|-------|-----|
| API calls cho 50 đơn | ~50 calls | ~5-10 calls |
| Thời gian xử lý | ~30-60s | ~5-10s |
| Risk rate limit | Cao | Thấp |
| Data integrity | Không đảm bảo | Đảm bảo 100% |
| Rollback capability | Không | Có |

---

## Rollback Strategy

Nếu có lỗi xảy ra:
1. **Google API fail** → Không approve record, giữ status cũ
2. **Database commit fail** → Rollback toàn bộ transaction
3. **Partial success** → Chỉ approve những record sync thành công

---

## Testing Plan

1. Test với 5 đơn nghỉ phép → verify batch grouping
2. Test với 20 đơn từ nhiều department → verify multi-spreadsheet
3. Test rate limit bằng cách approve 50+ đơn liên tục
4. Test rollback bằng cách giả lập Google API error
5. Test data integrity: so sánh DB status với Google Sheet

---

## Implementation Checklist

- [x] Tạo `batch_update_multi_leave_requests_sync()` ✅ DONE
- [x] Tạo `_prepare_batch_updates_for_leave()` ✅ DONE
- [x] Refactor `approve_all_leave_requests()` cho ADMIN flow ✅ DONE
- [x] Xử lý các loại leave: full_day, half_day, 30min_break, late_early ✅ DONE (sử dụng process_leave_requests_for_excel)
- [x] Thêm retry logic với exponential backoff ✅ DONE (sử dụng lại từ batch_update_values_with_formatting)
- [ ] Test với nhiều đơn từ nhiều department
- [ ] Test rollback khi Google API fail
- [ ] Verify data integrity

---

## Notes

- Giữ nguyên logic cho TEAM_LEADER và MANAGER (không cần sync Google Sheet)
- Chỉ ADMIN mới trigger Google Sheet sync
- Backward compatible với single approve (không thay đổi `/leave-request/<id>/approve`)
- Sử dụng lại các helper functions đã có: `GoogleDriveAPI`, `batch_update_values_with_formatting`
