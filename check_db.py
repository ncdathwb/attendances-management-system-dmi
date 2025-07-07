#!/usr/bin/env python3
import sqlite3
import os

def check_database():
    if not os.path.exists('attendance.db'):
        print("❌ Database file not found!")
        return
    
    try:
        conn = sqlite3.connect('attendance.db')
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📊 Tables found: {[t[0] for t in tables]}")
        
        # Check users
        if 'users' in [t[0] for t in tables]:
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"👥 Users: {user_count}")
        
        # Check attendance
        if 'attendance' in [t[0] for t in tables]:
            cursor.execute("SELECT COUNT(*) FROM attendance")
            attendance_count = cursor.fetchone()[0]
            print(f"📅 Attendance records: {attendance_count}")
        
        conn.close()
        print("✅ Database check completed!")
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == '__main__':
    check_database() 