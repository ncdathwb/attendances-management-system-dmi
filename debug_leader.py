import sys
sys.path.insert(0, '.')
from app import app, db
from database.models import Attendance, User
from sqlalchemy import func

with app.app_context():
    # Leader COMO
    leader = db.session.get(User, 28)
    print(f'Leader: {leader.name} (ID: {leader.id})')
    print(f'Department: [{leader.department}]')
    print(f'Roles: {leader.roles}')
    print()
    
    # Tìm bản ghi pending của leader
    leader_pending = Attendance.query.filter(
        Attendance.user_id == 28,
        Attendance.status == 'pending'
    ).all()
    print(f'Ban ghi PENDING cua Leader: {len(leader_pending)}')
    for att in leader_pending:
        print(f'  ID: {att.id}, Date: {att.date}, Status: {att.status}, approved: {att.approved}')
    print()
    
    # Kiểm tra scalar_subquery
    user_dept = (leader.department or '').strip().upper()
    print(f'user_dept: [{user_dept}]')
    
    team_user_ids = db.session.query(User.id).filter(
        func.upper(func.trim(User.department)) == user_dept,
        User.is_deleted == False
    ).all()
    print(f'Team user IDs: {[u[0] for u in team_user_ids]}')
    print(f'Leader ID (28) in team? {28 in [u[0] for u in team_user_ids]}')
