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

// Current time
function getCurrentTime() {
    const now = new Date();
    return now.toISOString().slice(0, 16);
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    }).replace(/\//g, '-');
}

// Show loading spinner
function showSpinner() {
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    attendanceList.appendChild(spinner);
}

// Hide loading spinner
function hideSpinner() {
    const spinner = document.querySelector('.spinner');
    if (spinner) {
        spinner.remove();
    }
}

// Show alert message
function showAlert(message, type = 'success') {
    showToast(message, type);
}

// Show toast message
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.minWidth = '180px';
    toast.style.marginBottom = '12px';
    toast.style.background = type === 'success' ? '#e8fbe8' : '#ffeaea';
    toast.style.color = type === 'success' ? '#256d1b' : '#d32f2f';
    toast.style.border = type === 'success' ? '1.5px solid #7ac142' : '1px solid #ffcdd2';
    toast.style.borderRadius = '6px';
    toast.style.padding = '12px 20px';
    toast.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
    toast.style.fontSize = '15px';
    toast.style.fontWeight = '500';
    toast.style.textAlign = 'center';
    toast.style.opacity = '0.98';
    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 400);
    }, 2000);
}

// Load attendance history
async function loadAttendanceHistory() {
    showSpinner();
    try {
        const response = await fetch('/api/attendance/history');
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

// Handle role switching
async function switchRole(role) {
    try {
        const response = await fetch('/switch-role', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role })
        });
        if (response.ok) {
            // Thay vì reload trang, cập nhật giao diện động
            updateUIForRole(role);
            showAlert('Đã chuyển vai trò thành công', 'success');
        } else {
            showAlert('Không thể chuyển vai trò', 'danger');
        }
    } catch (e) {
        showAlert('Lỗi khi chuyển vai trò', 'danger');
    }
}

// Function to update UI based on role
function updateUIForRole(role) {
    const attendanceFormSection = document.getElementById('attendanceFormSection');
    const attendanceHistorySection = document.getElementById('attendanceHistorySection');
    const approvalSection = document.getElementById('approvalSection');
    const allAttendanceHistorySection = document.getElementById('allAttendanceHistorySection');
    const departmentFilterContainer = document.getElementById('departmentFilterContainer');
    
    // Ẩn tất cả các section trước
    if (attendanceFormSection) attendanceFormSection.style.display = 'none';
    if (attendanceHistorySection) attendanceHistorySection.style.display = 'none';
    if (approvalSection) approvalSection.style.display = 'none';
    if (allAttendanceHistorySection) allAttendanceHistorySection.style.display = 'none';
    
    if (role === 'EMPLOYEE') {
        // Hiển thị form chấm công và lịch sử cho nhân viên
        if (attendanceFormSection) attendanceFormSection.style.display = 'block';
        if (attendanceHistorySection) attendanceHistorySection.style.display = 'block';
        // Load lại dữ liệu chấm công
        updateAttendanceHistory();
    } else if (['TEAM_LEADER', 'MANAGER', 'ADMIN'].includes(role)) {
        // Hiển thị phần phê duyệt cho quản lý
        if (approvalSection) approvalSection.style.display = 'block';
        
        // Hiển thị filter phòng ban cho MANAGER và ADMIN
        if (departmentFilterContainer) {
            if (['MANAGER', 'ADMIN'].includes(role)) {
                departmentFilterContainer.style.display = 'block';
            } else {
                departmentFilterContainer.style.display = 'none';
            }
        }
        
        // Load dữ liệu phê duyệt
        loadApprovalAttendance();
    }
    
    // Cập nhật tiêu đề trang
    const pageTitle = document.querySelector('.page-title');
    if (pageTitle) {
        if (role === 'EMPLOYEE') {
            pageTitle.textContent = 'Bảng điều khiển';
        } else {
            pageTitle.textContent = 'Quản lý chấm công';
        }
    }
    
    // Cập nhật active state cho menu
    updateMenuActiveState(role);
}

// Function to update menu active state
function updateMenuActiveState(role) {
    // Cập nhật active state cho các menu item
    const menuItems = document.querySelectorAll('.nav-link');
    menuItems.forEach(item => {
        item.classList.remove('active');
    });
    
    // Set active cho menu phù hợp
    if (role === 'EMPLOYEE') {
        const homeMenu = document.querySelector('.nav-link');
        if (homeMenu) homeMenu.classList.add('active');
    } else {
        // Tìm menu phê duyệt hoặc tạo mới
        const approvalMenu = document.querySelector('.nav-link[data-role="approval"]');
        if (approvalMenu) {
            approvalMenu.classList.add('active');
        }
    }
}

// Function to load approval attendance data
function loadApprovalAttendance() {
    const approvalBody = document.getElementById('approvalAttendanceBody');
    if (!approvalBody) return;
    
    // Hiển thị loading
    approvalBody.innerHTML = '<tr><td colspan="13" class="text-center">Đang tải dữ liệu...</td></tr>';
    
    // Lấy các filter
    const searchName = document.getElementById('approvalSearchName')?.value || '';
    const department = document.getElementById('approvalDepartment')?.value || '';
    const dateFrom = document.getElementById('approvalDateFrom')?.value || '';
    const dateTo = document.getElementById('approvalDateTo')?.value || '';
    
    // Tạo URL với các tham số filter
    let url = '/api/attendance/pending';
    const params = new URLSearchParams();
    if (searchName) params.append('search', searchName);
    if (department) params.append('department', department);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    
    if (params.toString()) {
        url += '?' + params.toString();
    }
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                approvalBody.innerHTML = '<tr><td colspan="13" class="text-center text-danger">Lỗi tải dữ liệu</td></tr>';
                return;
            }
            
            approvalBody.innerHTML = '';
            if (!data.data || data.data.length === 0) {
                approvalBody.innerHTML = '<tr><td colspan="13" class="text-center">Không có bản ghi chấm công chờ phê duyệt</td></tr>';
                return;
            }
            
            data.data.forEach(record => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${record.date}</td>
                    <td>${record.check_in ? record.check_in.substring(0,5) : '--:--'}</td>
                    <td>${record.check_out ? record.check_out.substring(0,5) : '--:--'}</td>
                    <td>${record.break_time || '-'}</td>
                    <td>${record.total_work_hours || '-'}</td>
                    <td>${record.work_hours_display || '-'}</td>
                    <td>${record.overtime_before_22 || '0:00'}</td>
                    <td>${record.overtime_after_22 || '0:00'}</td>
                    <td>${record.holiday_type || '-'}</td>
                    <td>${record.user_name || '-'}</td>
                    <td>${record.department || '-'}</td>
                    <td>${record.note || '-'}</td>
                    <td>
                        <button class="btn btn-success btn-sm" onclick="approveAttendance(${record.id}, 'approve')">Duyệt</button>
                        <button class="btn btn-danger btn-sm" onclick="approveAttendance(${record.id}, 'reject')">Từ chối</button>
                    </td>
                `;
                approvalBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error loading approval data:', error);
            approvalBody.innerHTML = '<tr><td colspan="13" class="text-center text-danger">Lỗi tải dữ liệu</td></tr>';
        });
}

// Add event listeners for approval filters
function setupApprovalEventListeners() {
    // Filter button
    const btnApprovalFilter = document.getElementById('btnApprovalFilter');
    if (btnApprovalFilter) {
        btnApprovalFilter.addEventListener('click', function() {
            loadApprovalAttendance();
        });
    }
    
    // Reset button
    const btnApprovalReset = document.getElementById('btnApprovalReset');
    if (btnApprovalReset) {
        btnApprovalReset.addEventListener('click', function() {
            // Reset all filter inputs
            const searchInput = document.getElementById('approvalSearchName');
            const departmentSelect = document.getElementById('approvalDepartment');
            const dateFromInput = document.getElementById('approvalDateFrom');
            const dateToInput = document.getElementById('approvalDateTo');
            
            if (searchInput) searchInput.value = '';
            if (departmentSelect) departmentSelect.value = '';
            if (dateFromInput) dateFromInput.value = '';
            if (dateToInput) dateToInput.value = '';
            
            // Reload data
            loadApprovalAttendance();
        });
    }
}

// Function to approve/reject attendance
function approveAttendance(attendanceId, action) {
    let reason = '';
    if (action === 'reject') {
        reason = prompt('Lý do từ chối:');
        if (reason === null) return; // Người dùng hủy
    }
    
    fetch(`/api/attendance/${attendanceId}/approve`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: action,
            reason: reason
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert(data.error, 'danger');
        } else {
            showAlert(data.message, 'success');
            // Reload dữ liệu phê duyệt
            loadApprovalAttendance();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Đã xảy ra lỗi khi phê duyệt', 'danger');
    });
}

// Handle form submission
timeAttendanceForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(timeAttendanceForm);
    const action = formData.get('checkIn') ? 'check_in' : 'check_out';
    
    try {
        const response = await fetch('/api/attendance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Lấy vai trò hiện tại
    const roleSelect = document.getElementById('role-select');
    const currentRole = roleSelect ? roleSelect.value : 'EMPLOYEE';
    
    // Cập nhật giao diện theo vai trò hiện tại
    updateUIForRole(currentRole);
    
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
    
    // Set up role switcher
    if (roleSelect) {
        roleSelect.addEventListener('change', (e) => switchRole(e.target.value));
    }

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

    fetch('/api/attendance', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
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
window.switchRole = switchRole;
window.approveAttendance = approveAttendance;

// Function to update attendance history
function updateAttendanceHistory() {
    console.log('Fetching attendance history...');  // Debug log
    
    // Kiểm tra xem element attendanceHistory có tồn tại không
    const attendanceHistoryElement = document.getElementById('attendanceHistory');
    if (!attendanceHistoryElement) {
        console.log('attendanceHistory element not found, skipping update');
        return;
    }
    
    fetch('/api/attendance/history')
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
    fetch(`/api/attendance/${id}`)
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
        fetch(`/api/attendance/${id}`, {
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
        fetch(`/api/attendance/${editIdInput.value}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
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
    fetch('/api/attendance', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
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