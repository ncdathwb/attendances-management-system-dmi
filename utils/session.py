"""
Session management utilities for the attendance management system
"""
from datetime import datetime, timedelta, time
from flask import request, session
from database.models import db, AuditLog

def check_session_timeout():
    """Check if session has timed out"""
    if 'last_activity' in session:
        last_activity = datetime.fromisoformat(session['last_activity'])
        if datetime.now() - last_activity > timedelta(minutes=30):
            session.clear()
            return True
    return False

def update_session_activity():
    """Update last activity time in session"""
    session['last_activity'] = datetime.now().isoformat()

def log_audit_action(user_id, action, table_name, record_id=None, old_values=None, new_values=None):
    """Log audit action to database"""
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        print(f"Error logging audit action: {e}")
        db.session.rollback() 