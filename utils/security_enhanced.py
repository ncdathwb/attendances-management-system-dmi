"""
Enhanced security utilities for the attendance management system
"""
import time
from datetime import datetime, timedelta
from collections import defaultdict
from flask import request, session
from utils.logger import security_logger

class SecurityManager:
    """Enhanced security manager with brute force protection and session security"""
    
    def __init__(self):
        # In-memory storage for failed login attempts (in production, use Redis)
        self.failed_attempts = defaultdict(list)
        self.account_lockouts = {}
        self.session_tracking = {}
    
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
            security_logger.security_event(
                event_type='SessionIPInitialized',
                details=f'Initialized session IP for user {session.get("user_id")}',
                user_id=session.get('user_id'),
                ip_address=current_ip
            )
        elif session_ip != current_ip:
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
