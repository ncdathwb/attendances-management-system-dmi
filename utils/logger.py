"""
Structured logging system for the attendance management system
"""
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request, session

class StructuredLogger:
    """Enhanced structured logger with context awareness"""
    
    def __init__(self, name: str = __name__):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Tạo formatter cho structured logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(
            os.path.join(log_dir, 'attendance.log'),
        encoding='utf-8'
    )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def _get_context(self) -> Dict[str, Any]:
        """Lấy thông tin context hiện tại"""
        context = {
            'timestamp': datetime.now().isoformat(),
            'ip_address': getattr(request, 'remote_addr', None) if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
        }
        
        if session:
            context.update({
                'user_id': session.get('user_id'),
                'employee_id': session.get('employee_id'),
                'current_role': session.get('current_role'),
                'session_id': session.get('_id')
            })
        
        return context
    
    def info(self, message: str, **kwargs):
        """Log info message với context"""
        log_data = {
            'level': 'INFO',
            'message': message,
            **self._get_context(),
            **kwargs
        }
        self.logger.info(json.dumps(log_data, ensure_ascii=False))
    
    def warning(self, message: str, **kwargs):
        """Log warning message với context"""
        log_data = {
            'level': 'WARNING',
            'message': message,
            **self._get_context(),
            **kwargs
        }
        self.logger.warning(json.dumps(log_data, ensure_ascii=False))
    
    def error(self, message: str, error_type: str = None, **kwargs):
        """Log error message với context"""
        log_data = {
            'level': 'ERROR',
            'message': message,
            'error_type': error_type,
            **self._get_context(),
            **kwargs
        }
        self.logger.error(json.dumps(log_data, ensure_ascii=False))
    
    def critical(self, message: str, error_type: str = None, **kwargs):
        """Log critical message với context"""
        log_data = {
            'level': 'CRITICAL',
            'message': message,
            'error_type': error_type,
            **self._get_context(),
            **kwargs
        }
        self.logger.critical(json.dumps(log_data, ensure_ascii=False))
    
    def security_event(self, event_type: str, details: str, **kwargs):
        """Log security events"""
        log_data = {
            'level': 'SECURITY',
        'event_type': event_type,
        'details': details,
            **self._get_context(),
            **kwargs
        }
        self.logger.warning(json.dumps(log_data, ensure_ascii=False))
    
    def audit_action(self, action: str, table_name: str = None, record_id: int = None, **kwargs):
        """Log audit actions"""
        log_data = {
            'level': 'AUDIT',
        'action': action,
            'table_name': table_name,
        'record_id': record_id,
            **self._get_context(),
            **kwargs
        }
        self.logger.info(json.dumps(log_data, ensure_ascii=False))

# Global logger instance
logger = StructuredLogger()

# Specific loggers for different modules
security_logger = StructuredLogger('security')
audit_logger = StructuredLogger('audit')
database_logger = StructuredLogger('database')
api_logger = StructuredLogger('api')
