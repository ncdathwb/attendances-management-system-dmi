#!/usr/bin/env python3
"""
Script cập nhật tất cả records cũ với logic tính toán mới
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database.models import Attendance

def update_all_records_with_new_logic():
    """Cập nhật tất cả records với logic tính toán mới"""
    
    with app.app_context():
        # Lấy tất cả attendance records
        records = Attendance.query.all()
        
        print(f"📊 Tìm thấy {len(records)} records cần cập nhật...")
        
        updated = 0
        for att in records:
            # Tính toán lại work hours với logic mới
            att.update_work_hours()
            updated += 1
            
            # Hiển thị progress mỗi 100 records
            if updated % 100 == 0:
                print(f"✅ Đã cập nhật {updated}/{len(records)} records...")
        
        # Commit thay đổi
        try:
            db.session.commit()
            print(f"✅ Đã cập nhật thành công {updated} records với logic mới!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi cập nhật: {e}")
        
        # Hiển thị một số ví dụ
        print("\n=== VÍ DỤ SAU KHI CẬP NHẬT ===")
        sample_records = Attendance.query.limit(3).all()
        for i, att in enumerate(sample_records):
            print(f"Record {i+1}:")
            print(f"- ID: {att.id}")
            print(f"- Date: {att.date}")
            print(f"- Check-in: {att.check_in}")
            print(f"- Check-out: {att.check_out}")
            print(f"- Shift code: {att.shift_code}")
            print(f"- Total work hours: {att.total_work_hours}")
            print(f"- Regular work hours: {att.regular_work_hours}")
            print(f"- Overtime before 22: {att.overtime_before_22}")
            print(f"- Overtime after 22: {att.overtime_after_22}")
            print()

if __name__ == "__main__":
    update_all_records_with_new_logic() 