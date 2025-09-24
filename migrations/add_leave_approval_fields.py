#!/usr/bin/env python3
"""
Migration: Add approval fields to leave_requests table
Thêm các trường phê duyệt cho đơn nghỉ phép giống chấm công
"""

import sqlite3
import os
from datetime import datetime

def run_migration():
    """Thêm các cột mới vào bảng leave_requests"""
    
    # Đường dẫn database
    db_path = 'attendance.db'
    if not os.path.exists(db_path):
        print(f"❌ Không tìm thấy database: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Bắt đầu migration: Thêm trường phê duyệt cho leave_requests...")
        
        # Kiểm tra các cột đã tồn tại
        cursor.execute("PRAGMA table_info(leave_requests)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 Các cột hiện tại: {existing_columns}")
        
        # Danh sách cột cần thêm
        new_columns = [
            ("approved", "BOOLEAN DEFAULT 0", "Đã phê duyệt hoàn tất"),
            ("approved_by", "INTEGER", "ID người phê duyệt cuối cùng"),
            ("approved_at", "DATETIME", "Thời gian phê duyệt cuối cùng"),
            ("team_leader_signature", "TEXT", "Chữ ký trưởng nhóm"),
            ("team_leader_signer_id", "INTEGER", "ID người ký trưởng nhóm")
        ]
        
        # Thêm từng cột nếu chưa tồn tại
        for column_name, column_type, description in new_columns:
            if column_name not in existing_columns:
                try:
                    sql = f"ALTER TABLE leave_requests ADD COLUMN {column_name} {column_type}"
                    cursor.execute(sql)
                    print(f"✅ Đã thêm cột: {column_name} ({description})")
                except sqlite3.Error as e:
                    print(f"❌ Lỗi thêm cột {column_name}: {e}")
                    return False
            else:
                print(f"⏭️  Cột {column_name} đã tồn tại, bỏ qua")
        
        # Thêm foreign key constraints nếu cần
        try:
            # Kiểm tra xem có cần thêm foreign key không
            cursor.execute("PRAGMA foreign_keys")
            fk_enabled = cursor.fetchone()[0]
            if fk_enabled:
                print("🔗 Foreign keys đã được bật")
            else:
                print("⚠️  Foreign keys chưa được bật")
        except:
            pass
        
        # Commit changes
        conn.commit()
        print("💾 Đã commit các thay đổi")
        
        # Kiểm tra kết quả
        cursor.execute("PRAGMA table_info(leave_requests)")
        final_columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 Các cột sau migration: {final_columns}")
        
        # Cập nhật dữ liệu hiện tại
        print("🔄 Cập nhật dữ liệu hiện tại...")
        
        # Set approved = 1 cho các đơn đã approved
        cursor.execute("""
            UPDATE leave_requests 
            SET approved = 1, approved_at = updated_at 
            WHERE status = 'approved'
        """)
        updated_count = cursor.rowcount
        print(f"✅ Đã cập nhật {updated_count} đơn nghỉ phép đã được phê duyệt")
        
        conn.commit()
        conn.close()
        
        print("🎉 Migration hoàn tất thành công!")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi migration: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def rollback_migration():
    """Rollback migration (xóa các cột đã thêm)"""
    print("⚠️  Rollback migration không được hỗ trợ cho SQLite")
    print("   Cần tạo bảng mới và migrate dữ liệu thủ công")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 MIGRATION: Add Leave Request Approval Fields")
    print("=" * 60)
    
    success = run_migration()
    
    if success:
        print("\n✅ Migration thành công!")
        print("   Các trường mới đã được thêm vào bảng leave_requests")
        print("   Hệ thống phê duyệt 3 cấp đã sẵn sàng hoạt động")
    else:
        print("\n❌ Migration thất bại!")
        print("   Vui lòng kiểm tra lỗi và thử lại")
    
    print("=" * 60)
