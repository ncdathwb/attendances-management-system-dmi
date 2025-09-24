"""
Enhanced validation utilities for the attendance management system
"""
import re
import logging
from datetime import datetime, date, time
from typing import Optional, Union, Dict, Any
from flask import request
import os

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
    """Enhanced validate time string in HH:MM format"""
    if not time_str:
        raise ValidationError("Time is required", "time", time_str)
    
    try:
        parsed_time = datetime.strptime(time_str, '%H:%M').time()
        return parsed_time
    except ValueError:
        raise ValidationError("Invalid time format. Use HH:MM", "time", time_str)

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
        raise ValidationError("Invalid number format", "float", val)

def validate_str(val: str, max_length: int = 255, allow_empty: bool = False, pattern: Optional[str] = None) -> Optional[str]:
    """Enhanced validate string with length constraints and optional pattern matching"""
    if not isinstance(val, str):
        raise ValidationError("Value must be a string", "string", val)
    
    if not allow_empty and not val.strip():
        raise ValidationError("String cannot be empty", "string", val)
    
    if len(val) > max_length:
        raise ValidationError(f"String too long (max {max_length} characters)", "string", val)
    
    result = val.strip()
    
    if pattern and not re.match(pattern, result):
        raise ValidationError(f"String does not match required pattern", "string", val)
    
    return result if result else None

def validate_note(val: str) -> Optional[str]:
    """Enhanced validate note field"""
    return validate_str(val, max_length=1000, allow_empty=True)

def validate_reason(val: str) -> Optional[str]:
    """Enhanced validate reason field"""
    return validate_str(val, max_length=500, allow_empty=False)

def validate_holiday_type(val: str) -> Optional[str]:
    """Enhanced validate holiday type"""
    allowed = ['normal', 'weekend', 'vietnamese_holiday', 'japanese_holiday']
    if val not in allowed:
        raise ValidationError(f"Holiday type must be one of: {', '.join(allowed)}", "holiday_type", val)
    return val

def validate_role_value(val: str) -> Optional[str]:
    """Enhanced validate role value"""
    allowed = ['EMPLOYEE', 'TEAM_LEADER', 'MANAGER', 'ADMIN']
    if val not in allowed:
        raise ValidationError(f"Role must be one of: {', '.join(allowed)}", "role", val)
    return val

def validate_int(val: Union[str, int], min_val: Optional[int] = None, max_val: Optional[int] = None) -> Optional[int]:
    """Enhanced validate integer value with optional min/max constraints"""
    if val is None:
        return None
    
    try:
        i = int(val)
        if min_val is not None and i < min_val:
            raise ValidationError(f"Value must be at least {min_val}", "integer", val)
        if max_val is not None and i > max_val:
            raise ValidationError(f"Value must be at most {max_val}", "integer", val)
        return i
    except (ValueError, TypeError):
        raise ValidationError("Invalid integer format", "integer", val)

def validate_email(email: str) -> Optional[str]:
    """Validate email address format"""
    if not email:
        return None
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError("Invalid email format", "email", email)
    
    return email.lower().strip()

def validate_phone(phone: str) -> Optional[str]:
    """Validate phone number format"""
    if not phone:
        return None
    
    # Remove all non-digit characters
    digits_only = re.sub(r'[^\d]', '', phone)
    
    # Check if it's a valid Vietnamese phone number
    if len(digits_only) == 10 and digits_only.startswith('0'):
        return digits_only
    elif len(digits_only) == 11 and digits_only.startswith('84'):
        return '0' + digits_only[2:]
    else:
        raise ValidationError("Invalid phone number format", "phone", phone)

def validate_password(password: str) -> Optional[str]:
    """Validate password strength"""
    if not password:
        raise ValidationError("Password is required", "password", password)
    
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long", "password", password)
    
    if len(password) > 128:
        raise ValidationError("Password too long (max 128 characters)", "password", password)
    
    # Check for common weak passwords
    weak_passwords = ['password', '123456', 'qwerty', 'admin', 'user']
    if password.lower() in weak_passwords:
        raise ValidationError("Password is too common", "password", password)
    
    return password

def validate_json_data(data: Dict[str, Any], required_fields: list, optional_fields: list = None) -> Dict[str, Any]:
    """Validate JSON request data structure"""
    if not isinstance(data, dict):
        raise ValidationError("Request data must be a JSON object", "data", data)
    
    validated_data = {}
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}", "data", data)
        validated_data[field] = data[field]
    
    # Check optional fields
    if optional_fields:
        for field in optional_fields:
            if field in data:
                validated_data[field] = data[field]
    
    return validated_data

def validate_file_upload(file, allowed_extensions: list = None, max_size_mb: int = 10) -> Optional[str]:
    """Validate file upload"""
    if not file:
        return None
    
    # Check file size
    max_size_bytes = max_size_mb * 1024 * 1024
    if len(file.read()) > max_size_bytes:
        file.seek(0)  # Reset file pointer
        raise ValidationError(f"File too large (max {max_size_mb}MB)", "file", file.filename)
    
    file.seek(0)  # Reset file pointer
    
    # Check file extension
    if allowed_extensions:
        filename = file.filename
        if not filename or '.' not in filename:
            raise ValidationError("Invalid file format", "file", filename)
        
        extension = filename.rsplit('.', 1)[1].lower()
        if extension not in allowed_extensions:
            raise ValidationError(f"File type not allowed. Allowed: {', '.join(allowed_extensions)}", "file", filename)
    
    return file.filename

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    if not filename:
        return ""
    
    # Remove path traversal attempts
    filename = os.path.basename(filename)
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename

def validate_attendance_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Comprehensive validation for attendance data"""
    try:
        validated = {}
        
        # Required fields
        validated['date'] = validate_date(data.get('date'))
        validated['check_in'] = validate_time(data.get('check_in'))
        validated['check_out'] = validate_time(data.get('check_out'))
        validated['holiday_type'] = validate_holiday_type(data.get('holiday_type'))
        validated['shift_code'] = validate_str(data.get('shift_code'), max_length=10)
        validated['shift_start'] = validate_time(data.get('shift_start'))
        validated['shift_end'] = validate_time(data.get('shift_end'))
        
        # Optional fields
        validated['note'] = validate_note(data.get('note', ''))
        # Chỉ chấp nhận HH:MM cho thời lượng
        bt = data.get('break_time', '01:00') or '01:00'
        if not (isinstance(bt, str) and re.match(r'^\d{1,2}:[0-5]\d$', bt)):
            raise ValidationError("break_time phải ở định dạng HH:MM", "break_time", bt)
        validated['break_time'] = bt
        validated['is_holiday'] = bool(data.get('is_holiday', False))
        # Giờ đối ứng trong ca làm việc: 0-8 giờ
        # Chỉ chấp nhận HH:MM cho các trường đối ứng
        for field in ['comp_time_regular', 'comp_time_overtime', 'comp_time_ot_before_22', 'comp_time_ot_after_22', 'overtime_comp_time']:
            raw = data.get(field, '00:00') or '00:00'
            if not (isinstance(raw, str) and re.match(r'^\d{1,2}:[0-5]\d$', raw)):
                raise ValidationError(f"{field} phải ở định dạng HH:MM", field, raw)
            # Lưu dạng HH:MM để lớp trên tự quy đổi sang giây/phút khi tính
            validated[field] = raw
        
        # Validate time logic
        if validated['check_in'] and validated['check_out']:
            if validated['check_in'] >= validated['check_out']:
                raise ValidationError("Check-in time must be before check-out time", "time_logic", data)
        
        # Cuối tuần & Lễ Việt Nam: KHÔNG cho phép đối ứng trong ca hoặc comp_time_overtime
        if validated['holiday_type'] in ['weekend', 'vietnamese_holiday']:
            if validated['comp_time_regular'] > 0:
                raise ValidationError("Ngày nghỉ (cuối tuần/Lễ VN) không được phép sử dụng đối ứng trong ca (comp_time_regular). Chỉ được sử dụng đối ứng tăng ca.", "comp_time_regular", data)
            if validated['comp_time_overtime'] > 0:
                raise ValidationError("Ngày nghỉ (cuối tuần/Lễ VN) không được phép sử dụng đối ứng tăng ca tổng (comp_time_overtime). Chỉ được sử dụng đối ứng tăng ca trước/sau 22h.", "comp_time_overtime", data)
        
        return validated
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during attendance validation: {e}")
        raise ValidationError("Invalid attendance data", "data", data)

def validate_duration_to_minutes(val: Union[str, float, int], *, min_minutes: int = 0, max_minutes: int = 8*60) -> int:
    """Chuẩn hoá thời lượng về phút (int). Chấp nhận 'HH:MM', số thập phân giờ, hoặc phút (int).
    Trả về số phút, giới hạn trong [min_minutes, max_minutes].
    """
    if val is None:
        return 0
    try:
        minutes: int
        if isinstance(val, int):
            minutes = val
        elif isinstance(val, str) and ':' in val:
            hh, mm = val.split(':')
            minutes = int(hh) * 60 + int(mm)
        else:
            hours = float(val)
            minutes = int(round(hours * 60))
        if minutes < min_minutes:
            minutes = min_minutes
        if minutes > max_minutes:
            minutes = max_minutes
        return minutes
    except (ValueError, TypeError):
        raise ValidationError("Invalid duration format", "duration", val)

def validate_time_precision(hours_float: float, field_name: str = "time") -> bool:
    """Kiểm tra precision loss trong chuyển đổi thời gian
    
    Args:
        hours_float: Giá trị giờ thập phân
        field_name: Tên trường để log
        
    Returns:
        True nếu không có precision loss đáng kể, False nếu có
    """
    try:
        minutes = int(round(hours_float * 60))
        hours_back = minutes / 60.0
        precision_loss = abs(hours_back - hours_float)
        
        # Nếu precision loss > 0.01 giờ (0.6 phút) thì cảnh báo
        if precision_loss > 0.01:
            logger.warning(f"Precision loss detected in {field_name}: {hours_float:.6f}h -> {hours_back:.6f}h (loss: {precision_loss:.6f}h = {precision_loss*60:.1f} minutes)")
            return False
        return True
    except Exception as e:
        logger.error(f"Error validating time precision for {field_name}: {e}")
        return False

def safe_convert_to_minutes(value: Union[str, float, int, None]) -> int:
    """Chuyển đổi an toàn giá trị thời gian sang phút
    
    Args:
        value: Giá trị thời gian (có thể là HH:MM, số giờ, hoặc None)
        
    Returns:
        Số phút (int)
    """
    if value is None or value == "":
        return 0
    try:
        if isinstance(value, str) and ":" in value:
            # Xử lý format HH:MM
            hh, mm = value.split(":")
            return int(hh) * 60 + int(mm)
        elif isinstance(value, (int, float)):
            # Xử lý số giờ thập phân
            minutes = int(round(float(value) * 60))
            # Kiểm tra precision loss
            validate_time_precision(float(value), "conversion")
            return minutes
        else:
            # Thử chuyển đổi string số
            float_val = float(value)
            minutes = int(round(float_val * 60))
            validate_time_precision(float_val, "conversion")
            return minutes
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to convert time value {repr(value)} to minutes: {e}")
        return 0

def log_validation_error(error: ValidationError, user_id: Optional[int] = None):
    """Log validation errors for monitoring"""
    logger.warning(f"Validation error: {error.message}", extra={
        'field': error.field,
        'value': str(error.value)[:100] if error.value else None,  # Truncate long values
        'user_id': user_id,
        'ip_address': request.remote_addr if request else None
    }) 