import os
from datetime import timedelta
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

load_dotenv()

def derive_fernet_key_from_secret(secret, salt) -> bytes:
    """Derive a stable Fernet key (urlsafe base64) from SECRET_KEY and a salt."""
    secret_bytes = secret.encode('utf-8') if isinstance(secret, str) else secret
    salt_bytes = salt.encode('utf-8') if isinstance(salt, str) else salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt_bytes,
        iterations=390000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret_bytes))

class Config:
    # Use fixed default as requested; prefer env if provided
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dmi'
    
    # CSRF Configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Session Configuration
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_REFRESH_EACH_REQUEST = True
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
    }
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    
    # Database Configuration - SQLite Only
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///attendance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
    }
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/attendance.log')
    
    # Email Configuration (for notifications) - SECURE: No hardcoded credentials
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Production settings
    DEBUG = False
    TESTING = False

    # Signature System Configuration
    _ENV_SIGNATURE_KEY = os.environ.get('SIGNATURE_SECRET_KEY')
    if _ENV_SIGNATURE_KEY:
        # Ensure bytes for Fernet
        SIGNATURE_SECRET_KEY = _ENV_SIGNATURE_KEY.encode('utf-8')
    else:
        # Derive a stable Fernet key from SECRET_KEY to keep decryption consistent across restarts
        _SIGN_SALT = os.environ.get('SIGNATURE_KEY_SALT', 'dmi_signature_salt')
        SIGNATURE_SECRET_KEY = derive_fernet_key_from_secret(SECRET_KEY, _SIGN_SALT)
    SIGNATURE_SESSION_TIMEOUT = int(os.environ.get('SIGNATURE_SESSION_TIMEOUT', 1800))  # 30 minutes

    # SMTP Configuration (no personal defaults). Configure via environment /.env
    SMTP_SERVER = os.environ.get('SMTP_SERVER')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    MAIL_FROM = os.environ.get('MAIL_FROM') or os.environ.get('SMTP_USER')
    
    # HR Email Configuration
    HR_EMAIL = os.environ.get('HR_EMAIL') or 'dmihue-nhansu01@acraft.jp'

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False
    SECURITY_HEADERS = {}

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # Additional production security settings
    SESSION_COOKIE_SAMESITE = 'Strict'
    WTF_CSRF_TIME_LIMIT = 1800

class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

    # SMTP Configuration for password reset - SECURE: No hardcoded credentials
    SMTP_SERVER = os.environ.get('SMTP_SERVER')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    MAIL_FROM = os.environ.get('MAIL_FROM')

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 