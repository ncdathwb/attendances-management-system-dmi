"""
Enhanced logging configuration for the attendance management system
"""
import logging
import os
import sys
import json
from datetime import datetime, time
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import traceback
from functools import wraps
import time as time_module

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record):
        # Create structured log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'ip_address'):
            log_entry['ip_address'] = record.ip_address
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'performance'):
            log_entry['performance'] = record.performance
        
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logger(app):
    """Setup enhanced application logging"""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure structured formatter
    structured_formatter = StructuredFormatter()
    
    # Standard formatter for console output
    console_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s'
    )
    
    # File handler for all logs with structured format
    file_handler = RotatingFileHandler(
        'logs/attendance.log', 
        maxBytes=10240000,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(structured_formatter)
    file_handler.setLevel(logging.INFO)
    
    # Error file handler with structured format
    error_handler = RotatingFileHandler(
        'logs/error.log',
        maxBytes=10240000,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setFormatter(structured_formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Security file handler with structured format
    security_handler = RotatingFileHandler(
        'logs/security.log',
        maxBytes=10240000,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    security_handler.setFormatter(structured_formatter)
    security_handler.setLevel(logging.WARNING)
    
    # Performance monitoring handler
    performance_handler = TimedRotatingFileHandler(
        'logs/performance.log',
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    performance_handler.setFormatter(structured_formatter)
    performance_handler.setLevel(logging.INFO)
    
    # Console handler with UTF-8 encoding for Windows
    if os.name == 'nt':  # Windows
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        app.logger.addHandler(console_handler)
    
    # Configure app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(security_handler)
    app.logger.addHandler(performance_handler)
    app.logger.setLevel(logging.INFO)
    
    # Create specialized loggers
    security_logger = logging.getLogger('security')
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.WARNING)
    
    performance_logger = logging.getLogger('performance')
    performance_logger.addHandler(performance_handler)
    performance_logger.setLevel(logging.INFO)
    
    # Disable propagation to avoid duplicate logs
    security_logger.propagate = False
    performance_logger.propagate = False
    
    return app.logger

def log_error(error, context=None, user_id=None, ip_address=None):
    """Enhanced error logging with context"""
    logger = logging.getLogger('error')
    
    # Create structured error log
    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context,
        'user_id': user_id,
        'ip_address': ip_address,
        'traceback': traceback.format_exc()
    }
    
    logger.error('Application error occurred', extra=error_data)

def log_security_event(event_type, details, user_id=None, ip_address=None):
    """Log security-related events"""
    logger = logging.getLogger('security')
    
    security_data = {
        'event_type': event_type,
        'details': details,
        'user_id': user_id,
        'ip_address': ip_address,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    logger.warning(f'Security event: {event_type}', extra=security_data)

def log_performance(operation, duration, details=None, user_id=None):
    """Log performance metrics"""
    logger = logging.getLogger('performance')
    
    performance_data = {
        'operation': operation,
        'duration_ms': round(duration * 1000, 2),
        'details': details,
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Log slow operations as warnings
    if duration > 1.0:  # Operations taking more than 1 second
        logger.warning(f'Slow operation detected: {operation}', extra=performance_data)
    else:
        logger.info(f'Performance metric: {operation}', extra=performance_data)

def performance_monitor(operation_name):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time_module.time()
            try:
                result = func(*args, **kwargs)
                duration = time_module.time() - start_time
                log_performance(operation_name, duration)
                return result
            except Exception as e:
                duration = time_module.time() - start_time
                log_performance(operation_name, duration, {'error': str(e)})
                raise
        return wrapper
    return decorator

def log_user_action(action, user_id, details=None, ip_address=None):
    """Log user actions for audit purposes"""
    logger = logging.getLogger('audit')
    
    audit_data = {
        'action': action,
        'user_id': user_id,
        'details': details,
        'ip_address': ip_address,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    logger.info(f'User action: {action}', extra=audit_data)

def log_database_operation(operation, table, record_id=None, user_id=None):
    """Log database operations"""
    logger = logging.getLogger('database')
    
    db_data = {
        'operation': operation,
        'table': table,
        'record_id': record_id,
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    logger.info(f'Database operation: {operation} on {table}', extra=db_data)

def log_api_request(method, endpoint, status_code, duration=None, user_id=None, ip_address=None):
    """Log API requests"""
    logger = logging.getLogger('api')
    
    api_data = {
        'method': method,
        'endpoint': endpoint,
        'status_code': status_code,
        'duration_ms': round(duration * 1000, 2) if duration else None,
        'user_id': user_id,
        'ip_address': ip_address,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Log errors as warnings
    if status_code >= 400:
        logger.warning(f'API error: {method} {endpoint} - {status_code}', extra=api_data)
    else:
        logger.info(f'API request: {method} {endpoint} - {status_code}', extra=api_data)

def log_memory_usage():
    """Log current memory usage"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        logger = logging.getLogger('system')
        system_data = {
            'memory_rss_mb': round(memory_info.rss / 1024 / 1024, 2),
            'memory_vms_mb': round(memory_info.vms / 1024 / 1024, 2),
            'cpu_percent': process.cpu_percent(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info('System resource usage', extra=system_data)
        
    except ImportError:
        # psutil not available, skip memory logging
        pass
    except Exception as e:
        logging.getLogger('system').error(f'Failed to log memory usage: {e}')

def cleanup_old_logs(days_to_keep=30):
    """Clean up old log files"""
    import glob
    from datetime import datetime, timedelta, time
    
    log_dir = 'logs'
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    for log_file in glob.glob(os.path.join(log_dir, '*.log.*')):
        try:
            file_time = datetime.fromtimestamp(os.path.getctime(log_file))
            if file_time < cutoff_date:
                os.remove(log_file)
                logging.getLogger('system').info(f'Cleaned up old log file: {log_file}')
        except Exception as e:
            logging.getLogger('system').error(f'Failed to clean up log file {log_file}: {e}') 