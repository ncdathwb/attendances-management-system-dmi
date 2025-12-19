"""
Real-time updates utilities for immediate data refresh
"""
from flask import session, request
from database.models import db, Attendance, User, LeaveRequest
from sqlalchemy import func
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_realtime_pending_count(user_id, current_role):
    """
    Get real-time pending count for current role
    """
    try:
        user = db.session.get(User, user_id)
        if not user:
            return 0
        
        if current_role == 'TEAM_LEADER':
            # Count team members' pending records
            # Sử dụng so sánh không phân biệt hoa thường
            user_dept = (user.department or '').strip().upper()
            team_user_ids = db.session.query(User.id).filter(
                func.upper(func.trim(User.department)) == user_dept,
                User.is_deleted == False
            ).scalar_subquery()
            
            count = db.session.query(func.count(Attendance.id)).filter(
                Attendance.approved == False,
                Attendance.status == 'pending',
                Attendance.user_id.in_(team_user_ids)
            ).scalar()
            
        elif current_role == 'MANAGER':
            # Count department pending records
            count = db.session.query(func.count(Attendance.id)).join(
                Attendance.user
            ).filter(
                Attendance.approved == False,
                Attendance.status == 'pending_manager',
                User.department == user.department,
                User.is_deleted == False
            ).scalar()
            
        elif current_role == 'ADMIN':
            # Count all pending records
            count = db.session.query(func.count(Attendance.id)).filter(
                Attendance.approved == False,
                Attendance.status == 'pending_admin'
            ).scalar()
            
        else:
            count = 0
            
        return count or 0
        
    except Exception as e:
        logger.error(f"Error getting realtime pending count: {e}")
        return 0

def get_realtime_leave_pending_count(user_id, current_role):
    """
    Get real-time pending leave requests count
    """
    try:
        user = db.session.get(User, user_id)
        if not user:
            return 0
        
        if current_role == 'TEAM_LEADER':
            # Count team members' pending leave requests
            # Sử dụng so sánh không phân biệt hoa thường
            user_dept = (user.department or '').strip().upper()
            team_user_ids = db.session.query(User.id).filter(
                func.upper(func.trim(User.department)) == user_dept,
                User.is_deleted == False
            ).scalar_subquery()
            
            count = db.session.query(func.count(LeaveRequest.id)).filter(
                LeaveRequest.status == 'pending',
                LeaveRequest.user_id.in_(team_user_ids)
            ).scalar()
            
        elif current_role == 'MANAGER':
            # MANAGER đếm đơn pending_manager (đã được TEAM_LEADER phê duyệt)
            count = db.session.query(func.count(LeaveRequest.id)).filter(
                LeaveRequest.status == 'pending_manager'
            ).scalar()
            
        elif current_role == 'ADMIN':
            # ADMIN đếm đơn pending_admin (đã được MANAGER phê duyệt)
            count = db.session.query(func.count(LeaveRequest.id)).filter(
                LeaveRequest.status == 'pending_admin'
            ).scalar()
            
        else:
            count = 0
            
        return count or 0
        
    except Exception as e:
        logger.error(f"Error getting realtime leave pending count: {e}")
        return 0

def invalidate_role_cache(user_id, current_role):
    """
    Invalidate cache for specific role and user
    """
    try:
        # Clear any cached data for this user/role combination
        cache_key = f"user_{user_id}_role_{current_role}"
        
        # In a real implementation, you would clear from Redis or memcached
        # For now, we'll just log the cache invalidation
        logger.info(f"Cache invalidated for {cache_key}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return False

def get_fresh_attendance_data(user_id, current_role, filters=None):
    """
    Get fresh attendance data without cache
    """
    try:
        user = db.session.get(User, user_id)
        if not user:
            return []
        
        # Build query based on role
        if current_role == 'ADMIN':
            query = db.session.query(Attendance).options(
                db.joinedload(Attendance.user).load_only(User.name, User.employee_id, User.department)
            )
        else:
            query = db.session.query(Attendance).filter_by(user_id=user.id)
        
        # Apply filters if provided
        if filters:
            if filters.get('search'):
                search = filters['search'].lower()
                query = query.join(Attendance.user).filter(
                    func.lower(User.name).contains(search)
                )
            
            if filters.get('date_from'):
                query = query.filter(Attendance.date >= filters['date_from'])
            
            if filters.get('date_to'):
                query = query.filter(Attendance.date <= filters['date_to'])
        
        # Get recent records (last 30 days)
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        query = query.filter(Attendance.date >= thirty_days_ago)
        
        # Order by date desc and limit
        records = query.order_by(Attendance.date.desc()).limit(100).all()
        
        return records
        
    except Exception as e:
        logger.error(f"Error getting fresh attendance data: {e}")
        return []

def check_data_freshness(user_id, current_role):
    """
    Check if data needs refresh based on recent activity
    """
    try:
        # Check for recent attendance submissions (last 5 minutes)
        recent_threshold = datetime.now() - timedelta(minutes=5)
        
        recent_count = db.session.query(func.count(Attendance.id)).filter(
            Attendance.created_at >= recent_threshold
        ).scalar()
        
        # Check for recent approvals (last 2 minutes)
        approval_threshold = datetime.now() - timedelta(minutes=2)
        
        recent_approvals = db.session.query(func.count(Attendance.id)).filter(
            Attendance.approved_at >= approval_threshold
        ).scalar()
        
        # Data needs refresh if there's recent activity
        needs_refresh = (recent_count > 0) or (recent_approvals > 0)
        
        return {
            'needs_refresh': needs_refresh,
            'recent_submissions': recent_count or 0,
            'recent_approvals': recent_approvals or 0,
            'last_check': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking data freshness: {e}")
        return {
            'needs_refresh': True,  # Default to refresh on error
            'recent_submissions': 0,
            'recent_approvals': 0,
            'last_check': datetime.now().isoformat()
        }
