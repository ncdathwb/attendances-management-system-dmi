/**
 * Admin Users Management JavaScript
 * ===================================
 * File: static/js/admin-users.js
 * Version: 1.0.0
 * Date: 2026-01-29
 *
 * Xử lý các chức năng quản lý người dùng:
 * - Toggle user active/inactive
 * - Soft delete user
 * - Reset password
 * - Upload users from file
 * - Delete all users
 * - Clear system data (attendances, leave requests, all data)
 *
 * Dependencies:
 * - Bootstrap 5.x
 * - notifications.js (Notify module)
 */

const AdminUsers = (function() {
    'use strict';

    // =========================================
    // Private Variables
    // =========================================
    let currentResetUserId = null;
    let resetPasswordModalInstance = null;

    // =========================================
    // Utility Functions
    // =========================================

    /**
     * Get CSRF token from meta tag
     * @returns {string} CSRF token
     */
    function getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    /**
     * Show notification using Notify module or fallback to alert
     * @param {string} message - Message to display
     * @param {string} type - Type: success, error, warning, info
     * @param {number} duration - Duration in ms (optional)
     */
    function showNotification(message, type = 'success', duration = 5000) {
        // Use Notify if available (from notifications.js)
        if (typeof Notify !== 'undefined') {
            switch(type) {
                case 'success':
                    Notify.success(message);
                    break;
                case 'error':
                    Notify.error(message);
                    break;
                case 'warning':
                    Notify.warning(message);
                    break;
                case 'info':
                    Notify.info(message);
                    break;
                default:
                    Notify.success(message);
            }
        } else {
            // Fallback to alert
            alert(message);
        }
    }

    /**
     * Set button loading state
     * @param {HTMLElement} button - Button element
     * @param {boolean} loading - Loading state
     * @param {string} text - Loading text
     */
    function setButtonLoading(button, loading = true, text = 'Đang xử lý...') {
        if (!button) return;

        if (loading) {
            button.dataset.originalHtml = button.innerHTML;
            button.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>${text}`;
            button.disabled = true;
        } else {
            button.innerHTML = button.dataset.originalHtml || button.innerHTML;
            button.disabled = false;
        }
    }

    // =========================================
    // User Management Functions
    // =========================================

    /**
     * Toggle user active status
     * @param {number} userId - User ID
     * @param {HTMLElement} btn - Button element (optional)
     */
    function toggleUserActive(userId, btn) {
        fetch(`/admin/users/${userId}/toggle_active`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(async res => {
            const contentType = res.headers.get('content-type') || '';
            if (!contentType.includes('application/json')) {
                location.reload();
                return {};
            }
            return res.json();
        })
        .then(data => {
            if (data.success) {
                const row = document.getElementById('user-row-' + userId);
                if (!row) return;

                const btnGroup = row.querySelector('td:last-child .btn-group');

                // Update row class
                if (data.is_active) {
                    row.classList.remove('table-secondary', 'user-inactive');
                } else {
                    row.classList.add('table-secondary', 'user-inactive');
                }

                // Update action buttons
                if (btnGroup) {
                    btnGroup.innerHTML = `
                        <a href="/admin/users/${userId}/edit" class="btn btn-warning btn-sm" title="Chỉnh Sửa">
                            <i class="fas fa-edit"></i>
                        </a>
                        ${data.is_active
                            ? `<button class="btn btn-outline-warning btn-sm toggle-user-btn" title="Khóa tài khoản" data-user-id="${userId}">
                                    <i class="fas fa-user-lock"></i>
                                </button>`
                            : `<button class="btn btn-unlock btn-sm toggle-user-btn" title="Mở khóa tài khoản" data-user-id="${userId}">
                                    <i class="fas fa-user-check"></i>
                                </button>`
                        }
                        <button class="btn btn-outline-danger btn-sm delete-user-btn" title="Xóa người dùng" data-user-id="${userId}" data-user-name="${data.user_name || ''}">
                            <i class="fas fa-trash"></i>
                        </button>
                    `;
                }

                // Update status cell (column 9 - Trạng thái)
                const statusCell = row.querySelector('td:nth-child(9)');
                if (statusCell) {
                    statusCell.innerHTML = `<span class="badge ${data.status_class}">${data.status_label}</span>`;
                }
            } else if (data.error) {
                showNotification(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error toggling user:', error);
            showNotification('Đã xảy ra lỗi khi thay đổi trạng thái', 'error');
        });
    }

    /**
     * Soft delete user
     * @param {number} userId - User ID
     * @param {string} userName - User name for confirmation
     */
    function softDeleteUser(userId, userName) {
        // Use Notify.confirm if available
        if (typeof Notify !== 'undefined' && Notify.confirm) {
            Notify.confirm(
                `Bạn có chắc muốn xóa người dùng "${userName}"?`,
                'Hành động này có thể khôi phục lại trong phần "Người dùng đã xóa".'
            ).then(result => {
                if (result.isConfirmed) {
                    performSoftDelete(userId);
                }
            });
        } else {
            if (confirm(`Bạn có chắc muốn xóa người dùng "${userName}"? Hành động này có thể khôi phục lại.`)) {
                performSoftDelete(userId);
            }
        }
    }

    /**
     * Perform soft delete API call
     * @param {number} userId - User ID
     */
    function performSoftDelete(userId) {
        fetch(`/admin/users/${userId}/soft_delete`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'success');
                // Remove row from table
                const row = document.getElementById('user-row-' + userId);
                if (row) {
                    row.remove();
                }
                // Reload page after 1 second to update stats
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else if (data.error) {
                showNotification(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Đã xảy ra lỗi khi xóa người dùng', 'error');
        });
    }

    // =========================================
    // Reset Password Functions
    // =========================================

    /**
     * Show reset password modal
     * @param {number} userId - User ID
     * @param {string} userName - User name
     */
    function resetUserPassword(userId, userName) {
        currentResetUserId = userId;

        const modalElement = document.getElementById('resetPasswordModal');
        if (!modalElement) {
            console.error('Modal resetPasswordModal not found');
            showNotification('Lỗi: Không tìm thấy modal đặt lại mật khẩu', 'error');
            return;
        }

        if (!resetPasswordModalInstance) {
            resetPasswordModalInstance = new bootstrap.Modal(modalElement);
        }

        // Reset form
        const userNameInput = document.getElementById('resetPasswordUserName');
        const newPasswordInput = document.getElementById('resetPasswordNew');
        const confirmPasswordInput = document.getElementById('resetPasswordConfirm');
        const errorDiv = document.getElementById('resetPasswordError');
        const passwordMatchError = document.getElementById('passwordMatchError');
        const passwordToggleIcon = document.getElementById('passwordToggleIcon');
        const passwordConfirmToggleIcon = document.getElementById('passwordConfirmToggleIcon');
        const confirmBtn = document.getElementById('confirmResetPasswordBtn');

        if (userNameInput) userNameInput.value = userName;
        if (newPasswordInput) {
            newPasswordInput.value = '';
            newPasswordInput.type = 'password';
        }
        if (confirmPasswordInput) {
            confirmPasswordInput.value = '';
            confirmPasswordInput.type = 'password';
        }
        if (errorDiv) errorDiv.classList.add('d-none');
        if (passwordMatchError) passwordMatchError.style.display = 'none';

        // Reset icons
        if (passwordToggleIcon) {
            passwordToggleIcon.classList.remove('fa-eye-slash');
            passwordToggleIcon.classList.add('fa-eye');
        }
        if (passwordConfirmToggleIcon) {
            passwordConfirmToggleIcon.classList.remove('fa-eye-slash');
            passwordConfirmToggleIcon.classList.add('fa-eye');
        }

        // Reset button state
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '<i class="fas fa-key me-1"></i>Đặt Lại Mật Khẩu';
        }

        resetPasswordModalInstance.show();
    }

    /**
     * Confirm reset password
     */
    function confirmResetPassword() {
        const newPassword = document.getElementById('resetPasswordNew')?.value;
        const confirmPassword = document.getElementById('resetPasswordConfirm')?.value;
        const errorDiv = document.getElementById('resetPasswordError');
        const confirmBtn = document.getElementById('confirmResetPasswordBtn');

        // Clear previous errors
        if (errorDiv) {
            errorDiv.classList.add('d-none');
            errorDiv.innerHTML = '';
        }

        // Validation
        if (!newPassword || newPassword.length < 6) {
            if (errorDiv) {
                errorDiv.innerHTML = '<i class="fas fa-exclamation-circle me-1"></i>Mật khẩu phải có ít nhất 6 ký tự!';
                errorDiv.classList.remove('d-none');
            }
            return;
        }

        if (newPassword !== confirmPassword) {
            if (errorDiv) {
                errorDiv.innerHTML = '<i class="fas fa-exclamation-circle me-1"></i>Mật khẩu xác nhận không khớp!';
                errorDiv.classList.remove('d-none');
            }
            return;
        }

        if (!currentResetUserId) {
            if (errorDiv) {
                errorDiv.innerHTML = '<i class="fas fa-exclamation-circle me-1"></i>Lỗi: Không tìm thấy ID người dùng!';
                errorDiv.classList.remove('d-none');
            }
            return;
        }

        // Disable button during request
        setButtonLoading(confirmBtn, true, 'Đang xử lý...');

        fetch(`/admin/users/${currentResetUserId}/reset_password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                password: newPassword
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'success');
                // Close modal
                if (resetPasswordModalInstance) {
                    resetPasswordModalInstance.hide();
                }
                // Reset form
                document.getElementById('resetPasswordNew').value = '';
                document.getElementById('resetPasswordConfirm').value = '';
                currentResetUserId = null;
            } else if (data.error) {
                if (errorDiv) {
                    errorDiv.innerHTML = '<i class="fas fa-exclamation-circle me-1"></i>' + data.error;
                    errorDiv.classList.remove('d-none');
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (errorDiv) {
                errorDiv.innerHTML = '<i class="fas fa-exclamation-circle me-1"></i>Đã xảy ra lỗi khi đặt lại mật khẩu';
                errorDiv.classList.remove('d-none');
            }
        })
        .finally(() => {
            setButtonLoading(confirmBtn, false);
            if (confirmBtn) {
                confirmBtn.innerHTML = '<i class="fas fa-key me-1"></i>Đặt Lại Mật Khẩu';
            }
        });
    }

    /**
     * Toggle password visibility
     * @param {string} inputId - Password input ID
     * @param {string} iconId - Toggle icon ID
     */
    function togglePasswordVisibility(inputId, iconId) {
        const passwordInput = document.getElementById(inputId);
        const icon = document.getElementById(iconId);

        if (passwordInput && icon) {
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                passwordInput.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        }
    }

    /**
     * Validate password match
     */
    function validatePasswordMatch() {
        const newPassword = document.getElementById('resetPasswordNew')?.value;
        const confirmPassword = document.getElementById('resetPasswordConfirm')?.value;
        const errorDiv = document.getElementById('passwordMatchError');

        if (errorDiv) {
            if (confirmPassword && newPassword !== confirmPassword) {
                errorDiv.style.display = 'block';
            } else {
                errorDiv.style.display = 'none';
            }
        }
    }

    // =========================================
    // Upload Users Functions
    // =========================================

    /**
     * Show upload users modal
     */
    function showUploadUsersModal() {
        const modalElement = document.getElementById('uploadUsersModal');
        if (!modalElement) {
            console.error('Modal uploadUsersModal not found');
            return;
        }

        const modal = new bootstrap.Modal(modalElement);

        // Reset form
        const uploadFile = modalElement.querySelector('#uploadFile');
        const defaultPassword = modalElement.querySelector('#defaultPassword');
        const uploadError = modalElement.querySelector('#uploadError');
        const uploadResults = modalElement.querySelector('#uploadResults');
        const uploadResultsContent = modalElement.querySelector('#uploadResultsContent');
        const confirmUploadBtn = modalElement.querySelector('#confirmUploadBtn');

        if (uploadFile) uploadFile.value = '';
        if (defaultPassword) defaultPassword.value = '123456';
        if (uploadError) {
            uploadError.classList.add('d-none');
            uploadError.textContent = '';
        }
        if (uploadResults) uploadResults.classList.add('d-none');
        if (uploadResultsContent) uploadResultsContent.innerHTML = '';
        if (confirmUploadBtn) {
            confirmUploadBtn.disabled = false;
            confirmUploadBtn.innerHTML = '<i class="fas fa-upload me-1"></i>Upload';
        }

        modal.show();
    }

    /**
     * Confirm upload users from file
     */
    function confirmUploadUsers() {
        console.log('confirmUploadUsers function called');

        const modalElement = document.getElementById('uploadUsersModal');
        if (!modalElement) {
            console.error('Modal uploadUsersModal not found');
            alert('Lỗi: Không tìm thấy modal upload. Vui lòng reload trang.');
            return;
        }

        // Find elements
        const fileInput = document.getElementById('uploadFile') || modalElement.querySelector('#uploadFile');
        const defaultPasswordEl = document.getElementById('defaultPassword') || modalElement.querySelector('#defaultPassword');
        let errorDivElement = document.getElementById('uploadError') || modalElement.querySelector('#uploadError');
        const resultsDiv = document.getElementById('uploadResults') || modalElement.querySelector('#uploadResults');
        const resultsContent = document.getElementById('uploadResultsContent') || modalElement.querySelector('#uploadResultsContent');
        const confirmBtn = document.getElementById('confirmUploadBtn') || modalElement.querySelector('#confirmUploadBtn');

        // Create error div if not found
        if (!errorDivElement) {
            const modalBody = modalElement.querySelector('.modal-body');
            if (modalBody) {
                errorDivElement = document.createElement('div');
                errorDivElement.id = 'uploadError';
                errorDivElement.className = 'alert alert-danger d-none';
                errorDivElement.setAttribute('role', 'alert');
                modalBody.appendChild(errorDivElement);
            }
        }

        // Validate file input
        if (!fileInput) {
            alert('Lỗi: Không tìm thấy file input. Vui lòng reload trang.');
            return;
        }
        if (!defaultPasswordEl) {
            alert('Lỗi: Không tìm thấy password input. Vui lòng reload trang.');
            return;
        }

        const defaultPassword = defaultPasswordEl.value.trim();

        // Validate file selected
        if (!fileInput.files || fileInput.files.length === 0) {
            const msg = 'Vui lòng chọn file TXT hoặc Excel';
            if (errorDivElement) {
                errorDivElement.textContent = msg;
                errorDivElement.classList.remove('d-none');
            } else {
                alert(msg);
            }
            return;
        }

        // Validate password
        if (!defaultPassword || defaultPassword.length < 6) {
            const msg = 'Mật khẩu mặc định phải có ít nhất 6 ký tự';
            if (errorDivElement) {
                errorDivElement.textContent = msg;
                errorDivElement.classList.remove('d-none');
            } else {
                alert(msg);
            }
            return;
        }

        console.log('Starting upload process...');

        // Create FormData
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('default_password', defaultPassword);

        // Disable button
        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Đang upload...';
        }
        if (errorDivElement) errorDivElement.classList.add('d-none');
        if (resultsDiv) resultsDiv.classList.add('d-none');

        // Send request
        fetch('/admin/users/upload', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken()
            },
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Display results
                let html = `<div class="alert alert-success">
                    <strong>${data.message}</strong><br>
                    <small>Tổng: ${data.summary.total_lines} dòng |
                    Thành công: ${data.summary.success_count} |
                    Lỗi: ${data.summary.error_count} |
                    Bỏ qua: ${data.summary.skipped_count}</small>
                </div>`;

                // Display errors if any
                if (data.results.errors && data.results.errors.length > 0) {
                    html += '<div class="mt-3"><strong>Chi tiết lỗi:</strong><ul class="list-group mt-2">';
                    data.results.errors.slice(0, 10).forEach(err => {
                        html += `<li class="list-group-item list-group-item-danger">
                            <strong>Dòng ${err.line}:</strong> ${err.error}<br>
                            <small><code>${err.content}</code></small>
                        </li>`;
                    });
                    if (data.results.errors.length > 10) {
                        html += `<li class="list-group-item">... và ${data.results.errors.length - 10} lỗi khác</li>`;
                    }
                    html += '</ul></div>';
                }

                // Display skipped if any
                if (data.results.skipped && data.results.skipped.length > 0) {
                    html += '<div class="mt-3"><strong>Đã bỏ qua (đã tồn tại):</strong><ul class="list-group mt-2">';
                    data.results.skipped.slice(0, 10).forEach(skip => {
                        html += `<li class="list-group-item list-group-item-warning">
                            <strong>Dòng ${skip.line}:</strong> ${skip.employee_id} - ${skip.name}<br>
                            <small>${skip.reason}</small>
                        </li>`;
                    });
                    if (data.results.skipped.length > 10) {
                        html += `<li class="list-group-item">... và ${data.results.skipped.length - 10} nhân viên khác</li>`;
                    }
                    html += '</ul></div>';
                }

                if (resultsContent) resultsContent.innerHTML = html;
                if (resultsDiv) resultsDiv.classList.remove('d-none');

                showNotification(data.message, 'success');

                // Reload page after 3 seconds if successful
                if (data.summary.success_count > 0) {
                    setTimeout(() => {
                        location.reload();
                    }, 3000);
                } else {
                    if (confirmBtn) {
                        confirmBtn.disabled = false;
                        confirmBtn.innerHTML = '<i class="fas fa-upload me-1"></i>Upload';
                    }
                }
            } else if (data.error) {
                if (errorDivElement) {
                    errorDivElement.textContent = data.error;
                    errorDivElement.classList.remove('d-none');
                } else {
                    alert(data.error);
                }
                if (confirmBtn) {
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = '<i class="fas fa-upload me-1"></i>Upload';
                }

                // Display partial results if any
                if (data.partial_results) {
                    if (resultsContent) {
                        resultsContent.innerHTML = `<div class="alert alert-warning">${JSON.stringify(data.partial_results, null, 2)}</div>`;
                    }
                    if (resultsDiv) resultsDiv.classList.remove('d-none');
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            const errorMessage = error.message || 'Đã xảy ra lỗi khi upload file. Vui lòng thử lại.';
            if (errorDivElement) {
                errorDivElement.textContent = errorMessage;
                errorDivElement.classList.remove('d-none');
            } else {
                alert(errorMessage);
            }
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = '<i class="fas fa-upload me-1"></i>Upload';
            }
        });
    }

    // =========================================
    // Delete All Users Functions
    // =========================================

    /**
     * Show delete all users modal
     */
    function showDeleteAllUsersModal() {
        const modal = new bootstrap.Modal(document.getElementById('deleteAllUsersModal'));
        document.getElementById('deleteAllPassword').value = '';
        document.getElementById('deleteAllError').classList.add('d-none');
        document.getElementById('deleteAllError').textContent = '';
        document.getElementById('confirmDeleteAllBtn').disabled = false;
        modal.show();
    }

    /**
     * Confirm delete all users
     */
    function confirmDeleteAllUsers() {
        const password = document.getElementById('deleteAllPassword')?.value.trim();
        const errorDiv = document.getElementById('deleteAllError');
        const confirmBtn = document.getElementById('confirmDeleteAllBtn');

        // Validate password
        if (!password) {
            if (errorDiv) {
                errorDiv.textContent = 'Vui lòng nhập mật khẩu để xác nhận';
                errorDiv.classList.remove('d-none');
            }
            return;
        }

        // Disable button
        setButtonLoading(confirmBtn, true, 'Đang xóa...');

        // Send request
        fetch('/admin/users/delete-all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                password: password
            })
        })
        .then(async res => {
            if (!res.ok) {
                const text = await res.text();
                let errorMessage = 'Đã xảy ra lỗi khi xóa nhân viên';
                try {
                    const json = JSON.parse(text);
                    errorMessage = json.error || errorMessage;
                } catch (e) {
                    errorMessage = `Lỗi ${res.status}: ${res.statusText}`;
                }
                throw new Error(errorMessage);
            }
            return res.json();
        })
        .then(data => {
            if (data.success) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('deleteAllUsersModal'));
                modal.hide();
                showNotification(data.message || `Đã xóa thành công ${data.deleted_count} nhân viên`, 'success');
                setTimeout(() => {
                    location.reload();
                }, 1500);
            } else if (data.error) {
                if (errorDiv) {
                    errorDiv.textContent = data.error;
                    errorDiv.classList.remove('d-none');
                }
                setButtonLoading(confirmBtn, false);
                confirmBtn.innerHTML = '<i class="fas fa-trash-alt me-1"></i>Xác Nhận Xóa';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (errorDiv) {
                errorDiv.textContent = error.message || 'Đã xảy ra lỗi khi xóa nhân viên. Vui lòng thử lại.';
                errorDiv.classList.remove('d-none');
            }
            setButtonLoading(confirmBtn, false);
            confirmBtn.innerHTML = '<i class="fas fa-trash-alt me-1"></i>Xác Nhận Xóa';
        });
    }

    // =========================================
    // Clear Data Functions
    // =========================================

    /**
     * Show clear all data modal
     */
    function showClearAllDataModal() {
        const modalElement = document.getElementById('clearAllDataModal');
        if (!modalElement) {
            console.error('Modal clearAllDataModal not found');
            return;
        }

        const modal = new bootstrap.Modal(modalElement);
        document.getElementById('clearDataPassword').value = '';
        document.getElementById('clearDataPassword').classList.remove('is-invalid');
        document.getElementById('clear-data-password-error').textContent = '';
        modal.show();
    }

    /**
     * Confirm clear all data
     */
    function confirmClearAllData() {
        const password = document.getElementById('clearDataPassword')?.value.trim();
        const passwordInput = document.getElementById('clearDataPassword');
        const passwordError = document.getElementById('clear-data-password-error');
        const confirmBtn = document.getElementById('confirmClearAllDataBtn');

        if (!password) {
            passwordInput?.classList.add('is-invalid');
            if (passwordError) passwordError.textContent = 'Vui lòng nhập mật khẩu';
            return;
        }

        setButtonLoading(confirmBtn, true, 'Đang xóa...');

        fetch('/admin/system/clear-all-data', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ password: password })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('clearAllDataModal'));
                modal.hide();

                let message = data.message;
                if (data.deleted_counts) {
                    message += '\n\nĐã xóa:';
                    message += '\n- ' + data.deleted_counts.attendances + ' bản ghi chấm công';
                    message += '\n- ' + data.deleted_counts.leave_requests + ' đơn nghỉ phép';
                    message += '\n- ' + data.deleted_counts.requests + ' request khác';
                    message += '\n- ' + data.deleted_counts.audit_logs + ' audit logs';
                    message += '\n- ' + data.deleted_counts.password_tokens + ' password tokens';
                    message += '\n- ' + data.deleted_counts.users + ' nhân viên';
                }
                if (data.kept_admin) {
                    message += '\n\nĐã giữ lại: ' + data.kept_admin.name + ' (Mã NV: ' + data.kept_admin.employee_id + ')';
                }

                showNotification(message, 'success');
                setTimeout(() => { location.reload(); }, 3000);
            } else if (data.error) {
                passwordInput?.classList.add('is-invalid');
                if (passwordError) passwordError.textContent = data.error;
                setButtonLoading(confirmBtn, false);
                confirmBtn.innerHTML = '<i class="fas fa-broom me-1"></i>Xóa Toàn Bộ Dữ Liệu';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Đã xảy ra lỗi khi xóa toàn bộ dữ liệu', 'error');
            setButtonLoading(confirmBtn, false);
            confirmBtn.innerHTML = '<i class="fas fa-broom me-1"></i>Xóa Toàn Bộ Dữ Liệu';
        });
    }

    /**
     * Show clear attendances modal
     */
    function showClearAttendancesModal() {
        const modalElement = document.getElementById('clearAttendancesModal');
        if (!modalElement) {
            console.error('Modal clearAttendancesModal not found');
            return;
        }

        const modal = new bootstrap.Modal(modalElement);
        document.getElementById('clearAttendancesPassword').value = '';
        document.getElementById('clearAttendancesPassword').classList.remove('is-invalid');
        document.getElementById('clear-attendances-password-error').textContent = '';
        modal.show();
    }

    /**
     * Confirm clear attendances
     */
    function confirmClearAttendances() {
        const password = document.getElementById('clearAttendancesPassword')?.value.trim();
        const passwordInput = document.getElementById('clearAttendancesPassword');
        const passwordError = document.getElementById('clear-attendances-password-error');
        const confirmBtn = document.getElementById('confirmClearAttendancesBtn');

        if (!password) {
            passwordInput?.classList.add('is-invalid');
            if (passwordError) passwordError.textContent = 'Vui lòng nhập mật khẩu';
            return;
        }

        setButtonLoading(confirmBtn, true, 'Đang xóa...');

        fetch('/admin/system/clear-attendances', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ password: password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'success');
                const modal = bootstrap.Modal.getInstance(document.getElementById('clearAttendancesModal'));
                modal?.hide();
                setTimeout(() => { location.reload(); }, 2000);
            } else if (data.error) {
                passwordInput?.classList.add('is-invalid');
                if (passwordError) passwordError.textContent = data.error;
                setButtonLoading(confirmBtn, false);
                confirmBtn.innerHTML = '<i class="fas fa-calendar-times me-1"></i>Xóa Chấm Công';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Đã xảy ra lỗi khi xóa chấm công', 'error');
            setButtonLoading(confirmBtn, false);
            confirmBtn.innerHTML = '<i class="fas fa-calendar-times me-1"></i>Xóa Chấm Công';
        });
    }

    /**
     * Show clear leave requests modal
     */
    function showClearLeaveRequestsModal() {
        const modalElement = document.getElementById('clearLeaveRequestsModal');
        if (!modalElement) {
            console.error('Modal clearLeaveRequestsModal not found');
            return;
        }

        const modal = new bootstrap.Modal(modalElement);
        document.getElementById('clearLeaveRequestsPassword').value = '';
        document.getElementById('clearLeaveRequestsPassword').classList.remove('is-invalid');
        document.getElementById('clear-leave-requests-password-error').textContent = '';
        modal.show();
    }

    /**
     * Confirm clear leave requests
     */
    function confirmClearLeaveRequests() {
        const password = document.getElementById('clearLeaveRequestsPassword')?.value.trim();
        const passwordInput = document.getElementById('clearLeaveRequestsPassword');
        const passwordError = document.getElementById('clear-leave-requests-password-error');
        const confirmBtn = document.getElementById('confirmClearLeaveRequestsBtn');

        if (!password) {
            passwordInput?.classList.add('is-invalid');
            if (passwordError) passwordError.textContent = 'Vui lòng nhập mật khẩu';
            return;
        }

        setButtonLoading(confirmBtn, true, 'Đang xóa...');

        fetch('/admin/system/clear-leave-requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ password: password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'success');
                const modal = bootstrap.Modal.getInstance(document.getElementById('clearLeaveRequestsModal'));
                modal?.hide();
                setTimeout(() => { location.reload(); }, 2000);
            } else if (data.error) {
                passwordInput?.classList.add('is-invalid');
                if (passwordError) passwordError.textContent = data.error;
                setButtonLoading(confirmBtn, false);
                confirmBtn.innerHTML = '<i class="fas fa-file-alt me-1"></i>Xóa Nghỉ Phép';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Đã xảy ra lỗi khi xóa nghỉ phép', 'error');
            setButtonLoading(confirmBtn, false);
            confirmBtn.innerHTML = '<i class="fas fa-file-alt me-1"></i>Xóa Nghỉ Phép';
        });
    }

    /**
     * Show clear records only modal
     */
    function showClearRecordsOnlyModal() {
        const modalElement = document.getElementById('clearRecordsOnlyModal');
        if (!modalElement) {
            console.error('Modal clearRecordsOnlyModal not found');
            return;
        }

        const modal = new bootstrap.Modal(modalElement);
        document.getElementById('clearRecordsOnlyPassword').value = '';
        document.getElementById('clearRecordsOnlyPassword').classList.remove('is-invalid');
        document.getElementById('clear-records-only-password-error').textContent = '';
        modal.show();
    }

    /**
     * Confirm clear records only
     */
    function confirmClearRecordsOnly() {
        const password = document.getElementById('clearRecordsOnlyPassword')?.value.trim();
        const passwordInput = document.getElementById('clearRecordsOnlyPassword');
        const passwordError = document.getElementById('clear-records-only-password-error');
        const confirmBtn = document.getElementById('confirmClearRecordsOnlyBtn');

        if (!password) {
            passwordInput?.classList.add('is-invalid');
            if (passwordError) passwordError.textContent = 'Vui lòng nhập mật khẩu';
            return;
        }

        setButtonLoading(confirmBtn, true, 'Đang xóa...');

        fetch('/admin/system/clear-records-only', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ password: password })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'success');
                const modal = bootstrap.Modal.getInstance(document.getElementById('clearRecordsOnlyModal'));
                modal?.hide();
                setTimeout(() => { location.reload(); }, 2000);
            } else if (data.error) {
                passwordInput?.classList.add('is-invalid');
                if (passwordError) passwordError.textContent = data.error;
                setButtonLoading(confirmBtn, false);
                confirmBtn.innerHTML = '<i class="fas fa-eraser me-1"></i>Xóa Chấm Công + Nghỉ Phép';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Đã xảy ra lỗi khi xóa dữ liệu', 'error');
            setButtonLoading(confirmBtn, false);
            confirmBtn.innerHTML = '<i class="fas fa-eraser me-1"></i>Xóa Chấm Công + Nghỉ Phép';
        });
    }

    // =========================================
    // Event Handlers Setup
    // =========================================

    /**
     * Setup all event listeners
     */
    function setupEventListeners() {
        // Event delegation for toggle user active
        document.addEventListener('click', function(e) {
            if (e.target.closest('.toggle-user-btn')) {
                const btn = e.target.closest('.toggle-user-btn');
                const userId = parseInt(btn.getAttribute('data-user-id'));
                toggleUserActive(userId, btn);
            }
        });

        // Event delegation for delete user
        document.addEventListener('click', function(e) {
            if (e.target.closest('.delete-user-btn')) {
                const btn = e.target.closest('.delete-user-btn');
                const userId = parseInt(btn.getAttribute('data-user-id'));
                const userName = btn.getAttribute('data-user-name');
                softDeleteUser(userId, userName);
            }
        });

        // Event delegation for reset password
        document.addEventListener('click', function(e) {
            if (e.target.closest('.reset-password-btn')) {
                const btn = e.target.closest('.reset-password-btn');
                const userId = parseInt(btn.getAttribute('data-user-id'));
                const userName = btn.getAttribute('data-user-name');
                resetUserPassword(userId, userName);
            }
        });

        // Toggle password visibility
        const togglePasswordBtn = document.getElementById('togglePasswordVisibility');
        if (togglePasswordBtn) {
            togglePasswordBtn.addEventListener('click', function() {
                togglePasswordVisibility('resetPasswordNew', 'passwordToggleIcon');
            });
        }

        const togglePasswordConfirmBtn = document.getElementById('togglePasswordConfirmVisibility');
        if (togglePasswordConfirmBtn) {
            togglePasswordConfirmBtn.addEventListener('click', function() {
                togglePasswordVisibility('resetPasswordConfirm', 'passwordConfirmToggleIcon');
            });
        }

        // Validate password match
        const resetPasswordConfirmInput = document.getElementById('resetPasswordConfirm');
        if (resetPasswordConfirmInput) {
            resetPasswordConfirmInput.addEventListener('input', validatePasswordMatch);
        }

        const resetPasswordNewInput = document.getElementById('resetPasswordNew');
        if (resetPasswordNewInput) {
            resetPasswordNewInput.addEventListener('input', validatePasswordMatch);
        }

        // Confirm reset password button
        const confirmResetPasswordBtn = document.getElementById('confirmResetPasswordBtn');
        if (confirmResetPasswordBtn) {
            confirmResetPasswordBtn.addEventListener('click', confirmResetPassword);
        }

        // Clear data confirm buttons
        document.getElementById('confirmClearAllDataBtn')?.addEventListener('click', confirmClearAllData);
        document.getElementById('confirmClearAttendancesBtn')?.addEventListener('click', confirmClearAttendances);
        document.getElementById('confirmClearLeaveRequestsBtn')?.addEventListener('click', confirmClearLeaveRequests);
        document.getElementById('confirmClearRecordsOnlyBtn')?.addEventListener('click', confirmClearRecordsOnly);

        // Reset validation on input for clear data modals
        document.getElementById('clearDataPassword')?.addEventListener('input', function() {
            this.classList.remove('is-invalid');
            document.getElementById('clear-data-password-error').textContent = '';
        });
        document.getElementById('clearAttendancesPassword')?.addEventListener('input', function() {
            this.classList.remove('is-invalid');
            document.getElementById('clear-attendances-password-error').textContent = '';
        });
        document.getElementById('clearLeaveRequestsPassword')?.addEventListener('input', function() {
            this.classList.remove('is-invalid');
            document.getElementById('clear-leave-requests-password-error').textContent = '';
        });
        document.getElementById('clearRecordsOnlyPassword')?.addEventListener('input', function() {
            this.classList.remove('is-invalid');
            document.getElementById('clear-records-only-password-error').textContent = '';
        });

        // Enter key to submit for clear data modals
        document.getElementById('clearDataPassword')?.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                document.getElementById('confirmClearAllDataBtn')?.click();
            }
        });
    }

    /**
     * Initialize tooltips
     */
    function initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    /**
     * Initialize module
     */
    function init() {
        console.log('AdminUsers module initializing...');
        setupEventListeners();
        initTooltips();
        console.log('AdminUsers module initialized');
    }

    // =========================================
    // Public API
    // =========================================
    return {
        init: init,
        toggleUserActive: toggleUserActive,
        softDeleteUser: softDeleteUser,
        resetUserPassword: resetUserPassword,
        showUploadUsersModal: showUploadUsersModal,
        confirmUploadUsers: confirmUploadUsers,
        showDeleteAllUsersModal: showDeleteAllUsersModal,
        confirmDeleteAllUsers: confirmDeleteAllUsers,
        showClearAllDataModal: showClearAllDataModal,
        showClearAttendancesModal: showClearAttendancesModal,
        showClearLeaveRequestsModal: showClearLeaveRequestsModal,
        showClearRecordsOnlyModal: showClearRecordsOnlyModal
    };

})();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    AdminUsers.init();
});
