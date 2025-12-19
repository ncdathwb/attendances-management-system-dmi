import sys
sys.path.insert(0, '.')
from app import app, db
from database.models import Attendance, User

with app.app_context():
    print('TAT CA BAN GHI PENDING:')
    pending = Attendance.query.filter(Attendance.status == 'pending').all()
    for att in pending:
        user = db.session.get(User, att.user_id)
        print(f'  ID: {att.id}, User: {user.name} (ID: {user.id}), Dept: {user.department}')
