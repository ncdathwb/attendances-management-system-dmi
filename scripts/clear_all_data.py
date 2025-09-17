#!/usr/bin/env python3
"""
Script to clear all data from the database for testing purposes
"""

import sys
import os

# Add the parent directory to the path so we can import from the main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import User, Attendance, AuditLog

def clear_all_data():
    """Clear all data from the database"""
    with app.app_context():
        try:
            print("🗑️ Clearing all data from database...")
            
            # Clear all tables in reverse order of dependencies
            print("  - Clearing audit logs...")
            AuditLog.query.delete()
            
            print("  - Clearing attendance records...")
            Attendance.query.delete()
            
            print("  - Clearing users...")
            User.query.delete()
            
            # Commit the changes
            db.session.commit()
            
            print("✅ All data cleared successfully!")
            print("📊 Database is now empty and ready for testing.")
            
        except Exception as e:
            print(f"❌ Error clearing data: {str(e)}")
            db.session.rollback()
            return False
    
    return True

if __name__ == "__main__":
    print("🧹 Database Cleanup Tool")
    print("=" * 50)
    
    # Ask for confirmation
    response = input("⚠️  This will DELETE ALL DATA from the database. Are you sure? (yes/no): ")
    
    if response.lower() in ['yes', 'y', 'có']:
        if clear_all_data():
            print("\n🎉 Database cleanup completed successfully!")
            print("You can now test the signature check feature with a fresh database.")
        else:
            print("\n💥 Database cleanup failed!")
    else:
        print("❌ Operation cancelled.") 