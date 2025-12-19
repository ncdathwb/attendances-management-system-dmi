"""
Quick fix script to add the missing timesheet_file column to the departments table.
Run this script to fix the OperationalError.
"""
import sqlite3
import os

# Database file paths - check both locations
db_paths = ['instance/attendance.db', 'attendance.db']

# Process all database files
fixed_count = 0
for db_path in db_paths:
    if not os.path.exists(db_path):
        print(f"⚠️  Database file not found: {db_path} (skipping)")
        continue
    
    try:
        print(f"\n📂 Processing: {db_path}")
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(departments)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'timesheet_file' in columns:
            print(f"✅ Column 'timesheet_file' already exists in {db_path}")
        else:
            # Add the column
            cursor.execute("""
                ALTER TABLE departments 
                ADD COLUMN timesheet_file VARCHAR(100) NULL
            """)
            conn.commit()
            print(f"✅ Successfully added 'timesheet_file' column to {db_path}")
            fixed_count += 1
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error in {db_path}: {e}")
    except Exception as e:
        print(f"❌ Error processing {db_path}: {e}")

if fixed_count > 0:
    print(f"\n✅ Fixed {fixed_count} database file(s)!")
else:
    print("\n✅ All databases already have the column!")
print("\n✅ Database fix completed!")

