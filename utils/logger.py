"""
Logging configuration for the attendance management system
"""
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logger(app):
    """Setup application logging"""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure logging format
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    
    # File handler for all logs with UTF-8 encoding
    file_handler = RotatingFileHandler(
        'logs/attendance.log', 
        maxBytes=10240000,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Error file handler with UTF-8 encoding
    error_handler = RotatingFileHandler(
        'logs/error.log',
        maxBytes=10240000,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Security file handler with UTF-8 encoding
    security_handler = RotatingFileHandler(
        'logs/security.log',
        maxBytes=10240000,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    security_handler.setFormatter(formatter)
    security_handler.setLevel(logging.WARNING)
    
    # Console handler with UTF-8 encoding for Windows
    if os.name == 'nt':  # Windows
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        app.logger.addHandler(console_handler)
    
    # Configure app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(security_handler)
    app.logger.setLevel(logging.INFO)
    
    # Log application startup
    app.logger.info('Attendance Management System startup')

def log_security_event(event_type, user_id=None, ip_address=None, details=None):
    """Log security-related events"""
    logger = logging.getLogger('security')
    message = f"SECURITY: {event_type}"
    if user_id:
        message += f" | User: {user_id}"
    if ip_address:
        message += f" | IP: {ip_address}"
    if details:
        message += f" | Details: {details}"
    logger.warning(message)

def log_error(error, context=None):
    """Log application errors"""
    logger = logging.getLogger('error')
    message = f"ERROR: {str(error)}"
    if context:
        message += f" | Context: {context}"
    logger.error(message, exc_info=True)

def log_activity(activity_type, user_id=None, details=None):
    """Log user activities"""
    logger = logging.getLogger('activity')
    message = f"ACTIVITY: {activity_type}"
    if user_id:
        message += f" | User: {user_id}"
    if details:
        message += f" | Details: {details}"
    logger.info(message) 