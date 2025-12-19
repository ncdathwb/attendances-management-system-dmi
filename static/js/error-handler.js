/**
 * Enhanced error handling system for frontend
 */
class ErrorHandler {
    constructor() {
        this.errorTypes = {
            400: { type: 'BadRequest', message: 'Dữ liệu không hợp lệ', action: 'show' },
            401: { type: 'Unauthorized', message: 'Phiên đăng nhập đã hết hạn', action: 'redirect' },
            403: { type: 'Forbidden', message: 'Bạn không có quyền thực hiện hành động này', action: 'show' },
            404: { type: 'NotFound', message: 'Không tìm thấy dữ liệu', action: 'show' },
            429: { type: 'RateLimited', message: 'Quá nhiều yêu cầu. Vui lòng thử lại sau', action: 'show' },
            500: { type: 'ServerError', message: 'Lỗi server. Vui lòng thử lại sau', action: 'show' },
            502: { type: 'BadGateway', message: 'Lỗi kết nối server', action: 'show' },
            503: { type: 'ServiceUnavailable', message: 'Dịch vụ tạm thời không khả dụng', action: 'show' }
        };
        
        this.retryConfig = {
            maxRetries: 3,
            baseDelay: 1000,
            maxDelay: 10000
        };
        
        this.setupGlobalErrorHandlers();
    }
    
    setupGlobalErrorHandlers() {
        // Global unhandled promise rejection
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            this.handleError(event.reason, 'UnhandledPromiseRejection');
            event.preventDefault();
        });
        
        // Global JavaScript errors
        window.addEventListener('error', (event) => {
            console.error('Global JavaScript error:', event.error);
            this.handleError(event.error, 'JavaScriptError');
        });
        
        // Network errors
        window.addEventListener('online', () => {
            this.showToast('Kết nối mạng đã được khôi phục', 'success');
        });
        
        window.addEventListener('offline', () => {
            this.showToast('Mất kết nối mạng. Kiểm tra kết nối của bạn', 'warning');
        });
    }
    
    async handleApiError(response, context = '') {
        const status = response.status;
        const errorInfo = this.errorTypes[status] || {
            type: 'UnknownError',
            message: `Lỗi không xác định (${status})`,
            action: 'show'
        };
        
        console.error(`API Error ${status}:`, {
            context,
            errorType: errorInfo.type,
            url: response.url,
            statusText: response.statusText
        });
        
        switch (errorInfo.action) {
            case 'redirect':
                this.handleRedirect(errorInfo.message);
                break;
            case 'show':
                this.showError(errorInfo.message, errorInfo.type);
                break;
            default:
                this.showError(errorInfo.message, errorInfo.type);
        }
        
        return errorInfo;
    }
    
    handleError(error, context = '') {
        console.error('Error handled:', {
            error: error.message || error,
            context,
            stack: error.stack
        });
        
        if (error instanceof TypeError) {
            this.showError('Lỗi dữ liệu không hợp lệ', 'TypeError');
        } else if (error instanceof ReferenceError) {
            this.showError('Lỗi tham chiếu dữ liệu', 'ReferenceError');
        } else if (error instanceof SyntaxError) {
            this.showError('Lỗi cú pháp trong dữ liệu', 'SyntaxError');
        } else {
            this.showError('Đã xảy ra lỗi không xác định', 'UnknownError');
        }
    }
    
    async retryOperation(operation, context = '') {
        let lastError;
        
        for (let attempt = 1; attempt <= this.retryConfig.maxRetries; attempt++) {
            try {
                return await operation();
            } catch (error) {
                lastError = error;
                
                if (attempt === this.retryConfig.maxRetries) {
                    console.error(`Operation failed after ${this.retryConfig.maxRetries} attempts:`, {
                        context,
                        error: error.message || error,
                        attempts: attempt
                    });
                    break;
                }
                
                const delay = Math.min(
                    this.retryConfig.baseDelay * Math.pow(2, attempt - 1),
                    this.retryConfig.maxDelay
                );
                
                console.warn(`Operation failed, retrying in ${delay}ms (attempt ${attempt}/${this.retryConfig.maxRetries}):`, {
                    context,
                    error: error.message || error
                });
                
                await this.delay(delay);
            }
        }
        
        throw lastError;
    }
    
    handleRedirect(message) {
        this.showToast(message, 'warning');
        setTimeout(() => {
            window.location.href = '/login';
        }, 2000);
    }
    
    showError(message, type = 'error') {
        this.showToast(message, 'error');
        
        // Log error for monitoring
        this.logError(message, type);
    }
    
    showToast(message, type = 'success') {
        if (typeof Swal !== 'undefined') {
            const Toast = Swal.mixin({
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: type === 'error' ? 5000 : 3000,
                timerProgressBar: true,
                didOpen: (toast) => {
                    toast.addEventListener('mouseenter', Swal.stopTimer);
                    toast.addEventListener('mouseleave', Swal.resumeTimer);
                }
            });
            
            const icons = {
                success: 'success',
                error: 'error',
                warning: 'warning',
                info: 'info'
            };
            
            Toast.fire({
                icon: icons[type] || 'info',
                title: message
            });
        } else {
            // Fallback to native alert
            // console.log(`${type.toUpperCase()}: ${message}`);
            alert(message);
        }
    }
    
    logError(message, type) {
        // Send error to server for logging
        try {
            fetch('/api/log-error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    message,
                    type,
                    url: window.location.href,
                    userAgent: navigator.userAgent,
                    timestamp: new Date().toISOString()
                })
            }).catch(err => {
                console.error('Failed to log error to server:', err);
            });
        } catch (err) {
            console.error('Failed to send error log:', err);
        }
    }
    
    getCSRFToken() {
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        const inputToken = document.querySelector('input[name="csrf_token"]');
        return metaToken ? metaToken.getAttribute('content') : 
               inputToken ? inputToken.value : '';
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // Utility method for safe JSON parsing
    safeJsonParse(jsonString, fallback = null) {
        try {
            return JSON.parse(jsonString);
        } catch (error) {
            console.error('JSON parse error:', error);
            return fallback;
        }
    }
    
    // Utility method for safe property access
    safeGet(obj, path, fallback = null) {
        try {
            return path.split('.').reduce((current, key) => {
                return current && current[key] !== undefined ? current[key] : fallback;
            }, obj);
        } catch (error) {
            console.error('Safe property access error:', error);
            return fallback;
        }
    }
}

// Global error handler instance
window.errorHandler = new ErrorHandler();

// Enhanced fetch wrapper with error handling
window.safeFetch = async function(url, options = {}) {
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            await window.errorHandler.handleApiError(response, url);
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return response;
    } catch (error) {
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            window.errorHandler.handleError(new Error('Lỗi kết nối mạng. Kiểm tra kết nối của bạn'), 'NetworkError');
        } else {
            window.errorHandler.handleError(error, 'FetchError');
        }
        throw error;
    }
};

// Enhanced API call function
window.apiCall = async function(url, options = {}) {
    return window.errorHandler.retryOperation(async () => {
        return await window.safeFetch(url, options);
    }, url);
};
