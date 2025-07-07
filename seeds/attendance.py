"""
Attendance seeding data for the attendance management system
"""
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, User, Attendance
from datetime import datetime, timedelta
import random

# Fix Unicode output for Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def seed_attendance_data(start_date=None, end_date=None, records_per_user=30):
    """
    Seed attendance table with sample data
    
    Args:
        start_date: Start date for attendance records (default: 30 days ago)
        end_date: End date for attendance records (default: today)
        records_per_user: Number of records to generate per user
    """
    
    if start_date is None:
        start_date = datetime.now().date() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.now().date()
    
    print(f"Generating attendance data from {start_date} to {end_date}")
    print(f"Records per user: {records_per_user}")
    
    with app.app_context():
        users = User.query.all()
        if not users:
            print("❌ No users found in database. Please seed users first.")
            return
        
        # Clear existing attendance data in the date range
        existing_count = Attendance.query.filter(
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).count()
        
        if existing_count > 0:
            print(f"⚠️  Found {existing_count} existing attendance records in date range")
            confirm = input("Do you want to replace existing data? (y/N): ")
            if confirm.lower() != 'y':
                print("Operation cancelled.")
                return
            
            # Delete existing records in date range
            deleted = Attendance.query.filter(
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).delete()
            db.session.commit()
            print(f"Deleted {deleted} existing records")
        
        attendance_count = 0
        
        for user in users:
            print(f"Generating data for {user.name}...")
            
            # Generate random dates for this user
            user_dates = []
            current_date = start_date
            
            while len(user_dates) < records_per_user and current_date <= end_date:
                # 90% chance of working on weekdays, 30% on weekends
                is_weekend = current_date.weekday() >= 5
                should_work = random.random() < 0.9 if not is_weekend else random.random() < 0.3
                
                if should_work:
                    user_dates.append(current_date)
                
                current_date += timedelta(days=1)
            
            # Generate attendance records for selected dates
            for date in user_dates:
                attendance = generate_attendance_record(user, date)
                db.session.add(attendance)
                attendance_count += 1
        
        try:
            db.session.commit()
            print(f"\n✅ Successfully generated {attendance_count} attendance records!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error generating attendance data: {e}")
            raise

def generate_attendance_record(user, date):
    """Generate a single attendance record for a user on a specific date"""
    
    # Determine if it's a weekend
    is_weekend = date.weekday() >= 5
    
    # Choose work shift
    shifts = [
        (7, 30, 16, 30),  # 7:30 - 16:30
        (8, 0, 17, 0),    # 8:00 - 17:00
        (9, 0, 18, 0),    # 9:00 - 18:00
        (11, 0, 22, 0)    # 11:00 - 22:00 (night shift)
    ]
    
    shift = random.choice(shifts)
    
    # Base check-in and check-out times
    base_check_in = datetime.combine(date, datetime.min.time().replace(hour=shift[0], minute=shift[1]))
    base_check_out = datetime.combine(date, datetime.min.time().replace(hour=shift[2], minute=shift[3]))
    
    # Add some randomness to check-in time (late arrival)
    late_minutes = random.choice([0, 0, 0, 5, 10, 15, 30])  # Mostly on time, sometimes late
    check_in = base_check_in + timedelta(minutes=late_minutes)
    
    # Add some randomness to check-out time (early departure or overtime)
    early_minutes = random.choice([0, 0, 0, 10, 20, 30])  # Mostly work full shift
    overtime_hours = 0
    
    # 30% chance of overtime
    if random.random() < 0.3:
        overtime_hours = random.randint(1, 3)
    
    check_out = base_check_out - timedelta(minutes=early_minutes) + timedelta(hours=overtime_hours)
    
    # Break time (usually 1 hour)
    break_time = 1.0
    
    # Determine holiday type
    holiday_type = "normal"
    is_holiday = False
    
    if is_weekend:
        holiday_type = "weekend"
        is_holiday = True
    elif random.random() < 0.05:  # 5% chance of holiday
        holiday_type = random.choice(["vietnamese_holiday", "japanese_holiday"])
        is_holiday = True
    
    # Generate note
    notes = [
        "", "Dự án A", "Báo cáo tuần", "Làm thêm giờ", 
        "Meeting với khách hàng", "Training", "Maintenance"
    ]
    note = random.choice(notes)
    
    # Approval status
    approved = random.random() < 0.8  # 80% approved
    status = 'approved' if approved else 'pending'
    
    # Create attendance record
    attendance = Attendance(
        user_id=user.id,
        date=date,
        check_in=check_in,
        check_out=check_out,
        break_time=break_time,
        is_holiday=is_holiday,
        holiday_type=holiday_type,
        note=note,
        approved=approved,
        status=status,
        overtime_before_22="0:00",
        overtime_after_22="0:00"
    )
    
    # Calculate work hours
    attendance.update_work_hours()
    
    return attendance

def clear_attendance_data(start_date=None, end_date=None):
    """Clear attendance data within a date range"""
    
    if start_date is None:
        start_date = datetime.now().date() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.now().date()
    
    with app.app_context():
        try:
            deleted = Attendance.query.filter(
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).delete()
            db.session.commit()
            print(f"✅ Deleted {deleted} attendance records from {start_date} to {end_date}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error clearing attendance data: {e}")
            raise

def clear_all_attendance_data():
    """Clear all attendance data"""
    with app.app_context():
        try:
            deleted = Attendance.query.delete()
            db.session.commit()
            print(f"✅ Deleted {deleted} attendance records")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error clearing attendance data: {e}")
            raise

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'seed':
            # Optional parameters
            days_back = 30
            records_per_user = 30
            
            if len(sys.argv) > 2:
                days_back = int(sys.argv[2])
            if len(sys.argv) > 3:
                records_per_user = int(sys.argv[3])
            
            start_date = datetime.now().date() - timedelta(days=days_back)
            end_date = datetime.now().date()
            
            seed_attendance_data(start_date, end_date, records_per_user)
            
        elif command == 'clear':
            if len(sys.argv) > 2:
                days_back = int(sys.argv[2])
                start_date = datetime.now().date() - timedelta(days=days_back)
                end_date = datetime.now().date()
                clear_attendance_data(start_date, end_date)
            else:
                clear_all_attendance_data()
        else:
            print("Usage: python attendance.py [seed [days_back] [records_per_user] | clear [days_back]]")
    else:
        print("Seeding attendance data...")
        seed_attendance_data() 