#!/usr/bin/env python3
"""
Script cập nhật approved_by và approved_at cho các records cũ
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database.models import Attendance, User
from datetime import datetime
from sqlalchemy import and_, or_

def fix_old_approval_data():
    """Cập nhật approved_by và approved_at cho records cũ"""
    
    with app.app_context():
        # Tìm admin user đầu tiên để làm người phê duyệt cho records cũ
        admin_user = User.query.filter(User.roles.contains('ADMIN')).first()
        
        if not admin_user:
            print("❌ Không tìm thấy admin user!")
            return
        
        print(f"✅ Sử dụng admin: {admin_user.name} (ID: {admin_user.id})")
        
        # Tìm records có approved=true nhưng approved_by=null
        problem_records = Attendance.query.filter(
            and_(Attendance.approved == True, 
                 or_(Attendance.approved_by == None, Attendance.approved_at == None))
        ).all()
        
        print(f"📊 Tìm thấy {len(problem_records)} records cần cập nhật...")
        
        if len(problem_records) == 0:
            print("✅ Không có records nào cần cập nhật!")
            return
        
        # Cập nhật từng record
        updated = 0
        for att in problem_records:
            att.approved_by = admin_user.id
            att.approved_at = datetime.now()
            att.status = 'approved'  # Đảm bảo status đúng
            updated += 1
        
        # Commit thay đổi
        try:
            db.session.commit()
            print(f"✅ Đã cập nhật thành công {updated} records!")
            print(f"📝 Admin {admin_user.name} đã được gán làm người phê duyệt cho tất cả records cũ")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi khi cập nhật: {e}")

if __name__ == "__main__":
    fix_old_approval_data() 