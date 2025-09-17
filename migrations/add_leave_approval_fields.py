#!/usr/bin/env python3
"""
Migration to add approval fields to leave_requests table
"""

import sqlite3
import os

def run_migration():
    """Add approved_by and approved_at fields to leave_requests table"""
    
    db_path = 'attendance.db'
    if not os.path.exists(db_path):
        db_path = 'instance/attendance.db'
    
    if not os.path.exists(db_path):
        print("Database file not found!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(leave_requests)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'approved_by' not in columns:
            cursor.execute("""
                ALTER TABLE leave_requests 
                ADD COLUMN approved_by INTEGER REFERENCES users(id)
            """)
            print("Added approved_by column")
        
        if 'approved_at' not in columns:
            cursor.execute("""
                ALTER TABLE leave_requests 
                ADD COLUMN approved_at DATETIME
            """)
            print("Added approved_at column")
        
        # Update status values for existing records
        cursor.execute("""
            UPDATE leave_requests 
            SET status = 'pending' 
            WHERE status NOT IN ('pending', 'pending_manager', 'pending_admin', 'approved', 'rejected')
        """)
        
        conn.commit()
        conn.close()
        
        print("Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    run_migration()
