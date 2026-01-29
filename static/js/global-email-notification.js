/**
 * Global Email Notification System
 * Hiển thị thông báo email status trên tất cả các trang
 */
// // console.log('[global-email-notification] script file executing');

// Hàm kiểm tra trạng thái email toàn cục
function checkGlobalEmailStatus() {
    // Kiểm tra request_id từ URL parameters hoặc data attribute
    const urlParams = new URLSearchParams(window.location.search);
    let requestId = urlParams.get('request_id');

    if (!requestId) {
        const bodyElement = document.body;
        if (bodyElement) {
            requestId = bodyElement.getAttribute('data-request-id');
        }
    }

    // Nếu có requestId cụ thể, kiểm tra theo request
    if (requestId) {
        const roleSelect = document.getElementById('role-select');
        const currentRole = window.currentRole || (roleSelect ? roleSelect.value : 'EMPLOYEE');
        // console.log('Checking email status for role:', currentRole, 'requestId:', requestId);
        checkEmailStatus(parseInt(requestId));
            return;
        }
        
    // Nếu KHÔNG có requestId, fallback: kiểm tra trạng thái gần nhất từ session
    // console.log('No request_id found. Fallback to latest email status');
    checkLatestEmailStatus();
}

// Hàm kiểm tra trạng thái email
function checkEmailStatus(requestId) {
    if (!requestId) return;
    
    let pollCount = 0;
    const maxPolls = 20; // Tối đa 20 lần polling (khoảng 1 phút)
    
    const checkStatus = () => {
        pollCount++;
        // console.log(`Polling attempt ${pollCount}/${maxPolls} for request ${requestId}`);
        
        // Dừng polling nếu đã quá số lần cho phép
        if (pollCount > maxPolls) {
            // console.log('Max polling attempts reached, stopping');
            return;
        }
        // console.log(`Checking email status for request_id: ${requestId}`);
        fetch(`/api/email-status/${requestId}`)
            .then(response => response.json())
            .then(data => {
                // console.log('Email status response:', data);
                if (data.status === 'success') {
                    // console.log('Email sent successfully, showing toast');
                    showToast('Email đã được gửi thành công đến HR!', 'success');
                    return; // Dừng kiểm tra
                } else if (data.status === 'error') {
                    // console.log('Email send failed, showing error toast');
                    showToast('Có lỗi khi gửi email: ' + data.message, 'error');
                    return; // Dừng kiểm tra
                } else if (data.status === 'skipped') {
                    // console.log('Email notification skipped for non-employee role');
                    return; // Dừng kiểm tra cho vai trò không phải nhân viên
                } else if (data.status === 'sending') {
                    // console.log('Email still sending, checking again in 3 seconds');
                    // Tiếp tục kiểm tra sau 3 giây
                    setTimeout(checkStatus, 3000);
                } else {
                    // console.log('Unknown status, checking again in 2 seconds');
                    // Trạng thái unknown, kiểm tra lại sau 2 giây
                    setTimeout(checkStatus, 2000);
                }
            })
            .catch(error => {
                console.error('Error checking email status:', error);
                setTimeout(checkStatus, 3000); // Thử lại sau 3 giây
            });
    };
    
    // Bắt đầu kiểm tra sau 2 giây để đảm bảo email có thời gian gửi
    setTimeout(checkStatus, 2000);
}

// Kiểm tra trạng thái email gần nhất từ session (không cần request_id)
function checkLatestEmailStatus() {
    // Guard: tránh hiện nhiều lần cho cùng request_id (kể cả reload)
    const shownKey = 'email_status_shown_request_id';
    const maxRetries = 20;  // Max retry limit to prevent infinite polling
    let retryCount = 0;

    const checkStatus = () => {
        retryCount++;
        // Stop polling if max retries reached
        if (retryCount > maxRetries) {
            // console.log('Max polling retries reached for latest email status');
            return;
        }

        // console.log('Checking latest email status');
        fetch('/api/email-status/latest')
            .then(response => response.json())
            .then(data => {
                // console.log('Latest email status response:', data);
                if (data.status === 'success') {
                    const alreadyShownFor = localStorage.getItem(shownKey);
                    if (alreadyShownFor !== String(data.request_id)) {
                        // console.log('Latest: Email sent successfully, showing toast');
                        showToast('Email đã được gửi thành công đến HR!', 'success');
                        localStorage.setItem(shownKey, String(data.request_id || ''));
                    } else {
                        // console.log('Latest: toast already shown for request', data.request_id);
                    }
                    return;
                } else if (data.status === 'error') {
                    const alreadyShownFor = localStorage.getItem(shownKey);
                    if (alreadyShownFor !== String(data.request_id)) {
                        // console.log('Latest: Email send failed, showing error toast');
                        showToast('Có lỗi khi gửi email: ' + data.message, 'error');
                        localStorage.setItem(shownKey, String(data.request_id || ''));
                    } else {
                        // console.log('Latest: error toast already shown for request', data.request_id);
                    }
                    return;
                } else if (data.status === 'sending') {
                    // Khi phát hiện bắt đầu một lượt gửi mới, xóa guard để lần success tiếp theo hiển thị toast
                    try { localStorage.removeItem(shownKey); } catch (e) {}
                    // console.log('Latest: Email still sending, checking again in 3 seconds');
                    setTimeout(checkStatus, 3000);
                } else {
                    // unknown -> dừng im lặng
                    // console.log('Latest: Unknown status, stop polling');
                }
            })
            .catch(error => {
                console.error('Error checking latest email status:', error);
                // Only retry if under max limit
                if (retryCount < maxRetries) {
                    setTimeout(checkStatus, 3000);
                }
            });
    };

    // bắt đầu sau 2s
    setTimeout(checkStatus, 2000);
}

// Đảm bảo các hàm có mặt trên phạm vi global để template có thể kiểm tra
try {
    window.checkGlobalEmailStatus = checkGlobalEmailStatus;
    window.checkEmailStatus = checkEmailStatus;
    window.checkLatestEmailStatus = checkLatestEmailStatus;
    // console.log('[global-email-notification] functions exposed to window');
} catch (e) {
    console.error('[global-email-notification] failed to expose functions:', e);
}

// Hàm hiển thị Toast (sử dụng SweetAlert2)
function showToast(message, type = 'success') {
    // console.log('Showing toast:', message, type);
    const Toast = Swal.mixin({
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.addEventListener('mouseenter', Swal.stopTimer)
            toast.addEventListener('mouseleave', Swal.resumeTimer)
        }
    });

    let icon = type;
    if (type === 'success') icon = 'success';
    else if (type === 'error') icon = 'error';
    else if (type === 'warning') icon = 'warning';
    else if (type === 'info') icon = 'info';

    Toast.fire({
        icon: icon,
        title: message
    });
}

// Hàm khởi tạo với delay để đợi window.currentRole được set
function initializeEmailNotification() {
    // console.log('Initializing email notification...');
    // console.log('Current role:', window.currentRole);
    // console.log('Request ID from URL:', new URLSearchParams(window.location.search).get('request_id'));
    // console.log('Request ID from data attribute:', document.body ? document.body.getAttribute('data-request-id') : 'Body not found');
    
    // Đợi một chút để đảm bảo window.currentRole đã được set
    setTimeout(() => {
        // console.log('Checking email status after delay...');
        checkGlobalEmailStatus();
    }, 100);
}

// Khởi tạo khi DOM loaded
document.addEventListener('DOMContentLoaded', function() {
    // console.log('Global email notification script loaded');
    initializeEmailNotification();
});

// Cũng kiểm tra ngay lập tức nếu DOM đã sẵn sàng
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeEmailNotification);
} else {
    // console.log('DOM already loaded, initializing email notification immediately');
    initializeEmailNotification();
}

// ===================== SSE: realtime push (preferred) =====================
let emailSSEConnection = null;

function startSSEEmailStatus() {
    if (!('EventSource' in window)) {
        // console.log('SSE not supported, fallback to polling');
        return;
    }
    try {
        // Close existing connection if any
        if (emailSSEConnection) {
            emailSSEConnection.close();
        }

        const es = new EventSource('/sse/email-status');
        emailSSEConnection = es;

        es.addEventListener('email_status', (evt) => {
            try {
                const data = JSON.parse(evt.data);
                // console.log('SSE email status:', data);
                const shownKey = 'email_status_shown_request_id';
                if (data.status === 'success') {
                    const already = localStorage.getItem(shownKey);
                    if (already !== String(data.request_id)) {
                        showToast('Email đã được gửi thành công đến HR!', 'success');
                        localStorage.setItem(shownKey, String(data.request_id || ''));
                    }
                } else if (data.status === 'error') {
                    const already = localStorage.getItem(shownKey);
                    if (already !== String(data.request_id)) {
                        showToast('Có lỗi khi gửi email: ' + (data.message || ''), 'error');
                        localStorage.setItem(shownKey, String(data.request_id || ''));
                    }
                } else if (data.status === 'sending') {
                    try { localStorage.removeItem(shownKey); } catch (e) {}
                }
            } catch (e) {
                console.error('SSE parse error', e);
            }
        });
        es.onerror = () => {
            // console.log('SSE connection error; it will retry automatically');
        };
    } catch (e) {
        // console.log('SSE init failed, fallback to polling', e);
    }
}

// Cleanup SSE connection when page unloads
window.addEventListener('beforeunload', function() {
    if (emailSSEConnection) {
        emailSSEConnection.close();
        emailSSEConnection = null;
    }
});

// start SSE asap
try { startSSEEmailStatus(); } catch (e) {}
