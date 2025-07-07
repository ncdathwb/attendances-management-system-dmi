"""
Validation utilities for the attendance management system
"""
import re
from datetime import datetime

def validate_input_sanitize(text):
    """Sanitize and validate text input to prevent XSS and injection attacks"""
    if not isinstance(text, str):
        return None
    
    # Remove potentially dangerous characters
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    # Remove SQL injection patterns
    text = re.sub(r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)', '', text, flags=re.IGNORECASE)
    
    return text.strip() if text.strip() else None

def validate_employee_id(employee_id_str):
    """Validate employee ID with proper sanitization"""
    if not employee_id_str:
        return None
    
    # Remove any non-digit characters
    employee_id_str = re.sub(r'[^\d]', '', str(employee_id_str))
    
    try:
        employee_id = int(employee_id_str)
        if 1 <= employee_id <= 999999:  # Reasonable range
            return employee_id
    except (ValueError, TypeError):
        pass
    
    return None

def validate_date(date_str):
    """Validate date string in YYYY-MM-DD format"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return None

def validate_time(time_str):
    """Validate time string in HH:MM format"""
    try:
        return datetime.strptime(time_str, '%H:%M').time()
    except Exception:
        return None

def validate_float(val, min_val=None, max_val=None):
    """Validate float value with optional min/max constraints"""
    try:
        f = float(val)
        if min_val is not None and f < min_val:
            return None
        if max_val is not None and f > max_val:
            return None
        return f
    except Exception:
        return None

def validate_str(val, max_length=255, allow_empty=False):
    """Validate string with length constraints"""
    if not isinstance(val, str):
        return None
    if not allow_empty and not val.strip():
        return None
    if len(val) > max_length:
        return None
    return val.strip()

def validate_note(val):
    """Validate note field"""
    return validate_str(val, max_length=1000, allow_empty=True)

def validate_reason(val):
    """Validate reason field"""
    return validate_str(val, max_length=500, allow_empty=False)

def validate_holiday_type(val):
    """Validate holiday type"""
    allowed = ['normal', 'weekend', 'vietnamese_holiday', 'japanese_holiday']
    return val if val in allowed else None

def validate_role_value(val):
    """Validate role value"""
    allowed = ['EMPLOYEE', 'TEAM_LEADER', 'MANAGER', 'ADMIN']
    return val if val in allowed else None

def validate_int(val, min_val=None, max_val=None):
    """Validate integer value with optional min/max constraints"""
    try:
        i = int(val)
        if min_val is not None and i < min_val:
            return None
        if max_val is not None and i > max_val:
            return None
        return i
    except Exception:
        return None 