"""
Logging configuration cho hệ thống quản lý chấm công
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logging(app):
    """Setup logging cho Flask app"""
    
    # Tạo thư mục logs nếu chưa có
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Cấu hình log level
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    app.logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Không log trong debug mode của Flask
    if not app.debug:
        # File handler với rotation
        file_handler = RotatingFileHandler(
            'logs/app.log',
            maxBytes=10240,  # 10KB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Error log riêng
        error_handler = RotatingFileHandler(
            'logs/error.log',
            maxBytes=10240,
            backupCount=5
        )
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        error_handler.setLevel(logging.ERROR)
        app.logger.addHandler(error_handler)
        
        # Security log
        security_handler = RotatingFileHandler(
            'logs/security.log',
            maxBytes=10240,
            backupCount=5
        )
        security_handler.setFormatter(logging.Formatter(
            '%(asctime)s SECURITY: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        security_handler.setLevel(logging.WARNING)
        app.logger.addHandler(security_handler)
    
    # Console handler cho development
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        app.logger.addHandler(console_handler)
    
    app.logger.info('Logging setup completed')

def get_logger(name):
    """Lấy logger instance"""
    return logging.getLogger(name)

# Các logger chuyên biệt
def get_auth_logger():
    """Logger cho authentication"""
    return get_logger('auth')

def get_attendance_logger():
    """Logger cho attendance operations"""
    return get_logger('attendance')

def get_email_logger():
    """Logger cho email operations"""
    return get_logger('email')

def get_security_logger():
    """Logger cho security events"""
    return get_logger('security')

# Utility functions
def log_user_action(logger, user_id, action, details=None):
    """Log user action"""
    message = f"User {user_id} performed {action}"
    if details:
        message += f" - {details}"
    logger.info(message)

def log_security_event(event, user_id=None, ip_address=None, details=None):
    """Log security event"""
    logger = get_security_logger()
    message = f"Security event: {event}"
    if user_id:
        message += f" - User: {user_id}"
    if ip_address:
        message += f" - IP: {ip_address}"
    if details:
        message += f" - Details: {details}"
    logger.warning(message)

def log_error(logger, error, context=None):
    """Log error với context"""
    message = f"Error: {str(error)}"
    if context:
        message += f" - Context: {context}"
    logger.error(message, exc_info=True)
