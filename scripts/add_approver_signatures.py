#!/usr/bin/env python3
"""
Script để thêm các trường chữ ký người phê duyệt vào bảng attendances
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import Attendance

def add_approver_signature_columns():
    """Thêm các cột chữ ký người phê duyệt vào bảng attendances"""
    with app.app_context():
        try:
            # Kiểm tra xem các cột đã tồn tại chưa
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('attendances')]
            
            if 'team_leader_signature' not in columns:
                print("Thêm cột team_leader_signature...")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE attendances ADD COLUMN team_leader_signature TEXT'))
                    conn.commit()
                print("✓ Đã thêm cột team_leader_signature")
            else:
                print("✓ Cột team_leader_signature đã tồn tại")
                
            if 'manager_signature' not in columns:
                print("Thêm cột manager_signature...")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE attendances ADD COLUMN manager_signature TEXT'))
                    conn.commit()
                print("✓ Đã thêm cột manager_signature")
            else:
                print("✓ Cột manager_signature đã tồn tại")
                
            print("\n✅ Hoàn thành cập nhật database schema!")
            
        except Exception as e:
            print(f"❌ Lỗi khi cập nhật database: {str(e)}")
            return False
    
    return True

if __name__ == '__main__':
    print("🔄 Đang cập nhật database schema...")
    success = add_approver_signature_columns()
    if success:
        print("🎉 Cập nhật thành công!")
    else:
        print("💥 Cập nhật thất bại!")
        sys.exit(1) 