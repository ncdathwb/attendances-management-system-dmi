// ===== LEAVE REQUESTS LIST - JavaScript =====

// Global variables - should be set from template
window.leaveRequestsListUrl = window.leaveRequestsListUrl || '/leave-requests';
window.currentRole = window.currentRole || '';
window.userDepartment = window.userDepartment || '';

// Navigation handler to prevent errors
function handleNavigation(element) {
    try {
        if (window.pendingOperations) {
            window.pendingOperations.forEach(op => {
                if (op && typeof op.abort === 'function') {
                    op.abort();
                }
            });
            window.pendingOperations = [];
        }
        return true;
    } catch (error) {
        console.error('Navigation error:', error);
        return true;
    }
}

// Enhanced Toast Notification
function showToast(message, type) {
    type = type || 'info';
    var Toast = Swal.mixin({
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 4000,
        timerProgressBar: true,
        background: 'var(--card-bg)',
        color: 'var(--text-primary)',
        customClass: {
            popup: 'swal2-toast-custom'
        },
        didOpen: function(toast) {
            toast.addEventListener('mouseenter', Swal.stopTimer);
            toast.addEventListener('mouseleave', Swal.resumeTimer);
        }
    });

    var icon = type;
    var iconColor = '';

    if (type === 'success') {
        icon = 'success';
        iconColor = 'var(--success-color)';
    } else if (type === 'error') {
        icon = 'error';
        iconColor = 'var(--danger-color)';
    } else if (type === 'warning') {
        icon = 'warning';
        iconColor = 'var(--warning-color)';
    } else {
        icon = 'info';
        iconColor = 'var(--primary-color)';
    }

    Toast.fire({
        icon: icon,
        title: message,
        iconColor: iconColor
    });
}

// Loading state for buttons
function setButtonLoading(button, loading) {
    if (loading === undefined) loading = true;
    if (loading) {
        if (!button.getAttribute('data-original-text')) {
            button.setAttribute('data-original-text', button.innerHTML);
        }
        button.disabled = true;
        button.innerHTML = '<span class="loading"></span><span>Dang loc...</span>';
        button.classList.add('is-loading');
    } else {
        button.disabled = false;
        button.classList.remove('is-loading');
        button.innerHTML = button.getAttribute('data-original-text') || '<i class="fas fa-search me-1"></i> Loc';
    }
}

// Apply filters with loading state
function applyFilters() {
    var filterBtn = document.getElementById('filterButton') || document.querySelector('.btn-filter');
    if (!filterBtn) return;

    if (!filterBtn.getAttribute('data-original-text')) {
        filterBtn.setAttribute('data-original-text', filterBtn.innerHTML);
    }

    requestAnimationFrame(function() {
        requestAnimationFrame(function() {
            setButtonLoading(filterBtn, true);
        });
    });

    var status = document.getElementById('statusFilter').value;
    var employee = document.getElementById('employeeFilter').value;
    var department = document.getElementById('departmentFilter').value;
    var requestType = document.getElementById('requestTypeFilter').value;
    var dateFrom = document.getElementById('dateFromFilter').value;
    var dateTo = document.getElementById('dateToFilter').value;

    var params = new URLSearchParams();
    if (status) params.append('status', status);
    if (employee) params.append('employee', employee);
    if (department) params.append('department', department);
    if (requestType) params.append('request_type', requestType);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);

    setTimeout(function() {
        window.location.href = window.leaveRequestsListUrl + '?' + params.toString();
    }, 250);
}

// Clear all filters
function clearFilters() {
    Swal.fire({
        title: 'Xoa bo loc',
        text: 'Ban co chac chan muon xoa tat ca bo loc?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: 'var(--secondary-color)',
        cancelButtonColor: 'var(--primary-color)',
        confirmButtonText: '<i class="fas fa-check me-1"></i> Xoa',
        cancelButtonText: '<i class="fas fa-times me-1"></i> Huy',
        customClass: {
            popup: 'swal2-popup-custom'
        }
    }).then(function(result) {
        if (result.isConfirmed) {
            document.getElementById('statusFilter').value = '';
            document.getElementById('employeeFilter').value = '';
            document.getElementById('departmentFilter').value = '';
            document.getElementById('requestTypeFilter').value = '';
            document.getElementById('dateFromFilter').value = '';
            document.getElementById('dateToFilter').value = '';
            window.location.href = window.leaveRequestsListUrl;
        }
    });
}

// Enhanced tooltip for truncated content
function showFullTextFrom(el) {
    var fullText = el.getAttribute('title') || '';
    if (!fullText) return;
    Swal.fire({
        title: 'Chi tiet',
        html: '<div style="text-align:left;max-width:600px;word-break:break-word;padding:1rem;background:#f8f9fa;border-radius:0.5rem;">' + fullText + '</div>',
        confirmButtonText: '<i class="fas fa-check me-1"></i> Dong',
        confirmButtonColor: 'var(--primary-color)'
    });
}

// Function to download all attachments for a leave request
function downloadAllAttachments(requestId, attachments) {
    try {
        if (!attachments || attachments.length === 0) {
            showToast('Khong co chung tu de tai xuong', 'warning');
            return;
        }

        showToast('Dang tao file ZIP voi ' + attachments.length + ' file(s)...', 'info');

        var downloadUrl = '/leave-request/' + requestId + '/download-all';
        var link = document.createElement('a');
        link.href = downloadUrl;
        link.download = 'Chung_tu_nghi_phep_' + requestId + '.zip';
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        setTimeout(function() {
            showToast('Da tai xuong file ZIP voi ' + attachments.length + ' file(s)', 'success');
        }, 1000);

    } catch (error) {
        console.error('Error downloading attachments:', error);
        showToast('Co loi khi tai xuong chung tu', 'error');
    }
}

// Show notification modal
function showNotificationModal(title, message, type) {
    type = type || 'info';
    var bgClass = type === 'error' ? 'danger' : type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'info';
    var iconClass = type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle';

    var modalHtml = '<div class="modal fade" id="notificationModal" tabindex="-1">' +
        '<div class="modal-dialog">' +
            '<div class="modal-content">' +
                '<div class="modal-header bg-' + bgClass + ' text-white">' +
                    '<h5 class="modal-title"><i class="fas fa-' + iconClass + ' me-2"></i>' + title + '</h5>' +
                    '<button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>' +
                '</div>' +
                '<div class="modal-body"><p class="mb-0">' + message + '</p></div>' +
                '<div class="modal-footer">' +
                    '<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Dong</button>' +
                '</div>' +
            '</div>' +
        '</div>' +
    '</div>';

    var existingModal = document.getElementById('notificationModal');
    if (existingModal) {
        existingModal.remove();
    }

    document.body.insertAdjacentHTML('beforeend', modalHtml);

    var modal = new bootstrap.Modal(document.getElementById('notificationModal'));
    modal.show();

    document.getElementById('notificationModal').addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
}

// Count pending leave requests based on role
function getPendingLeaveRequestsCount() {
    var table = document.querySelector('.data-table tbody');
    if (!table) return 0;

    var currentRole = window.currentRole || '';
    var count = 0;

    var rows = table.querySelectorAll('tr');
    rows.forEach(function(row) {
        var statusBadge = row.querySelector('.status-badge, [class*="status-"]');
        if (!statusBadge) return;

        var status = statusBadge.textContent.trim().toLowerCase();

        if (currentRole === 'ADMIN' || currentRole === 'MANAGER') {
            if (status.indexOf('cho') >= 0) count++;
        } else if (currentRole === 'TEAM_LEADER') {
            if (status.indexOf('cho') >= 0) count++;
        }
    });

    return count;
}

// Update button visibility based on pending records count
function updateBulkActionButtonsVisibility() {
    var count = getPendingLeaveRequestsCount();
    var container = document.getElementById('bulkActionButtons');
    var btnApprove = document.getElementById('btnBulkApprove');

    if (container) {
        if (count > 0) {
            container.style.removeProperty('display');
            if (btnApprove) btnApprove.style.display = 'inline-block';
        } else {
            container.style.setProperty('display', 'none', 'important');
        }
    }
}

// Get IDs of pending leave requests from the visible table
function getPendingOfferIds() {
    var table = document.querySelector('.data-table tbody');
    if (!table) return [];

    var currentRole = window.currentRole || '';
    var ids = [];

    var rows = table.querySelectorAll('tr');
    rows.forEach(function(row) {
        var statusBadge = row.querySelector('.status-badge, [class*="status-"]');
        if (!statusBadge) return;

        var status = statusBadge.textContent.trim().toLowerCase();
        var isPending = false;

        if (currentRole === 'ADMIN' || currentRole === 'MANAGER') {
            if (status.indexOf('cho') >= 0) isPending = true;
        } else if (currentRole === 'TEAM_LEADER') {
            if (status.indexOf('cho') >= 0) isPending = true;
        }

        if (isPending) {
            var approveBtn = row.querySelector('.btn-approve');
            if (approveBtn) {
                ids.push(approveBtn.getAttribute('data-request-id'));
            } else {
                var idCell = row.querySelector('td:first-child span');
                if (idCell) {
                    ids.push(idCell.textContent.replace('#', '').trim());
                }
            }
        }
    });

    return ids;
}

function showBulkApproveModal() {
    var ids = getPendingOfferIds();
    var count = ids.length;

    if (count === 0) {
        showNotificationModal('Thong bao', 'Khong co don nao can phe duyet!', 'warning');
        return;
    }

    document.getElementById('bulkApproveCount').textContent = count;
    var modal = new bootstrap.Modal(document.getElementById('bulkApproveModal'));
    modal.show();
}

function bulkApproveLeaveRequests() {
    var approveBtn = event.target.closest('button');
    if (!approveBtn) return;

    approveBtn.disabled = true;
    approveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Dang xu ly...';

    var ids = getPendingOfferIds();

    fetch('/api/leave/approve-all', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({
            action: 'approve',
            leave_request_ids: ids
        })
    })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.error) {
                showNotificationModal('Loi', data.error, 'error');
                approveBtn.disabled = false;
                approveBtn.innerHTML = '<i class="fas fa-check me-2"></i>Phe duyet';
            } else {
                var approveModal = bootstrap.Modal.getInstance(document.getElementById('bulkApproveModal'));
                if (approveModal) approveModal.hide();
                showNotificationModal('Thanh cong', data.message || 'Phe duyet thanh cong!', 'success');
                setTimeout(function() { window.location.reload(); }, 1500);
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            showNotificationModal('Loi', 'Co loi xay ra khi phe duyet hang loat!', 'error');
            approveBtn.disabled = false;
            approveBtn.innerHTML = '<i class="fas fa-check me-2"></i>Phe duyet';
        });
}

function bulkRejectLeaveRequests() {
    var reason = document.getElementById('bulkRejectReason').value.trim();
    var password = document.getElementById('bulkRejectPassword').value;

    if (!reason) {
        showNotificationModal('Thieu thong tin', 'Vui long nhap ly do tu choi!', 'warning');
        return;
    }

    if (!password) {
        showNotificationModal('Thieu thong tin', 'Vui long nhap mat khau de xac nhan!', 'warning');
        return;
    }

    var rejectBtn = event.target.closest('button');
    if (!rejectBtn) return;

    rejectBtn.disabled = true;
    rejectBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Dang xu ly...';

    fetch('/api/leave/approve-all', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({
            action: 'reject',
            reason: reason,
            password: password
        })
    })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.error) {
                showNotificationModal('Loi', data.error, 'error');
                rejectBtn.disabled = false;
                rejectBtn.innerHTML = '<i class="fas fa-times me-2"></i>Tu choi';
            } else {
                var rejectModal = bootstrap.Modal.getInstance(document.getElementById('bulkRejectModal'));
                if (rejectModal) rejectModal.hide();
                showNotificationModal('Thanh cong', data.message || 'Tu choi thanh cong!', 'success');
                setTimeout(function() { window.location.reload(); }, 1500);
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            showNotificationModal('Loi', 'Co loi xay ra khi tu choi hang loat!', 'error');
            rejectBtn.disabled = false;
            rejectBtn.innerHTML = '<i class="fas fa-times me-2"></i>Tu choi';
        });
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    // Add smooth animations
    var rows = document.querySelectorAll('.data-table tbody tr');
    rows.forEach(function(row, index) {
        row.style.opacity = '0';
        row.style.transform = 'translateY(20px)';
        setTimeout(function() {
            row.style.transition = 'all 0.3s ease';
            row.style.opacity = '1';
            row.style.transform = 'translateY(0)';
        }, index * 50);
    });

    // Update bulk action buttons visibility
    updateBulkActionButtonsVisibility();

    // Truncated text click handler
    document.addEventListener('click', function(e) {
        var target = e.target.closest('.text-truncate');
        if (target) { showFullTextFrom(target); }
    });

    document.addEventListener('keydown', function(e) {
        if ((e.key === 'Enter' || e.key === ' ') && e.target.classList && e.target.classList.contains('text-truncate')) {
            e.preventDefault();
            showFullTextFrom(e.target);
        }
    });

    // Download all attachments handler
    document.addEventListener('click', function(e) {
        if (e.target.closest('.download-all-btn')) {
            var btn = e.target.closest('.download-all-btn');
            var requestId = btn.getAttribute('data-request-id');
            var attachmentsJson = btn.getAttribute('data-attachments');

            try {
                var cleanJson = attachmentsJson;
                if (typeof cleanJson === 'string') {
                    cleanJson = cleanJson.replace(/&quot;/g, '"').replace(/&amp;/g, '&');
                }

                var attachments = JSON.parse(cleanJson);
                downloadAllAttachments(requestId, attachments);
            } catch (error) {
                console.error('Error parsing attachments:', error);
                showToast('Co loi khi tai xuong chung tu', 'error');
            }
        }
    });
});

// ========== APPROVE/REJECT SINGLE REQUEST HANDLERS ==========

// Variable to track pending rejection request ID
var pendingRejectRequestId = null;

// Approve leave request with enhanced UX
document.addEventListener('click', function(e) {
    var btn = e.target.closest('.btn-approve');
    if (!btn) return;

    var requestId = btn.getAttribute('data-request-id');
    var originalText = btn.innerHTML;

    Swal.fire({
        title: 'Xác nhận phê duyệt',
        text: 'Bạn có chắc chắn muốn phê duyệt đơn nghỉ phép này?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: 'var(--success-color)',
        cancelButtonColor: 'var(--secondary-color)',
        confirmButtonText: '<i class="fas fa-check me-1"></i> Phê duyệt',
        cancelButtonText: '<i class="fas fa-times me-1"></i> Hủy',
        customClass: {
            popup: 'swal2-popup-custom'
        }
    }).then(function(result) {
        if (result.isConfirmed) {
            setButtonLoading(btn, true);

            var controller = new AbortController();
            if (!window.pendingOperations) window.pendingOperations = [];
            window.pendingOperations.push(controller);

            var csrfToken = document.querySelector('meta[name=csrf-token]');
            csrfToken = csrfToken ? csrfToken.getAttribute('content') : null;
            if (!csrfToken) {
                showToast('Không tìm thấy CSRF token. Vui lòng refresh trang.', 'error');
                setButtonLoading(btn, false);
                return;
            }

            fetch('/leave-request/' + requestId + '/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({
                    action: 'approve',
                    csrf_token: csrfToken
                }),
                signal: controller.signal
            }).then(function(r) {
                return r.text().then(function(text) {
                    if (text.trim().indexOf('<!doctype') === 0 || text.trim().indexOf('<html') === 0) {
                        throw new Error('Server returned HTML instead of JSON');
                    }
                    try {
                        var data = JSON.parse(text);
                        return { response: r, data: data };
                    } catch (e) {
                        throw new Error('Invalid JSON response');
                    }
                });
            }).then(function(obj) {
                if (obj.response.ok) {
                    showToast(obj.data.message || 'Đã phê duyệt đơn nghỉ phép thành công!', 'success');
                    setTimeout(function() { window.location.reload(); }, 1000);
                } else {
                    throw obj.data;
                }
            }).catch(function(error) {
                console.error('Approval error:', error);
                showToast(error.error || error.message || 'Có lỗi xảy ra khi phê duyệt', 'error');
                setButtonLoading(btn, false);
            });
        }
    });
});

// Reject leave request - open modal
document.addEventListener('click', function(e) {
    var btn = e.target.closest('.btn-reject');
    if (!btn) return;

    pendingRejectRequestId = btn.getAttribute('data-request-id');
    var reasonInput = document.getElementById('rejectionReasonInput');
    if (reasonInput) reasonInput.value = '';

    var modal = new bootstrap.Modal(document.getElementById('rejectReasonModal'));
    modal.show();
});

// Confirm rejection handler - bind on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    var confirmRejectBtn = document.getElementById('confirmRejectBtn');
    if (confirmRejectBtn) {
        confirmRejectBtn.addEventListener('click', function() {
            if (!pendingRejectRequestId) return;

            var reason = document.getElementById('rejectionReasonInput').value.trim();

            if (!reason) {
                showToast('Vui lòng nhập lý do từ chối', 'warning');
                return;
            }

            setButtonLoading(confirmRejectBtn, true);

            var csrfToken = document.querySelector('meta[name=csrf-token]');
            csrfToken = csrfToken ? csrfToken.getAttribute('content') : null;
            if (!csrfToken) {
                showToast('Không tìm thấy CSRF token. Vui lòng refresh trang.', 'error');
                return;
            }

            fetch('/leave-request/' + pendingRejectRequestId + '/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({
                    action: 'reject',
                    rejection_reason: reason,
                    csrf_token: csrfToken
                })
            }).then(function(r) {
                if (r.ok) {
                    showToast('Đã từ chối đơn nghỉ phép thành công!', 'success');
                    var modal = bootstrap.Modal.getInstance(document.getElementById('rejectReasonModal'));
                    modal.hide();
                    setTimeout(function() { window.location.reload(); }, 1000);
                } else {
                    showToast('Có lỗi xảy ra khi từ chối', 'error');
                    setButtonLoading(confirmRejectBtn, false);
                }
            }).catch(function() {
                showToast('Có lỗi xảy ra, vui lòng thử lại', 'error');
                setButtonLoading(confirmRejectBtn, false);
            });
        });
    }
});

// Delete leave request handler
document.addEventListener('click', function(e) {
    var btn = e.target.closest('.btn-delete');
    if (!btn) return;

    var requestId = btn.getAttribute('data-request-id');
    var employeeName = btn.getAttribute('data-employee-name');

    Swal.fire({
        title: 'Xác nhận xóa',
        html: '<div class="text-center">' +
            '<i class="fas fa-exclamation-triangle text-warning" style="font-size: 3rem; margin-bottom: 1rem;"></i>' +
            '<p>Bạn có chắc chắn muốn xóa đơn nghỉ phép của <strong>' + employeeName + '</strong>?</p>' +
            '<p class="text-muted small">Hành động này không thể hoàn tác!</p>' +
            '</div>',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: 'var(--danger-color)',
        cancelButtonColor: 'var(--secondary-color)',
        confirmButtonText: '<i class="fas fa-trash me-1"></i> Xóa',
        cancelButtonText: '<i class="fas fa-times me-1"></i> Hủy',
        customClass: {
            popup: 'swal2-popup-custom'
        }
    }).then(function(result) {
        if (result.isConfirmed) {
            setButtonLoading(btn, true);

            fetch('/leave-request/' + requestId + '/delete', {
                method: 'GET'
            }).then(function(r) {
                if (r.ok) {
                    showToast('Đã xóa đơn nghỉ phép thành công!', 'success');
                    setTimeout(function() { window.location.reload(); }, 1000);
                } else {
                    showToast('Có lỗi xảy ra khi xóa', 'error');
                    setButtonLoading(btn, false);
                }
            }).catch(function() {
                showToast('Có lỗi xảy ra, vui lòng thử lại', 'error');
                setButtonLoading(btn, false);
            });
        }
    });
});

// ========== TOKEN STATUS MANAGEMENT (Admin Only) ==========
var tokenStatus = null;
var tokenEventSource = null;
var isAdmin = false;

function checkIfAdmin() {
    var adminCheckEl = document.getElementById('admin-check-data');
    if (adminCheckEl) {
        try {
            isAdmin = JSON.parse(adminCheckEl.textContent.trim());
        } catch (e) {
            isAdmin = false;
        }
    }
    return isAdmin;
}

function updateTokenStatusUI(status) {
    tokenStatus = status;
    var isLicenseWarning = status && typeof status.message === 'string' &&
        (status.message.indexOf('ỨNG DỤNG CHẤM CÔNG') >= 0 || status.message.indexOf('LICENSE') >= 0);

    var banner = document.getElementById('tokenStatusBanner');
    var alert = document.getElementById('tokenStatusAlert');
    var title = document.getElementById('tokenStatusTitle');
    var message = document.getElementById('tokenStatusMessage');
    var icon = document.getElementById('tokenStatusIcon');
    var refreshBtn = document.getElementById('btnRefreshToken');

    if (!banner) {
        console.warn('Token status banner not found');
        return;
    }

    if (isLicenseWarning) {
        try {
            var lastDismiss = localStorage.getItem('licenseBannerDismissedAt');
            var lastTs = lastDismiss ? parseInt(lastDismiss, 10) : 0;
            var now = Date.now();
            if (lastTs && (now - lastTs) < 60000) {
                banner.style.display = 'none';
                return;
            }
        } catch (e) {
            console.warn('Could not read license banner dismiss state:', e);
        }

        banner.style.display = 'block';
        alert.className = 'alert alert-warning alert-dismissible fade show shadow-sm';
        icon.className = 'fas fa-exclamation-circle me-2';
        icon.style.color = '#856404';
        title.textContent = '⚠️ Ứng dụng sắp hết hạn LICENSE';
        title.style.color = '#856404';

        var rawMsg = status.message || '';
        message.innerHTML = rawMsg.replace(/\n/g, '<br>');
        message.style.color = '#856404';

        if (refreshBtn) {
            refreshBtn.style.display = 'none';
        }
        return;
    }

    if (!isAdmin) {
        banner.style.display = 'none';
        return;
    }

    banner.style.display = 'block';

    var isValid = status.valid && status.can_approve;

    if (!isValid) {
        banner.style.display = 'block';
        alert.className = 'alert alert-danger alert-dismissible fade show shadow-sm';
        icon.className = 'fas fa-exclamation-triangle me-2';
        icon.style.color = '#dc3545';
        title.textContent = '⚠️ Token Google API hết hạn';
        title.style.color = '#721c24';
        message.textContent = status.message || 'Token không hợp lệ. Vui lòng refresh token trước khi phê duyệt.';
        message.style.color = '#721c24';
        if (refreshBtn) {
            refreshBtn.style.display = 'inline-flex';
            refreshBtn.className = 'btn btn-sm btn-primary';
        }
        disableApprovalButtons(true);
    } else {
        banner.style.display = 'none';
        disableApprovalButtons(false);
    }
}

function disableApprovalButtons(disable) {
    var approveButtons = document.querySelectorAll('.btn-approve, .approve-btn, [onclick*="approve"]');
    approveButtons.forEach(function(btn) {
        if (disable) {
            btn.disabled = true;
            btn.classList.add('disabled');
            btn.title = 'Token Google API hết hạn. Vui lòng refresh token trước khi phê duyệt.';
        } else {
            btn.disabled = false;
            btn.classList.remove('disabled');
            btn.title = btn.getAttribute('data-original-title') || 'Phê duyệt';
        }
    });
}

function connectTokenStatusSSE() {
    if (tokenEventSource) {
        tokenEventSource.close();
    }

    tokenEventSource = new EventSource('/sse/token-status');

    tokenEventSource.addEventListener('token_status', function(event) {
        try {
            var status = JSON.parse(event.data);
            updateTokenStatusUI(status);
        } catch (error) {
            console.error('Error parsing token status:', error);
        }
    });

    tokenEventSource.onerror = function(error) {
        console.error('SSE connection error:', error);
        setTimeout(connectTokenStatusSSE, 5000);
    };
}

function fetchTokenStatus() {
    checkIfAdmin();

    if (!isAdmin) {
        var banner = document.getElementById('tokenStatusBanner');
        if (banner) {
            banner.style.display = 'none';
        }
        return Promise.resolve();
    }

    var banner = document.getElementById('tokenStatusBanner');
    if (banner && isAdmin) {
        banner.style.display = 'none';
    }

    return fetch('/api/token/status')
        .then(function(response) {
            if (response.ok) {
                return response.json().then(function(status) {
                    console.log('Token status received:', status);
                    updateTokenStatusUI(status);
                });
            } else {
                updateTokenStatusUI({
                    valid: false,
                    can_approve: false,
                    needs_reauth: true,
                    message: 'Không thể kiểm tra trạng thái token. Vui lòng thử lại.'
                });
            }
        })
        .catch(function(error) {
            console.error('Error fetching token status:', error);
            updateTokenStatusUI({
                valid: false,
                can_approve: false,
                needs_reauth: true,
                message: 'Lỗi kết nối khi kiểm tra token. Vui lòng thử lại.'
            });
        });
}

function refreshToken() {
    if (tokenStatus && tokenStatus.valid && tokenStatus.can_approve) {
        showToast('Token vẫn còn hiệu lực, không cần refresh.', 'info');
        return;
    }

    var refreshBtn = document.getElementById('btnRefreshToken');
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Đang mở Chrome...';
    }

    var csrfToken = document.querySelector('meta[name="csrf-token"]');
    csrfToken = csrfToken ? csrfToken.getAttribute('content') : '';

    fetch('/api/token/authorize', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    }).then(function(response) {
        var contentType = response.headers.get('content-type');
        if (contentType && contentType.indexOf('application/json') >= 0) {
            return response.json().then(function(data) {
                return { response: response, data: data };
            });
        } else {
            throw new Error('Server trả về response không hợp lệ. Vui lòng thử lại.');
        }
    }).then(function(obj) {
        if (obj.response.ok && obj.data.success) {
            showToast(obj.data.message || 'Đã mở Chrome để ủy quyền. Vui lòng hoàn tất quá trình ủy quyền trong Chrome.', 'info');
            if (obj.data.auth_url) {
                window.open(obj.data.auth_url, '_blank');
            }
            setTimeout(function() {
                fetchTokenStatus();
            }, 2000);
        } else {
            var errorMsg = obj.data.message || obj.data.error || 'Không thể mở Chrome để ủy quyền. Vui lòng thử lại.';
            showToast(errorMsg, 'error');
        }
    }).catch(function(error) {
        console.error('Error opening Chrome for authorization:', error);
        showToast(error.message || 'Lỗi khi mở Chrome để ủy quyền. Vui lòng thử lại.', 'error');
    }).finally(function() {
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Refresh Token';
        }
    });
}

// Initialize token status management on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    var banner = document.getElementById('tokenStatusBanner');
    if (banner) {
        banner.style.display = 'none';
    }

    checkIfAdmin();

    // Connect SSE for all users (for license warnings)
    connectTokenStatusSSE();

    // Fetch initial license warning status
    fetch('/api/license/warning-status')
        .then(function(resp) {
            if (!resp.ok) return null;
            return resp.json();
        })
        .then(function(data) {
            if (data && data.active && data.payload) {
                updateTokenStatusUI(data.payload);
            }
        })
        .catch(function(e) {
            console.warn('Could not fetch initial license warning status:', e);
        });

    if (isAdmin) {
        console.log('Admin detected, initializing token status management...');
        fetchTokenStatus();

        var refreshBtn = document.getElementById('btnRefreshToken');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', refreshToken);
        }
    }

    // Handle banner close button
    var closeBtn = document.querySelector('#tokenStatusBanner .btn-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            try {
                localStorage.setItem('licenseBannerDismissedAt', Date.now().toString());
            } catch (e) {
                console.warn('Could not store license banner dismiss time:', e);
            }

            setTimeout(function() {
                try {
                    localStorage.removeItem('licenseBannerDismissedAt');
                    if (tokenStatus) {
                        updateTokenStatusUI(tokenStatus);
                    }
                } catch (e) {
                    console.warn('Could not re-show license banner after 60s:', e);
                }
            }, 60000);
        });
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (tokenEventSource) {
        tokenEventSource.close();
    }
});
