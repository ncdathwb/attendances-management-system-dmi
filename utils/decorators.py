"""
Decorators for the attendance management system
"""
from functools import wraps
from flask import request, jsonify, current_app
from collections import defaultdict
import time as time_module
import logging
from database.models import db, AuditLog

logger = logging.getLogger(__name__)

# Fallback in-memory storage (for development)
rate_limit_storage = defaultdict(list)

def rate_limit(max_requests=10, window_seconds=60):
    """Rate limiting decorator with Redis/database support"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client IP
            client_ip = request.remote_addr
            current_time = time_module.time()
            
            # Try to use Redis if available
            if current_app.config.get('REDIS_URL'):
                return _rate_limit_with_redis(client_ip, current_time, max_requests, window_seconds, f, *args, **kwargs)
            else:
                return _rate_limit_with_memory(client_ip, current_time, max_requests, window_seconds, f, *args, **kwargs)
                
        return decorated_function
    return decorator

def _rate_limit_with_redis(client_ip, current_time, max_requests, window_seconds, func, *args, **kwargs):
    """Rate limiting using Redis"""
    try:
        import redis
        redis_client = redis.from_url(current_app.config['REDIS_URL'])
        
        # Create a unique key for this client and endpoint
        key = f"rate_limit:{client_ip}:{func.__name__}"
        
        # Use Redis pipeline for atomic operations
        pipe = redis_client.pipeline()
        
        # Add current timestamp to sorted set
        pipe.zadd(key, {str(current_time): current_time})
        
        # Remove old entries (older than window_seconds)
        pipe.zremrangebyscore(key, 0, current_time - window_seconds)
        
        # Count current entries
        pipe.zcard(key)
        
        # Set expiry on the key
        pipe.expire(key, window_seconds)
        
        # Execute pipeline
        results = pipe.execute()
        current_count = results[2]  # zcard result
        
        if current_count > max_requests:
            logger.warning(f"Rate limit exceeded for IP {client_ip} on {func.__name__}")
            return jsonify({'error': 'Quá nhiều yêu cầu. Vui lòng thử lại sau.'}), 429
        
        return func(*args, **kwargs)
        
    except Exception as e:
        logger.error(f"Redis rate limiting failed, falling back to memory: {e}")
        return _rate_limit_with_memory(client_ip, current_time, max_requests, window_seconds, func, *args, **kwargs)

def _rate_limit_with_memory(client_ip, current_time, max_requests, window_seconds, func, *args, **kwargs):
    """Rate limiting using in-memory storage (fallback)"""
    # Clean old requests
    rate_limit_storage[client_ip] = [
        req_time for req_time in rate_limit_storage[client_ip]
        if current_time - req_time < window_seconds
    ]
    
    # Check if limit exceeded
    if len(rate_limit_storage[client_ip]) >= max_requests:
        logger.warning(f"Rate limit exceeded for IP {client_ip} on {func.__name__}")
        return jsonify({'error': 'Quá nhiều yêu cầu. Vui lòng thử lại sau.'}), 429
    
    # Add current request
    rate_limit_storage[client_ip].append(current_time)
    
    return func(*args, **kwargs)

def log_action(action_type, user_id=None, details=None):
    """Decorator to log user actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get user_id from session if not provided
                if user_id is None:
                    from flask import session
                    user_id = session.get('user_id')
                
                # Log the action
                if user_id:
                    audit_log = AuditLog(
                        user_id=user_id,
                        action=action_type,
                        table_name='api_calls',
                        record_id=None,
                        new_values=details or {},
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent')
                    )
                    db.session.add(audit_log)
                    db.session.commit()
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Failed to log action {action_type}: {e}")
                return f(*args, **kwargs)
                
        return decorated_function
    return decorator

def validate_json_schema(schema):
    """Decorator to validate JSON request body against schema"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json()
                if data is None:
                    return jsonify({'error': 'Invalid JSON data'}), 400
                
                # Basic schema validation
                for field, field_type in schema.items():
                    if field not in data:
                        return jsonify({'error': f'Missing required field: {field}'}), 400
                    
                    if not isinstance(data[field], field_type):
                        return jsonify({'error': f'Invalid type for field {field}'}), 400
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"JSON validation error: {e}")
                return jsonify({'error': 'Invalid request data'}), 400
                
        return decorated_function
    return decorator 