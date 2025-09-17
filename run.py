#!/usr/bin/env python3
"""
Enhanced startup script for the attendance management system
Handles Unicode encoding issues and provides better error handling
"""
import os
import sys
import logging
from app import app, db

def setup_unicode_environment():
    """Setup Unicode environment for Windows"""
    if os.name == 'nt':  # Windows
        # Set environment variables for Unicode support
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        
        # Configure stdout and stderr for UTF-8
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
        
        # Set console code page to UTF-8 (Windows 10+)
        try:
            os.system('chcp 65001 > nul')
        except:
            pass

def setup_logging():
    """Setup proper logging configuration"""
    # Create logs directory
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress SQLAlchemy warnings
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

def main():
    """Main application entry point"""
    try:
        # Setup environment
        setup_unicode_environment()
        setup_logging()
        
        print("🚀 Starting Attendance Management System...")
        print("📝 Unicode support: Enabled")
        print("📊 Database: SQLite")
        
        # Initialize database
        with app.app_context():
            db.create_all()
            print("✅ Database initialized")
        
        # Production-ready settings
        debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
        host = os.environ.get('FLASK_HOST', '0.0.0.0')
        port = int(os.environ.get('FLASK_PORT', 5000))
        
        print(f"🌐 Server: http://{host}:{port}")
        print(f"🔧 Debug mode: {'ON' if debug_mode else 'OFF'}")
        print("=" * 50)
        
        # Start the application
        app.run(
            debug=debug_mode, 
            host=host, 
            port=port,
            use_reloader=debug_mode
        )
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Startup error: {e}")
        logging.error(f"Startup error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 