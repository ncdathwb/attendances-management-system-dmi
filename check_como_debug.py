"""
Script để kiểm tra department COMO trong database
Chạy script này để xem tình trạng department COMO
"""
import sys
sys.path.insert(0, '.')

from app import app, db
from database.models import User, Attendance

with app.app_context():
    print("=" * 60)
    print("KIỂM TRA DEPARTMENT COMO TRONG DATABASE")
    print("=" * 60)
    
    # 1. Tìm tất cả user có department chứa "como" (case-insensitive)
    print("\n1. TẤT CẢ USER CÓ DEPARTMENT CHỨA 'COMO':")
    print("-" * 60)
    como_users = User.query.filter(
        User.department.ilike('%como%'),
        User.is_deleted == False
    ).all()
    
    if como_users:
        for u in como_users:
            print(f"  ID: {u.id}, Name: {u.name}")
            print(f"    Department: '{u.department}'")
            print(f"    Department (repr): {repr(u.department)}")
            print(f"    Roles: {u.roles}")
            print()
    else:
        print("  Không tìm thấy user nào!")
    
    # 2. Tìm tất cả các phiên bản department có liên quan COMO
    print("\n2. TẤT CẢ DEPARTMENT TRONG DATABASE:")
    print("-" * 60)
    all_depts = db.session.query(User.department).distinct().filter(
        User.is_deleted == False
    ).all()
    
    for d in sorted(all_depts, key=lambda x: x[0] or ''):
        dept_name = d[0]
        count = User.query.filter(User.department == dept_name, User.is_deleted == False).count()
        # Highlight COMO-like departments
        marker = " <-- COMO-like" if dept_name and 'como' in dept_name.lower() else ""
        print(f"  '{dept_name}' (repr: {repr(dept_name)}) - {count} users{marker}")
    
    # 3. Kiểm tra attendance pending
    print("\n3. TẤT CẢ ATTENDANCE CÓ STATUS='pending':")
    print("-" * 60)
    pending_att = Attendance.query.filter(Attendance.status == 'pending').all()
    
    if pending_att:
        for att in pending_att:
            user = db.session.get(User, att.user_id)
            print(f"  Attendance ID: {att.id}")
            print(f"    User: {user.name if user else 'Unknown'}")
            print(f"    User Department: '{user.department if user else 'Unknown'}'")
            print(f"    Date: {att.date}")
            print(f"    Status: {att.status}")
            print()
    else:
        print("  Không có attendance nào có status='pending'!")
    
    # 4. Kiểm tra xem có Team Leader nào trong COMO không
    print("\n4. TEAM LEADER TRONG COMO:")
    print("-" * 60)
    leaders = User.query.filter(
        User.department.ilike('%como%'),
        User.roles.ilike('%TEAM_LEADER%'),
        User.is_deleted == False
    ).all()
    
    if leaders:
        for l in leaders:
            print(f"  ID: {l.id}, Name: {l.name}")
            print(f"    Department: '{l.department}' (repr: {repr(l.department)})")
            print(f"    Roles: {l.roles}")
            
            # Tìm nhân viên cùng phòng ban (exact match)
            exact_match = User.query.filter(
                User.department == l.department,
                User.is_deleted == False
            ).count()
            print(f"    Nhân viên cùng phòng ban (exact match): {exact_match}")
            
            # Tìm nhân viên cùng phòng ban (case-insensitive)
            from sqlalchemy import func
            l_dept_upper = (l.department or '').strip().upper()
            case_insensitive = User.query.filter(
                func.upper(func.trim(User.department)) == l_dept_upper,
                User.is_deleted == False
            ).count()
            print(f"    Nhân viên cùng phòng ban (case-insensitive): {case_insensitive}")
            print()
    else:
        print("  Không tìm thấy Team Leader nào trong COMO!")
    
    print("=" * 60)
    print("HOÀN TẤT KIỂM TRA")
    print("=" * 60)
