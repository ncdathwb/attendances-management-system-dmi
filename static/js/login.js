document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.querySelector('.login-form');
    const submitButton = loginForm.querySelector('button[type="submit"]');
    const inputs = loginForm.querySelectorAll('input');
    const rememberCheckbox = document.getElementById('remember');

    // Add floating label effect
    inputs.forEach(input => {
        if (input.type !== 'checkbox') {
            const label = input.previousElementSibling;
            
            // Set initial state
            if (input.value) {
                label.classList.add('active');
            }

            // Focus effect
            input.addEventListener('focus', () => {
                label.classList.add('active');
                input.parentElement.classList.add('focused');
            });

            // Blur effect
            input.addEventListener('blur', () => {
                if (!input.value) {
                    label.classList.remove('active');
                }
                input.parentElement.classList.remove('focused');
            });

            // Input effect
            input.addEventListener('input', () => {
                if (input.value) {
                    label.classList.add('active');
                } else {
                    label.classList.remove('active');
                }
            });
        }
    });

    // Form submission handling
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate form
        let isValid = true;
        inputs.forEach(input => {
            if (input.required && !input.value.trim()) {
                isValid = false;
                showError(input, 'Vui lòng điền thông tin này');
            } else if (input.id === 'username' && input.value) {
                if (!/^\d+$/.test(input.value)) {
                    isValid = false;
                    showError(input, 'Mã nhân viên phải là số');
                }
            }
        });

        if (!isValid) {
            return;
        }
        
        // Lấy thông tin gửi đi
        const username = loginForm.querySelector('#username').value;
        const password = loginForm.querySelector('#password').value;
        const remember = rememberCheckbox ? rememberCheckbox.checked : false;
        console.log('Thông tin gửi đi:', { username, password, remember });
        
        // Add loading state
        submitButton.classList.add('loading');
        submitButton.disabled = true;
        
        // Simulate form submission
        setTimeout(() => {
            this.submit();
        }, 800);
    });

    // Password show/hide functionality
    const passwordInput = document.getElementById('password');
    const toggleBtn = document.querySelector('.toggle-password');
    
    if (toggleBtn && passwordInput) {
        let visible = false;
        
        function updateEye() {
            if (visible) {
                toggleBtn.innerHTML = '<i class="fa fa-eye-slash"></i>';
                toggleBtn.title = "Ẩn mật khẩu";
            } else {
                toggleBtn.innerHTML = '<i class="fa fa-eye"></i>';
                toggleBtn.title = "Hiện mật khẩu";
            }
        }
        
        toggleBtn.addEventListener('click', function() {
            visible = !visible;
            passwordInput.type = visible ? 'text' : 'password';
            updateEye();
        });
        
        updateEye(); // Initialize state
    }

    // Remember me functionality
    if (rememberCheckbox) {
        rememberCheckbox.addEventListener('change', function() {
            const inputs = loginForm.querySelectorAll('input[type="text"], input[type="password"]');
            inputs.forEach(input => {
                if (this.checked) {
                    input.setAttribute('data-remember', 'true');
                } else {
                    input.removeAttribute('data-remember');
                }
            });

            // Add animation
            const checkmark = this.nextElementSibling;
            checkmark.style.transform = 'scale(1.1)';
            setTimeout(() => {
                checkmark.style.transform = 'scale(1)';
            }, 200);
        });
    }

    // Add input validation
    inputs.forEach(input => {
        if (input.type !== 'checkbox') {
            input.addEventListener('input', function() {
                validateInput(this);
            });

            input.addEventListener('blur', function() {
                validateInput(this);
            });
        }
    });

    function validateInput(input) {
        const value = input.value.trim();
        const formGroup = input.closest('.form-group');
        
        if (input.required && !value) {
            formGroup.classList.add('error');
            showError(input, 'Vui lòng điền thông tin này');
        } else if (input.id === 'username' && value) {
            if (!/^\d+$/.test(value)) {
                formGroup.classList.add('error');
                showError(input, 'Mã nhân viên phải là số');
            } else {
                formGroup.classList.remove('error');
                hideError(input);
            }
        } else {
            formGroup.classList.remove('error');
            hideError(input);
        }
    }

    function showError(input, message) {
        let errorDiv = input.parentNode.querySelector('.error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            input.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
        
        // Add shake animation
        input.parentNode.classList.add('shake');
        setTimeout(() => {
            input.parentNode.classList.remove('shake');
        }, 500);
    }

    function hideError(input) {
        const errorDiv = input.parentNode.querySelector('.error-message');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    // Add ripple effect to button
    submitButton.addEventListener('click', function(e) {
        const rect = this.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const ripple = document.createElement('span');
        ripple.className = 'ripple';
        ripple.style.left = `${x}px`;
        ripple.style.top = `${y}px`;
        
        this.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
}); 