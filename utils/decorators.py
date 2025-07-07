"""
Decorators for the attendance management system
"""
from functools import wraps
from flask import request, jsonify
from collections import defaultdict
import time

# Rate limiting storage
rate_limit_storage = defaultdict(list)

def rate_limit(max_requests=10, window_seconds=60):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client IP
            client_ip = request.remote_addr
            current_time = time.time()
            
            # Clean old requests
            rate_limit_storage[client_ip] = [
                req_time for req_time in rate_limit_storage[client_ip]
                if current_time - req_time < window_seconds
            ]
            
            # Check if limit exceeded
            if len(rate_limit_storage[client_ip]) >= max_requests:
                return jsonify({'error': 'Quá nhiều yêu cầu. Vui lòng thử lại sau.'}), 429
            
            # Add current request
            rate_limit_storage[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator 