#!/usr/bin/env python3
"""
Script cập nhật shift_code cho các bản ghi chấm công cũ dựa vào giờ check_in
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database.models import Attendance
from sqlalchemy import or_

def guess_shift_code(check_in_time):
    if not check_in_time:
        return None
    hour = check_in_time.hour
    minute = check_in_time.minute
    if hour < 8 or (hour == 8 and minute == 0):
        return '1'  # Ca 1: 7:30 - 16:30
    elif hour < 9 or (hour == 9 and minute == 0):
        return '2'  # Ca 2: 8:00 - 17:00
    elif hour < 11:
        return '3'  # Ca 3: 9:00 - 18:00
    else:
        return '4'  # Ca 4: 11:00 - 22:00

def update_old_attendance_shift_code():
    with app.app_context():
        records = Attendance.query.filter(
            or_(Attendance.shift_code == None, Attendance.shift_code == '')
        ).all()
        print(f"Tìm thấy {len(records)} bản ghi cần cập nhật shift_code...")
        updated = 0
        for att in records:
            shift_code = guess_shift_code(att.check_in)
            if shift_code:
                att.shift_code = shift_code
                att.update_work_hours()
                updated += 1
        db.session.commit()
        print(f"Đã cập nhật {updated} bản ghi.")

if __name__ == "__main__":
    update_old_attendance_shift_code() 