// login.js - file để xử lý các hiệu ứng cho trang đăng nhập/quên mật khẩu

document.addEventListener('DOMContentLoaded', function() {
    // Toggle password visibility
    const togglePassword = document.querySelector('.toggle-password');
    const passwordInput = document.getElementById('password');
    
    if (togglePassword && passwordInput) {
        togglePassword.addEventListener('click', function() {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            // Toggle icon
            const icon = this.querySelector('i');
            if (type === 'text') {
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    }
    
    // Auto focus on username field
    const usernameInput = document.getElementById('username');
    if (usernameInput) {
        usernameInput.focus();
    }
    
    // Form validation
    const loginForm = document.querySelector('.login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value.trim();
            const alert = document.getElementById('login-alert');
            
            // Clear previous alerts
            if (alert) {
                alert.style.visibility = 'hidden';
                alert.textContent = '';
            }
            
            // Basic validation
            if (!username) {
                e.preventDefault();
                showAlert('Vui lòng nhập mã nhân viên!', 'error');
                document.getElementById('username').focus();
                return false;
            }
            
            if (!password) {
                e.preventDefault();
                showAlert('Vui lòng nhập mật khẩu!', 'error');
                document.getElementById('password').focus();
                return false;
            }
            
            // Show loading state
            const submitBtn = document.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Đang đăng nhập...';
            }
        });
    }
    
    // Function to show alerts
    function showAlert(message, type) {
        const alert = document.getElementById('login-alert');
        if (alert) {
            alert.textContent = message;
            alert.style.visibility = 'visible';
            alert.className = `alert alert-${type}`;
            
            // Auto hide after 5 seconds
            setTimeout(() => {
                alert.style.visibility = 'hidden';
            }, 5000);
        }
    }
    
    // Handle Enter key in password field
    if (passwordInput) {
        passwordInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                loginForm.submit();
            }
        });
    }
    
    // Handle Enter key in username field
    if (usernameInput) {
        usernameInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                passwordInput.focus();
            }
        });
    }
}); 