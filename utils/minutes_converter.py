"""
Minutes Converter - Convert between hours and minutes with no floating point errors
"""
from decimal import Decimal, ROUND_HALF_UP

def hours_to_minutes(hours):
    """
    Convert hours to minutes (integer) - NO FLOATING POINT ERRORS
    """
    if hours is None:
        return 0
    
    try:
        # Use decimal arithmetic for precise conversion
        decimal_hours = Decimal(str(hours))
        minutes = decimal_hours * Decimal('60')
        return int(minutes.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (ValueError, TypeError):
        return 0

def minutes_to_hours(minutes):
    """
    Convert minutes to hours (float) - for display purposes only
    """
    if minutes is None:
        return 0.0
    
    try:
        # Use decimal arithmetic for precise conversion
        decimal_minutes = Decimal(str(minutes))
        hours = decimal_minutes / Decimal('60')
        return float(hours.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
    except (ValueError, TypeError):
        return 0.0

def minutes_to_hhmm(minutes):
    """
    Convert minutes to HH:MM format - NO FLOATING POINT ERRORS
    """
    if minutes is None or minutes <= 0:
        return "0:00"
    
    try:
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}:{mins:02d}"
    except (ValueError, TypeError):
        return "0:00"

def hhmm_to_minutes(time_str):
    """
    Convert HH:MM string to minutes (integer) - NO FLOATING POINT ERRORS
    """
    if not time_str or time_str == "0:00":
        return 0
    
    try:
        if ':' in time_str:
            hours, minutes = map(int, time_str.split(':'))
            return hours * 60 + minutes
        else:
            return int(time_str) * 60
    except (ValueError, TypeError):
        return 0

def safe_convert_to_minutes(value):
    """
    Safely convert any time value to minutes (integer)
    Handles both string (HH:MM) and float (hours) inputs
    """
    if value is None:
        return 0
    
    if isinstance(value, str):
        return hhmm_to_minutes(value)
    elif isinstance(value, (int, float)):
        return hours_to_minutes(value)
    else:
        return 0

def get_comp_time_minutes(attendance, field_type):
    """
    Get comp_time in minutes from attendance object
    Returns the NEW minutes column if available, otherwise converts from legacy float
    """
    minutes_field = f"{field_type}_minutes"
    legacy_field = field_type
    
    # Try to get from new minutes column first
    if hasattr(attendance, minutes_field):
        minutes_value = getattr(attendance, minutes_field)
        if minutes_value is not None and minutes_value > 0:
            return minutes_value
    
    # Fallback to legacy float column and convert
    if hasattr(attendance, legacy_field):
        legacy_value = getattr(attendance, legacy_field)
        if legacy_value is not None and legacy_value > 0:
            return hours_to_minutes(legacy_value)
    
    return 0

def set_comp_time_minutes(attendance, field_type, minutes):
    """
    Set comp_time in minutes for attendance object
    Updates both new minutes column and legacy float column for compatibility
    """
    minutes_field = f"{field_type}_minutes"
    legacy_field = field_type
    
    # Set new minutes column
    if hasattr(attendance, minutes_field):
        setattr(attendance, minutes_field, minutes)
    
    # Update legacy float column for compatibility
    if hasattr(attendance, legacy_field):
        setattr(attendance, legacy_field, minutes_to_hours(minutes))

def format_comp_time_for_display(attendance, field_type):
    """
    Format comp_time for display - always returns clean HH:MM format
    """
    minutes = get_comp_time_minutes(attendance, field_type)
    return minutes_to_hhmm(minutes)

def calculate_comp_time_deduction(attendance, field_type):
    """
    Calculate comp_time deduction in minutes for calculations
    """
    return get_comp_time_minutes(attendance, field_type)

def migrate_legacy_comp_times():
    """
    Migration helper: Update legacy float values to new minutes columns
    """
    from database.models import Attendance, db
    
    try:
        attendances = Attendance.query.all()
        updated_count = 0
        
        for att in attendances:
            # Migrate each comp_time field
            comp_fields = [
                'comp_time_regular',
                'comp_time_overtime', 
                'comp_time_ot_before_22',
                'comp_time_ot_after_22',
                'overtime_comp_time'
            ]
            
            updated = False
            for field in comp_fields:
                legacy_value = getattr(att, field)
                if legacy_value and legacy_value > 0:
                    minutes_value = hours_to_minutes(legacy_value)
                    minutes_field = f"{field}_minutes"
                    if hasattr(att, minutes_field):
                        setattr(att, minutes_field, minutes_value)
                        updated = True
            
            if updated:
                updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            print(f"✅ Migrated {updated_count} attendance records to minutes-based comp_time")
        else:
            print("ℹ️ No records needed migration")
            
        return updated_count
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.session.rollback()
        return 0
