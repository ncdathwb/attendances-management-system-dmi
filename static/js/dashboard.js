// DOM Elements
const timeAttendanceForm = document.getElementById('timeAttendanceForm');
const attendanceList = document.getElementById('attendanceList');
const roleSelect = document.getElementById('role-select');
const currentRole = document.getElementById('current-role');

// Global variables
let attendanceData = [];
let currentPage = 1;
const rowsPerPage = 5;
let approvalPage = 1;
let approvalPerPage = 10;

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
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        }).replace(/\//g, '-');
    } catch (error) {
        console.error('Date formatting error:', error);
        return 'Invalid Date';
    }
}

// Enhanced loading spinner with better UX
function showSpinner(container = attendanceList) {
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

// Enhanced alert system with better styling
function showAlert(message, type = 'success') {
    showToast(message, type);
}

// Enhanced toast system with better animations
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        console.warn('Toast container not found');
        return;
    }
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-icon">${getToastIcon(type)}</span>
            <span class="toast-message">${message}</span>
        </div>
    `;
    
    // Apply styles
    Object.assign(toast.style, {
        minWidth: '280px',
        marginBottom: '12px',
        background: getToastBackground(type),
        color: getToastColor(type),
        border: getToastBorder(type),
        borderRadius: '8px',
        padding: '16px 20px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        fontSize: '14px',
        fontWeight: '500',
        textAlign: 'left',
        opacity: '0',
        transform: 'translateY(-20px)',
        transition: 'all 0.3s ease',
        position: 'relative',
        overflow: 'hidden'
    });
    
    toastContainer.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 10);
    
    // Auto remove
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Helper functions for toast styling
function getToastIcon(type) {
    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };
    return icons[type] || icons.info;
}

function getToastBackground(type) {
    const backgrounds = {
        success: '#f0f9ff',
        error: '#fef2f2',
        warning: '#fffbeb',
        info: '#f0f9ff'
    };
    return backgrounds[type] || backgrounds.info;
}

function getToastColor(type) {
    const colors = {
        success: '#065f46',
        error: '#dc2626',
        warning: '#d97706',
        info: '#1e40af'
    };
    return colors[type] || colors.info;
}

function getToastBorder(type) {
    const borders = {
        success: '1px solid #10b981',
        error: '1px solid #ef4444',
        warning: '1px solid #f59e0b',
        info: '1px solid #3b82f6'
    };
    return borders[type] || borders.info;
}

// Load attendance history
async function loadAttendanceHistory() {
    showSpinner();
    try {
        const response = await apiCall('/api/attendance/history');
        const data = await response.json();
        
        if (response.ok) {
            displayAttendanceHistory(data);
        } else {
            showAlert(data.error || 'Lỗi khi tải lịch sử chấm công', 'danger');
        }
    } catch (error) {
        showAlert('Lỗi kết nối server', 'danger');
    } finally {
        hideSpinner();
    }
}

// Display attendance history
function displayAttendanceHistory(history) {
    attendanceList.innerHTML = '';
    
    if (history.length === 0) {
        attendanceList.innerHTML = '<p>Chưa có lịch sử chấm công</p>';
        return;
    }
    
    const table = document.createElement('table');
    table.className = 'table';
    
    // Table header
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>Ngày</th>
            <th>Giờ vào</th>
            <th>Giờ ra</th>
            <th>Trạng thái</th>
        </tr>
    `;
    table.appendChild(thead);
    
    // Table body
    const tbody = document.createElement('tbody');
    history.forEach(record => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(record.date)}</td>
            <td>${record.check_in || '-'}</td>
            <td>${record.check_out || '-'}</td>
            <td><span class="badge badge-${getStatusBadgeClass(record.status)}">${record.status}</span></td>
        `;
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    
    attendanceList.appendChild(table);
}

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

// Handle form submission
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
            timeAttendanceForm.reset();
            loadAttendanceHistory();
        } else {
            showAlert(data.error || 'Lỗi khi chấm công', 'danger');
        }
    } catch (error) {
        showAlert('Lỗi kết nối server', 'danger');
    }
});

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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Lấy vai trò hiện tại
    const roleSelect = document.getElementById('role-select');
    const currentRole = roleSelect ? roleSelect.value : 'EMPLOYEE';
    
    // Cập nhật giao diện theo vai trò hiện tại - moved to HTML template
    
    // Setup event listeners cho approval filters
    setupApprovalEventListeners();
    
    // Setup event listeners cho form
    setupFormEventListeners();
    
    // Set current time in datetime inputs
    const checkInInput = document.getElementById('checkIn');
    const checkOutInput = document.getElementById('checkOut');
    
    if (checkInInput) checkInInput.value = getCurrentTime();
    if (checkOutInput) checkOutInput.value = getCurrentTime();
    
    // Load initial attendance history (chỉ khi là nhân viên)
    if (currentRole === 'EMPLOYEE') {
        loadAttendanceHistory();
    }
    
    // Set up role switcher - moved to HTML template to avoid conflicts
    
    // Setup session refresh
    setupSessionRefresh();

    const today = new Date();
    const dateInput = document.getElementById('attendanceDate');
    const checkInTimeInput = document.getElementById('checkInTime');
    const checkOutTimeInput = document.getElementById('checkOutTime');
    const breakTimeInput = document.getElementById('breakTime');
    const dayTypeSelect = document.getElementById('dayType');
    
    // Format date as YYYY-MM-DD
    const formattedDate = today.toISOString().split('T')[0];
    // Format time as HH:mm
    const formattedTime = today.toTimeString().slice(0, 5);
    
    if (dateInput) dateInput.value = formattedDate;
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
});

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

// Function to update attendance history
function updateAttendanceHistory() {
    console.log('Fetching attendance history...');  // Debug log
    
    // Kiểm tra xem element attendanceHistory có tồn tại không
    const attendanceHistoryElement = document.getElementById('attendanceHistory');
    if (!attendanceHistoryElement) {
        console.log('attendanceHistory element not found, skipping update');
        return;
    }
    
    apiCall('/api/attendance/history')
        .then(response => {
            console.log('Response status:', response.status);  // Debug log
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Received data:', data);  // Debug log
            if (data.error) {
                showAlert(data.error, 'error');
                return;
            }
            attendanceData = data;
            currentPage = 1;
            renderAttendancePage(currentPage);
            renderAttendancePagination();
        })
        .catch(error => {
            console.error('Error fetching attendance history:', error);
            showAlert('Không thể tải lịch sử chấm công. Vui lòng thử lại sau.', 'error');
        });
}

// Function to render attendance page
function renderAttendancePage(page) {
    const tbody = document.getElementById('attendanceHistory');
    if (!tbody) {
        console.log('attendanceHistory element not found, skipping render');
        return;
    }
    
    tbody.innerHTML = '';
    
    if (!attendanceData || attendanceData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="text-center">Không có dữ liệu chấm công</td></tr>';
        return;
    }

    const start = (page - 1) * rowsPerPage;
    const end = start + rowsPerPage;
    const pageData = attendanceData.slice(start, end);
    
    pageData.forEach(record => {
        const row = document.createElement('tr');
        let statusText = record.approved ? 'Đã phê duyệt' : 'Chờ phê duyệt';
        
        // Xử lý hiển thị loại ngày
        let holidayTypeText = '-';
        if (record.holiday_type) {
            switch(record.holiday_type) {
                case 'normal':
                    holidayTypeText = 'Ngày thường';
                    break;
                case 'weekend':
                    holidayTypeText = 'Cuối tuần';
                    break;
                case 'vietnamese_holiday':
                    holidayTypeText = 'Lễ Việt Nam';
                    break;
                case 'japanese_holiday':
                    holidayTypeText = 'Lễ Nhật Bản';
                    break;
                default:
                    holidayTypeText = record.holiday_type;
            }
        }

        // Xác định class cho trạng thái
        let statusClass = record.approved ? 'status-approved' : 'status-pending';
        if (record.status === 'rejected') {
            statusText = 'Từ chối';
            statusClass = 'status-rejected';
        }
        
        row.innerHTML = `
            <td>${formatDate(record.date)}</td>
            <td>${record.check_in ? record.check_in.substring(0,5) : '--:--'}</td>
            <td>${record.check_out ? record.check_out.substring(0,5) : '--:--'}</td>
            <td>${record.break_time || '-'}</td>
            <td>${record.total_work_hours || '-'}</td>
            <td>${record.work_hours_display || '-'}</td>
            <td>${record.overtime_before_22 || '0:00'}</td>
            <td>${record.overtime_after_22 || '0:00'}</td>
            <td>${holidayTypeText}</td>
            <td><span class="${statusClass}">${statusText}</span></td>
            <td>
                ${!record.approved ? `
                    <button class="btn btn-warning btn-sm" onclick="handleEditAttendance(${record.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="deleteAttendance(${record.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                ` : '-'}
            </td>
            <td>${record.note || '-'}</td>
        `;
        tbody.appendChild(row);
    });
}

// Function to render attendance pagination
function renderAttendancePagination() {
    const totalPages = Math.ceil(attendanceData.length / rowsPerPage);
    const pagination = document.getElementById('attendancePagination');
    if (!pagination) {
        console.log('attendancePagination element not found, skipping pagination render');
        return;
    }
    
    pagination.innerHTML = '';
    
    if (totalPages <= 1) return;
    
    for (let i = 1; i <= totalPages; i++) {
        const li = document.createElement('li');
        li.className = 'page-item' + (i === currentPage ? ' active' : '');
        const a = document.createElement('a');
        a.className = 'page-link';
        a.href = '#';
        a.textContent = i;
        a.addEventListener('click', function(e) {
            e.preventDefault();
            currentPage = i;
            renderAttendancePage(currentPage);
            renderAttendancePagination();
        });
        li.appendChild(a);
        pagination.appendChild(li);
    }
}

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

            if (dateInput) dateInput.value = data.date;
            if (checkInTimeInput) checkInTimeInput.value = data.check_in ? data.check_in.split(' ')[1].substring(0, 5) : '';
            if (checkOutTimeInput) checkOutTimeInput.value = data.check_out ? data.check_out.split(' ')[1].substring(0, 5) : '';
            if (breakTimeInput) breakTimeInput.value = formatTimeForInput(data.break_time);
            if (dayTypeSelect) dayTypeSelect.value = data.holiday_type || '';
            if (noteInput) noteInput.value = data.note || '';
            if (editIdInput) editIdInput.value = id;
            
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
    const hh = Math.floor(hours);
    const mm = Math.round((hours - hh) * 60);
    return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
}

// Make functions globally available
window.handleEditAttendance = handleEditAttendance;
window.deleteAttendance = deleteAttendance;

// Function to handle form submission
function handleAttendanceSubmit() {
    const dateInput = document.getElementById('attendanceDate');
    const checkInTimeInput = document.getElementById('checkInTime');
    const checkOutTimeInput = document.getElementById('checkOutTime');
    const noteInput = document.getElementById('attendanceNote');
    const breakTimeInput = document.getElementById('breakTime');
    const dayTypeSelect = document.getElementById('dayType');
    const editIdInput = document.getElementById('editAttendanceId');

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

    // Validate inputs
    if (!date || !checkIn || !checkOut) {
        showAlert('Vui lòng nhập đầy đủ ngày và giờ vào/ra', 'warning');
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

    // Prepare data
    const data = {
        date: date,
        check_in: checkIn,
        check_out: checkOut,
        note: note,
        break_time: breakTime,
        is_holiday: isHoliday,
        holiday_type: dayType
    };

    console.log('Submitting data:', data);  // Debug log

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
    
    // Format date as YYYY-MM-DD
    const formattedDate = today.toISOString().split('T')[0];
    // Format time as HH:mm
    const formattedTime = today.toTimeString().slice(0, 5);
    
    if (dateInput) dateInput.value = formattedDate;
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