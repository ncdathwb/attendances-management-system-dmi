/**
 * =============================================================================
 * DMI ATTENDANCE MANAGEMENT SYSTEM - NOTIFICATION UTILITY
 * =============================================================================
 * Version: 1.0.0
 * Last Updated: 2026-01-29
 *
 * Unified notification system using SweetAlert2.
 * This replaces inconsistent usage of native alert(), Bootstrap alerts,
 * and various SweetAlert2 configurations across the application.
 * =============================================================================
 */

const Notify = (function() {
    'use strict';

    // Default configuration
    const defaults = {
        toast: {
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true,
            didOpen: (toast) => {
                toast.addEventListener('mouseenter', Swal.stopTimer);
                toast.addEventListener('mouseleave', Swal.resumeTimer);
            }
        },
        modal: {
            customClass: {
                popup: 'notify-popup',
                confirmButton: 'btn btn-primary',
                cancelButton: 'btn btn-secondary',
                denyButton: 'btn btn-danger'
            },
            buttonsStyling: false,
            reverseButtons: true
        }
    };

    // Icon configurations matching design system
    const icons = {
        success: {
            icon: 'success',
            iconColor: 'var(--success, #16a34a)'
        },
        error: {
            icon: 'error',
            iconColor: 'var(--danger, #dc2626)'
        },
        warning: {
            icon: 'warning',
            iconColor: 'var(--warning, #d97706)'
        },
        info: {
            icon: 'info',
            iconColor: 'var(--info, #0891b2)'
        },
        question: {
            icon: 'question',
            iconColor: 'var(--primary, #2563eb)'
        }
    };

    /**
     * Show a toast notification
     * @param {string} type - success, error, warning, info
     * @param {string} message - The message to display
     * @param {Object} options - Additional SweetAlert2 options
     */
    function showToast(type, message, options = {}) {
        if (typeof Swal === 'undefined') {
            console.warn('SweetAlert2 not loaded. Falling back to console.');
            console.log(`[${type.toUpperCase()}] ${message}`);
            return Promise.resolve();
        }

        const config = {
            ...defaults.toast,
            ...icons[type] || icons.info,
            title: message,
            ...options
        };

        return Swal.fire(config);
    }

    /**
     * Show a modal dialog
     * @param {string} type - success, error, warning, info, question
     * @param {string} title - Modal title
     * @param {string} text - Modal content
     * @param {Object} options - Additional SweetAlert2 options
     */
    function showModal(type, title, text, options = {}) {
        if (typeof Swal === 'undefined') {
            console.warn('SweetAlert2 not loaded. Falling back to alert.');
            alert(`${title}\n\n${text}`);
            return Promise.resolve({ isConfirmed: true });
        }

        const config = {
            ...defaults.modal,
            ...icons[type] || icons.info,
            title: title,
            text: text,
            ...options
        };

        return Swal.fire(config);
    }

    // Public API
    return {
        /**
         * Success toast notification
         * @param {string} message - Success message
         * @param {Object} options - Additional options
         */
        success: function(message, options = {}) {
            return showToast('success', message, options);
        },

        /**
         * Error toast notification
         * @param {string} message - Error message
         * @param {Object} options - Additional options
         */
        error: function(message, options = {}) {
            return showToast('error', message, options);
        },

        /**
         * Warning toast notification
         * @param {string} message - Warning message
         * @param {Object} options - Additional options
         */
        warning: function(message, options = {}) {
            return showToast('warning', message, options);
        },

        /**
         * Info toast notification
         * @param {string} message - Info message
         * @param {Object} options - Additional options
         */
        info: function(message, options = {}) {
            return showToast('info', message, options);
        },

        /**
         * Success modal dialog
         * @param {string} title - Modal title
         * @param {string} text - Modal content
         * @param {Object} options - Additional options
         */
        successModal: function(title, text = '', options = {}) {
            return showModal('success', title, text, {
                confirmButtonText: 'OK',
                ...options
            });
        },

        /**
         * Error modal dialog
         * @param {string} title - Modal title
         * @param {string} text - Modal content
         * @param {Object} options - Additional options
         */
        errorModal: function(title, text = '', options = {}) {
            return showModal('error', title, text, {
                confirmButtonText: 'OK',
                ...options
            });
        },

        /**
         * Warning modal dialog
         * @param {string} title - Modal title
         * @param {string} text - Modal content
         * @param {Object} options - Additional options
         */
        warningModal: function(title, text = '', options = {}) {
            return showModal('warning', title, text, {
                confirmButtonText: 'OK',
                ...options
            });
        },

        /**
         * Info modal dialog
         * @param {string} title - Modal title
         * @param {string} text - Modal content
         * @param {Object} options - Additional options
         */
        infoModal: function(title, text = '', options = {}) {
            return showModal('info', title, text, {
                confirmButtonText: 'OK',
                ...options
            });
        },

        /**
         * Confirmation dialog
         * @param {string} title - Confirmation title
         * @param {string} text - Confirmation message
         * @param {Object} options - Additional options
         * @returns {Promise} - Resolves to { isConfirmed, isDenied, isDismissed }
         */
        confirm: function(title, text = '', options = {}) {
            if (typeof Swal === 'undefined') {
                const result = confirm(`${title}\n\n${text}`);
                return Promise.resolve({ isConfirmed: result, isDenied: false, isDismissed: !result });
            }

            return Swal.fire({
                ...defaults.modal,
                ...icons.question,
                title: title,
                text: text,
                showCancelButton: true,
                confirmButtonText: options.confirmText || 'Xác nhận',
                cancelButtonText: options.cancelText || 'Hủy',
                ...options
            });
        },

        /**
         * Delete confirmation dialog (with danger styling)
         * @param {string} title - Confirmation title
         * @param {string} text - Confirmation message
         * @param {Object} options - Additional options
         */
        confirmDelete: function(title = 'Xác nhận xóa?', text = 'Dữ liệu sẽ không thể khôi phục!', options = {}) {
            if (typeof Swal === 'undefined') {
                const result = confirm(`${title}\n\n${text}`);
                return Promise.resolve({ isConfirmed: result });
            }

            return Swal.fire({
                ...defaults.modal,
                ...icons.warning,
                title: title,
                text: text,
                showCancelButton: true,
                confirmButtonText: options.confirmText || 'Xóa',
                cancelButtonText: options.cancelText || 'Hủy',
                customClass: {
                    ...defaults.modal.customClass,
                    confirmButton: 'btn btn-danger'
                },
                ...options
            });
        },

        /**
         * Show loading indicator
         * @param {string} title - Loading message
         * @param {string} text - Additional text
         */
        loading: function(title = 'Đang xử lý...', text = '') {
            if (typeof Swal === 'undefined') {
                console.log(`[LOADING] ${title} ${text}`);
                return { close: () => {} };
            }

            Swal.fire({
                title: title,
                text: text,
                allowOutsideClick: false,
                allowEscapeKey: false,
                showConfirmButton: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });

            return {
                close: () => Swal.close(),
                update: (newTitle, newText) => {
                    Swal.update({ title: newTitle, text: newText });
                }
            };
        },

        /**
         * Close any open notification/modal
         */
        close: function() {
            if (typeof Swal !== 'undefined') {
                Swal.close();
            }
        },

        /**
         * Input dialog
         * @param {string} title - Dialog title
         * @param {Object} options - Input options
         */
        input: function(title, options = {}) {
            if (typeof Swal === 'undefined') {
                const result = prompt(title, options.inputValue || '');
                return Promise.resolve({ isConfirmed: result !== null, value: result });
            }

            return Swal.fire({
                ...defaults.modal,
                title: title,
                input: options.inputType || 'text',
                inputValue: options.inputValue || '',
                inputPlaceholder: options.placeholder || '',
                inputAttributes: options.inputAttributes || {},
                showCancelButton: true,
                confirmButtonText: options.confirmText || 'OK',
                cancelButtonText: options.cancelText || 'Hủy',
                inputValidator: options.validator || null,
                ...options
            });
        },

        /**
         * Show HTML content in modal
         * @param {string} title - Modal title
         * @param {string} html - HTML content
         * @param {Object} options - Additional options
         */
        html: function(title, html, options = {}) {
            if (typeof Swal === 'undefined') {
                alert(`${title}\n\nHTML content cannot be displayed.`);
                return Promise.resolve({ isConfirmed: true });
            }

            return Swal.fire({
                ...defaults.modal,
                title: title,
                html: html,
                confirmButtonText: 'OK',
                ...options
            });
        },

        /**
         * Progress dialog with steps
         * @param {Array} steps - Array of step objects { title, text }
         * @param {Function} onStep - Callback for each step
         */
        progress: async function(steps, onStep) {
            if (typeof Swal === 'undefined') {
                console.log('[PROGRESS] SweetAlert2 not available');
                return;
            }

            const queue = steps.map((step, index) => ({
                ...defaults.modal,
                title: step.title,
                text: step.text,
                currentProgressStep: index,
                progressSteps: steps.map((_, i) => (i + 1).toString()),
                showConfirmButton: false,
                allowOutsideClick: false
            }));

            for (let i = 0; i < queue.length; i++) {
                Swal.fire(queue[i]);
                Swal.showLoading();

                if (onStep) {
                    await onStep(i, steps[i]);
                }
            }

            Swal.close();
        },

        /**
         * Custom notification with full control
         * @param {Object} config - Full SweetAlert2 configuration
         */
        custom: function(config) {
            if (typeof Swal === 'undefined') {
                console.warn('SweetAlert2 not loaded');
                return Promise.resolve();
            }

            return Swal.fire({
                ...defaults.modal,
                ...config
            });
        }
    };
})();

// Make Notify globally available
if (typeof window !== 'undefined') {
    window.Notify = Notify;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Notify;
}
