import sys
sys.path.insert(0, '.')
from app import app, db
from database.models import Attendance, User

with app.app_context():
    print('=' * 60)
    print('KIEM TRA BUD C')
    print('=' * 60)
    
    # Tìm tất cả nhân viên BUD C
    print('\n1. TAT CA NHAN VIEN BUD C:')
    bud_c_users = User.query.filter(User.department == 'BUD C', User.is_deleted == False).all()
    for u in bud_c_users:
        print(f'  ID: {u.id}, Name: {u.name}, Employee ID: {u.employee_id}, Roles: {u.roles}')
    
    # Tìm Đặng Châu Anh
    print('\n2. TIM DANG CHAU ANH (1006):')
    chau_anh = User.query.filter(User.employee_id == '1006').first()
    if chau_anh:
        print(f'  ID: {chau_anh.id}')
        print(f'  Name: {chau_anh.name}')
        print(f'  Employee ID: {chau_anh.employee_id}')
        print(f'  Department: {chau_anh.department}')
        print(f'  Roles: {chau_anh.roles}')
        
        # Kiểm tra attendance của Đặng Châu Anh
        print('\n3. ATTENDANCE CUA DANG CHAU ANH:')
        att = Attendance.query.filter(Attendance.user_id == chau_anh.id).all()
        if att:
            for a in att:
                print(f'  ID: {a.id}, Date: {a.date}, Status: {a.status}')
        else:
            print('  KHONG CO ATTENDANCE NAO!')
    else:
        print('  KHONG TIM THAY!')
    
    # Kiểm tra tất cả attendance pending của BUD C
    print('\n4. TAT CA ATTENDANCE PENDING CUA BUD C:')
    bud_c_ids = [u.id for u in bud_c_users]
    pending = Attendance.query.filter(
        Attendance.user_id.in_(bud_c_ids),
        Attendance.status == 'pending'
    ).all()
    if pending:
        for a in pending:
            user = db.session.get(User, a.user_id)
            print(f'  ID: {a.id}, User: {user.name}, Date: {a.date}')
    else:
        print('  KHONG CO PENDING NAO!')
    
    # Tìm Team Leader của BUD C
    print('\n5. TEAM LEADER CUA BUD C:')
    leaders = User.query.filter(
        User.department == 'BUD C',
        User.roles.like('%TEAM_LEADER%'),
        User.is_deleted == False
    ).all()
    if leaders:
        for l in leaders:
            print(f'  ID: {l.id}, Name: {l.name}, Roles: {l.roles}')
    else:
        print('  KHONG CO TEAM LEADER!')
