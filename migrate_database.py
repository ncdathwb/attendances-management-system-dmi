#!/usr/bin/env python3
"""
Migration script for instance/attendance.db
"""
import sqlite3
import os

def migrate_database():
    """Migrate the ACTUAL database Flask is using."""
    
    # Target the instance database
    db_path = r'instance\attendance.db'
    
    print(f"📁 Target database: {os.path.abspath(db_path)}")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Starting migration on instance/attendance.db...")
        
        # --- Check current state ---
        cursor.execute("PRAGMA table_info(attendances)")
        att_columns = [col[1] for col in cursor.fetchall()]
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        print(f"\n📊 Current state:")
        print(f"  attendances.required_hours: {'✅ EXISTS' if 'required_hours' in att_columns else '❌ MISSING'}")
        print(f"  users.maternity_flex_from: {'✅ EXISTS' if 'maternity_flex_from' in user_columns else '❌ MISSING'}")
        print(f"  users.is_maternity_flex: {'✅ EXISTS' if 'is_maternity_flex' in user_columns else '❌ MISSING'}")
        print(f"  users.maternity_flex_until: {'✅ EXISTS' if 'maternity_flex_until' in user_columns else '❌ MISSING'}")
        
        # --- Add missing columns ---
        changes_made = False
        
        # users table
        if 'maternity_flex_from' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN maternity_flex_from DATE")
            print("✅ Added: users.maternity_flex_from")
            changes_made = True
        if 'is_maternity_flex' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN is_maternity_flex BOOLEAN DEFAULT 0")
            print("✅ Added: users.is_maternity_flex")
            changes_made = True
        
        if 'maternity_flex_until' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN maternity_flex_until DATE")
            print("✅ Added: users.maternity_flex_until")
            changes_made = True
        
        # attendances table
        if 'required_hours' not in att_columns:
            cursor.execute("ALTER TABLE attendances ADD COLUMN required_hours REAL DEFAULT 8.0")
            print("✅ Added: attendances.required_hours")
            changes_made = True
        
        # leave_requests table (bonus)
        cursor.execute("PRAGMA table_info(leave_requests)")
        leave_columns = [col[1] for col in cursor.fetchall()]
        
        # Security: Frozen mapping of column name -> validated SQL definition
        # Using a whitelist dictionary ensures both column name and definition are trusted
        LEAVE_COLUMN_DEFINITIONS = {
            'step': 'VARCHAR(20) DEFAULT "leader"',
            'current_approver_id': 'INTEGER',
            'reject_reason': 'TEXT',
            'team_leader_signature': 'TEXT',
            'team_leader_signer_id': 'INTEGER',
            'team_leader_approved_at': 'DATETIME',
            'manager_signature': 'TEXT',
            'manager_signer_id': 'INTEGER',
            'manager_approved_at': 'DATETIME',
            'admin_signature': 'TEXT',
            'admin_signer_id': 'INTEGER',
            'admin_approved_at': 'DATETIME'
        }

        for col_name, col_def in LEAVE_COLUMN_DEFINITIONS.items():
            if col_name not in leave_columns:
                try:
                    # Safe: col_name and col_def are from hardcoded whitelist above
                    cursor.execute(f"ALTER TABLE leave_requests ADD COLUMN {col_name} {col_def}")
                    print(f"✅ Added: leave_requests.{col_name}")
                    changes_made = True
                except sqlite3.Error as e:
                    print(f"⚠️  leave_requests.{col_name}: {e}")
        
        if not changes_made:
            print("\nℹ️  No changes needed - all columns already exist!")
        
        # Commit
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
        # Verify
        print("\n📊 Final verification:")
        cursor.execute("PRAGMA table_info(attendances)")
        att_final = [col[1] for col in cursor.fetchall()]
        cursor.execute("PRAGMA table_info(users)")
        user_final = [col[1] for col in cursor.fetchall()]
        
        print(f"  attendances.required_hours: {'✅' if 'required_hours' in att_final else '❌'}")
        print(f"  users.maternity_flex_from: {'✅' if 'maternity_flex_from' in user_final else '❌'}")
        print(f"  users.is_maternity_flex: {'✅' if 'is_maternity_flex' in user_final else '❌'}")
        print(f"  users.maternity_flex_until: {'✅' if 'maternity_flex_until' in user_final else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Instance Database Migration")
    print("=" * 60)
    
    success = migrate_database()
    
    if success:
        print("\n🎉 SUCCESS! Now restart Flask app:")
        print("   python app.py")
    else:
        print("\n💥 Migration failed!")