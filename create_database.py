#!/usr/bin/env python3
"""
Script tạo database PostgreSQL cho hệ thống chấm công DMI
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

def create_database():
    """Tạo database PostgreSQL"""
    
    # Thông tin kết nối PostgreSQL
    DB_USER = os.environ.get('DB_USER') or 'postgres'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'password'
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_PORT = os.environ.get('DB_PORT') or '5432'
    DB_NAME = os.environ.get('DB_NAME') or 'attendance_db'
    
    try:
        # Kết nối đến PostgreSQL server (không chỉ định database cụ thể)
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database='postgres'  # Kết nối đến database mặc định
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Kiểm tra xem database đã tồn tại chưa
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()
        
        if not exists:
            # Tạo database mới
            cursor.execute(f'CREATE DATABASE {DB_NAME}')
            print(f"✅ Đã tạo database '{DB_NAME}' thành công!")
        else:
            print(f"ℹ️  Database '{DB_NAME}' đã tồn tại.")
        
        cursor.close()
        conn.close()
        
        print("🎉 Database đã sẵn sàng để sử dụng!")
        print(f"📝 Thông tin kết nối:")
        print(f"   - Host: {DB_HOST}")
        print(f"   - Port: {DB_PORT}")
        print(f"   - Database: {DB_NAME}")
        print(f"   - User: {DB_USER}")
        
    except psycopg2.Error as e:
        print(f"❌ Lỗi khi tạo database: {e}")
        print("\n🔧 Hướng dẫn khắc phục:")
        print("1. Đảm bảo PostgreSQL đã được cài đặt")
        print("2. Kiểm tra thông tin kết nối trong file .env")
        print("3. Đảm bảo user có quyền tạo database")
        print("4. Kiểm tra PostgreSQL service đang chạy")
        
    except Exception as e:
        print(f"❌ Lỗi không xác định: {e}")

def drop_database():
    """Xóa database PostgreSQL"""
    
    DB_USER = os.environ.get('DB_USER') or 'postgres'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'password'
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_PORT = os.environ.get('DB_PORT') or '5432'
    DB_NAME = os.environ.get('DB_NAME') or 'attendance_db'
    
    try:
        # Kết nối đến PostgreSQL server
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Kiểm tra xem database có tồn tại không
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()
        
        if exists:
            # Xóa database
            cursor.execute(f'DROP DATABASE {DB_NAME}')
            print(f"✅ Đã xóa database '{DB_NAME}' thành công!")
        else:
            print(f"ℹ️  Database '{DB_NAME}' không tồn tại.")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ Lỗi khi xóa database: {e}")
    except Exception as e:
        print(f"❌ Lỗi không xác định: {e}")

if __name__ == '__main__':
    print("🗄️  PostgreSQL Database Manager")
    print("=" * 40)
    
    while True:
        print("\nChọn hành động:")
        print("1. Tạo database")
        print("2. Xóa database")
        print("3. Thoát")
        
        choice = input("\nNhập lựa chọn (1-3): ").strip()
        
        if choice == '1':
            create_database()
        elif choice == '2':
            confirm = input("⚠️  Bạn có chắc chắn muốn xóa database? (y/N): ").strip().lower()
            if confirm == 'y':
                drop_database()
            else:
                print("❌ Đã hủy thao tác xóa database.")
        elif choice == '3':
            print("👋 Tạm biệt!")
            break
        else:
            print("❌ Lựa chọn không hợp lệ. Vui lòng chọn lại!") 