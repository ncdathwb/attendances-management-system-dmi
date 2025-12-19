"""
Precision utilities for handling floating point arithmetic
"""
from decimal import Decimal, ROUND_HALF_UP, getcontext
import math

# Set precision for decimal calculations
getcontext().prec = 28

def safe_float_to_minutes(hours):
    """
    Convert hours to minutes with precision handling
    """
    if hours is None:
        return 0
    
    try:
        # Convert to decimal to avoid floating point errors
        decimal_hours = Decimal(str(hours))
        minutes = decimal_hours * Decimal('60')
        return int(minutes.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (ValueError, TypeError):
        return 0

def safe_minutes_to_hours(minutes):
    """
    Convert minutes to hours with precision handling
    """
    if minutes is None:
        return 0.0
    
    try:
        # Convert to decimal to avoid floating point errors
        decimal_minutes = Decimal(str(minutes))
        hours = decimal_minutes / Decimal('60')
        return float(hours.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
    except (ValueError, TypeError):
        return 0.0

def safe_round_hours(hours, precision=4):
    """
    Round hours to specified precision to avoid floating point errors
    """
    if hours is None:
        return 0.0
    
    try:
        # Use decimal arithmetic for precise rounding
        decimal_hours = Decimal(str(hours))
        rounded = decimal_hours.quantize(Decimal(f'0.{"0" * precision}'), rounding=ROUND_HALF_UP)
        return float(rounded)
    except (ValueError, TypeError):
        return 0.0

def format_hours_minutes_precise(hours):
    """
    Format hours to HH:MM with precise decimal arithmetic
    """
    if hours is None:
        return "0:00"
    
    try:
        # Use decimal arithmetic to avoid floating point errors
        decimal_hours = Decimal(str(hours))
        
        # Extract hours and minutes
        h = int(decimal_hours)
        minutes_decimal = (decimal_hours - Decimal(h)) * Decimal('60')
        m = int(minutes_decimal.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        
        # Handle overflow
        if m == 60:
            h += 1
            m = 0
        
        return f"{h}:{m:02d}"
    except (ValueError, TypeError):
        return "0:00"

def calculate_work_hours_precise(check_in, check_out, break_time=0):
    """
    Calculate work hours with precise decimal arithmetic
    """
    if not check_in or not check_out:
        return 0.0
    
    try:
        from datetime import datetime, timedelta
        
        # Convert to datetime objects if strings
        if isinstance(check_in, str):
            check_in = datetime.strptime(check_in, '%H:%M')
        if isinstance(check_out, str):
            check_out = datetime.strptime(check_out, '%H:%M')
        
        # Calculate difference in minutes
        time_diff = check_out - check_in
        total_minutes = time_diff.total_seconds() / 60
        
        # Subtract break time
        break_minutes = safe_float_to_minutes(break_time)
        work_minutes = total_minutes - break_minutes
        
        # Convert back to hours
        work_hours = safe_minutes_to_hours(work_minutes)
        
        return safe_round_hours(work_hours, 4)
    except Exception:
        return 0.0

def calculate_overtime_precise(work_hours, regular_hours=8):
    """
    Calculate overtime hours with precise decimal arithmetic
    """
    if work_hours is None:
        return 0.0
    
    try:
        decimal_work = Decimal(str(work_hours))
        decimal_regular = Decimal(str(regular_hours))
        
        overtime = decimal_work - decimal_regular
        if overtime < 0:
            overtime = Decimal('0')
        
        return safe_round_hours(float(overtime), 4)
    except (ValueError, TypeError):
        return 0.0

def is_time_equal(time1, time2, tolerance=0.0001):
    """
    Compare two time values with tolerance for floating point errors
    """
    if time1 is None and time2 is None:
        return True
    if time1 is None or time2 is None:
        return False
    
    try:
        diff = abs(Decimal(str(time1)) - Decimal(str(time2)))
        return diff <= Decimal(str(tolerance))
    except (ValueError, TypeError):
        return False

def normalize_time_value(value):
    """
    Normalize time value to remove floating point precision errors
    """
    if value is None:
        return 0.0
    
    try:
        # Round to 4 decimal places (good enough for minutes precision)
        return safe_round_hours(value, 4)
    except (ValueError, TypeError):
        return 0.0
