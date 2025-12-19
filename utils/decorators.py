"""
Decorators for the attendance management system
"""
from functools import wraps
from flask import request, jsonify, current_app
from collections import defaultdict
import time as time_module
import logging

logger = logging.getLogger(__name__)

# Fallback in-memory storage (for development)
rate_limit_storage = defaultdict(list)

def rate_limit(max_requests=10, window_seconds=60):
    """Rate limiting decorator with in-memory storage"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client IP
            client_ip = request.remote_addr
            current_time = time_module.time()
            
            # Clean up old entries
            cutoff_time = current_time - window_seconds
            rate_limit_storage[client_ip] = [
                timestamp for timestamp in rate_limit_storage[client_ip]
                if timestamp > cutoff_time
            ]
            
            # Check if limit exceeded
            if len(rate_limit_storage[client_ip]) >= max_requests:
                logger.warning(f"Rate limit exceeded for IP {client_ip}")
                return jsonify({'error': 'Quá nhiều yêu cầu. Vui lòng thử lại sau.'}), 429
            
            # Add current request
            rate_limit_storage[client_ip].append(current_time)
            
            # Execute function
            return f(*args, **kwargs)
                
        return decorated_function
    return decorator