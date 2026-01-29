// Global Helper Functions - accessible from all IIFEs
window.parseHHMM = function (hhmm) {
    if (!hhmm) return null;
    const [h, m] = hhmm.split(':').map(x => parseInt(x || '0', 10));
    if (isNaN(h) || isNaN(m)) return null;
    return { h, m };
};

window.getShiftRangeByCode = function (code) {
    // Đồng bộ với backend: 1: 07:30-16:30, 2: 09:00-18:00, 3: 11:00-20:00, 4: 08:00-17:00
    switch (code) {
        case '1': return { start: '07:30', end: '16:30' };
        case '2': return { start: '09:00', end: '18:00' };
        case '3': return { start: '11:00', end: '20:00' };
        case '4': return { start: '08:00', end: '17:00' };
        default: return null;
    }
};

window.getBreakHours = function () {
    const el = document.getElementById('breakTime');
    const v = el ? el.value : '01:00';
    const t = window.parseHHMM(v) || { h: 1, m: 0 };
    return (t.h || 0) + (t.m || 0) / 60;
};

window.toDate = function (dateStr, hhmm) {
    const t = window.parseHHMM(hhmm);
    if (!t) return null;
    const base = dateStr && dateStr.includes('-') ? new Date(`${dateStr}T00:00:00`) : new Date();
    const d = new Date(base);
    d.setHours(t.h, t.m, 0, 0);
    return d;
};

window.hoursBetween = function (a, b) {
    if (!a || !b) return 0;
    return (b - a) / 3600000;
};

// DOM Elements
const timeAttendanceForm = document.getElementById('timeAttendanceForm');
const roleSelect = document.getElementById('role-select');
const currentRole = document.getElementById('current-role');

// Global variables are declared in the HTML template to avoid conflicts
let lastRegularShiftCode = '';

function enforceFreeShiftAvailability() {
    const dayTypeSelect = document.getElementById('dayType');
    const shiftSelect = document.getElementById('shiftSelect');
    if (!dayTypeSelect || !shiftSelect) return;
    const freeShiftOption = shiftSelect.querySelector('option[value="5"]');
    if (!freeShiftOption) return;

    const isNormalDay = dayTypeSelect.value === 'normal';
    freeShiftOption.disabled = !!isNormalDay;
    if (isNormalDay) {
        freeShiftOption.title = 'Ca tự do chỉ áp dụng cho ngày nghỉ';
        if (shiftSelect.value === '5') {
            shiftSelect.value = lastRegularShiftCode || '';
            try {
                shiftSelect.dispatchEvent(new Event('change', { bubbles: true }));
            } catch (e) { }
        }
    } else {
        freeShiftOption.removeAttribute('title');
    }
}
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

// Enhanced API call function with better error handling + request cancellation + cache-buster
async function apiCall(url, options = {}) {
    // Abort previous in-flight request for the same key
    if (!window.__inFlightControllers) window.__inFlightControllers = {};
    const requestKey = options.key || (url.split('?')[0] || url);
    if (window.__inFlightControllers[requestKey]) {
        try { window.__inFlightControllers[requestKey].abort(); } catch (e) { }
    }
    const controller = new AbortController();
    window.__inFlightControllers[requestKey] = controller;

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

    // Add cache-buster to ensure fresh data when switching roles/filters
    const cacheBuster = `_t=${Date.now()}`;
    const urlWithBuster = url.includes('?') ? `${url}&${cacheBuster}` : `${url}?${cacheBuster}`;

    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        },
        signal: controller.signal
    };

    try {
        const response = await fetch(urlWithBuster, finalOptions);

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
        if (error && error.name === 'AbortError') {
            // Silently ignore aborted requests when switching roles/filters rapidly
            return new Response(null, { status: 499, statusText: 'Client Closed Request' });
        }
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

// Enhanced date formatting with consistent DD/MM/YYYY format
function formatDate(dateString) {
    // Nếu là dạng DD/MM/YYYY thì parse thủ công
    if (typeof dateString === 'string' && dateString.includes('/')) {
        const [d, m, y] = dateString.split('/');
        return `${d.padStart(2, '0')}/${m.padStart(2, '0')}/${y}`;
    }
    // Nếu là dạng ISO hoặc object Date
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
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

// Toast notification system
function showToast(message, type = 'success') {
    // Kiểm tra xem SweetAlert2 có sẵn không
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            title: type === 'success' ? 'Thành công!' : type === 'error' ? 'Lỗi!' : type === 'warning' ? 'Cảnh báo!' : 'Thông báo!',
            text: message,
            icon: type,
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true
        });
    } else {
        // Fallback nếu không có SweetAlert2
        // console.log(`${type.toUpperCase()}: ${message}`);
        alert(message);
    }
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
        btnApprovalFilter.addEventListener('click', function () {
            // Function moved to HTML template
        });
    }

    // Reset button - moved to HTML template to avoid conflicts
    const btnApprovalReset = document.getElementById('btnApprovalReset');
    if (btnApprovalReset) {
        btnApprovalReset.addEventListener('click', function () {
            // Function moved to HTML template
        });
    }

    // Bulk approve button
    const btnBulkApprove = document.getElementById('btnBulkApprove');
    if (btnBulkApprove) {
        btnBulkApprove.addEventListener('click', handleBulkApproval);
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
                resetFormToDefaults();
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
let sessionRefreshIntervalId = null;

function setupSessionRefresh() {
    // Clear existing interval if any
    if (sessionRefreshIntervalId) {
        clearInterval(sessionRefreshIntervalId);
    }

    sessionRefreshIntervalId = setInterval(async () => {
        try {
            await apiCall('/api/attendance/history');
        } catch (error) {
            // console.log('Session refresh failed:', error);
        }
    }, 25 * 60 * 1000); // 25 minutes
}

// Cleanup interval on page unload
window.addEventListener('beforeunload', function() {
    if (sessionRefreshIntervalId) {
        clearInterval(sessionRefreshIntervalId);
        sessionRefreshIntervalId = null;
    }
});

// Initialize - REMOVED (already handled in HTML template)
// The DOMContentLoaded event listener has been moved to the HTML template
// to avoid conflicts and ensure proper initialization order

// Function to auto-check next day checkout checkbox
// Function to auto-check next day checkout - REMOVED (Replaced by inline date selection)
function autoCheckNextDayCheckout() {
    // Legacy function removed
}

// Function to setup form event listeners
function setupFormEventListeners() {
    // Save attendance button
    const saveAttendanceBtn = document.getElementById('saveAttendanceBtn');
    if (saveAttendanceBtn) {
        // Tránh double-submit: disable button trong khi đang gửi
        let isSubmitting = false;
        saveAttendanceBtn.addEventListener('click', async function (e) {
            if (isSubmitting) return;
            isSubmitting = true;
            saveAttendanceBtn.disabled = true;
            try {
                await handleAttendanceSubmit(e);
            } finally {
                // Re-enable sau khi API phản hồi xong (thành công hoặc lỗi)
                isSubmitting = false;
                saveAttendanceBtn.disabled = false;
            }
        });
    }

    // Cancel edit button
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', resetForm);
    }

    // Day type change - chỉ xử lý khi ca đã được chọn trước
    const dayTypeSelect = document.getElementById('dayType');
    if (dayTypeSelect) {
        dayTypeSelect.addEventListener('change', function () {
            const shiftSelect = document.getElementById('shiftSelect');
            if (shiftSelect) {
                // Luôn đồng bộ ca ↔ loại ngày
                if (['weekend', 'vietnamese_holiday', 'japanese_holiday'].includes(this.value)) {
                    // Ngày nghỉ: tự động chọn ca 5 và không cho sửa
                    shiftSelect.value = '5';
                    shiftSelect.disabled = true;
                    shiftSelect.style.opacity = '0.6';

                    // Ngày nghỉ: ẩn/disable các field đối ứng trong ca (Cuối tuần & Lễ VN)
                    if (this.value === 'weekend' || this.value === 'vietnamese_holiday') {
                        const compTimeRegularInput = document.getElementById('compTimeRegular');
                        const compTimeOvertimeInput = document.getElementById('compTimeOvertime');
                        const compTimeRegularLabel = document.querySelector('label[for="compTimeRegular"]');
                        const compTimeOvertimeLabel = document.querySelector('label[for="compTimeOvertime"]');

                        if (compTimeRegularInput) {
                            compTimeRegularInput.disabled = true;
                            compTimeRegularInput.value = '00:00';
                            compTimeRegularInput.style.opacity = '0.5';
                        }
                        if (compTimeOvertimeInput) {
                            compTimeOvertimeInput.disabled = true;
                            compTimeOvertimeInput.value = '00:00';
                            compTimeOvertimeInput.style.opacity = '0.5';
                        }
                        if (compTimeRegularLabel) compTimeRegularLabel.style.opacity = '0.5';
                        if (compTimeOvertimeLabel) compTimeOvertimeLabel.style.opacity = '0.5';
                    } else {
                        // Ngày lễ khác: khôi phục các field đối ứng trong ca
                        const compTimeRegularInput = document.getElementById('compTimeRegular');
                        const compTimeOvertimeInput = document.getElementById('compTimeOvertime');
                        const compTimeRegularLabel = document.querySelector('label[for="compTimeRegular"]');
                        const compTimeOvertimeLabel = document.querySelector('label[for="compTimeOvertime"]');

                        if (compTimeRegularInput) {
                            compTimeRegularInput.disabled = false;
                            compTimeRegularInput.style.opacity = '1';
                        }
                        if (compTimeOvertimeInput) {
                            compTimeOvertimeInput.disabled = false;
                            compTimeOvertimeInput.style.opacity = '1';
                        }
                        if (compTimeRegularLabel) compTimeRegularLabel.style.opacity = '1';
                        if (compTimeOvertimeLabel) compTimeOvertimeLabel.style.opacity = '1';
                    }
                } else if (this.value === 'normal') {
                    // Ngày thường: cho phép chọn ca tự do, khôi phục ca thường trước đó nếu đang ở '5'
                    shiftSelect.disabled = false;
                    shiftSelect.style.opacity = '1';
                    if (shiftSelect.value === '5') {
                        shiftSelect.value = lastRegularShiftCode || '';
                        // Đồng bộ UI giờ vào/ra theo ca khôi phục
                        try { shiftSelect.dispatchEvent(new Event('change', { bubbles: true })); } catch (e) { }
                    }
                    // IMPORTANT: Đừng tự động xóa ca đang có khi chuyển/đồng bộ về "ngày thường".
                    // Chỉ khôi phục lastRegularShiftCode nếu hiện tại chưa có ca.
                    if (!shiftSelect.value && lastRegularShiftCode) {
                        shiftSelect.value = lastRegularShiftCode;
                        try { shiftSelect.dispatchEvent(new Event('change', { bubbles: true })); } catch (e) { }
                    }

                    // Khôi phục các field đối ứng trong ca
                    const compTimeRegularInput = document.getElementById('compTimeRegular');
                    const compTimeOvertimeInput = document.getElementById('compTimeOvertime');
                    const compTimeRegularLabel = document.querySelector('label[for="compTimeRegular"]');
                    const compTimeOvertimeLabel = document.querySelector('label[for="compTimeOvertime"]');

                    if (compTimeRegularInput) {
                        compTimeRegularInput.disabled = false;
                        compTimeRegularInput.style.opacity = '1';
                    }
                    if (compTimeOvertimeInput) {
                        compTimeOvertimeInput.disabled = false;
                        compTimeOvertimeInput.style.opacity = '1';
                    }
                    if (compTimeRegularLabel) compTimeRegularLabel.style.opacity = '1';
                    if (compTimeOvertimeLabel) compTimeOvertimeLabel.style.opacity = '1';
                }
            }

            enforceFreeShiftAvailability();

            // Cập nhật UI đối ứng sau khi thay đổi loại ngày
            setTimeout(() => {
                if (typeof window.updateCompTimeUI === 'function') {
                    window.updateCompTimeUI();
                }
            }, 100);
        });

        // Kiểm tra ban đầu nếu đã chọn ngày nghỉ
        if (['weekend', 'vietnamese_holiday', 'japanese_holiday'].includes(dayTypeSelect.value)) {
            const shiftSelect = document.getElementById('shiftSelect');
            if (shiftSelect) {
                shiftSelect.value = '5';
                shiftSelect.disabled = true;
                shiftSelect.style.opacity = '0.6';
            }

            // Cuối tuần: disable các field đối ứng trong ca
            if (dayTypeSelect.value === 'weekend') {
                const compTimeRegularInput = document.getElementById('compTimeRegular');
                const compTimeOvertimeInput = document.getElementById('compTimeOvertime');
                const compTimeRegularLabel = document.querySelector('label[for="compTimeRegular"]');
                const compTimeOvertimeLabel = document.querySelector('label[for="compTimeOvertime"]');

                if (compTimeRegularInput) {
                    compTimeRegularInput.disabled = true;
                    compTimeRegularInput.value = '00:00';
                    compTimeRegularInput.style.opacity = '0.5';
                }
                if (compTimeOvertimeInput) {
                    compTimeOvertimeInput.disabled = true;
                    compTimeOvertimeInput.value = '00:00';
                    compTimeOvertimeInput.style.opacity = '0.5';
                }
                if (compTimeRegularLabel) compTimeRegularLabel.style.opacity = '0.5';
                if (compTimeOvertimeLabel) compTimeOvertimeLabel.style.opacity = '0.5';
            }
        }

        enforceFreeShiftAvailability();
    }

    // Shift select change
    const shiftSelect = document.getElementById('shiftSelect');
    if (shiftSelect) {
        shiftSelect.addEventListener('change', function () {
            const shiftValue = this.value;
            // Lưu lại ca thường cuối cùng (khác ca 5)
            if (shiftValue && shiftValue !== '5') {
                lastRegularShiftCode = shiftValue;
            }

            // Logic mới: Tự động thay đổi loại ngày dựa trên ca được chọn
            const dayTypeSelect = document.getElementById('dayType');
            if (dayTypeSelect) {
                if (['1', '2', '3', '4'].includes(shiftValue)) {
                    // Ca 1-4: chỉ hiển thị "ngày thường"
                    dayTypeSelect.value = 'normal';
                    // Disable các option khác
                    dayTypeSelect.querySelectorAll('option').forEach(option => {
                        if (option.value !== 'normal' && option.value !== '') {
                            option.disabled = true;
                        } else {
                            option.disabled = false;
                        }
                    });
                } else if (shiftValue === '5') {
                    // Ca đặc biệt: chỉ hiển thị các loại ngày nghỉ
                    dayTypeSelect.value = 'weekend'; // Mặc định chọn cuối tuần
                    // Enable các option ngày nghỉ, disable ngày thường
                    dayTypeSelect.querySelectorAll('option').forEach(option => {
                        if (option.value === 'normal') {
                            option.disabled = true;
                        } else {
                            option.disabled = false;
                        }
                    });

                    // Tự động disable các field đối ứng trong ca khi chọn ca 5
                    const compTimeRegularInput = document.getElementById('compTimeRegular');
                    const compTimeOvertimeInput = document.getElementById('compTimeOvertime');
                    const compTimeRegularLabel = document.querySelector('label[for="compTimeRegular"]');
                    const compTimeOvertimeLabel = document.querySelector('label[for="compTimeOvertime"]');

                    if (compTimeRegularInput) {
                        compTimeRegularInput.disabled = true;
                        compTimeRegularInput.value = '00:00';
                        compTimeRegularInput.style.opacity = '0.5';
                    }
                    if (compTimeOvertimeInput) {
                        compTimeOvertimeInput.disabled = true;
                        compTimeOvertimeInput.value = '00:00';
                        compTimeOvertimeInput.style.opacity = '0.5';
                    }
                    if (compTimeRegularLabel) compTimeRegularLabel.style.opacity = '0.5';
                    if (compTimeOvertimeLabel) compTimeOvertimeLabel.style.opacity = '0.5';
                } else {
                    // Không chọn ca: enable tất cả
                    dayTypeSelect.querySelectorAll('option').forEach(option => {
                        option.disabled = false;
                    });

                    // Khôi phục các field đối ứng trong ca
                    const compTimeRegularInput = document.getElementById('compTimeRegular');
                    const compTimeOvertimeInput = document.getElementById('compTimeOvertime');
                    const compTimeRegularLabel = document.querySelector('label[for="compTimeRegular"]');
                    const compTimeOvertimeLabel = document.querySelector('label[for="compTimeOvertime"]');

                    if (compTimeRegularInput) {
                        compTimeRegularInput.disabled = false;
                        compTimeRegularInput.style.opacity = '1';
                    }
                    if (compTimeOvertimeInput) {
                        compTimeOvertimeInput.disabled = false;
                        compTimeOvertimeInput.style.opacity = '1';
                    }
                    if (compTimeRegularLabel) compTimeRegularLabel.style.opacity = '1';
                    if (compTimeOvertimeLabel) compTimeRegularLabel.style.opacity = '1';
                }
            }

            if (shiftValue === '1') {
                // Ca 1: 7:30 - 16:30
                document.getElementById('checkInTime').value = '07:30';
                document.getElementById('checkOutTime').value = '16:30';
            }
            else if (shiftValue === '2') {
                // Ca 2: 9:00 - 18:00
                document.getElementById('checkInTime').value = '09:00';
                document.getElementById('checkOutTime').value = '18:00';
            }
            else if (shiftValue === '3') {
                // Ca 3: 11:00 - 20:00
                document.getElementById('checkInTime').value = '11:00';
                document.getElementById('checkOutTime').value = '20:00';
            }
            else if (shiftValue === '4') {
                // Ca 4: 8:00 - 17:00
                document.getElementById('checkInTime').value = '08:00';
                document.getElementById('checkOutTime').value = '17:00';
            }
            else if (shiftValue === '5') {
                // Ca 5: Ca đặc biệt - tự do giờ giấc
                // Không tự động set hoặc xóa giờ vào/ra; giữ nguyên giá trị người dùng đã nhập
            }

            enforceFreeShiftAvailability();

            // Tự động check checkbox tăng ca qua ngày mới nếu cần
            autoCheckNextDayCheckout();

            // Đảm bảo "Loại đối ứng" luôn mặc định là "-- chọn loại đối ứng --"
            const compTimeTypeSelect = document.getElementById('compTimeType');
            if (compTimeTypeSelect) {
                compTimeTypeSelect.value = '';
            }

            // Cập nhật UI đối ứng sau khi thay đổi ca
            setTimeout(() => {
                if (typeof window.updateCompTimeUI === 'function') {
                    window.updateCompTimeUI();
                }
            }, 100);
        });

        // Khởi tạo trạng thái ban đầu cho loại ngày
        if (shiftSelect.value) {
            // Trigger change event để áp dụng logic ban đầu
            shiftSelect.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    // Check in/out time change - Auto-sync checkout date (Simple Sync Mode)
    const checkInTimeInput = document.getElementById('checkInTime');
    const checkOutTimeInput = document.getElementById('checkOutTime');
    const entryDateInput = document.getElementById('attendanceDate'); // Ngày vào
    const checkoutDateInput = document.getElementById('checkoutDate'); // Ngày ra

    function updateCheckoutDateAuto() {
        // Logic mới: MẶC ĐỊNH LÀ CÙNG NGÀY.
        // Hủy bỏ việc tự động cộng ngày khi giờ ra < giờ vào.
        // Chỉ khi thay đổi ngày vào -> ngày ra tự động đổi theo cho khớp.
        // Nếu qua đêm -> người dùng tự chọn lại.

        if (!entryDateInput || !checkoutDateInput) return;

        const entryDateVal = entryDateInput.value;
        if (entryDateVal) {
            // Chỉ sync đơn giản: Ngày vào sao thì ngày ra vậy
            if (checkoutDateInput._flatpickr) {
                checkoutDateInput._flatpickr.setDate(entryDateVal, true);
            } else {
                checkoutDateInput.value = entryDateVal;
            }
        }
    }

    // Chỉ listen vào thay đổi Ngày Vào.
    // Không listen vào giờ ra/giờ vào nữa vì không tự động +1 ngày theo yêu cầu.
    if (entryDateInput) {
        entryDateInput.addEventListener('change', function () {
            updateCheckoutDateAuto();
        });
    }

    // ============================================================================
    // PHÁT HIỆN CA QUA ĐÊM - Popup Warning
    // ============================================================================
    // Thêm event listener cho giờ ra để phát hiện ca qua đêm
    if (checkOutTimeInput && checkInTimeInput && entryDateInput && checkoutDateInput) {
        checkOutTimeInput.addEventListener('change', async function () {
            const checkInTime = checkInTimeInput.value;
            const checkOutTime = this.value;

            // Nếu chưa nhập đủ thông tin thì bỏ qua
            if (!checkInTime || !checkOutTime) return;

            // Lấy ngày vào và ngày ra
            const attendanceDate = entryDateInput.value; // YYYY-MM-DD
            let checkoutDate = null;

            // Lấy ngày ra từ flatpickr
            if (checkoutDateInput._flatpickr && checkoutDateInput._flatpickr.selectedDates.length > 0) {
                const selectedDate = checkoutDateInput._flatpickr.selectedDates[0];
                const year = selectedDate.getFullYear();
                const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
                const day = String(selectedDate.getDate()).padStart(2, '0');
                checkoutDate = `${year}-${month}-${day}`;
            } else if (checkoutDateInput.value) {
                // Fallback: parse từ value (DD/MM/YYYY)
                const val = checkoutDateInput.value;
                if (val.includes('/')) {
                    const [d, m, y] = val.split('/');
                    checkoutDate = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
                } else {
                    checkoutDate = val; // Đã là YYYY-MM-DD
                }
            }

            if (!attendanceDate || !checkoutDate) return;

            // Chỉ kiểm tra nếu CÙNG NGÀY
            if (attendanceDate === checkoutDate) {
                // So sánh giờ
                const [inHour, inMin] = checkInTime.split(':').map(Number);
                const [outHour, outMin] = checkOutTime.split(':').map(Number);
                const inMinutesTotal = inHour * 60 + inMin;
                const outMinutesTotal = outHour * 60 + outMin;

                // Nếu giờ ra < giờ vào → Ca qua đêm
                if (outMinutesTotal < inMinutesTotal) {
                    // Helper function để format ngày tiếp theo
                    const formatDateNextDay = (dateStr) => {
                        const date = new Date(dateStr + 'T00:00:00');
                        date.setDate(date.getDate() + 1);
                        const day = String(date.getDate()).padStart(2, '0');
                        const month = String(date.getMonth() + 1).padStart(2, '0');
                        const year = date.getFullYear();
                        return `${day}/${month}/${year}`;
                    };

                    // Hiển thị popup xác nhận
                    const result = await Swal.fire({
                        title: '⚠️ Phát hiện ca qua đêm',
                        html: `
                            <div style="text-align: left; padding: 10px;">
                                <p style="margin-bottom: 15px;">
                                    <strong>Giờ ra (${checkOutTime}) nhỏ hơn giờ vào (${checkInTime})</strong>
                                </p>
                                <p style="margin-bottom: 15px;">
                                    Bạn có đang chấm công cho <strong style="color: #e74c3c;">ca qua đêm</strong> không?
                                </p>
                                <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; border-radius: 4px; margin-top: 15px;">
                                    <p style="margin: 0; color: #856404; font-size: 14px;">
                                        <i class="fas fa-info-circle"></i>
                                        Nếu có, ngày giờ ra sẽ tự động là <strong>${formatDateNextDay(attendanceDate)} ${checkOutTime}</strong>
                                    </p>
                                </div>
                            </div>
                        `,
                        icon: 'question',
                        showCancelButton: true,
                        confirmButtonText: '<i class="fas fa-check me-1"></i> Có, ca qua đêm',
                        cancelButtonText: '<i class="fas fa-times me-1"></i> Không, giờ ra sai',
                        confirmButtonColor: '#3085d6',
                        cancelButtonColor: '#d33',
                        width: '500px',
                        customClass: {
                            confirmButton: 'btn btn-primary',
                            cancelButton: 'btn btn-secondary'
                        }
                    });

                    if (result.isConfirmed) {
                        // Tự động cộng 1 ngày vào checkout_date
                        const nextDay = new Date(attendanceDate + 'T00:00:00');
                        nextDay.setDate(nextDay.getDate() + 1);

                        if (checkoutDateInput._flatpickr) {
                            checkoutDateInput._flatpickr.setDate(nextDay, true);
                        } else {
                            // Fallback: set value trực tiếp (DD/MM/YYYY)
                            checkoutDateInput.value = formatDateNextDay(attendanceDate);
                        }

                        // Hiển thị thông báo thành công
                        const formattedNextDay = `${String(nextDay.getDate()).padStart(2, '0')}/${String(nextDay.getMonth() + 1).padStart(2, '0')}/${nextDay.getFullYear()}`;
                        showToast(`✅ Đã tự động set ngày ra: ${formattedNextDay}`, 'success');
                    } else {
                        // User chọn "Không" → Focus vào ô giờ ra để sửa
                        checkOutTimeInput.focus();
                        checkOutTimeInput.select();
                    }
                }
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
    // Gửi giờ nghỉ dạng HH:MM (không convert sang số thập phân)
    const breakTimeStr = document.getElementById('breakTime').value;
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
            break_time: breakTimeStr || '01:00',
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
window.addEventListener('DOMContentLoaded', function () {
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
        .then(response => {
            if (!response) return; // safety
            if (response.status === 499) {
                // Request was aborted (role switch or rapid actions) → ignore silently
                return Promise.reject({ silent: true });
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                showAlert(data.error, 'error');
                return;
            }

            // DEBUG: Log dữ liệu nhận từ server
            console.log('📥 Data received from server for edit:', data);

            // Prevent attendanceDate flatpickr onChange (async) from auto-detecting dayType / syncing checkoutDate during edit
            window.__suppressCheckoutDateSync = true;
            window.__suppressDayTypeDetect = true;

            // Fill form with attendance data
            const dateInput = document.getElementById('attendanceDate');
            const checkInTimeInput = document.getElementById('checkInTime');
            const checkOutTimeInput = document.getElementById('checkOutTime');
            const breakTimeInput = document.getElementById('breakTime');
            const compTimeRegularInput = document.getElementById('compTimeRegular');
            const compTimeOvertimeInput = document.getElementById('compTimeOvertime');
            const compTimeBefore22Input = document.getElementById('compTimeBefore22');
            const compTimeAfter22Input = document.getElementById('compTimeAfter22');
            const compTimeTypeSelect = document.getElementById('compTimeType');
            const dayTypeSelect = document.getElementById('dayType');
            const noteInput = document.getElementById('attendanceNote');
            const editIdInput = document.getElementById('editAttendanceId');
            const saveBtn = document.getElementById('saveAttendanceBtn');
            const cancelBtn = document.getElementById('cancelEditBtn');
            const shiftSelect = document.getElementById('shiftSelect');
            const signatureInput = document.getElementById('signature-input');

            if (dateInput) {
                // Convert DD/MM/YYYY to YYYY-MM-DD for flatpickr
                let isoDate = data.date;
                if (data.date && data.date.includes('/')) {
                    const [d, m, y] = data.date.split('/');
                    isoDate = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
                }

                if (dateInput._flatpickr) {
                    dateInput._flatpickr.setDate(isoDate, true);
                } else {
                    dateInput.value = isoDate;
                }
            }
            if (checkInTimeInput) checkInTimeInput.value = data.check_in || '';
            if (checkOutTimeInput) {
                checkOutTimeInput.value = data.check_out || '';

                // Initialize Checkout Date Input
                const checkoutDateInput = document.getElementById('checkoutDate');
                if (checkoutDateInput) {
                    // SỬ DỤNG checkout_date TỪ BACKEND (nếu có)
                    // Nếu backend không trả về checkout_date, fallback về data.date
                    let coDateStr = data.checkout_date || data.date; // DD/MM/YYYY

                    if (checkoutDateInput._flatpickr) {
                        // Convert DD/MM/YYYY to YYYY-MM-DD for flatpickr
                        const [dd, mm, yyyy] = coDateStr.split('/');
                        const isoDateStr = `${yyyy}-${mm.padStart(2, '0')}-${dd.padStart(2, '0')}`;
                        checkoutDateInput._flatpickr.setDate(isoDateStr, true);
                    } else {
                        checkoutDateInput.value = coDateStr;
                    }
                }
            }
            if (breakTimeInput) breakTimeInput.value = data.break_time || "01:00";
            if (compTimeRegularInput) compTimeRegularInput.value = data.comp_time_regular || "00:00";
            if (compTimeOvertimeInput) compTimeOvertimeInput.value = data.comp_time_overtime || "00:00";
            if (compTimeBefore22Input) compTimeBefore22Input.value = data.comp_time_ot_before_22 || "00:00";
            if (compTimeAfter22Input) compTimeAfter22Input.value = data.comp_time_ot_after_22 || "00:00";
            if (dayTypeSelect) dayTypeSelect.value = data.holiday_type || '';
            if (noteInput) noteInput.value = data.note || '';
            if (editIdInput) editIdInput.value = id;
            if (shiftSelect) shiftSelect.value = data.shift_code || '';

            // Cập nhật chữ ký từ dữ liệu cũ (auto signature feature)
            if (data.signature && signatureInput) {
                signatureInput.value = data.signature;
                // console.log('Auto signature: Loaded existing signature for editing');
            }

            // Show cancel button and update save button text
            if (cancelBtn) cancelBtn.style.display = 'inline-block';
            if (saveBtn) saveBtn.innerHTML = '<i class="fas fa-save me-2"></i>Cập nhật đăng ký';

            if (checkInTimeInput) checkInTimeInput.focus();

            // Release the suppression after the async determineDayType() has had time to finish
            setTimeout(() => {
                window.__suppressCheckoutDateSync = false;
                window.__suppressDayTypeDetect = false;
            }, 800);
            // Suy luận loại đối ứng từ dữ liệu đã load và đồng bộ UI
            setTimeout(() => {
                try {
                    const toHours = (v) => {
                        if (!v) return 0; if (typeof v === 'number') return v; if (String(v).includes(':')) { const [h, m] = String(v).split(':').map(Number); return (h || 0) + ((m || 0) / 60); } const f = parseFloat(v); return isNaN(f) ? 0 : f;
                    };
                    const r = toHours(compTimeRegularInput?.value || '0:00');
                    const b = toHours(compTimeBefore22Input?.value || '0:00');
                    const a = toHours(compTimeAfter22Input?.value || '0:00');
                    if (compTimeTypeSelect) {
                        if (r > 0 && b <= 0 && a <= 0) compTimeTypeSelect.value = 'regular';
                        else if (b > 0 && r <= 0 && a <= 0) compTimeTypeSelect.value = 'ot_before';
                        else if (a > 0 && r <= 0 && b <= 0) compTimeTypeSelect.value = 'ot_after';
                    }
                    if (typeof window.updateCompTypeOptions === 'function') window.updateCompTypeOptions();
                    if (typeof window.updateCompTimeLocks === 'function') window.updateCompTimeLocks();
                    if (typeof window.updateCompTimeUI === 'function') window.updateCompTimeUI();

                    // Đồng bộ trạng thái loại ngày dựa trên ca đã chọn
                    if (shiftSelect && dayTypeSelect) {
                        const shiftValue = shiftSelect.value;
                        if (['1', '2', '3', '4'].includes(shiftValue)) {
                            // Ca 1-4: chỉ hiển thị "ngày thường"
                            dayTypeSelect.value = 'normal';
                            // Disable các option khác
                            dayTypeSelect.querySelectorAll('option').forEach(option => {
                                if (option.value !== 'normal' && option.value !== '') {
                                    option.disabled = true;
                                } else {
                                    option.disabled = false;
                                }
                            });
                        } else if (shiftValue === '5') {
                            // Ca đặc biệt: chỉ hiển thị các loại ngày nghỉ
                            // Enable các option ngày nghỉ, disable ngày thường
                            dayTypeSelect.querySelectorAll('option').forEach(option => {
                                if (option.value === 'normal') {
                                    option.disabled = true;
                                } else {
                                    option.disabled = false;
                                }
                            });
                        }
                    }
                    enforceFreeShiftAvailability();
                } catch (e) { console.warn('sync comp type on edit failed', e); }
            }, 0);
        })
        .catch(error => {
            if (error && error.silent) return; // ignore aborted
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
window.formatDate = formatDate;
window.setupFormEventListeners = setupFormEventListeners;
window.autoCheckNextDayCheckout = autoCheckNextDayCheckout;

// Function to handle form submission
function handleAttendanceSubmit(e) {
    if (e) e.preventDefault();
    const dateInput = document.getElementById('attendanceDate');
    const checkInTimeInput = document.getElementById('checkInTime');
    const checkOutTimeInput = document.getElementById('checkOutTime');
    const noteInput = document.getElementById('attendanceNote');
    const breakTimeInput = document.getElementById('breakTime');
    const dayTypeSelect = document.getElementById('dayType');
    const compTimeRegularInput = document.getElementById('compTimeRegular');
    const compTimeOvertimeInput = document.getElementById('compTimeOvertime'); // deprecated (removed from UI)
    const compTimeBefore22Input = document.getElementById('compTimeBefore22');
    const compTimeAfter22Input = document.getElementById('compTimeAfter22');
    const compTimeTypeSelect = document.getElementById('compTimeType');
    const editIdInput = document.getElementById('editAttendanceId');
    const shiftSelect = document.getElementById('shiftSelect');

    // Tự động lấy chữ ký từ database - không cần user ký
    let signature = '';
    const signatureInput = document.getElementById('signature-input');
    if (signatureInput) signatureInput.value = signature;

    // Kiểm tra các element cần thiết có tồn tại không
    if (!dateInput || !checkInTimeInput || !checkOutTimeInput) {
        showAlert('Không thể tìm thấy form chấm công', 'error');
        return;
    }

    // Get values
    let date = dateInput.value;
    const checkIn = checkInTimeInput.value;
    let checkOut = checkOutTimeInput.value;

    // Normalize date early (flatpickr altInput can show DD/MM/YYYY but value should be YYYY-MM-DD)
    if (date && date.includes('/')) {
        const [d, m, y] = date.split('/');
        date = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
    }

    // Calculate checkout_date (Explicit)
    // IMPORTANT: Always prefer flatpickr selectedDates to avoid stale value issues when flatpickr is re-initialized.
    const checkoutDateEl = document.getElementById('checkoutDate');
    let checkoutDate = '';
    if (checkoutDateEl?._flatpickr && checkoutDateEl._flatpickr.selectedDates.length > 0) {
        const d = checkoutDateEl._flatpickr.selectedDates[0];
        checkoutDate = checkoutDateEl._flatpickr.formatDate(d, 'Y-m-d');
    } else {
        let raw = checkoutDateEl?.value ? String(checkoutDateEl.value).trim() : '';
        if (raw && raw.includes('/')) {
            const [d, m, y] = raw.split('/');
            checkoutDate = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
        } else {
            checkoutDate = raw; // already YYYY-MM-DD or empty
        }
    }
    if (!checkoutDate) checkoutDate = date;
    const note = noteInput ? noteInput.value : '';
    // Lễ Việt Nam không đi làm: break_time = 0:00, ngược lại = 1:00
    const breakTimeStr = breakTimeInput ? breakTimeInput.value :
        (dayType === 'vietnamese_holiday' && (!checkIn || !checkOut) ? '00:00' : '01:00');
    const compTimeRegularStr = compTimeRegularInput ? compTimeRegularInput.value : '00:00';
    const compTimeOvertimeStr = '00:00';
    const compTimeBefore22Str = compTimeBefore22Input ? compTimeBefore22Input.value : '00:00';
    const compTimeAfter22Str = compTimeAfter22Input ? compTimeAfter22Input.value : '00:00';
    const dayType = dayTypeSelect ? dayTypeSelect.value : '';
    const isHoliday = dayType !== 'normal';
    // Lấy lại shiftCode từ DOM mỗi lần submit
    const shiftSelectEl = document.getElementById('shiftSelect');
    const shiftCode = shiftSelectEl ? shiftSelectEl.value : '';

    // Validate inputs
    // Cho phép lễ Việt Nam không cần nhập giờ vào/ra (nhân viên được 8h mặc định)
    if (dayType !== 'vietnamese_holiday' && (!date || !checkIn || !checkOut)) {
        showAlert('Vui lòng nhập đầy đủ ngày và giờ vào/ra', 'warning');
        return;
    }
    // Lễ Việt Nam không đi làm: không cần shiftCode
    if (dayType !== 'vietnamese_holiday' && !shiftCode) {
        showAlert('Vui lòng chọn ca làm việc!', 'warning');
        return;
    }

    // Multi-day shifts are allowed. We only warn if the selection implies >24h duration.
    if (checkIn && checkOut && date && checkoutDate && checkoutDate !== date) {
        const [inHour, inMin] = checkIn.split(':').map(Number);
        const [outHour, outMin] = checkOut.split(':').map(Number);
        const inMinutesTotal = inHour * 60 + inMin;
        const outMinutesTotal = outHour * 60 + outMin;
        if (outMinutesTotal >= inMinutesTotal) {
            showAlert('Bạn đang chọn ngày ra là ngày hôm sau và giờ ra >= giờ vào → ca có thể dài hơn 24h. Nếu đây là ca nhiều ngày thì vẫn có thể lưu, còn nếu không thì vui lòng kiểm tra lại.', 'warning');
        }
    }

    // Validation: Kiểm tra giờ vào >= giờ ra khi cùng ngày (validation sớm)
    if (checkIn && checkOut && date && checkoutDate) {
        const [inHour, inMin] = checkIn.split(':').map(Number);
        const [outHour, outMin] = checkOut.split(':').map(Number);
        const inMinutesTotal = inHour * 60 + inMin;
        const outMinutesTotal = outHour * 60 + outMin;

        // Nếu cùng ngày và giờ vào >= giờ ra → lỗi
        if (date === checkoutDate && inMinutesTotal >= outMinutesTotal) {
            showAlert('Giờ vào phải nhỏ hơn giờ ra khi cùng ngày. Nếu làm ca qua đêm (SA/AM), vui lòng chọn ngày ra là ngày hôm sau.', 'warning');
            return;
        }
    }

    // Chuyển HH:MM ↔ phút (int) để tránh sai số số thực
    const hhmmToMinutes = (v) => {
        if (!v) return 0;
        const [h, m] = String(v).split(':').map(Number);
        return (h || 0) * 60 + (m || 0);
    };
    const minutesToHHMM = (mins) => {
        const m = Math.max(0, Math.round(mins || 0));
        const h = Math.floor(m / 60);
        const mm = m % 60;
        return `${h}:${String(mm).padStart(2, '0')}`;
    };
    const breakMinutes = hhmmToMinutes(breakTimeStr);
    const compRegularMinutes = hhmmToMinutes(compTimeRegularStr);
    const compOvertimeMinutes = 0; // deprecated on UI
    const compBefore22Minutes = hhmmToMinutes(compTimeBefore22Str);
    const compAfter22Minutes = hhmmToMinutes(compTimeAfter22Str);

    // Calculate shift start and end times based on shift code
    let shiftStart = null;
    let shiftEnd = null;
    if (shiftCode === '1') {
        shiftStart = '07:30';
        shiftEnd = '16:30';
    } else if (shiftCode === '2') {
        shiftStart = '09:00';
        shiftEnd = '18:00';
    } else if (shiftCode === '3') {
        shiftStart = '11:00';
        shiftEnd = '20:00';
    } else if (shiftCode === '4') {
        shiftStart = '08:00';
        shiftEnd = '17:00';
    } else if (shiftCode === '5') {
        shiftStart = '00:00';
        shiftEnd = '23:59';
    }
    // Nếu người dùng đã sửa giờ vào/ra, shiftStart/shiftEnd phải lấy từ input
    if (!shiftStart || !shiftEnd) {
        shiftStart = checkIn;
        shiftEnd = checkOut;
    }
    shiftStart = shiftStart || '';
    shiftEnd = shiftEnd || '';

    // Log chi tiết để debug
    // console.log('shiftCode:', shiftCode, 'shiftStart:', shiftStart, 'shiftEnd:', shiftEnd);

    // Prepare data
    // Pre-submit validation: cho phép chọn nhiều loại đối ứng
    const editIdInputVal = document.getElementById('editAttendanceId')?.value || '';
    const isEditing = !!(editIdInputVal && String(editIdInputVal).trim().length > 0);
    const activeCount = (compRegularMinutes > 0 ? 1 : 0) + (compBefore22Minutes > 0 ? 1 : 0) + (compAfter22Minutes > 0 ? 1 : 0);

    // Kiểm tra tổng đối ứng không vượt quá tổng giờ làm
    const totalCompMinutes = compRegularMinutes + compBefore22Minutes + compAfter22Minutes;

    // Tính tổng phút làm từ checkIn và checkOut (format "HH:MM")
    let totalWorkMinutes = 0;
    if (checkIn && checkOut) {
        const [inHour, inMin] = checkIn.split(':').map(Number);
        const [outHour, outMin] = checkOut.split(':').map(Number);

        if (!isNaN(inHour) && !isNaN(inMin) && !isNaN(outHour) && !isNaN(outMin)) {
            const inMinutes = inHour * 60 + inMin;
            const outMinutes = outHour * 60 + outMin;

            // Xử lý ca qua đêm: nếu ngày ra khác ngày vào
            if (date !== checkoutDate) {
                // Ca qua đêm: tính từ giờ vào đến 24:00 + từ 00:00 đến giờ ra
                // Đơn giản hóa: (24*60 - inMinutes) + outMinutes
                totalWorkMinutes = (24 * 60 - inMinutes) + outMinutes;
            } else {
                // Cùng ngày
                totalWorkMinutes = outMinutes - inMinutes;
            }

            // Trừ giờ nghỉ (phút)
            totalWorkMinutes -= breakMinutes;
            // Đảm bảo không âm
            totalWorkMinutes = Math.max(0, totalWorkMinutes);
        }
    }

    // console.log('Debug validation (minutes):', {
    //     checkIn, checkOut,
    //     breakMinutes,
    //     totalWorkMinutes,
    //     totalCompMinutes,
    //     totalWorkHHMM: minutesToHHMM(totalWorkMinutes),
    //     totalCompHHMM: minutesToHHMM(totalCompMinutes)
    // });

    // Chỉ chặn ở frontend khi có đủ dữ liệu và tổng giờ làm > 0, tránh báo sai (đặc biệt cuối tuần/ca 5)
    const dayTypeValForCheck = dayType;
    if (dayTypeValForCheck !== 'weekend' && totalWorkMinutes > 0 && totalCompMinutes > totalWorkMinutes) {
        showAlert(`Tổng đối ứng (${minutesToHHMM(totalCompMinutes)}) không được vượt quá tổng giờ làm (${minutesToHHMM(totalWorkMinutes)})`, 'warning');
        return;
    }

    // ✅ LOGIC MỚI: KHÔNG reset các loại đối ứng - cho phép chọn nhiều loại cùng lúc
    // Bỏ hoàn toàn logic cũ "zero-out" để cho phép người dùng chọn nhiều loại đối ứng
    // console.log('Debug - Comp time (minutes) before submit:', {
    //     regular: compRegularMinutes,
    //     before22: compBefore22Minutes,
    //     after22: compAfter22Minutes,
    //     total: totalCompMinutes
    // });

    const data = {
        date: date,  // Ngày vào
        checkout_date: checkoutDate,  // Ngày ra (MỚI)
        check_in: checkIn || null,  // Cho phép null cho lễ Việt Nam
        check_out: checkOut || null,  // Cho phép null cho lễ Việt Nam
        note: note,
        break_time: breakTimeStr || (dayType === 'vietnamese_holiday' && (!checkIn || !checkOut) ? '00:00' : '01:00'),
        is_holiday: isHoliday,
        holiday_type: dayType,
        shift_code: shiftCode || (dayType === 'vietnamese_holiday' && (!checkIn || !checkOut) ? '5' : null),  // Ca 5 cho lễ Việt Nam không đi làm
        shift_start: shiftStart || null,  // Cho phép null cho lễ Việt Nam
        shift_end: shiftEnd || null,  // Cho phép null cho lễ Việt Nam
        comp_time_regular: compTimeRegularStr || '00:00',
        comp_time_overtime: compTimeOvertimeStr || '00:00',
        comp_time_ot_before_22: compTimeBefore22Str || '00:00',
        comp_time_ot_after_22: compTimeAfter22Str || '00:00',
        overtime_comp_time: '00:00',  // Giữ lại để tương thích
        signature: signature // LUÔN gửi chữ ký (có thể rỗng)
    };

    console.log('Debug - Data being sent to server:', data);

    console.log('Submitting data:', data);

    // If editing, use PUT request
    if (editIdInput && editIdInput.value) {
        return apiCall(`/api/attendance/${editIdInput.value}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        })
            .then(async response => {
                const contentType = response.headers.get('content-type') || '';
                let respData;
                if (contentType.includes('application/json')) {
                    respData = await response.json();
                } else {
                    const text = await response.text();
                    showAlert('Lỗi server: ' + text, 'error');
                    throw new Error('Server trả về không phải JSON: ' + text);
                }
                if (respData.error) {
                    showAlert(respData.error, 'error');
                } else {
                    showAlert('Cập nhật chấm công thành công', 'success');
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
    console.log('Submitting attendance data:', data);  // Debug log
    return apiCall('/api/attendance', {
        method: 'POST',
        body: JSON.stringify(data)
    })
        .then(response => {
            // console.log('Response status:', response.status);
            // console.log('Response headers:', response.headers);

            // Kiểm tra content-type để xử lý đúng loại response
            const contentType = response.headers.get('content-type') || '';

            // Kiểm tra status code trước khi parse JSON
            if (response.status >= 400) {
                if (contentType.includes('application/json')) {
                    return response.json().then(data => {
                        // console.log('Error response data:', data);
                        throw new Error(data.error || `HTTP ${response.status}`);
                    });
                } else {
                    // Server trả về HTML thay vì JSON - đọc text để debug
                    return response.text().then(text => {
                        console.error('Server returned HTML instead of JSON:', text.substring(0, 500));
                        throw new Error('Đã xảy ra lỗi server. Vui lòng kiểm tra console để biết chi tiết.');
                    });
                }
            }

            if (contentType.includes('application/json')) {
                return response.json().then(data => {
                    // console.log('Success response data:', data);
                    return data;
                });
            } else {
                // Server trả về HTML thay vì JSON - đọc text để debug
                return response.text().then(text => {
                    console.error('Server returned HTML instead of JSON:', text.substring(0, 500));
                    throw new Error('Đã xảy ra lỗi server. Vui lòng kiểm tra console để biết chi tiết.');
                });
            }
        })
        .then(data => {
            if (data.error) {
                showAlert(data.error, 'error');
            } else {
                // Hiển thị thông tin chữ ký nếu có
                if (data.signature_info && data.signature_info.message) {
                    showAlert(`Lưu chấm công thành công. ${data.signature_info.message}`, 'success');
                } else {
                    showAlert('Lưu chấm công thành công', 'success');
                }
                // Reset form về trạng thái mặc định sau khi tạo thành công
                resetFormToDefaults();
                updateAttendanceHistory();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert(error.message || 'Đã xảy ra lỗi khi lưu chấm công', 'error');
        });
}

// Dynamic show/hide comp time inputs based on selection
(function setupCompTimeSwitcher() {
    const typeSelect = document.getElementById('compTimeType');
    if (!typeSelect) return;
    const groups = document.querySelectorAll('.comp-group');
    function updateVisibility() {
        groups.forEach(g => g.style.display = 'none');
        if (typeSelect.value === 'regular') {
            document.querySelectorAll('.comp-regular').forEach(g => g.style.display = 'block');
        } else if (typeSelect.value === 'ot_before') {
            document.querySelectorAll('.comp-ot-before').forEach(g => g.style.display = 'block');
        } else if (typeSelect.value === 'ot_after') {
            document.querySelectorAll('.comp-ot-after').forEach(g => g.style.display = 'block');
        }
        // Đồng bộ disable theo lựa chọn
        if (typeof window.updateCompTimeLocks === 'function') {
            window.updateCompTimeLocks();
        }
    }
    typeSelect.addEventListener('change', function (e) {
        const dayTypeVal = document.getElementById('dayType')?.value || '';
        if (dayTypeVal === 'weekend' && typeSelect.value === 'regular') {
            // Block selecting regular on weekend
            typeSelect.value = '';
            if (typeof showToast === 'function') showToast('Cuối tuần không được chọn đối ứng trong ca', 'warning');
        }
        updateVisibility();
    });
    // Initialize
    updateVisibility();
})();

// Ràng buộc cho phép chọn nhiều loại đối ứng trên UI
(function setupCompTimeMutualExclusion() {
    const regularInput = document.getElementById('compTimeRegular');
    const before22Input = document.getElementById('compTimeBefore22');
    const after22Input = document.getElementById('compTimeAfter22');
    const typeSelect = document.getElementById('compTimeType');
    if (!regularInput || !before22Input || !after22Input) return;

    function hhmmToHours(v) {
        if (!v) return 0;
        if (typeof v === 'number') return v;
        if (v.includes(':')) {
            const parts = v.split(':');
            const hh = parseInt(parts[0] || '0', 10);
            const mm = parseInt(parts[1] || '0', 10);
            return (isNaN(hh) ? 0 : hh) + (isNaN(mm) ? 0 : mm) / 60;
        }
        const f = parseFloat(v);
        return isNaN(f) ? 0 : f;
    }

    function isPositive(x) { return (x || 0) > 1e-6; }

    function setDisabled(el, disabled) { if (el) el.disabled = !!disabled; }

    // parseHHMM moved to global scope

    function applyLocks() {
        // Nếu đang sửa bản ghi, KHÔNG disable input để tránh cản trở chỉnh sửa
        const editIdInput = document.getElementById('editAttendanceId');
        const isEditing = !!(editIdInput && editIdInput.value && String(editIdInput.value).trim().length > 0);

        if (isEditing) {
            // Khi sửa: enable tất cả để không cản trở chỉnh sửa
            setDisabled(regularInput, false);
            setDisabled(before22Input, false);
            setDisabled(after22Input, false);
            return;
        }

        // LOGIC MỚI: Tính toán giờ làm việc và tăng ca để quyết định enable/disable
        const checkIn = document.getElementById('checkInTime')?.value || '';
        const checkOut = document.getElementById('checkOutTime')?.value || '';
        const shiftCode = document.getElementById('shiftSelect')?.value || '';
        const dayType = document.getElementById('dayType')?.value || 'normal';

        if (!checkIn || !checkOut || !shiftCode) {
            // Chưa có đủ thông tin: enable tất cả
            setDisabled(regularInput, false);
            setDisabled(before22Input, false);
            setDisabled(after22Input, false);
            return;
        }

        // Tính giờ làm việc thực tế
        const checkInTime = window.parseHHMM(checkIn);
        const checkOutTime = window.parseHHMM(checkOut);
        if (!checkInTime || !checkOutTime) return;

        const shiftRange = window.getShiftRangeByCode(shiftCode);
        if (!shiftRange) return;

        const shiftStart = window.parseHHMM(shiftRange.start);
        const shiftEnd = window.parseHHMM(shiftRange.end);
        if (!shiftStart || !shiftEnd) return;

        // Tính giờ làm việc thực tế (trừ giờ nghỉ)
        const breakHours = window.getBreakHours();
        const checkInDate = new Date(`2000-01-01T${checkIn}:00`);
        const checkOutDate = new Date(`2000-01-01T${checkOut}:00`);
        let actualWorkHours = (checkOutDate - checkInDate) / 3600000 - breakHours;

        // Xử lý trường hợp qua ngày
        if (actualWorkHours < 0) {
            actualWorkHours += 24;
        }

        // Tính tăng ca
        const shiftStartDate = new Date(`2000-01-01T${shiftRange.start}:00`);
        const shiftEndDate = new Date(`2000-01-01T${shiftRange.end}:00`);
        const twentyTwoDate = new Date(`2000-01-01T22:00:00`);

        let overtimeBefore22 = 0;
        let overtimeAfter22 = 0;

        if (checkOutDate > shiftEndDate) {
            // Có tăng ca
            const postShiftStart = new Date(Math.max(checkInDate.getTime(), shiftEndDate.getTime()));
            const postShiftEnd = new Date(Math.min(checkOutDate.getTime(), twentyTwoDate.getTime()));

            if (postShiftEnd > postShiftStart) {
                overtimeBefore22 = (postShiftEnd - postShiftStart) / 3600000;
            }

            if (checkOutDate > twentyTwoDate) {
                overtimeAfter22 = (checkOutDate - twentyTwoDate) / 3600000;
            }
        }

        // Áp dụng quy tắc mới
        if (actualWorkHours < 8.0) {
            // < 8h: chỉ cho phép đối ứng trong ca
            setDisabled(regularInput, false);
            setDisabled(before22Input, true);
            setDisabled(after22Input, true);

            // Clear các giá trị không hợp lệ
            if (before22Input.value && before22Input.value !== '00:00') {
                before22Input.value = '00:00';
                showToast('Đã xóa đối ứng tăng ca trước 22h vì giờ làm < 8h', 'info');
            }
            if (after22Input.value && after22Input.value !== '00:00') {
                after22Input.value = '00:00';
                showToast('Đã xóa đối ứng tăng ca sau 22h vì giờ làm < 8h', 'info');
            }
        } else if (actualWorkHours >= 8.0 && overtimeBefore22 > 0.1 && overtimeAfter22 <= 0.1) {
            // ≥ 8h và chỉ có tăng ca trước 22h: cho phép đối ứng trong ca và trước 22h
            setDisabled(regularInput, false);
            setDisabled(before22Input, false);
            setDisabled(after22Input, true);

            // Clear đối ứng sau 22h nếu không hợp lệ
            if (after22Input.value && after22Input.value !== '00:00') {
                after22Input.value = '00:00';
                showToast('Đã xóa đối ứng tăng ca sau 22h vì không có tăng ca sau 22h', 'info');
            }
        } else if (actualWorkHours >= 8.0 && overtimeAfter22 > 0.1) {
            // ≥ 8h và có tăng ca sau 22h: cho phép tất cả
            setDisabled(regularInput, false);
            setDisabled(before22Input, false);
            setDisabled(after22Input, false);
        } else {
            // Trường hợp khác: enable tất cả
            setDisabled(regularInput, false);
            setDisabled(before22Input, false);
            setDisabled(after22Input, false);
        }

        // Cảnh báo nhẹ nếu tổng đối ứng quá cao
        const r = hhmmToHours(regularInput.value);
        const b = hhmmToHours(before22Input.value);
        const a = hhmmToHours(after22Input.value);
        const totalCompTime = r + b + a;
        if (totalCompTime > 24) {
            showToast('Tổng đối ứng quá cao. Vui lòng kiểm tra lại.', 'warning');
        }
    }

    ['input', 'change', 'blur'].forEach(evt => {
        regularInput.addEventListener(evt, applyLocks);
        before22Input.addEventListener(evt, applyLocks);
        after22Input.addEventListener(evt, applyLocks);
    });

    // Thêm event listeners cho các input ảnh hưởng đến logic enable/disable
    const checkInInput = document.getElementById('checkInTime');
    const checkOutInput = document.getElementById('checkOutTime');
    const shiftSelect = document.getElementById('shiftSelect');
    const dayTypeSelect = document.getElementById('dayType');
    const breakTimeInput = document.getElementById('breakTime');

    if (checkInInput) checkInInput.addEventListener('change', applyLocks);
    if (checkOutInput) checkOutInput.addEventListener('change', applyLocks);
    if (shiftSelect) shiftSelect.addEventListener('change', applyLocks);
    if (dayTypeSelect) dayTypeSelect.addEventListener('change', applyLocks);
    if (breakTimeInput) breakTimeInput.addEventListener('change', applyLocks);

    // Expose để nơi khác gọi đồng bộ
    window.updateCompTimeLocks = applyLocks;

    // Thêm function để cập nhật UI khi load form edit
    window.updateCompTimeUI = function () {
        applyLocks();
    };

    // Initialize
    applyLocks();
})();

// Tự động điều chỉnh các lựa chọn dropdown đối ứng dựa trên giờ vào/ra và ca làm việc
(function setupCompTypeOptionsAuto() {
    const typeSelect = document.getElementById('compTimeType');
    if (!typeSelect) return;
    // Helper: set select value and ensure UI toggles by firing change
    function setTypeSelectValue(newVal) {
        const prev = typeSelect.value;
        typeSelect.value = newVal;
        // Always dispatch change to sync visibility even if value is same
        typeSelect.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // Functions moved to global scope - using window functions

    function updateCompTypeOptions() {
        const dateEl = document.getElementById('attendanceDate');
        let dateVal = dateEl ? dateEl.value : '';
        if (dateVal && dateVal.includes('/')) {
            const [d, m, y] = dateVal.split('/');
            dateVal = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
        }
        const checkIn = document.getElementById('checkInTime')?.value || '';
        const checkOut = document.getElementById('checkOutTime')?.value || '';
        const shiftCode = document.getElementById('shiftSelect')?.value || '';

        // Phát hiện đang sửa bản ghi hay tạo mới
        const editIdInput = document.getElementById('editAttendanceId');
        const isEditing = !!(editIdInput && editIdInput.value && String(editIdInput.value).trim().length > 0);

        // Nếu thiếu dữ liệu cơ bản thì chỉ bật "đối ứng trong ca" khi tạo mới; khi sửa thì không disable gì
        const optRegular = typeSelect.querySelector('option[value="regular"]');
        const optBefore = typeSelect.querySelector('option[value="ot_before"]');
        const optAfter = typeSelect.querySelector('option[value="ot_after"]');

        function setOpt(o, disabled) { if (o) o.disabled = !!disabled; }

        // Nếu là Cuối tuần/Lễ VN hoặc Ca 5: disable hẳn lựa chọn đối ứng trong ca trong dropdown
        const dayTypeVal = document.getElementById('dayType')?.value || '';
        const isHolidayNoRegular = (dayTypeVal === 'weekend' || dayTypeVal === 'vietnamese_holiday');
        const isFreeShiftNoRegular = (shiftCode === '5' && dayTypeVal !== 'vietnamese_holiday');
        const disableRegular = isHolidayNoRegular || isFreeShiftNoRegular;
        if (disableRegular) {
            setOpt(optRegular, true);
            if (typeSelect.value === 'regular') {
                setTypeSelectValue('');
            }
        } else {
            setOpt(optRegular, false);
        }

        if (!checkIn || !checkOut) {
            if (isEditing) {
                // Khi sửa: vẫn phải giữ rule disable "đối ứng trong ca" cho weekend/Lễ VN/Ca 5
                setOpt(optRegular, disableRegular);
                setOpt(optBefore, false);
                setOpt(optAfter, false);
            } else {
                // Tạo mới: để placeholder mặc định, ẩn nhóm nhập
                setOpt(optRegular, disableRegular);
                setOpt(optBefore, true);
                setOpt(optAfter, true);
                // Đặt về rỗng và kích hoạt toggle để ẩn nhóm
                setTypeSelectValue('');
            }
            if (typeof window.updateCompTimeLocks === 'function') window.updateCompTimeLocks();
            return;
        }

        const ci = window.toDate(dateVal, checkIn);
        let co = window.toDate(dateVal, checkOut);
        // Nếu check-out trước check-in (qua nửa đêm), cộng ngày cho co
        if (co && ci && co <= ci) co = new Date(co.getTime() + 24 * 3600000);

        const breakH = window.getBreakHours();
        const cutoff = window.toDate(dateVal, '22:00');

        // Phân nhánh theo loại ngày: Lễ VN coi toàn bộ giờ làm là OT
        const dayTypeNow = document.getElementById('dayType')?.value || '';
        let hasOvertime = false;
        let hasBefore22 = false;
        let hasAfter22 = false;

        if (dayTypeNow === 'vietnamese_holiday') {
            // Có làm việc là có OT
            hasOvertime = !!(ci && co && co > ci);
            if (ci && co && cutoff) {
                const endBefore = new Date(Math.min(co.getTime(), cutoff.getTime()));
                hasBefore22 = endBefore > ci; // bất kỳ khoảng trước 22h
                hasAfter22 = co > cutoff;
            }
        } else {
            // Ngày thường/lễ khác: OT sau khi đủ 8h công + nghỉ
            const overtimeStart = ci ? new Date(ci.getTime() + (breakH + 8.0) * 3600000) : null;
            hasOvertime = (co && overtimeStart) ? (hoursBetween(overtimeStart, co) > 0.1) : false;
            if (hasOvertime && overtimeStart && co && cutoff) {
                const endBefore = new Date(Math.min(co.getTime(), cutoff.getTime()));
                hasBefore22 = endBefore > overtimeStart;
                const startAfter = new Date(Math.max(overtimeStart.getTime(), cutoff.getTime()));
                hasAfter22 = co > startAfter;
            }
        }

        // Mặc định: chỉ bật Regular nếu không bị cấm (ngày nghỉ/Lễ VN hoặc Ca 5)
        setOpt(optRegular, disableRegular);
        if (isEditing) {
            // Khi sửa: không disable các option, chỉ để người dùng tự chọn; backend sẽ kiểm tra logic
            setOpt(optBefore, false);
            setOpt(optAfter, false);
        } else {
            // Khi tạo mới: bật/tắt theo điều kiện thực tế
            setOpt(optBefore, !(hasOvertime && hasBefore22));
            setOpt(optAfter, !(hasOvertime && hasAfter22));
            // Nếu lựa chọn hiện tại bị vô hiệu, chuyển về placeholder (rỗng)
            if ((typeSelect.value === 'ot_before' && optBefore?.disabled) || (typeSelect.value === 'ot_after' && optAfter?.disabled)) {
                setTypeSelectValue('');
            }
        }

        // Đồng bộ khoá input theo lựa chọn mới
        if (typeof window.updateCompTimeLocks === 'function') window.updateCompTimeLocks();
    }

    // Gọi khi thay đổi các trường liên quan
    ['attendanceDate', 'checkInTime', 'checkOutTime', 'breakTime', 'shiftSelect', 'dayType'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', updateCompTypeOptions);
        if (el && (id === 'checkInTime' || id === 'checkOutTime' || id === 'breakTime')) {
            el.addEventListener('input', updateCompTypeOptions);
        }
    });

    // Gọi khi tải trang và sau khi chọn ca auto điền giờ
    document.addEventListener('DOMContentLoaded', updateCompTypeOptions);
    const shiftSelect = document.getElementById('shiftSelect');
    if (shiftSelect) shiftSelect.addEventListener('change', () => setTimeout(updateCompTypeOptions, 0));

    // Expose để nơi khác (edit) có thể gọi
    window.updateCompTypeOptions = updateCompTypeOptions;
    // Khởi tạo
    setTimeout(updateCompTypeOptions, 0);
})();

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

    // Clear signature input (không cần signature pad nữa)
    const signatureInput = document.getElementById('signature-input');
    if (signatureInput) signatureInput.value = '';

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

    // Thêm event listener để xử lý break_time khi chọn lễ Việt Nam
    if (dayTypeSelect) {
        dayTypeSelect.addEventListener('change', function () {
            if (this.value === 'vietnamese_holiday') {
                // Khi chọn lễ Việt Nam, set break_time = 0:00 nếu không có giờ vào/ra
                const checkInInput = document.getElementById('checkInTime');
                const checkOutInput = document.getElementById('checkOutTime');
                if (breakTimeInput && (!checkInInput.value || !checkOutInput.value)) {
                    breakTimeInput.value = '00:00';
                }
            } else {
                // Các loại ngày khác: set break_time = 1:00
                if (breakTimeInput) breakTimeInput.value = '01:00';
            }
        });
    }

    // Enable tất cả các option trong loại ngày
    if (dayTypeSelect) {
        dayTypeSelect.querySelectorAll('option').forEach(option => {
            option.disabled = false;
        });
    }

    // Reset ghi chú về giá trị mặc định
    const noteInput = document.getElementById('attendanceNote');
    if (noteInput) noteInput.value = 'Chưa hoàn thành công việc';
}

// Function to reset form to default state after successful submission
function resetFormToDefaults() {
    const attendanceForm = document.getElementById('attendanceForm');
    const editAttendanceId = document.getElementById('editAttendanceId');
    const saveAttendanceBtn = document.getElementById('saveAttendanceBtn');
    const cancelEditBtn = document.getElementById('cancelEditBtn');

    // Reset form
    if (attendanceForm) attendanceForm.reset();
    if (editAttendanceId) editAttendanceId.value = '';
    if (saveAttendanceBtn) saveAttendanceBtn.innerHTML = '<i class="fas fa-save me-2"></i>Lưu đăng ký';
    if (cancelEditBtn) cancelEditBtn.style.display = 'none';

    // Clear signature input
    const signatureInput = document.getElementById('signature-input');
    if (signatureInput) signatureInput.value = '';

    // Set ngày hiện tại
    const today = new Date();
    const dateInput = document.getElementById('attendanceDate');
    if (dateInput && dateInput._flatpickr) {
        dateInput._flatpickr.setDate(today, true);
    }

    // Thêm event listener để xử lý break_time khi thay đổi giờ vào/ra
    const checkInInput = document.getElementById('checkInTime');
    const checkOutInput = document.getElementById('checkOutTime');
    const dayTypeSelectForBreakTime = document.getElementById('dayTypeSelect');

    function updateBreakTimeForVietnameseHoliday() {
        if (dayTypeSelectForBreakTime && dayTypeSelectForBreakTime.value === 'vietnamese_holiday') {
            const breakTimeInput = document.getElementById('breakTime');
            if (breakTimeInput) {
                // Nếu không có giờ vào/ra: break_time = 0:00
                // Nếu có giờ vào/ra: break_time = 1:00
                if (!checkInInput.value || !checkOutInput.value) {
                    breakTimeInput.value = '00:00';
                } else {
                    breakTimeInput.value = '01:00';
                }
            }
        }
    }

    if (checkInInput) {
        checkInInput.addEventListener('change', updateBreakTimeForVietnameseHoliday);
    }
    if (checkOutInput) {
        checkOutInput.addEventListener('change', updateBreakTimeForVietnameseHoliday);
    }

    // Reset ca làm việc về "-- Chọn ca --"
    const shiftSelect = document.getElementById('shiftSelect');
    if (shiftSelect) shiftSelect.value = '';

    // Reset giờ vào/ra về "--:--"
    const checkInTimeInput = document.getElementById('checkInTime');
    const checkOutTimeInput = document.getElementById('checkOutTime');
    if (checkInTimeInput) checkInTimeInput.value = '';
    if (checkOutTimeInput) checkOutTimeInput.value = '';

    // Reset giờ nghỉ về "1:00"
    const breakTimeInput = document.getElementById('breakTime');
    if (breakTimeInput) breakTimeInput.value = '01:00';

    // Reset giờ đối ứng về "0:00"
    const compTimeRegularInput = document.getElementById('compTimeRegular');
    const compTimeOvertimeInput = document.getElementById('compTimeOvertime');
    if (compTimeRegularInput) compTimeRegularInput.value = '00:00';
    if (compTimeOvertimeInput) compTimeOvertimeInput.value = '00:00';

    // Reset loại ngày về "-- Chọn loại ngày --"
    const dayTypeSelectReset = document.getElementById('dayType');
    if (dayTypeSelectReset) dayTypeSelectReset.value = '';

    // Reset loại đối ứng về "-- Chọn loại đối ứng --"
    const compTimeTypeSelect = document.getElementById('compTimeType');
    if (compTimeTypeSelect) compTimeTypeSelect.value = '';

    // Reset moon toggle (overnight mode)
    const moonToggle = document.getElementById('moonToggle');
    const nextDayCheckout = document.getElementById('nextDayCheckout');
    if (moonToggle) moonToggle.classList.remove('active');
    if (nextDayCheckout) nextDayCheckout.value = 'false';

    // Reset ghi chú về giá trị mặc định
    const noteInput = document.getElementById('attendanceNote');
    if (noteInput) noteInput.value = 'Chưa hoàn thành công việc';

    // Enable tất cả các option trong loại ngày
    const dayTypeSelect = document.getElementById('dayType');
    if (dayTypeSelect) {
        dayTypeSelect.querySelectorAll('option').forEach(option => {
            option.disabled = false;
        });
    }
}

// Make functions globally available
window.handleAttendanceSubmit = handleAttendanceSubmit;
window.resetForm = resetForm;
window.resetFormToDefaults = resetFormToDefaults;

// Thêm vào trong renderAttendancePage hoặc renderApprovalAttendancePage
function getOvertimePrintButton(attendanceId, approved, isAdmin) {
    if (!approved || !isAdmin) return '';
    return `<a href="/admin/attendance/${attendanceId}/export-overtime-pdf" class="btn btn-outline-primary btn-sm ms-1"><i class="fas fa-print"></i> In giấy tăng ca</a>`;
}

// Bulk Export Functions
function setupBulkExport() {
    const bulkExportSection = document.getElementById('bulkExportSection');
    const btnBulkExport = document.getElementById('btnBulkExport');
    const description = document.getElementById('bulkExportDescription');

    if (!bulkExportSection || !btnBulkExport || !description) {
        console.warn('Bulk export elements not found');
        return;
    }

    // Show bulk export section for ADMIN role
    const currentRole = document.getElementById('role-select')?.value || 'EMPLOYEE';
    if (currentRole === 'ADMIN') {
        bulkExportSection.style.display = 'block';
    }

    // Add event listener for bulk export button
    btnBulkExport.addEventListener('click', handleBulkExport);

    // ===== Nút xuất Excel lịch sử chấm công =====
    const btnExportAttendanceExcel = document.getElementById('btnExportAttendanceExcel');
    console.log('[CLIENT DEBUG] btnExportAttendanceExcel element:', btnExportAttendanceExcel);
    if (btnExportAttendanceExcel) {
        btnExportAttendanceExcel.addEventListener('click', async () => {
            console.log('[CLIENT DEBUG] ====== EXPORT BUTTON CLICKED ======');
            try {
                btnExportAttendanceExcel.disabled = true;
                const originalHtml = btnExportAttendanceExcel.innerHTML;
                btnExportAttendanceExcel.innerHTML =
                    '<i class="fas fa-spinner fa-spin me-2"></i>Đang xuất Excel...';

                // Lấy bộ lọc hiện tại của bảng "Lịch sử chấm công"
                const searchInput = document.getElementById('allAttendanceSearchName') || document.getElementById('allHistorySearchName');
                const deptSelect = document.getElementById('allAttendanceDepartment') || document.getElementById('allHistoryDepartment');
                const fromInput = document.getElementById('allAttendanceDateFrom') || document.getElementById('allHistoryDateFrom');
                const toInput = document.getElementById('allAttendanceDateTo') || document.getElementById('allHistoryDateTo');
                const monthFromSelect = document.getElementById('allHistoryMonthFrom');
                const monthToSelect = document.getElementById('allHistoryMonthTo');
                const yearFromSelect = document.getElementById('allHistoryYearFrom');
                const yearToSelect = document.getElementById('allHistoryYearTo');

                const params = new URLSearchParams();
                params.set('all', '1');
                if (searchInput && searchInput.value.trim()) {
                    params.set('search', searchInput.value.trim());
                }
                if (deptSelect && deptSelect.value) {
                    params.set('department', deptSelect.value);
                }
                if (fromInput && fromInput.value) {
                    params.set('date_from', fromInput.value);
                }
                if (toInput && toInput.value) {
                    params.set('date_to', toInput.value);
                }
                // Bổ sung lọc theo khoảng tháng/năm
                if (monthFromSelect && monthFromSelect.value) params.set('month_from', monthFromSelect.value);
                if (monthToSelect && monthToSelect.value) params.set('month_to', monthToSelect.value);
                if (yearFromSelect && yearFromSelect.value) params.set('year_from', yearFromSelect.value);
                if (yearToSelect && yearToSelect.value) params.set('year_to', yearToSelect.value);

                const url = `/export-attendance-history-excel?${params.toString()}`;
                console.log('[CLIENT DEBUG] Sending fetch request to:', url);
                console.log('[CLIENT DEBUG] Full URL:', window.location.origin + url);
                console.log('[CLIENT DEBUG] Request params:', params.toString());

                const response = await fetch(url, {
                    method: 'GET',
                    credentials: 'include',
                    headers: {
                        'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    }
                });
                console.log('[CLIENT DEBUG] Response received:', response.status, response.statusText);
                console.log('[CLIENT DEBUG] Response ok:', response.ok);
                if (!response.ok) {
                    const data = await response.json().catch(() => ({}));
                    const msg = data.error || 'Không thể xuất Excel lịch sử chấm công';
                    showAlert(msg, 'danger');
                } else {
                    const blob = await response.blob();
                    const downloadUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = downloadUrl;
                    a.download = `lich_su_cham_cong_${new Date()
                        .toISOString()
                        .slice(0, 10)}.xlsx`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(downloadUrl);
                }

                btnExportAttendanceExcel.innerHTML = originalHtml;
                btnExportAttendanceExcel.disabled = false;
            } catch (e) {
                console.error('[CLIENT DEBUG] Export attendance Excel error:', e);
                console.error('[CLIENT DEBUG] Error stack:', e.stack);
                showAlert('Đã xảy ra lỗi khi xuất Excel lịch sử chấm công', 'danger');
                btnExportAttendanceExcel.disabled = false;
            }
        });
    }
}

// Hàm lấy tổng số bản ghi đã phê duyệt để ước lượng thời gian tạo ZIP
// Ưu tiên sử dụng cùng bộ lọc với bảng "Lịch sử chấm công đã phê duyệt"
async function estimateBulkExportTime(month, year, type = 'range') {
    try {
        const params = new URLSearchParams();
        params.set('all', '1');
        params.set('per_page', '1');

        // Lấy filter hiện tại của bảng lịch sử đã phê duyệt (nếu có)
        const dateFrom = document.getElementById('allHistoryDateFrom')?.value || '';
        const dateTo = document.getElementById('allHistoryDateTo')?.value || '';
        const monthFrom = document.getElementById('allHistoryMonthFrom')?.value || '';
        const monthTo = document.getElementById('allHistoryMonthTo')?.value || '';
        const yearFrom = document.getElementById('allHistoryYearFrom')?.value || '';
        const yearTo = document.getElementById('allHistoryYearTo')?.value || '';

        if (dateFrom) params.set('date_from', dateFrom);
        if (dateTo) params.set('date_to', dateTo);
        if (monthFrom) params.set('month_from', monthFrom);
        if (monthTo) params.set('month_to', monthTo);
        if (yearFrom) params.set('year_from', yearFrom);
        if (yearTo) params.set('year_to', yearTo);

        let url = `/api/attendance/history?${params.toString()}`;

        const res = await fetch(url);
        if (!res.ok) {
            // Nếu API trả về lỗi, coi như không có dữ liệu
            return { total: 0, seconds: 5 };
        }

        const data = await res.json();
        // Kiểm tra chính xác: total phải tồn tại và > 0
        if (data && typeof data.total === 'number' && data.total > 0) {
            // Giả sử mỗi bản ghi mất 0.5s để tạo PDF
            const seconds = Math.ceil(data.total * 0.5);
            return { total: data.total, seconds };
        }
    } catch (e) {
        console.error('Error estimating bulk export time:', e);
    }
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
    const exportType = 'range'; // luôn xuất theo khoảng đang lọc

    const btnBulkExport = document.getElementById('btnBulkExport');
    if (!btnBulkExport) return;
    btnBulkExport.disabled = true;
    const originalText = btnBulkExport.innerHTML;

    // Ước lượng thời gian
    // Ước lượng dựa trên bộ lọc hiện tại
    const { total, seconds } = await estimateBulkExportTime(null, null, exportType);
    if (!total || total === 0) {
        showAlert('Không có dữ liệu trong khoảng đã chọn để tạo ZIP.', 'warning');
        btnBulkExport.innerHTML = originalText;
        btnBulkExport.disabled = false;
        return;
    }
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
    // Sử dụng cùng bộ lọc với bảng lịch sử chấm công đã phê duyệt (khoảng ngày/tháng/năm)
    const params = new URLSearchParams();

    const dateFrom = document.getElementById('allHistoryDateFrom')?.value || '';
    const dateTo = document.getElementById('allHistoryDateTo')?.value || '';
    const monthFrom = document.getElementById('allHistoryMonthFrom')?.value || '';
    const monthTo = document.getElementById('allHistoryMonthTo')?.value || '';
    const yearFrom = document.getElementById('allHistoryYearFrom')?.value || '';
    const yearTo = document.getElementById('allHistoryYearTo')?.value || '';

    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    if (monthFrom) params.set('month_from', monthFrom);
    if (monthTo) params.set('month_to', monthTo);
    if (yearFrom) params.set('year_from', yearFrom);
    if (yearTo) params.set('year_to', yearTo);

    // Nếu không có filter range nào, yêu cầu người dùng chọn
    if (!dateFrom && !dateTo && !monthFrom && !monthTo && !yearFrom && !yearTo) {
        showAlert('Vui lòng chọn khoảng ngày / tháng / năm ở bộ lọc phía trên trước khi xuất ZIP.', 'warning');
        clearInterval(countdownInterval);
        clearTimeout(timeoutFallback);
        btnBulkExport.innerHTML = originalText;
        btnBulkExport.disabled = false;
        return;
    }

    let url = `/admin/attendance/export-overtime-bulk?${params.toString()}`;

    try {
        const response = await fetch(url);

        // Khi server bắt đầu trả về response, dừng đếm ngược ngay lập tức
        clearInterval(countdownInterval);
        clearTimeout(timeoutFallback);

        if (response.ok) {
            // Kiểm tra content-type để đảm bảo đây là file ZIP
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/zip')) {
                // Tạo blob và tải về
                const blob = await response.blob();

                // Kiểm tra kích thước file - nếu quá nhỏ có thể là file rỗng
                if (blob.size < 100) {
                    // File ZIP rỗng thường có kích thước khoảng 22 bytes
                    showAlert('Không có dữ liệu trong khoảng đã chọn để tạo ZIP.', 'warning');
                    btnBulkExport.innerHTML = originalText;
                    btnBulkExport.disabled = false;
                    return;
                }

                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;

                // Tạo tên file
                // Đặt tên file theo ngày hiện tại để tránh phụ thuộc vào tham số tháng/năm
                const today = new Date();
                const y = today.getFullYear();
                const m = (today.getMonth() + 1).toString().padStart(2, '0');
                const d = today.getDate().toString().padStart(2, '0');
                const filename = `tangca_bulk_${d}${m}${y}.zip`;

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
                // Nếu không phải ZIP, có thể là JSON error
                const errorData = await response.json().catch(() => ({}));
                const errorMsg = errorData.error || errorData.detail || 'Không có dữ liệu trong khoảng đã chọn để tạo ZIP.';
                showAlert(errorMsg, 'warning');
                btnBulkExport.innerHTML = originalText;
                btnBulkExport.disabled = false;
            }
        } else if (response.status === 404) {
            // Không có dữ liệu
            const errorData = await response.json().catch(() => ({}));
            const errorMsg = errorData.error || errorData.detail || 'Không có dữ liệu trong khoảng đã chọn để tạo ZIP.';
            showAlert(errorMsg, 'warning');
            btnBulkExport.innerHTML = originalText;
            btnBulkExport.disabled = false;
        } else {
            // Lỗi khác
            const errorData = await response.json().catch(() => ({}));
            const errorMsg = errorData.error || errorData.detail || 'Lỗi khi tải file ZIP.';
            showAlert(errorMsg, 'danger');
            btnBulkExport.innerHTML = originalText;
            btnBulkExport.disabled = false;
        }
    } catch (error) {
        console.error('Download error:', error);
        // Nếu fetch thất bại, dùng timeout fallback
        clearInterval(countdownInterval);
        clearTimeout(timeoutFallback);
        showAlert('Lỗi khi tải file ZIP. Vui lòng thử lại.', 'danger');
        btnBulkExport.innerHTML = originalText;
        btnBulkExport.disabled = false;
    }
}

// Function xử lý phê duyệt hàng loạt
async function handleBulkApproval() {
    try {
        // Hiển thị dialog xác nhận
        const result = await Swal.fire({
            title: 'Xác nhận phê duyệt hàng loạt',
            text: 'Bạn có chắc chắn muốn phê duyệt tất cả các bản ghi đang chờ duyệt không?',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Có, phê duyệt hết!',
            cancelButtonText: 'Hủy bỏ',
            confirmButtonColor: '#28a745',
            cancelButtonColor: '#6c757d',
            reverseButtons: true
        });

        if (!result.isConfirmed) {
            return;
        }

        // Hiển thị loading
        const btnBulkApprove = document.getElementById('btnBulkApprove');
        if (btnBulkApprove) {
            btnBulkApprove.disabled = true;
            const originalText = btnBulkApprove.innerHTML;
            btnBulkApprove.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Đang xử lý...';

            try {
                // Gọi API phê duyệt hàng loạt
                const response = await apiCall('/api/attendance/approve-all', {
                    method: 'POST',
                    body: JSON.stringify({
                        action: 'approve'
                    })
                });

                if (response.ok) {
                    const data = await response.json();

                    // Hiển thị thông báo thành công
                    await Swal.fire({
                        title: 'Thành công!',
                        text: data.message,
                        icon: 'success',
                        confirmButtonText: 'OK'
                    });

                    // Reload lại dữ liệu approval
                    if (typeof loadApprovalAttendance === 'function') {
                        loadApprovalAttendance(1);
                    }

                    // Reload lại dashboard nếu cần
                    if (typeof updateUIForRole === 'function') {
                        const roleSelect = document.getElementById('role-select');
                        if (roleSelect) {
                            updateUIForRole(roleSelect.value);
                        }
                    }

                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Lỗi không xác định');
                }

            } catch (error) {
                console.error('Bulk approval error:', error);

                // Hiển thị thông báo lỗi
                await Swal.fire({
                    title: 'Lỗi!',
                    text: error.message || 'Có lỗi xảy ra khi phê duyệt hàng loạt',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });

            } finally {
                // Khôi phục trạng thái nút
                btnBulkApprove.disabled = false;
                btnBulkApprove.innerHTML = originalText;
            }
        }

    } catch (error) {
        console.error('Bulk approval error:', error);
        showAlert('Có lỗi xảy ra khi xử lý phê duyệt hàng loạt', 'error');
    }
}

// Function hiển thị/ẩn nút phê duyệt hàng loạt theo vai trò
function toggleBulkApprovalButton() {
    const bulkApprovalContainer = document.getElementById('bulkApprovalContainer');
    const roleSelect = document.getElementById('role-select');

    if (bulkApprovalContainer && roleSelect) {
        const currentRole = roleSelect.value;

        // Chỉ hiển thị cho TEAM_LEADER, MANAGER, ADMIN
        if (['TEAM_LEADER', 'MANAGER', 'ADMIN'].includes(currentRole)) {
            bulkApprovalContainer.style.display = 'block';
        } else {
            bulkApprovalContainer.style.display = 'none';
        }
    }
}

// Initialize bulk export when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    setupBulkExport();
    setupApprovalEventListeners();

    // Khởi tạo trạng thái ban đầu cho form đăng ký chấm công
    const dayTypeSelect = document.getElementById('dayType');
    if (dayTypeSelect) {
        // Enable tất cả các option trong loại ngày khi khởi tạo
        dayTypeSelect.querySelectorAll('option').forEach(option => {
            option.disabled = false;
        });
    }
});

// Make functions globally available
window.setupBulkExport = setupBulkExport;
window.handleBulkExport = handleBulkExport;
window.showAlert = showAlert;
window.showToast = showToast;
window.handleBulkApproval = handleBulkApproval;
window.toggleBulkApprovalButton = toggleBulkApprovalButton; 