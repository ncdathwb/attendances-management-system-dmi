#!/usr/bin/env python3
"""
Migration: Create leave_requests table with approval fields
Tạo bảng leave_requests với đầy đủ trường phê duyệt
"""

import sqlite3
import os
from datetime import datetime

def run_migration():
    """Tạo bảng leave_requests với đầy đủ trường"""
    
    # Đường dẫn database
    db_path = 'attendance.db'
    if not os.path.exists(db_path):
        print(f"❌ Không tìm thấy database: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Bắt đầu migration: Tạo bảng leave_requests...")
        
        # Kiểm tra bảng đã tồn tại chưa
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leave_requests'")
        if cursor.fetchone():
            print("⏭️  Bảng leave_requests đã tồn tại, bỏ qua tạo bảng")
            conn.close()
            return True
        
        # SQL tạo bảng leave_requests với đầy đủ trường
        create_table_sql = """
        CREATE TABLE leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            employee_name VARCHAR(100),
            team VARCHAR(50),
            employee_code VARCHAR(20),
            leave_reason TEXT,
            reason_sick_child BOOLEAN DEFAULT 0,
            reason_sick BOOLEAN DEFAULT 0,
            reason_death_anniversary BOOLEAN DEFAULT 0,
            reason_other BOOLEAN DEFAULT 0,
            reason_other_detail TEXT,
            attachments TEXT,
            hospital_confirmation TEXT,
            wedding_invitation TEXT,
            death_birth_certificate TEXT,
            leave_from_hour INTEGER NOT NULL,
            leave_from_minute INTEGER NOT NULL,
            leave_from_day INTEGER NOT NULL,
            leave_from_month INTEGER NOT NULL,
            leave_from_year INTEGER NOT NULL,
            leave_to_hour INTEGER NOT NULL,
            leave_to_minute INTEGER NOT NULL,
            leave_to_day INTEGER NOT NULL,
            leave_to_month INTEGER NOT NULL,
            leave_to_year INTEGER NOT NULL,
            annual_leave_days FLOAT DEFAULT 0.0,
            unpaid_leave_days FLOAT DEFAULT 0.0,
            special_leave_days FLOAT DEFAULT 0.0,
            special_leave_type VARCHAR(50),
            substitute_name VARCHAR(100),
            substitute_employee_id VARCHAR(20),
            status VARCHAR(20) DEFAULT 'pending',
            approved BOOLEAN DEFAULT 0,
            approved_by INTEGER,
            approved_at DATETIME,
            team_leader_signature TEXT,
            team_leader_signer_id INTEGER,
            manager_signature TEXT,
            manager_signer_id INTEGER,
            manager_approval BOOLEAN DEFAULT 0,
            direct_superior_approval BOOLEAN DEFAULT 0,
            direct_superior_type VARCHAR(20),
            direct_superior_signature TEXT,
            direct_superior_signer_id INTEGER,
            applicant_signature TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            shift_code VARCHAR(10),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (approved_by) REFERENCES users (id),
            FOREIGN KEY (team_leader_signer_id) REFERENCES users (id),
            FOREIGN KEY (manager_signer_id) REFERENCES users (id),
            FOREIGN KEY (direct_superior_signer_id) REFERENCES users (id)
        )
        """
        
        cursor.execute(create_table_sql)
        print("✅ Đã tạo bảng leave_requests")
        
        # Tạo index cho hiệu năng
        indexes = [
            "CREATE INDEX idx_leave_requests_user_id ON leave_requests(user_id)",
            "CREATE INDEX idx_leave_requests_status ON leave_requests(status)",
            "CREATE INDEX idx_leave_requests_created_at ON leave_requests(created_at)",
            "CREATE INDEX idx_leave_requests_approved ON leave_requests(approved)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                print(f"✅ Đã tạo index: {index_sql.split()[-1]}")
            except sqlite3.Error as e:
                print(f"⚠️  Lỗi tạo index: {e}")
        
        # Commit changes
        conn.commit()
        print("💾 Đã commit các thay đổi")
        
        # Kiểm tra kết quả
        cursor.execute("PRAGMA table_info(leave_requests)")
        columns = cursor.fetchall()
        print(f"📋 Bảng leave_requests có {len(columns)} cột:")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        conn.close()
        
        print("🎉 Migration hoàn tất thành công!")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi migration: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 MIGRATION: Create Leave Requests Table")
    print("=" * 60)
    
    success = run_migration()
    
    if success:
        print("\n✅ Migration thành công!")
        print("   Bảng leave_requests đã được tạo với đầy đủ trường phê duyệt")
        print("   Hệ thống phê duyệt 3 cấp đã sẵn sàng hoạt động")
    else:
        print("\n❌ Migration thất bại!")
        print("   Vui lòng kiểm tra lỗi và thử lại")
    
    print("=" * 60)
