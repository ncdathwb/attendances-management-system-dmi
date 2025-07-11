// DOM Elements
const timeAttendanceForm = document.getElementById('timeAttendanceForm');
const roleSelect = document.getElementById('role-select');
const currentRole = document.getElementById('current-role');

// Global variables are declared in the HTML template to avoid conflicts
// let dashboardAttendanceData = [];
// let currentPage = 1;
// const rowsPerPage = 5;
// let approvalPage = 1;
// let approvalPerPage = 10;

// CSRF token function with better error handling
function getCSRFToken() {
    const metaToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    const inputToken = document.querySelector('input[name="csrf_token"]')?.value;
    
    if (!metaToken && !inputToken) {
        console.warn('CSRF token not found');
        return null;
    }
    
    return metaToken || inputToken;
}

// Enhanced API call function with better error handling
async function apiCall(url, options = {}) {
    const csrfToken = getCSRFToken();
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    // Add CSRF token if available
    if (csrfToken) {
        defaultOptions.headers['X-CSRFToken'] = csrfToken;
    }
    
    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(url, finalOptions);
        
        // Handle different response types
        if (response.status === 401) {
            const data = await response.json();
            if (data.error && data.error.includes('Phiên đăng nhập đã hết hạn')) {
                showAlert('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'warning');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
                return response;
            }
        }
        
        // Handle rate limiting
        if (response.status === 429) {
            showAlert('Quá nhiều yêu cầu. Vui lòng thử lại sau.', 'warning');
            return response;
        }
        
        // Handle server errors
        if (response.status >= 500) {
            showAlert('Lỗi server. Vui lòng thử lại sau.', 'error');
            return response;
        }
        
        return response;
    } catch (error) {
        console.error('API call error:', error);
        showAlert('Lỗi kết nối. Vui lòng kiểm tra kết nối mạng.', 'error');
        throw error;
    }
}

// Enhanced current time function with timezone support
function getCurrentTime() {
    const now = new Date();
    const timezoneOffset = now.getTimezoneOffset() * 60000; // offset in milliseconds
    const localTime = new Date(now.getTime() - timezoneOffset);
    return localTime.toISOString().slice(0, 16);
}

// Enhanced date formatting with better locale support
function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
            return 'Invalid Date';
        }
        
        return date.toLocaleDateString('vi-VN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    } catch (error) {
        console.error('Date formatting error:', error);
        return 'Invalid Date';
    }
}

// Enhanced loading spinner with better UX
function showSpinner(container = null) {
    if (!container) {
        console.warn('Container not specified for spinner');
        return;
    }
    
    const existingSpinner = container.querySelector('.spinner');
    if (existingSpinner) {
        existingSpinner.remove();
    }
    
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    spinner.innerHTML = `
        <div class="spinner-content">
            <div class="spinner-circle"></div>
            <p>Đang tải...</p>
        </div>
    `;
    container.appendChild(spinner);
}

// Hide spinner function
function hideSpinner(container = null) {
    if (!container) {
        console.warn('Container not specified for spinner');
        return;
    }
    
    const spinner = container.querySelector('.spinner');
    if (spinner) {
        spinner.remove();
    }
}

// Enhanced alert system with better styling
function showAlert(message, type = 'success') {
    // Chuyển đổi type để tương thích với SweetAlert2
    let sweetAlertType = type;
    if (type === 'danger') {
        sweetAlertType = 'error';
    }
    showToast(message, sweetAlertType);
}

// Load attendance history - REMOVED (using updateAttendanceHistory from HTML template instead)
// async function loadAttendanceHistory() { ... }

// Display attendance history - REMOVED (using renderAttendancePage from HTML template instead)
// function displayAttendanceHistory(history) { ... }

// Get status badge class
function getStatusBadgeClass(status) {
    switch (status.toLowerCase()) {
        case 'present':
            return 'success';
        case 'late':
            return 'warning';
        case 'absent':
            return 'danger';
        default:
            return 'success';
    }
}

// Handle role switching - moved to HTML template to avoid conflicts

// Function to update UI based on role - moved to HTML template to avoid conflicts

// Function to load approval attendance data - moved to HTML template to avoid conflicts

// Add event listeners for approval filters
function setupApprovalEventListeners() {
    // Filter button - moved to HTML template to avoid conflicts
    const btnApprovalFilter = document.getElementById('btnApprovalFilter');
    if (btnApprovalFilter) {
        btnApprovalFilter.addEventListener('click', function() {
            // Function moved to HTML template
        });
    }
    
    // Reset button - moved to HTML template to avoid conflicts
    const btnApprovalReset = document.getElementById('btnApprovalReset');
    if (btnApprovalReset) {
        btnApprovalReset.addEventListener('click', function() {
            // Function moved to HTML template
        });
    }
}

// Function to approve/reject attendance - moved to HTML template to avoid conflicts

// Handle form submission - chỉ chạy nếu form tồn tại
if (timeAttendanceForm) {
    timeAttendanceForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(timeAttendanceForm);
        const action = formData.get('checkIn') ? 'check_in' : 'check_out';
        
        try {
            const response = await apiCall('/api/attendance', {
                method: 'POST',
                body: JSON.stringify({
                    action: action,
                    time: formData.get(action === 'check_in' ? 'checkIn' : 'checkOut'),
                    note: formData.get('note')
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showAlert(data.message, 'success');
                resetForm();
                updateAttendanceHistory();
            } else {
                showAlert(data.error || 'Lỗi khi chấm công', 'danger');
            }
        } catch (error) {
            showAlert('Lỗi kết nối server', 'danger');
        }
    });
}

// Auto refresh session every 25 minutes to prevent timeout
function setupSessionRefresh() {
    setInterval(async () => {
        try {
            await apiCall('/api/attendance/history');
        } catch (error) {
            console.log('Session refresh failed:', error);
        }
    }, 25 * 60 * 1000); // 25 minutes
}

// Initialize - REMOVED (already handled in HTML template)
// The DOMContentLoaded event listener has been moved to the HTML template
// to avoid conflicts and ensure proper initialization order

// Function to setup form event listeners
function setupFormEventListeners() {
    // Save attendance button
    const saveAttendanceBtn = document.getElementById('saveAttendanceBtn');
    if (saveAttendanceBtn) {
        saveAttendanceBtn.addEventListener('click', handleAttendanceSubmit);
    }
    
    // Cancel edit button
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', resetForm);
    }
    
    // Shift select change
    const shiftSelect = document.getElementById('shiftSelect');
    if (shiftSelect) {
        shiftSelect.addEventListener('change', function() {
            const shiftValue = this.value;
            
            if (shiftValue === '1') {
                // Ca 1: 7:30 - 16:30
                document.getElementById('checkInTime').value = '07:30';
                document.getElementById('checkOutTime').value = '16:30';
            } 
            else if (shiftValue === '2') {
                // Ca 2: 8:00 - 17:00
                document.getElementById('checkInTime').value = '08:00';
                document.getElementById('checkOutTime').value = '17:00';
            }
            else if (shiftValue === '3') {
                // Ca 3: 9:00 - 18:00
                document.getElementById('checkInTime').value = '09:00';
                document.getElementById('checkOutTime').value = '18:00';
            }
            else if (shiftValue === '4') {
                // Ca 4: 11:00 - 22:00
                document.getElementById('checkInTime').value = '11:00';
                document.getElementById('checkOutTime').value = '22:00';
            }
        });
    }
}

// Function to handle check in/out
function handleAttendance(action) {
    const date = document.getElementById('attendanceDate').value;
    const time = action === 'check_in' ? 
        document.getElementById('checkInTime').value : 
        document.getElementById('checkOutTime').value;
    const note = document.getElementById('attendanceNote').value;
    // Convert breakTime from hh:mm to decimal hours
    const breakTimeStr = document.getElementById('breakTime').value;
    let breakTime = 1.0;
    if (breakTimeStr) {
        const [hh, mm] = breakTimeStr.split(':').map(Number);
        breakTime = hh + (mm / 60);
    }
    const dayType = document.getElementById('dayType').value;
    const isHoliday = dayType !== 'normal';

    if (!date || !time) {
        showToast('Vui lòng chọn ngày và giờ', 'warning');
        return;
    }

    const datetime = `${date}T${time}`;

    apiCall('/api/attendance', {
        method: 'POST',
        body: JSON.stringify({ 
            action: action,
            datetime: datetime,
            note: note,
            break_time: breakTime,
            is_holiday: isHoliday,
            holiday_type: dayType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showToast(data.error, 'error');
        } else {
            showToast(data.message, 'success');
            updateAttendanceHistory();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Đã xảy ra lỗi khi chấm công', 'error');
    });
}

// Hiển thị toast nếu có messages từ backend
window.addEventListener('DOMContentLoaded', function() {
    if (window.messages && window.messages.length > 0) {
        showToast(window.messages[0], 'success');
    }
});

// Make functions globally available
        // window.switchRole = switchRole; // moved to HTML template
        // window.approveAttendance = approveAttendance; // moved to HTML template

// Function to handle edit attendance
function handleEditAttendance(id) {
    apiCall(`/api/attendance/${id}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert(data.error, 'error');
                return;
            }

            // Fill form with attendance data
            const dateInput = document.getElementById('attendanceDate');
            const checkInTimeInput = document.getElementById('checkInTime');
            const checkOutTimeInput = document.getElementById('checkOutTime');
            const breakTimeInput = document.getElementById('breakTime');
            const dayTypeSelect = document.getElementById('dayType');
            const noteInput = document.getElementById('attendanceNote');
            const editIdInput = document.getElementById('editAttendanceId');
            const saveBtn = document.getElementById('saveAttendanceBtn');
            const cancelBtn = document.getElementById('cancelEditBtn');
            const shiftSelect = document.getElementById('shiftSelect');

            if (dateInput) dateInput.value = data.date;
            if (checkInTimeInput) checkInTimeInput.value = data.check_in ? data.check_in.split(' ')[1].substring(0, 5) : '';
            if (checkOutTimeInput) checkOutTimeInput.value = data.check_out ? data.check_out.split(' ')[1].substring(0, 5) : '';
            if (breakTimeInput) breakTimeInput.value = data.break_time || "01:00";
            if (dayTypeSelect) dayTypeSelect.value = data.holiday_type || '';
            if (noteInput) noteInput.value = data.note || '';
            if (editIdInput) editIdInput.value = id;
            if (shiftSelect) shiftSelect.value = data.shift_code || '';
            
            // Show cancel button and update save button text
            if (cancelBtn) cancelBtn.style.display = 'inline-block';
            if (saveBtn) saveBtn.innerHTML = '<i class="fas fa-save me-2"></i>Cập nhật đăng ký';
            
            if (checkInTimeInput) checkInTimeInput.focus();
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Không thể tải thông tin chấm công', 'error');
        });
}

// Function to delete attendance
function deleteAttendance(id) {
    if (confirm('Bạn có chắc chắn muốn xóa bản ghi chấm công này?')) {
        apiCall(`/api/attendance/${id}`, {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert(data.error, 'error');
            } else {
                showAlert('Đã xóa thành công!', 'success');
                updateAttendanceHistory();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Lỗi server khi xóa!', 'error');
        });
    }
}

// Function to format time for input
function formatTimeForInput(hours) {
    if (typeof hours === 'string' && hours.includes(':')) return hours;
    if (hours === undefined || hours === null || isNaN(hours)) return "01:00";
    const hh = Math.floor(hours);
    const mm = Math.round((hours - hh) * 60);
    return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
}

// Make functions globally available
window.handleEditAttendance = handleEditAttendance;
window.deleteAttendance = deleteAttendance;

// Function to handle form submission
function handleAttendanceSubmit(e) {
    if (e) e.preventDefault();
    const dateInput = document.getElementById('attendanceDate');
    const checkInTimeInput = document.getElementById('checkInTime');
    const checkOutTimeInput = document.getElementById('checkOutTime');
    const noteInput = document.getElementById('attendanceNote');
    const breakTimeInput = document.getElementById('breakTime');
    const dayTypeSelect = document.getElementById('dayType');
    const editIdInput = document.getElementById('editAttendanceId');
    const shiftSelect = document.getElementById('shiftSelect');

    // Lấy chữ ký từ signature pad (canvas) nếu có
    let signature = '';
    if (window.signaturePad) {
        if (window.signaturePad.isEmpty()) {
            showAlert('Vui lòng ký tên xác nhận!', 'warning');
            return;
        }
        signature = window.signaturePad.toDataURL();
        // Gán vào input ẩn để backend nhận được
        const signatureInput = document.getElementById('signature-input');
        if (signatureInput) signatureInput.value = signature;
    } else {
        // Nếu không có signaturePad, lấy từ input ẩn (trường hợp sửa bản ghi)
        const signatureInput = document.getElementById('signature-input');
        signature = signatureInput ? signatureInput.value : '';
    }

    // Kiểm tra các element cần thiết có tồn tại không
    if (!dateInput || !checkInTimeInput || !checkOutTimeInput) {
        showAlert('Không thể tìm thấy form chấm công', 'error');
        return;
    }

    // Get values
    let date = dateInput.value;
    const checkIn = checkInTimeInput.value;
    const checkOut = checkOutTimeInput.value;
    const note = noteInput ? noteInput.value : '';
    const breakTimeStr = breakTimeInput ? breakTimeInput.value : '01:00';
    const dayType = dayTypeSelect ? dayTypeSelect.value : '';
    const isHoliday = dayType !== 'normal';
    // Lấy lại shiftCode từ DOM mỗi lần submit
    const shiftSelectEl = document.getElementById('shiftSelect');
    const shiftCode = shiftSelectEl ? shiftSelectEl.value : '';

    // Validate inputs
    if (!date || !checkIn || !checkOut) {
        showAlert('Vui lòng nhập đầy đủ ngày và giờ vào/ra', 'warning');
        return;
    }
    if (!shiftCode) {
        showAlert('Vui lòng chọn ca làm việc!', 'warning');
        return;
    }

    // Convert date format if using flatpickr
    if (date.includes('/')) {
        const [d, m, y] = date.split('/');
        date = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
    }

    // Calculate break time in hours
    let breakTime = 1.0;
    if (breakTimeStr) {
        const [hh, mm] = breakTimeStr.split(':').map(Number);
        breakTime = hh + (mm / 60);
    }

    // Calculate shift start and end times based on shift code
    let shiftStart = null;
    let shiftEnd = null;
    if (shiftCode === '1') {
        shiftStart = '07:30';
        shiftEnd = '16:30';
    } else if (shiftCode === '2') {
        shiftStart = '08:00';
        shiftEnd = '17:00';
    } else if (shiftCode === '3') {
        shiftStart = '09:00';
        shiftEnd = '18:00';
    } else if (shiftCode === '4') {
        shiftStart = '11:00';
        shiftEnd = '22:00';
    }
    // Nếu người dùng đã sửa giờ vào/ra, shiftStart/shiftEnd phải lấy từ input
    if (!shiftStart || !shiftEnd) {
        shiftStart = checkIn;
        shiftEnd = checkOut;
    }
    shiftStart = shiftStart || '';
    shiftEnd = shiftEnd || '';

    // Log chi tiết để debug
    console.log('shiftCode:', shiftCode, 'shiftStart:', shiftStart, 'shiftEnd:', shiftEnd);

    // Prepare data
    const data = {
        date: date,
        check_in: checkIn,
        check_out: checkOut,
        note: note,
        break_time: breakTime,
        is_holiday: isHoliday,
        holiday_type: dayType,
        shift_code: shiftCode,
        shift_start: shiftStart,
        shift_end: shiftEnd,
        signature: signature // LUÔN gửi chữ ký (có thể rỗng)
    };

    console.log('Submitting data:', data);

    // If editing, use PUT request
    if (editIdInput && editIdInput.value) {
        apiCall(`/api/attendance/${editIdInput.value}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert(data.error, 'error');
            } else {
                showAlert('Cập nhật chấm công thành công', 'success');
                resetForm();
                updateAttendanceHistory();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Đã xảy ra lỗi khi cập nhật chấm công', 'error');
        });
        return;
    }

    // If new record, use POST request
    apiCall('/api/attendance', {
        method: 'POST',
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert(data.error, 'error');
        } else {
            showAlert('Lưu chấm công thành công', 'success');
            resetForm();
            updateAttendanceHistory();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Đã xảy ra lỗi khi lưu chấm công', 'error');
    });
}

// Function to reset form
function resetForm() {
    const attendanceForm = document.getElementById('attendanceForm');
    const editAttendanceId = document.getElementById('editAttendanceId');
    const saveAttendanceBtn = document.getElementById('saveAttendanceBtn');
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    
    if (attendanceForm) attendanceForm.reset();
    if (editAttendanceId) editAttendanceId.value = '';
    if (saveAttendanceBtn) saveAttendanceBtn.innerHTML = '<i class="fas fa-save me-2"></i>Lưu đăng ký';
    if (cancelEditBtn) cancelEditBtn.style.display = 'none';
    
    // Set default values
    const today = new Date();
    const dateInput = document.getElementById('attendanceDate');
    const checkInTimeInput = document.getElementById('checkInTime');
    const checkOutTimeInput = document.getElementById('checkOutTime');
    const breakTimeInput = document.getElementById('breakTime');
    const dayTypeSelect = document.getElementById('dayType');
    
    if (dateInput && dateInput._flatpickr) {
        dateInput._flatpickr.setDate(today, true);
    }
    // Format time as HH:mm
    const formattedTime = today.toTimeString().slice(0, 5);
    if (checkInTimeInput) checkInTimeInput.value = formattedTime;
    if (checkOutTimeInput) checkOutTimeInput.value = formattedTime;

    // Set default break time based on day of week
    const dayOfWeek = today.getDay(); // 0 = Sunday, 6 = Saturday
    if (dayOfWeek === 0 || dayOfWeek === 6) {
        if (breakTimeInput) breakTimeInput.value = '01:00';
        if (dayTypeSelect) dayTypeSelect.value = 'weekend';
    } else {
        if (breakTimeInput) breakTimeInput.value = '01:00';
        if (dayTypeSelect) dayTypeSelect.value = 'normal';
    }
}

// Make functions globally available
window.handleAttendanceSubmit = handleAttendanceSubmit;
window.resetForm = resetForm; 

// Thêm vào trong renderAttendancePage hoặc renderApprovalAttendancePage
function getOvertimePrintButton(attendanceId, approved, isAdmin) {
    if (!approved || !isAdmin) return '';
    return `<a href="/admin/attendance/${attendanceId}/export-overtime-pdf" class="btn btn-outline-primary btn-sm ms-1"><i class="fas fa-print"></i> In giấy tăng ca</a>`;
}

// Bulk Export Functions
function setupBulkExport() {
    const bulkExportSection = document.getElementById('bulkExportSection');
    const bulkExportMonth = document.getElementById('bulkExportMonth');
    const bulkExportYear = document.getElementById('bulkExportYear');
    const btnBulkExport = document.getElementById('btnBulkExport');
    const bulkExportType = document.getElementById('bulkExportType');
    const monthSelection = document.getElementById('monthSelection');
    const description = document.getElementById('bulkExportDescription');

    if (!bulkExportSection || !bulkExportMonth || !bulkExportYear || !btnBulkExport || !bulkExportType || !monthSelection || !description) {
        console.warn('Bulk export elements not found');
        return;
    }

    // Populate year dropdown
    const currentYear = new Date().getFullYear();
    for (let year = currentYear - 2; year <= currentYear + 1; year++) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        if (year === currentYear) {
            option.selected = true;
        }
        bulkExportYear.appendChild(option);
    }

    // Set current month
    const currentMonth = new Date().getMonth() + 1;
    bulkExportMonth.value = currentMonth;

    // Show bulk export section for ADMIN role
    const currentRole = document.getElementById('role-select')?.value || 'EMPLOYEE';
    if (currentRole === 'ADMIN') {
        bulkExportSection.style.display = 'block';
    }

    // Add event listener for bulk export button
    btnBulkExport.addEventListener('click', handleBulkExport);
    bulkExportType.addEventListener('change', handleBulkExportTypeChange);
}

// Hàm lấy tổng số bản ghi đã phê duyệt trong tháng/năm để ước lượng thời gian tạo ZIP
async function estimateBulkExportTime(month, year, type = 'month') {
    try {
        let url = `/api/attendance/history?all=1&per_page=1`;
        if (type === 'month') {
            url += `&month=${month}&year=${year}`;
        } else {
            url += `&year=${year}`;
        }
        
        const res = await fetch(url);
        const data = await res.json();
        if (data && data.total) {
            // Giả sử mỗi bản ghi mất 0.5s để tạo PDF
            const seconds = Math.ceil(data.total * 0.5);
            return { total: data.total, seconds };
        }
    } catch (e) {}
    return { total: 0, seconds: 5 };
}

// Hàm xử lý thay đổi loại xuất
function handleBulkExportTypeChange() {
    const exportType = document.getElementById('bulkExportType')?.value;
    const monthSelection = document.getElementById('monthSelection');
    const description = document.getElementById('bulkExportDescription');
    
    if (exportType === 'year') {
        monthSelection.style.display = 'none';
        description.textContent = 'Xuất tất cả giấy tăng ca của năm được chọn';
    } else {
        monthSelection.style.display = 'block';
        description.textContent = 'Xuất tất cả giấy tăng ca của tháng được chọn';
    }
}

// Sửa hàm handleBulkExport để hỗ trợ xuất theo năm
async function handleBulkExport() {
    const exportType = document.getElementById('bulkExportType')?.value;
    const month = document.getElementById('bulkExportMonth')?.value;
    const year = document.getElementById('bulkExportYear')?.value;

    if (!year) {
        showAlert('Vui lòng chọn năm!', 'warning');
        return;
    }
    
    if (exportType === 'month' && !month) {
        showAlert('Vui lòng chọn tháng!', 'warning');
        return;
    }

    const btnBulkExport = document.getElementById('btnBulkExport');
    if (!btnBulkExport) return;
    btnBulkExport.disabled = true;
    const originalText = btnBulkExport.innerHTML;

    // Ước lượng thời gian
    const { total, seconds } = await estimateBulkExportTime(month, year, exportType);
    let countdown = seconds;
    btnBulkExport.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>Đang tạo ZIP... (${countdown}s)`;

    // Đếm ngược
    let countdownInterval = setInterval(() => {
        countdown--;
        if (countdown > 0) {
            btnBulkExport.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>Đang tạo ZIP... (${countdown}s)`;
        } else {
            btnBulkExport.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>Đang tạo ZIP...`;
        }
    }, 1000);

    // Timeout fallback: nếu fetch không hoạt động, tự động reset sau thời gian ước lượng + 5s
    let timeoutFallback = setTimeout(() => {
        clearInterval(countdownInterval);
        btnBulkExport.innerHTML = '<i class="fas fa-check-circle text-success me-2"></i>Đã tải xong!';
        setTimeout(() => {
            btnBulkExport.innerHTML = originalText;
            btnBulkExport.disabled = false;
        }, 2000);
    }, (seconds + 5) * 1000);

    // Dùng fetch để bắt sự kiện khi server bắt đầu trả về response
    let url = `/admin/attendance/export-overtime-bulk?year=${year}`;
    if (exportType === 'month') {
        url += `&month=${month}`;
    }
    
    try {
        const response = await fetch(url);
        
        // Khi server bắt đầu trả về response, dừng đếm ngược ngay lập tức
        clearInterval(countdownInterval);
        clearTimeout(timeoutFallback);
        
        if (response.ok) {
            // Tạo blob và tải về
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            
            // Tạo tên file
            let filename;
            if (exportType === 'month') {
                filename = `tangca_${month.toString().padStart(2, '0')}_${year}.zip`;
            } else {
                filename = `tangca_${year}.zip`;
            }
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);
            
            // Báo đã tải xong
            btnBulkExport.innerHTML = '<i class="fas fa-check-circle text-success me-2"></i>Đã tải xong!';
            setTimeout(() => {
                btnBulkExport.innerHTML = originalText;
                btnBulkExport.disabled = false;
            }, 2000);
        } else {
            throw new Error('Server error');
        }
    } catch (error) {
        console.error('Download error:', error);
        // Nếu fetch thất bại, dùng timeout fallback
        clearInterval(countdownInterval);
        btnBulkExport.innerHTML = '<i class="fas fa-exclamation-triangle text-warning me-2"></i>Lỗi tải file';
        setTimeout(() => {
            btnBulkExport.innerHTML = originalText;
            btnBulkExport.disabled = false;
        }, 3000);
    }
}

// Initialize bulk export when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupBulkExport();
});

// Make functions globally available
window.setupBulkExport = setupBulkExport;
window.handleBulkExport = handleBulkExport; 