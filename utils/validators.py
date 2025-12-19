"""
Enhanced validation utilities for the attendance management system
"""
import re
import logging
from datetime import datetime, date, time
from typing import Optional, Union, Dict, Any

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error with detailed message"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)

def validate_input_sanitize(text: str, max_length: int = 1000) -> Optional[str]:
    """Enhanced sanitize and validate text input to prevent XSS and injection attacks"""
    if not isinstance(text, str):
        raise ValidationError("Input must be a string", "text", text)
    
    if len(text) > max_length:
        raise ValidationError(f"Input too long (max {max_length} characters)", "text", text)
    
    # Remove potentially dangerous characters and patterns
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove script tags and content
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    # Remove SQL injection patterns
    text = re.sub(r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute|script|javascript)\b)', '', text, flags=re.IGNORECASE)
    # Remove potential command injection
    text = re.sub(r'[;&|`$]', '', text)
    # Remove null bytes
    text = text.replace('\x00', '')
    
    result = text.strip()
    return result if result else None

def validate_employee_id(employee_id_str: Union[str, int]) -> Optional[int]:
    """Enhanced validate employee ID with proper sanitization"""
    if not employee_id_str:
        raise ValidationError("Employee ID is required", "employee_id", employee_id_str)
    
    # Remove any non-digit characters
    employee_id_str = re.sub(r'[^\d]', '', str(employee_id_str))
    
    try:
        employee_id = int(employee_id_str)
        if 1 <= employee_id <= 999999:  # Reasonable range
            return employee_id
        else:
            raise ValidationError("Employee ID must be between 1 and 999999", "employee_id", employee_id)
    except (ValueError, TypeError):
        raise ValidationError("Invalid employee ID format", "employee_id", employee_id_str)

def validate_date(date_str: str) -> Optional[date]:
    """Enhanced validate date string in YYYY-MM-DD format"""
    if not date_str:
        raise ValidationError("Date is required", "date", date_str)
    
    try:
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Check if date is not in the future (for attendance records)
        if parsed_date > date.today():
            raise ValidationError("Date cannot be in the future", "date", date_str)
        
        # Check if date is not too far in the past (e.g., more than 1 year)
        one_year_ago = date.today().replace(year=date.today().year - 1)
        if parsed_date < one_year_ago:
            raise ValidationError("Date cannot be more than 1 year in the past", "date", date_str)
        
        return parsed_date
    except ValueError:
        raise ValidationError("Invalid date format. Use YYYY-MM-DD", "date", date_str)

def validate_time(time_str: str) -> Optional[datetime.time]:
    """Enhanced validate time string in HH:MM format with SA/CH/AM/PM support"""
    if not time_str:
        raise ValidationError("Time is required", "time", time_str)
    
    try:
        # Xử lý đặc biệt cho các trường hợp 12:00
        if '12:00' in time_str:
            # 12:00 SA = 12:00 trưa (PM) - trong tiếng Việt
            if 'SA' in time_str:
                clean_time_str = '12:00'
            # 12:00 CH = 12:00 chiều (PM) - trong tiếng Việt  
            elif 'CH' in time_str:
                clean_time_str = '12:00'
            # 12:00 PM = 12:00 trưa (PM) - chuẩn quốc tế
            elif 'PM' in time_str:
                clean_time_str = '12:00'
            # 12:00 AM = 00:00 nửa đêm (AM) - chuẩn quốc tế
            elif 'AM' in time_str:
                clean_time_str = '00:00'
            else:
                clean_time_str = '12:00'
        else:
            # Xử lý định dạng thời gian có thể có SA/CH/AM/PM
            clean_time_str = time_str.replace('SA', '').replace('CH', '').replace('AM', '').replace('PM', '').strip()
        
        parsed_time = datetime.strptime(clean_time_str, '%H:%M').time()
        return parsed_time
    except ValueError:
        raise ValidationError("Invalid time format. Use HH:MM or HH:MM SA/CH/AM/PM", "time", time_str)

def validate_float(val: Union[str, float], min_val: Optional[float] = None, max_val: Optional[float] = None) -> Optional[float]:
    """[DEPRECATED for durations] Validate float with optional min/max. Không dùng cho thời lượng nữa."""
    if val is None:
        return None
    try:
        f = float(val)
        if min_val is not None and f < min_val:
            raise ValidationError(f"Value must be at least {min_val}", "float", val)
        if max_val is not None and f > max_val:
            raise ValidationError(f"Value must be at most {max_val}", "float", val)
        return f
    except (ValueError, TypeError):
        raise ValidationError("Invalid float value", "float", val)

def validate_str(val: str, max_length: int = 255, allow_empty: bool = False, pattern: Optional[str] = None) -> Optional[str]:
    """Validate string with optional pattern matching"""
    if not isinstance(val, str):
        raise ValidationError("Value must be a string", "str", val)
    
    if not allow_empty and not val.strip():
        raise ValidationError("String cannot be empty", "str", val)
    
    if len(val) > max_length:
        raise ValidationError(f"String too long (max {max_length} characters)", "str", val)
    
    if pattern and not re.match(pattern, val):
        raise ValidationError(f"String does not match required pattern", "str", val)
    
    return val.strip()

def validate_note(val: str) -> Optional[str]:
    """Validate note field"""
    return validate_str(val, max_length=1000, allow_empty=True)

def validate_reason(val: str) -> Optional[str]:
    """Validate reason field"""
    return validate_str(val, max_length=500, allow_empty=False)

def validate_holiday_type(val: str) -> Optional[str]:
    """Validate holiday type"""
    allowed = ['normal', 'weekend', 'vietnamese_holiday', 'japanese_holiday']
    return val if val in allowed else None

def validate_role_value(val: str) -> Optional[str]:
    """Validate role value"""
    allowed = ['EMPLOYEE', 'TEAM_LEADER', 'MANAGER', 'ADMIN']
    return val if val in allowed else None

def validate_int(val: Union[str, int], min_val: Optional[int] = None, max_val: Optional[int] = None) -> Optional[int]:
    """Validate integer with optional min/max"""
    if val is None or val == "":
        return None
    try:
        i = int(val)
        if min_val is not None and i < min_val:
            return None
        if max_val is not None and i > max_val:
            return None
        return i
    except (ValueError, TypeError):
        return None