#!/usr/bin/env python3
"""
Database Initialization Script
SQLite-only database setup for Attendance Management System
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseManager:
    """SQLite database management class"""
    
    def __init__(self):
        # SQLite configuration
        self.db_file = os.environ.get('DATABASE_URL', 'sqlite:///attendance.db').replace('sqlite:///', '')
        if self.db_file.startswith('/'):
            self.db_file = self.db_file[1:]
    
    def create_database(self):
        """Create SQLite database if it doesn't exist"""
        return self._create_sqlite_database()
    
    def _create_sqlite_database(self):
        """Create SQLite database"""
        try:
            # SQLite database is created automatically when first accessed
            # Just ensure the directory exists
            db_dir = os.path.dirname(self.db_file)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            print(f"✅ SQLite database '{self.db_file}' will be created automatically!")
            return True
            
        except Exception as e:
            print(f"❌ SQLite database creation error: {e}")
            return False
    
    def drop_database(self):
        """Drop SQLite database if it exists"""
        return self._drop_sqlite_database()
    
    def _drop_sqlite_database(self):
        """Drop SQLite database"""
        try:
            if os.path.exists(self.db_file):
                os.remove(self.db_file)
                print(f"✅ SQLite database '{self.db_file}' dropped successfully!")
            else:
                print(f"ℹ️  SQLite database '{self.db_file}' doesn't exist.")
            return True
            
        except Exception as e:
            print(f"❌ SQLite database drop error: {e}")
            return False
    
    def create_schema(self):
        """Create database schema using SQLite file"""
        try:
            return self._create_sqlite_schema()
        except Exception as e:
            print(f"❌ Schema creation error: {e}")
            return False
    
    def _create_sqlite_schema(self):
        """Create SQLite schema"""
        try:
            import sqlite3
            
            # Connect to SQLite database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Check if tables already exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if cursor.fetchone():
                print("ℹ️  Database schema already exists!")
                cursor.close()
                conn.close()
                return True
            
            # Use SQLite-specific schema file
            schema_file = os.path.join(os.path.dirname(__file__), 'schema-sqlite.sql')
            if not os.path.exists(schema_file):
                # Fallback to main schema file
                schema_file = os.path.join(os.path.dirname(__file__), 'schema.sql')
            
            try:
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
            except UnicodeDecodeError:
                # Try with different encoding if UTF-8 fails
                with open(schema_file, 'r', encoding='latin-1') as f:
                    schema_sql = f.read()
            
            # Execute schema
            cursor.executescript(schema_sql)
            conn.commit()
            
            print("✅ SQLite schema created successfully!")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ SQLite schema creation error: {e}")
            return False
    
    def reset_database(self):
        """Reset database (drop and recreate)"""
        print("🔄 Resetting database...")
        if self.drop_database():
            if self.create_database():
                if self.create_schema():
                    print("✅ Database reset completed successfully!")
                    return True
        return False
    
    def check_connection(self):
        """Test database connection"""
        return self._check_sqlite_connection()
    
    def _check_sqlite_connection(self):
        """Test SQLite connection"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_version();")
            version = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            print(f"✅ SQLite connection successful!")
            print(f"📊 SQLite version: {version[0]}")
            return True
            
        except Exception as e:
            print(f"❌ SQLite connection failed: {e}")
            return False
    
    def show_info(self):
        """Show database information"""
        print(f"📊 Database Type: SQLite")
        print(f"📁 Database File: {self.db_file}")
        print(f"🔧 Driver: Built-in SQLite (Python)")
        
        # Test connection
        if self.check_connection():
            print(f"✅ Status: Connected")
        else:
            print(f"❌ Status: Connection failed")

def main():
    """Main function for command line usage"""
    db_manager = DatabaseManager()
    
    if len(sys.argv) < 2:
        print("Usage: python init_db.py [create|drop|reset|check|info]")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'create':
        print("🔧 Creating database...")
        if db_manager.create_database():
            if db_manager.create_schema():
                print("✅ Database setup completed!")
            else:
                print("❌ Schema creation failed!")
        else:
            print("❌ Database creation failed!")
    
    elif command == 'drop':
        print("🗑️  Dropping database...")
        if db_manager.drop_database():
            print("✅ Database dropped successfully!")
        else:
            print("❌ Database drop failed!")
    
    elif command == 'reset':
        if db_manager.reset_database():
            print("✅ Database reset completed!")
        else:
            print("❌ Database reset failed!")
    
    elif command == 'check':
        print("🔍 Checking database connection...")
        db_manager.check_connection()
    
    elif command == 'info':
        print("ℹ️  Database Information:")
        db_manager.show_info()
    
    else:
        print("❌ Unknown command. Use: create|drop|reset|check|info")

if __name__ == '__main__':
    main() 