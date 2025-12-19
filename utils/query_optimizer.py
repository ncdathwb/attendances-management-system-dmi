"""
Query optimization utilities for fastest database operations
"""
from functools import wraps
from flask import current_app
from sqlalchemy.orm import joinedload, selectinload, load_only
from sqlalchemy import func, and_, or_
from database.models import db, Attendance, User, Request, LeaveRequest
import time
import logging

logger = logging.getLogger(__name__)

def optimize_attendance_history_query(search=None, department=None, date_from=None, date_to=None, 
                                    user_id=None, page=1, per_page=20, is_admin=False):
    """
    Optimized attendance history query with minimal database hits
    """
    # Base query with optimized joins
    if is_admin:
        # Chỉ lấy những bản ghi đã được phê duyệt (approved == True và approved_by IS NOT NULL)
        q = db.session.query(Attendance).filter(
            Attendance.approved == True,
            Attendance.approved_by.isnot(None)
        ).options(
            joinedload(Attendance.user).load_only(User.name, User.employee_id, User.department),
            joinedload(Attendance.approver).load_only(User.name, User.employee_id)
        )
    else:
        q = db.session.query(Attendance).filter_by(user_id=user_id).options(
            joinedload(Attendance.approver).load_only(User.name, User.employee_id)
        )
    
    # Apply filters efficiently
    if search:
        search_words = search.lower().strip().split()
        if is_admin:
            # Use subquery for better performance
            user_subq = db.session.query(User.id).filter(
                or_(
                    *[func.lower(User.name).contains(word) for word in search_words],
                    func.lower(func.cast(User.employee_id, db.String)).contains(search.lower())
                )
            ).subquery()
            q = q.join(user_subq, Attendance.user_id == user_subq.c.id)
        else:
            # For single user, search in notes only
            q = q.filter(or_(*[func.lower(Attendance.note).contains(word) for word in search_words]))
    
    if department and is_admin:
        q = q.join(Attendance.user).filter(User.department == department)
    
    if date_from:
        q = q.filter(Attendance.date >= date_from)
    if date_to:
        q = q.filter(Attendance.date <= date_to)
    
    # Get total count efficiently (without loading data)
    total = q.count()
    
    # Apply pagination and ordering
    records = q.order_by(Attendance.date.desc()).offset((page-1)*per_page).limit(per_page).all()
    
    return records, total

def optimize_pending_attendance_query(current_role, user, search=None, department=None, 
                                    date_from=None, date_to=None, page=1, per_page=20):
    """
    Optimized pending attendance query with role-based optimization
    """
    # Build query based on role
    if current_role == 'TEAM_LEADER':
        # Pre-filter team users for better performance
        # Sử dụng so sánh không phân biệt hoa thường để tránh lỗi matching
        user_dept = (user.department or '').strip().upper()
        
        # Debug: đếm số nhân viên cùng phòng ban
        team_count = db.session.query(func.count(User.id)).filter(
            func.upper(func.trim(User.department)) == user_dept,
            User.is_deleted == False
        ).scalar()
        print(f"🔍 [QUERY_OPT] TEAM_LEADER dept: [{user.department}] -> upper: [{user_dept}]", flush=True)
        print(f"🔍 [QUERY_OPT] Found {team_count} users in same department", flush=True)
        
        # Debug: đếm tổng số pending attendance
        total_pending = db.session.query(func.count(Attendance.id)).filter(
            Attendance.approved == False,
            Attendance.status == 'pending'
        ).scalar()
        print(f"🔍 [QUERY_OPT] Total pending attendance in DB: {total_pending}", flush=True)
        
        team_user_ids = db.session.query(User.id).filter(
            func.upper(func.trim(User.department)) == user_dept,
            User.is_deleted == False
        ).scalar_subquery()
        
        q = db.session.query(Attendance).filter(
            Attendance.approved == False,
            Attendance.status == 'pending',
            Attendance.user_id.in_(team_user_ids)
        )
    elif current_role == 'MANAGER':
        q = db.session.query(Attendance).filter(
            Attendance.approved == False,
            Attendance.status == 'pending_manager'
        )
        if department:
            q = q.join(Attendance.user).filter(User.department == department)
    else:  # ADMIN
        q = db.session.query(Attendance).filter(
            Attendance.approved == False,
            Attendance.status == 'pending_admin'
        )
    
    # Apply search efficiently
    if search:
        search_words = search.lower().strip().split()
        user_subq = db.session.query(User.id).filter(
            and_(
                User.is_deleted == False,
                or_(
                    *[func.lower(User.name).contains(word) for word in search_words],
                    func.lower(func.cast(User.employee_id, db.String)).contains(search.lower())
                )
            )
        ).subquery()
        q = q.join(user_subq, Attendance.user_id == user_subq.c.id)
    else:
        # Only join User if no search to avoid unnecessary joins
        if current_role in ['MANAGER', 'ADMIN']:
            q = q.join(Attendance.user).filter(User.is_deleted == False)
    
    # Apply date filters
    if date_from:
        q = q.filter(Attendance.date >= date_from)
    if date_to:
        q = q.filter(Attendance.date <= date_to)
    
    # Get count and records with eager loading
    total = q.count()
    records = q.options(
        joinedload(Attendance.user).load_only(User.name, User.employee_id, User.department)
    ).order_by(Attendance.date.desc()).offset((page-1)*per_page).limit(per_page).all()
    
    return records, total

def get_cached_departments():
    """
    Get departments with caching to avoid repeated queries
    """
    cache_key = 'departments_list'
    
    # Try to get from Flask cache first
    try:
        from flask import current_app
        if hasattr(current_app, 'cache') and current_app.cache:
            cached = current_app.cache.get(cache_key)
            if cached:
                return cached
    except:
        pass
    
    # Query database
    departments = db.session.query(User.department).filter(
        User.is_deleted == False,
        User.department.isnot(None)
    ).distinct().all()
    
    result = sorted([d[0] for d in departments if d[0]])
    
    # Cache for 5 minutes
    try:
        if hasattr(current_app, 'cache') and current_app.cache:
            current_app.cache.set(cache_key, result, timeout=300)
    except:
        pass
    
    return result

def bulk_convert_overtime_optimized():
    """
    Optimized bulk conversion with batch processing
    """
    batch_size = 100
    total_converted = 0
    
    try:
        while True:
            # Get batch of records that need conversion
            batch = db.session.query(Attendance).filter(
                or_(
                    Attendance.overtime_before_22.is_(None),
                    Attendance.overtime_before_22 == "",
                    Attendance.overtime_after_22.is_(None),
                    Attendance.overtime_after_22 == ""
                )
            ).limit(batch_size).all()
            
            if not batch:
                break
                
            # Process batch
            for att in batch:
                if att.overtime_before_22 is None or att.overtime_before_22 == "":
                    att.overtime_before_22 = "0:00"
                if att.overtime_after_22 is None or att.overtime_after_22 == "":
                    att.overtime_after_22 = "0:00"
                total_converted += 1
            
            # Commit batch
            db.session.commit()
            logger.info(f"Converted batch: {len(batch)} records")
        
        logger.info(f"✅ Total converted: {total_converted} records")
        return total_converted
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in bulk conversion: {e}")
        return 0

def query_performance_monitor(func):
    """
    Decorator to monitor query performance
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > 1.0:  # Log slow queries
                logger.warning(f"Slow query detected: {func.__name__} took {execution_time:.2f}s")
            elif execution_time > 0.5:  # Log medium queries
                logger.info(f"Query performance: {func.__name__} took {execution_time:.2f}s")
                
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Query error in {func.__name__}: {e} (took {execution_time:.2f}s)")
            raise
    return wrapper
