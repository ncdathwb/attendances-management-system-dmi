"""
Enhanced security utilities for the attendance management system
Merged: security.py + security_enhanced.py
"""
import hashlib
import hmac
import secrets
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, time
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import re
from collections import defaultdict
from flask import request, current_app, session
import time as time_module
import importlib
from functools import wraps

# Optional dependency: bcrypt. Avoid static import to keep type checkers happy.
try:
    bcrypt = importlib.import_module("bcrypt")  # type: ignore[reportMissingImports]
except Exception:
    bcrypt = None  # type: ignore[assignment]
import jwt

# Import security logger for brute force protection
try:
    from utils.logger import security_logger
except ImportError:
    security_logger = None

logger = logging.getLogger(__name__)

class SecurityManager:
    """Enhanced security manager for the application

    Includes:
    - Password hashing/verification (bcrypt)
    - Data encryption/decryption (Fernet)
    - JWT token generation/verification
    - Input sanitization
    - Brute force protection
    - Session security validation
    - Suspicious activity detection
    """

    def __init__(self, app=None):
        self.app = app
        self.cipher = None
        self.secret_key = None
        self.signature_key = None

        # Brute force protection (in production, use Redis)
        self.failed_attempts = defaultdict(list)
        self.account_lockouts = {}
        self.session_tracking = {}

        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security manager with Flask app"""
        self.app = app
        self.secret_key = app.config.get('SECRET_KEY')
        self.signature_key = app.config.get('SIGNATURE_SECRET_KEY')
        
        # Initialize encryption
        if self.signature_key:
            self.cipher = Fernet(self.signature_key)
        else:
            self.cipher = None
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        if bcrypt is not None:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        # Fallback to werkzeug if bcrypt not available
        from werkzeug.security import generate_password_hash
        return generate_password_hash(password, method='pbkdf2:sha256')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        if bcrypt is not None:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        # Fallback to werkzeug if bcrypt not available
        from werkzeug.security import check_password_hash
        return check_password_hash(hashed, password)
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not self.cipher:
            raise ValueError("Encryption not initialized")
        
        try:
            encrypted = self.cipher.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not self.cipher:
            raise ValueError("Encryption not initialized")
        
        try:
            # Normalize and fix base64 padding before decode to avoid "Incorrect padding"
            normalized = encrypted_data.strip()
            normalized = normalized.replace(' ', '+')
            padding_needed = (-len(normalized)) % 4
            if padding_needed:
                normalized += '=' * padding_needed

            try:
                encrypted_bytes = base64.urlsafe_b64decode(normalized.encode('utf-8'))
            except Exception:
                encrypted_bytes = base64.b64decode(normalized.encode('utf-8'))
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            if isinstance(e, InvalidToken):
                # Silent for InvalidToken to avoid noisy logs; logic unchanged (still raise to caller)
                raise
            else:
                logger.error(f"Decryption error: {type(e).__name__}: {repr(e)}")
                raise
    
    def generate_jwt_token(self, payload: Dict[str, Any], expires_in: int = 3600) -> str:
        """Generate JWT token"""
        payload.update({
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow(),
            'iss': 'attendance-system'
        })
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def sanitize_input(self, text: str, max_length: int = 1000) -> str:
        """Enhanced input sanitization"""
        if not isinstance(text, str):
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove script content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove SQL injection patterns
        sql_patterns = [
            r'\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b',
            r'--', r'/\*.*?\*/', r'xp_', r'sp_'
        ]
        for pattern in sql_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove command injection characters
        text = re.sub(r'[;&|`$]', '', text)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()
    
    def validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token"""
        if not token:
            return False
        
        # Additional validation beyond Flask-WTF
        if len(token) < 32:
            return False
        
        # Check if token contains only valid characters
        if not re.match(r'^[A-Za-z0-9+/=]+$', token):
            return False
        
        return True
    
    def rate_limit_key(self, client_ip: str, endpoint: str) -> str:
        """Generate rate limiting key"""
        return f"rate_limit:{client_ip}:{endpoint}"
    
    def log_security_event(self, event_type: str, details: Dict[str, Any], user_id: Optional[int] = None):
        """Log security events"""
        security_data = {
            'event_type': event_type,
            'details': details,
            'user_id': user_id,
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.warning(f"Security event: {event_type}", extra=security_data)
    
    def check_password_strength(self, password: str) -> Dict[str, Any]:
        """Check password strength"""
        score = 0
        feedback = []
        
        if len(password) < 8:
            feedback.append("Password must be at least 8 characters long")
        else:
            score += 1
        
        if re.search(r'[a-z]', password):
            score += 1
        else:
            feedback.append("Include lowercase letters")
        
        if re.search(r'[A-Z]', password):
            score += 1
        else:
            feedback.append("Include uppercase letters")
        
        if re.search(r'\d', password):
            score += 1
        else:
            feedback.append("Include numbers")
        
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
        else:
            feedback.append("Include special characters")
        
        # Check for common patterns
        common_patterns = [
            'password', '123456', 'qwerty', 'admin', 'user',
            'abc123', 'password123', 'admin123'
        ]
        
        if password.lower() in common_patterns:
            score = 0
            feedback.append("Password is too common")
        
        strength_level = "weak"
        if score >= 4:
            strength_level = "strong"
        elif score >= 3:
            strength_level = "medium"
        
        return {
            'score': score,
            'strength': strength_level,
            'feedback': feedback,
            'is_acceptable': score >= 3
        }
    
    def generate_secure_filename(self, original_filename: str) -> str:
        """Generate secure filename"""
        if not original_filename:
            return ""
        
        # Remove path traversal
        filename = original_filename.split('/')[-1].split('\\')[-1]
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # Add timestamp for uniqueness
        timestamp = str(int(time_module.time()))
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        
        if ext:
            return f"{name}_{timestamp}.{ext}"
        else:
            return f"{name}_{timestamp}"
    
    def validate_file_upload(self, file, allowed_extensions: list, max_size_mb: int) -> Dict[str, Any]:
        """Validate file upload security"""
        result = {
            'valid': False,
            'error': None,
            'filename': None
        }
        
        if not file:
            result['error'] = "No file provided"
            return result
        
        # Check file size
        max_size_bytes = max_size_mb * 1024 * 1024
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > max_size_bytes:
            result['error'] = f"File too large (max {max_size_mb}MB)"
            return result
        
        # Check file extension
        filename = file.filename
        if not filename or '.' not in filename:
            result['error'] = "Invalid file format"
            return result
        
        extension = filename.rsplit('.', 1)[1].lower()
        if extension not in allowed_extensions:
            result['error'] = f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            return result
        
        # Generate secure filename
        secure_filename = self.generate_secure_filename(filename)
        
        result['valid'] = True
        result['filename'] = secure_filename
        return result
    
    def create_audit_signature(self, data: Dict[str, Any]) -> str:
        """Create audit signature for data integrity"""
        # Sort keys for consistent hashing
        sorted_data = dict(sorted(data.items()))
        
        # Create signature
        message = str(sorted_data).encode('utf-8')
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message,
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def verify_audit_signature(self, data: Dict[str, Any], signature: str) -> bool:
        """Verify audit signature"""
        expected_signature = self.create_audit_signature(data)
        return hmac.compare_digest(signature, expected_signature)

    # ============ Brute Force Protection Methods ============

    def check_login_attempts(self, employee_id, max_attempts=5, lockout_minutes=15):
        """
        Kiểm tra số lần đăng nhập thất bại và lockout account nếu cần
        """
        now = datetime.now()

        # Clean up old attempts
        cutoff_time = now - timedelta(minutes=lockout_minutes)
        self.failed_attempts[employee_id] = [
            attempt_time for attempt_time in self.failed_attempts[employee_id]
            if attempt_time > cutoff_time
        ]

        # Check if account is currently locked out
        if employee_id in self.account_lockouts:
            lockout_until = self.account_lockouts[employee_id]
            if now < lockout_until:
                remaining_time = (lockout_until - now).total_seconds() / 60
                if security_logger:
                    security_logger.security_event(
                        event_type='AccountLockoutCheck',
                        details=f'Account locked for {employee_id}, {remaining_time:.1f} minutes remaining',
                        employee_id=employee_id,
                        lockout_remaining_minutes=remaining_time
                    )
                return False, f"Tài khoản tạm khóa do đăng nhập sai quá nhiều lần. Vui lòng thử lại sau {remaining_time:.0f} phút."

        # Check if too many failed attempts
        if len(self.failed_attempts[employee_id]) >= max_attempts:
            self.account_lockouts[employee_id] = now + timedelta(minutes=lockout_minutes)
            if security_logger:
                security_logger.security_event(
                    event_type='AccountLocked',
                    details=f'Account locked due to {max_attempts} failed attempts',
                    employee_id=employee_id,
                    failed_attempts=len(self.failed_attempts[employee_id])
                )
            return False, f"Tài khoản tạm khóa do đăng nhập sai quá {max_attempts} lần. Vui lòng thử lại sau {lockout_minutes} phút."

        return True, None

    def record_failed_login(self, employee_id, ip_address=None):
        """Ghi lại lần đăng nhập thất bại"""
        now = datetime.now()
        self.failed_attempts[employee_id].append(now)

        if security_logger:
            security_logger.security_event(
                event_type='FailedLoginAttempt',
                details=f'Failed login attempt for employee {employee_id}',
                employee_id=employee_id,
                ip_address=ip_address or request.remote_addr,
                attempt_count=len(self.failed_attempts[employee_id])
            )

    def clear_failed_attempts(self, employee_id):
        """Xóa lịch sử đăng nhập thất bại khi đăng nhập thành công"""
        if employee_id in self.failed_attempts:
            del self.failed_attempts[employee_id]

        if employee_id in self.account_lockouts:
            del self.account_lockouts[employee_id]

        if security_logger:
            security_logger.security_event(
                event_type='SuccessfulLogin',
                details=f'Successful login for employee {employee_id}',
                employee_id=employee_id,
                ip_address=request.remote_addr
            )

    def validate_session_security(self):
        """Kiểm tra bảo mật session"""
        if not session:
            return False, "Session không hợp lệ"

        # Check IP address consistency
        current_ip = request.remote_addr
        session_ip = session.get('ip_address')

        if not session_ip:
            session['ip_address'] = current_ip
            if security_logger:
                security_logger.security_event(
                    event_type='SessionIPInitialized',
                    details=f'Initialized session IP for user {session.get("user_id")}',
                    user_id=session.get('user_id'),
                    ip_address=current_ip
                )
        elif session_ip != current_ip:
            if security_logger:
                security_logger.security_event(
                    event_type='SessionHijackDetected',
                    details=f'IP address changed during session',
                    user_id=session.get('user_id'),
                    original_ip=session_ip,
                    current_ip=current_ip
                )
            return False, "Phát hiện thay đổi địa chỉ IP. Vui lòng đăng nhập lại."

        # Check User-Agent consistency
        current_ua = request.headers.get('User-Agent', '')
        session_ua = session.get('user_agent')

        if not session_ua:
            session['user_agent'] = current_ua
        elif session_ua != current_ua:
            if security_logger:
                security_logger.security_event(
                    event_type='UserAgentChanged',
                    details=f'User-Agent changed during session',
                    user_id=session.get('user_id'),
                    original_ua=session_ua,
                    current_ua=current_ua
                )
            # Warning only, not blocking

        return True, None

    def check_suspicious_activity(self, user_id, action, **kwargs):
        """Kiểm tra hoạt động đáng ngờ"""
        now = datetime.now()

        # Track user actions
        if user_id not in self.session_tracking:
            self.session_tracking[user_id] = {
                'actions': [],
                'last_activity': now
            }

        user_tracking = self.session_tracking[user_id]
        user_tracking['actions'].append({
            'action': action,
            'timestamp': now,
            'ip_address': request.remote_addr,
            **kwargs
        })

        # Keep only last 100 actions
        if len(user_tracking['actions']) > 100:
            user_tracking['actions'] = user_tracking['actions'][-100:]

        user_tracking['last_activity'] = now

        # Check for rapid-fire actions (potential automation)
        recent_actions = [
            a for a in user_tracking['actions']
            if (now - a['timestamp']).total_seconds() < 60
        ]

        if len(recent_actions) > 20:  # More than 20 actions per minute
            if security_logger:
                security_logger.security_event(
                    event_type='SuspiciousRapidActivity',
                    details=f'User performing too many actions rapidly',
                    user_id=user_id,
                    actions_per_minute=len(recent_actions),
                    action_type=action
                )
            return False, "Phát hiện hoạt động bất thường. Vui lòng thử lại sau."

        return True, None

# Global security manager instance
security_manager = SecurityManager()


def require_security_check(func):
    """Decorator để kiểm tra bảo mật trước khi thực hiện function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check session security
        is_secure, message = security_manager.validate_session_security()
        if not is_secure:
            return {'error': message}, 401

        # Check suspicious activity
        user_id = session.get('user_id')
        if user_id:
            is_safe, message = security_manager.check_suspicious_activity(
                user_id, func.__name__, **kwargs
            )
            if not is_safe:
                return {'error': message}, 429

        return func(*args, **kwargs)
    return wrapper
