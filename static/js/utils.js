/**
 * Shared JavaScript utilities for DMI Attendance Management System
 * Include this file BEFORE other JS files that need these utilities
 */

// Prevent duplicate loading
if (typeof window.DMIUtils === 'undefined') {
    window.DMIUtils = {
        /**
         * Get CSRF token from meta tag or hidden input
         * @returns {string|null} CSRF token or null if not found
         */
        getCSRFToken: function() {
            const metaToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            const inputToken = document.querySelector('input[name="csrf_token"]')?.value;

            if (!metaToken && !inputToken) {
                console.warn('CSRF token not found');
                return null;
            }

            return metaToken || inputToken;
        },

        /**
         * Get toast icon based on type
         * @param {string} type - Toast type: success, error, warning, info
         * @returns {string} Font Awesome icon class
         */
        getToastIcon: function(type) {
            const icons = {
                success: 'fa-check-circle',
                error: 'fa-times-circle',
                warning: 'fa-exclamation-triangle',
                info: 'fa-info-circle'
            };
            return icons[type] || icons.info;
        },

        /**
         * Show toast notification
         * @param {string} message - Message to display
         * @param {string} type - Type: success, error, warning, info
         * @param {object} options - Optional settings
         */
        showToast: function(message, type = 'success', options = {}) {
            const duration = options.duration || 5000;
            const position = options.position || 'top-right';

            // Try to use Notify module if available
            if (typeof window.Notify !== 'undefined') {
                switch(type) {
                    case 'success': Notify.success(message); break;
                    case 'error': Notify.error(message); break;
                    case 'warning': Notify.warning(message); break;
                    case 'info': Notify.info(message); break;
                    default: Notify.success(message);
                }
                return;
            }

            // Fallback: Create toast element
            let container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:99999;';
                document.body.appendChild(container);
            }

            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.style.cssText = `
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 15px 20px;
                margin-bottom: 10px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
                color: white;
                font-weight: 500;
                animation: slideIn 0.3s ease-out;
            `;
            toast.innerHTML = `
                <i class="fas ${this.getToastIcon(type)}"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.remove()" style="background:none;border:none;color:white;cursor:pointer;margin-left:10px;">
                    <i class="fas fa-times"></i>
                </button>
            `;

            container.appendChild(toast);

            // Auto remove after duration
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.style.animation = 'slideOut 0.3s ease-in';
                    setTimeout(() => toast.remove(), 300);
                }
            }, duration);
        },

        /**
         * Close specific toast
         * @param {HTMLElement} toastElement - Toast element to close
         */
        closeToast: function(toastElement) {
            if (toastElement) {
                toastElement.style.animation = 'slideOut 0.3s ease-in';
                setTimeout(() => toastElement.remove(), 300);
            }
        },

        /**
         * Set button loading state
         * @param {HTMLElement} button - Button element
         * @param {boolean} loading - Loading state
         * @param {string} text - Loading text
         */
        setButtonLoading: function(button, loading = true, text = 'Processing...') {
            if (!button) return;

            if (loading) {
                button.dataset.originalHtml = button.innerHTML;
                button.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>${text}`;
                button.disabled = true;
            } else {
                button.innerHTML = button.dataset.originalHtml || button.innerHTML;
                button.disabled = false;
            }
        },

        /**
         * Format date to Vietnamese format
         * @param {Date|string} date - Date object or string
         * @returns {string} Formatted date string (dd/mm/yyyy)
         */
        formatDate: function(date) {
            if (!date) return '';
            const d = new Date(date);
            if (isNaN(d.getTime())) return '';

            const day = String(d.getDate()).padStart(2, '0');
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const year = d.getFullYear();
            return `${day}/${month}/${year}`;
        },

        /**
         * Format time to HH:MM format
         * @param {Date|string} time - Time object or string
         * @returns {string} Formatted time string (HH:MM)
         */
        formatTime: function(time) {
            if (!time) return '';
            const d = new Date(time);
            if (isNaN(d.getTime())) return time; // Return as-is if already formatted

            const hours = String(d.getHours()).padStart(2, '0');
            const minutes = String(d.getMinutes()).padStart(2, '0');
            return `${hours}:${minutes}`;
        },

        /**
         * Debounce function
         * @param {Function} func - Function to debounce
         * @param {number} wait - Wait time in ms
         * @returns {Function} Debounced function
         */
        debounce: function(func, wait = 300) {
            let timeout;
            return function(...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), wait);
            };
        },

        /**
         * Escape HTML to prevent XSS
         * @param {string} str - String to escape
         * @returns {string} Escaped string
         */
        escapeHtml: function(str) {
            if (!str) return '';
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }
    };

    // Add CSS for toast animations
    if (!document.getElementById('dmi-utils-styles')) {
        const style = document.createElement('style');
        style.id = 'dmi-utils-styles';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }

    // Expose commonly used functions globally for backward compatibility
    // These can be used directly without the DMIUtils prefix
    if (typeof window.getCSRFToken === 'undefined') {
        window.getCSRFToken = DMIUtils.getCSRFToken;
    }
    if (typeof window.showToast === 'undefined') {
        window.showToast = function(message, type, options) {
            DMIUtils.showToast(message, type, options);
        };
    }
}
