#!/usr/bin/env python3
"""
Check which database file Flask is actually using
"""
import os
import sys
import sqlite3

print("🔍 Database Path Detective")
print("=" * 60)

# Method 1: Check all .db files in project
print("\n📂 All .db files found in project:")
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.db'):
            full_path = os.path.abspath(os.path.join(root, file))
            print(f"  ➜ {full_path}")
            
            # Check if it has required_hours column
            try:
                conn = sqlite3.connect(full_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(attendances)")
                cols = [col[1] for col in cursor.fetchall()]
                has_required = 'required_hours' in cols
                
                cursor.execute("PRAGMA table_info(users)")
                user_cols = [col[1] for col in cursor.fetchall()]
                has_maternity = 'is_maternity_flex' in user_cols
                has_maternity_from = 'maternity_flex_from' in user_cols
                has_maternity_until = 'maternity_flex_until' in user_cols
                
                status = "✅" if (has_required and has_maternity and has_maternity_from and has_maternity_until) else "❌"
                print(f"     {status} required_hours: {has_required}, is_maternity_flex: {has_maternity}, maternity_flex_from: {has_maternity_from}, maternity_flex_until: {has_maternity_until}")
                conn.close()
            except Exception as e:
                print(f"     ⚠️  Error checking: {e}")

# Method 2: Try to import Flask app and check config
print("\n🔧 Checking Flask config:")
try:
    sys.path.insert(0, os.getcwd())
    
    # Try to get config without running the app
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Find SQLALCHEMY_DATABASE_URI
    import re
    pattern = r"SQLALCHEMY_DATABASE_URI\s*=\s*['\"]([^'\"]+)['\"]"
    matches = re.findall(pattern, content)
    
    if matches:
        for match in matches:
            print(f"  Found config: {match}")
            if match.startswith('sqlite:///'):
                db_file = match.replace('sqlite:///', '')
                db_path = os.path.abspath(db_file)
                print(f"  Absolute path: {db_path}")
                print(f"  File exists: {os.path.exists(db_path)}")
    else:
        print("  ⚠️  Could not find SQLALCHEMY_DATABASE_URI in app.py")
        print("  Searching in all Python files...")
        
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            if 'SQLALCHEMY_DATABASE_URI' in f.read():
                                print(f"  Found in: {filepath}")
                    except:
                        pass
                        
except Exception as e:
    print(f"  ⚠️  Error: {e}")

print("\n" + "=" * 60)
print("💡 Solution:")
print("1. Find which .db file has ❌ (missing columns)")
print("2. Run migration on that specific file")
print("3. Or update Flask config to use the ✅ file")