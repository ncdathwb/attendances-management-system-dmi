"""
Kiểm tra ai đã phê duyệt các bản ghi COMO
"""
import sys
sys.path.insert(0, '.')
from app import app, db
from database.models import Attendance, User

with app.app_context():
    # Lấy tất cả user COMO
    como_users = User.query.filter(User.department == 'COMO', User.is_deleted == False).all()
    como_ids = [u.id for u in como_users]
    
    print('=== LỊCH SỬ PHÊ DUYỆT CÁC BẢN GHI COMO ===')
    print()
    
    # Lấy tất cả bản ghi của nhân viên COMO
    como_records = Attendance.query.filter(
        Attendance.user_id.in_(como_ids)
    ).order_by(Attendance.id).all()
    
    for att in como_records:
        user = db.session.get(User, att.user_id)
        approver = db.session.get(User, att.approved_by) if att.approved_by else None
        tl_signer = db.session.get(User, att.team_leader_signer_id) if att.team_leader_signer_id else None
        
        print(f'ID: {att.id}')
        print(f'  Nhân viên: {user.name} (ID: {user.id})')
        print(f'  Ngày: {att.date}')
        print(f'  Status: {att.status}')
        print(f'  approved_by: {approver.name if approver else "N/A"} (ID: {att.approved_by})')
        print(f'  approved_at: {att.approved_at}')
        print(f'  team_leader_signer_id: {tl_signer.name if tl_signer else "N/A"} (ID: {att.team_leader_signer_id})')
        print(f'  Có team_leader_signature: {"CÓ" if att.team_leader_signature else "KHÔNG"}')
        print()
