"""
Script để kiểm tra attendance status
"""
import sys
sys.path.insert(0, '.')

from app import app, db
from database.models import Attendance, User

with app.app_context():
    # Đếm tất cả attendance theo status
    all_statuses = db.session.query(Attendance.status, db.func.count(Attendance.id)).group_by(Attendance.status).all()
    print('THỐNG KÊ ATTENDANCE THEO STATUS:')
    print('-' * 40)
    for status, count in all_statuses:
        print(f'  {status}: {count}')
    
    # Kiểm tra attendance của nhân viên COMO
    como_users = User.query.filter(User.department == 'COMO', User.is_deleted == False).all()
    como_ids = [u.id for u in como_users]
    
    print()
    print('ATTENDANCE CỦA NHÂN VIÊN COMO (10 bản ghi gần nhất):')
    print('-' * 40)
    como_att = Attendance.query.filter(Attendance.user_id.in_(como_ids)).order_by(Attendance.date.desc()).limit(10).all()
    if como_att:
        for att in como_att:
            user = db.session.get(User, att.user_id)
            print(f'  ID: {att.id}, User: {user.name}, Date: {att.date}, Status: {att.status}')
    else:
        print('  Không có attendance nào của nhân viên COMO!')
