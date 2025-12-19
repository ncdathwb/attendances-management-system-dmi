import sys
sys.path.insert(0, '.')
from app import app, db
from database.models import Attendance, User

with app.app_context():
    leader_att = Attendance.query.filter(Attendance.user_id == 28).all()
    print('TAT CA BAN GHI CUA LEADER COMO:')
    for att in leader_att:
        print(f'  ID: {att.id}, Date: {att.date}, Status: {att.status}')
