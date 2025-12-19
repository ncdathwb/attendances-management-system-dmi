import sys
sys.path.insert(0, '.')
from app import app, db
from database.models import Attendance, User

with app.app_context():
    print('=== THỐNG KÊ ATTENDANCE THEO STATUS ===')
    all_statuses = db.session.query(Attendance.status, db.func.count(Attendance.id)).group_by(Attendance.status).all()
    for status, count in all_statuses:
        print(f'  {status}: {count}')
    
    print()
    print('=== TẤT CẢ BẢN GHI PENDING ===')
    pending = Attendance.query.filter(Attendance.status == 'pending').all()
    if pending:
        for att in pending:
            user = db.session.get(User, att.user_id)
            print(f'  ID: {att.id}, User: {user.name if user else "Unknown"}, Dept: {user.department if user else "Unknown"}, Date: {att.date}')
    else:
        print('  KHONG CO BAN GHI NAO!')
    
    print()
    print('=== 5 BẢN GHI PENDING_MANAGER ===')
    pm = Attendance.query.filter(Attendance.status == 'pending_manager').limit(5).all()
    for att in pm:
        user = db.session.get(User, att.user_id)
        print(f'  ID: {att.id}, User: {user.name if user else "Unknown"}, Dept: {user.department if user else "Unknown"}, Date: {att.date}')
