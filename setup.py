#!/usr/bin/env python3
"""
Automated Setup Script for Attendance Management System
Professional automated setup - just run and everything will be ready!
"""
import os
import sys
import subprocess
import time
from pathlib import Path

class AutoSetup:
    """Automated setup class for the attendance management system"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.env_file = self.project_root / '.env'
        self.requirements_file = self.project_root / 'requirements.txt'
        
    def print_banner(self):
        """Print welcome banner"""
        print("=" * 60)
        print("🚀 ATTENDANCE MANAGEMENT SYSTEM - AUTO SETUP")
        print("=" * 60)
        print("This script will automatically setup everything for you!")
        print("=" * 60)
        
    def check_python_version(self):
        """Check if Python version is compatible"""
        print("🐍 Checking Python version...")
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print("❌ Python 3.8+ is required!")
            print(f"Current version: {version.major}.{version.minor}.{version.micro}")
            return False
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
        
    def create_env_file(self):
        """Create .env file with default configuration"""
        print("📝 Creating environment configuration...")
        
        if self.env_file.exists():
            print("ℹ️  .env file already exists, skipping...")
            return True
            
        env_content = """# Attendance Management System Environment Configuration

# Database Configuration - SQLite Only
DATABASE_URL=sqlite:///attendance.db

# Flask Configuration
SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=development
FLASK_DEBUG=True

# Application Configuration
APP_NAME=Attendance Management System
APP_VERSION=1.0.0
"""
        
        try:
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)
            print("✅ .env file created successfully!")
            return True
        except Exception as e:
            print(f"❌ Error creating .env file: {e}")
            return False
            
    def install_dependencies(self):
        """Install Python dependencies"""
        print("📦 Installing Python dependencies...")
        
        # Choose requirements file based on platform
        if os.name == 'nt':  # Windows
            requirements_file = self.project_root / 'requirements-windows.txt'
            if not requirements_file.exists():
                requirements_file = self.requirements_file  # Fallback to original
        else:
            requirements_file = self.requirements_file
            
        if not requirements_file.exists():
            print("❌ requirements file not found!")
            return False
            
        try:
            # Upgrade pip first
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                         check=True, capture_output=True)
            
            # Install requirements
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)], 
                                  check=True, capture_output=True, text=True)
            
            print("✅ Dependencies installed successfully!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error installing dependencies: {e}")
            print(f"Error output: {e.stderr}")
            print("💡 Try using: pip install -r requirements-windows.txt")
            return False
            
    def setup_database(self):
        """Setup database using the database manager"""
        print("🗄️  Setting up database...")
        
        try:
            # Import and run database setup
            sys.path.append(str(self.project_root))
            from database.init_db import DatabaseManager
            
            db_manager = DatabaseManager()
            
            # Show database info
            db_manager.show_info()
            
            # Check if database already exists and has tables
            if db_manager.check_connection():
                print("ℹ️  Database connection successful!")
                
                # Check if tables exist
                import sqlite3
                try:
                    conn = sqlite3.connect(db_manager.db_file)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                    if cursor.fetchone():
                        print("ℹ️  Database schema already exists, skipping schema creation...")
                        cursor.close()
                        conn.close()
                        print("✅ Database setup completed!")
                        return True
                    cursor.close()
                    conn.close()
                except Exception:
                    pass  # Continue with schema creation if check fails
            
            # Create database
            if not db_manager.create_database():
                print("❌ Failed to create database!")
                return False
                
            # Create schema
            if not db_manager.create_schema():
                print("❌ Failed to create schema!")
                print("💡 If tables already exist, try: python database/init_db.py (option 5 to reset)")
                return False
                
            print("✅ Database setup completed!")
            return True
            
        except Exception as e:
            print(f"❌ Database setup error: {e}")
            return False
            
    def seed_data(self):
        """Seed initial data"""
        print("🌱 Seeding initial data...")
        
        try:
            # Set environment for Unicode support
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # Seed users
            print("   Creating users...")
            result = subprocess.run([sys.executable, 'seeds/users.py', 'seed'], 
                                  check=True, capture_output=True, text=True, encoding='utf-8', env=env)
            print("   ✅ Users seeded!")
            
            # Seed attendance data
            print("   Creating sample attendance data...")
            result = subprocess.run([sys.executable, 'seeds/attendance.py', 'seed', '30', '20'], 
                                  check=True, capture_output=True, text=True, encoding='utf-8', env=env)
            print("   ✅ Attendance data seeded!")
            
            print("✅ Data seeding completed!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Data seeding error: {e}")
            print(f"Error output: {e.stderr}")
            return False
            
    def create_startup_script(self):
        """Create startup script for easy application launch"""
        print("🚀 Creating startup script...")
        
        # Windows batch file
        startup_bat = self.project_root / 'start.bat'
        bat_content = """@echo off
echo Starting Attendance Management System...
echo.
python app.py
pause
"""
        
        # Linux/Mac shell script
        startup_sh = self.project_root / 'start.sh'
        sh_content = """#!/bin/bash
echo "Starting Attendance Management System..."
echo ""
python3 app.py
"""
        
        try:
            # Create Windows script
            with open(startup_bat, 'w', encoding='utf-8') as f:
                f.write(bat_content)
            
            # Create Linux/Mac script
            with open(startup_sh, 'w', encoding='utf-8') as f:
                f.write(sh_content)
            
            # Make shell script executable on Unix systems
            if os.name != 'nt':  # Not Windows
                os.chmod(startup_sh, 0o755)
                
            print("✅ Startup scripts created!")
            return True
            
        except Exception as e:
            print(f"❌ Error creating startup scripts: {e}")
            return False
            
    def create_readme(self):
        """Create comprehensive README file"""
        print("📖 Creating documentation...")
        
        readme_content = """# Attendance Management System

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)
```bash
python setup.py
```

### Option 2: Manual Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Setup database: `python database/init_db.py`
3. Seed data: `python seeds/users.py seed && python seeds/attendance.py seed`
4. Run application: `python app.py`

## 📋 System Requirements
- Python 3.8+
- SQLite (built into Python)
- 2GB RAM minimum

## 🔧 Configuration
Edit `.env` file to configure:
- Database connection
- Flask settings
- Application settings

## 👥 Default Users
- **Admin**: Employee ID `1395`, Password `dat123`
- **Other users**: See `user_list.txt` for details

## 🗄️ Database Management
- **Reset database**: `python database/init_db.py` (option 5)
- **Clear data**: `python seeds/users.py clear && python seeds/attendance.py clear`

## 🌐 Access Application
- URL: http://localhost:5000
- Default port: 5000

## 📁 Project Structure
```
attendance-management-system/
├── app.py                 # Main application
├── config.py             # Configuration
├── database/             # Database management
│   ├── models.py         # SQLAlchemy models
│   ├── schema.sql        # Database schema
│   └── init_db.py        # Database initialization
├── seeds/                # Data seeding
│   ├── users.py          # User seeding
│   └── attendance.py     # Attendance seeding
├── static/               # Static files (CSS, JS)
├── templates/            # HTML templates
└── requirements.txt      # Python dependencies
```

## 🔒 Security Notes
- Change default passwords in production
- Update SECRET_KEY in .env file
- Configure proper database credentials
- Enable HTTPS in production

## 🐛 Troubleshooting
1. **Database connection error**: Check SQLite file permissions and disk space
2. **Port already in use**: Change port in app.py or kill existing process
3. **Import errors**: Ensure all dependencies are installed

## 📞 Support
For issues and questions, check the logs or contact the development team.
"""
        
        try:
            with open(self.project_root / 'README.md', 'w', encoding='utf-8') as f:
                f.write(readme_content)
            print("✅ Documentation created!")
            return True
        except Exception as e:
            print(f"❌ Error creating documentation: {e}")
            return False
            
    def run_tests(self):
        """Run basic system tests"""
        print("🧪 Running system tests...")
        
        try:
            # Test database connection
            sys.path.append(str(self.project_root))
            from database.init_db import DatabaseManager
            
            db_manager = DatabaseManager()
            if db_manager.check_connection():
                print("   ✅ Database connection test passed!")
            else:
                print("   ❌ Database connection test failed!")
                return False
                
            # Test imports
            try:
                from app import app
                print("   ✅ Application import test passed!")
            except Exception as e:
                print(f"   ❌ Application import test failed: {e}")
                return False
                
            print("✅ All tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            return False
            
    def show_success_message(self):
        """Show success message with next steps"""
        print("\n" + "=" * 60)
        print("🎉 SETUP COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\n📋 What's been set up:")
        print("   ✅ Python environment configured")
        print("   ✅ Dependencies installed")
        print("   ✅ Database created and configured")
        print("   ✅ Sample data seeded")
        print("   ✅ Startup scripts created")
        print("   ✅ Documentation generated")
        print("   ✅ System tests passed")
        
        print("\n🚀 Next Steps:")
        print("   1. Start the application:")
        if os.name == 'nt':  # Windows
            print("      Double-click 'start.bat' or run: python app.py")
        else:  # Linux/Mac
            print("      Run: ./start.sh or python app.py")
        
        print("   2. Open your browser and go to: http://localhost:5000")
        print("   3. Login with:")
        print("      - Employee ID: 1395")
        print("      - Password: dat123")
        
        print("\n📚 Useful Commands:")
        print("   - Reset database: python database/init_db.py")
        print("   - Clear data: python seeds/users.py clear")
        print("   - Add more data: python seeds/attendance.py seed")
        
        print("\n🔧 Configuration:")
        print("   - Edit .env file to change database settings")
        print("   - Edit config.py for application settings")
        
        print("\n📖 Documentation:")
        print("   - See README.md for detailed information")
        print("   - Check user_list.txt for all user accounts")
        
        print("\n" + "=" * 60)
        print("🎯 Your Attendance Management System is ready!")
        print("=" * 60)
        
    def run_full_setup(self):
        """Run complete automated setup"""
        self.print_banner()
        
        # Set environment variables
        os.environ['FLASK_CONFIG'] = 'development'
        os.environ['FLASK_DEBUG'] = 'False'  # Set to False for production
        os.environ['SECRET_KEY'] = 'your-production-secret-key-change-this'
        
        steps = [
            ("Checking Python version", self.check_python_version),
            ("Creating environment config", self.create_env_file),
            ("Installing dependencies", self.install_dependencies),
            ("Setting up database", self.setup_database),
            ("Seeding initial data", self.seed_data),
            ("Creating startup scripts", self.create_startup_script),
            ("Creating documentation", self.create_readme),
            ("Running system tests", self.run_tests)
        ]
        
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            if not step_func():
                print(f"\n❌ Setup failed at: {step_name}")
                print("Please check the error messages above and try again.")
                return False
            time.sleep(1)  # Small delay for better UX
            
        self.show_success_message()
        return True

def main():
    """Main function"""
    setup = AutoSetup()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'test':
            setup.run_tests()
        elif command == 'db':
            setup.setup_database()
        elif command == 'seed':
            setup.seed_data()
        else:
            print("Usage: python setup.py [test|db|seed]")
    else:
        setup.run_full_setup()

if __name__ == '__main__':
    main() 