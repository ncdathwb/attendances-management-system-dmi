"""
Attendance routes
"""
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify
from database.models import db, User, Attendance
from utils.session import check_session_timeout, update_session_activity
from utils.decorators import rate_limit
from datetime import datetime, timedelta
import json

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/api/attendance/<int:attendance_id>/approve', methods=['POST'])
@rate_limit(max_requests=200, window_seconds=60)
def approve_attendance(attendance_id):
    """Phê duyệt chấm công"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Không có quyền truy cập'}), 401
        
        user = db.session.get(User, session['user_id'])
        if not user:
            return jsonify({'error': 'Không tìm thấy người dùng'}), 404
        
        current_role = session.get('current_role', user.roles.split(',')[0])
        user_roles = user.get_roles_list()
        
        if not any(role in ['ADMIN', 'MANAGER', 'TEAM_LEADER'] for role in user_roles):
            return jsonify({'error': 'Không có quyền phê duyệt'}), 403
        
        attendance = Attendance.query.get(attendance_id)
        if not attendance:
            return jsonify({'error': 'Không tìm thấy bản ghi chấm công'}), 404
        
        data = request.get_json()
        action = data.get('action')
        reason = data.get('reason', '')
        approver_signature = data.get('approver_signature', '')
        
        if action not in ['approve', 'reject']:
            return jsonify({'error': 'Hành động không hợp lệ'}), 400
        
        if action == 'reject' and not reason:
            return jsonify({'error': 'Lý do từ chối không hợp lệ'}), 400
        
        if attendance.approved:
            return jsonify({'error': 'Bản ghi đã được phê duyệt hoàn tất'}), 400
        
        old_status = attendance.status
        
        if action == 'approve':
            if current_role == 'TEAM_LEADER':
                if attendance.status != 'pending':
                    return jsonify({'error': 'Bản ghi không ở trạng thái chờ duyệt'}), 400
                attendance.status = 'pending_manager'
                attendance.approved_by = user.id
                attendance.approved_at = datetime.now()
                if approver_signature:
                    attendance.team_leader_signature = approver_signature
                attendance.team_leader_signer_id = user.id
                message = 'Đã chuyển lên Quản lý phê duyệt'
            elif current_role == 'MANAGER':
                if attendance.status != 'pending_manager':
                    return jsonify({'error': 'Bản ghi chưa được Trưởng nhóm phê duyệt'}), 400
                attendance.status = 'pending_admin'
                attendance.approved_by = user.id
                attendance.approved_at = datetime.now()
                if approver_signature:
                    attendance.manager_signature = approver_signature
                attendance.manager_signer_id = user.id
                message = 'Đã chuyển lên Admin phê duyệt'
            elif current_role == 'ADMIN':
                if attendance.status not in ['pending_manager', 'pending_admin']:
                    return jsonify({'error': 'Bản ghi chưa được cấp dưới phê duyệt'}), 400
                attendance.status = 'approved'
                attendance.approved = True
                attendance.approved_by = user.id
                attendance.approved_at = datetime.now()
                message = 'Phê duyệt hoàn tất'
        else:  # reject
            attendance.status = 'rejected'
            attendance.reject_reason = reason
            attendance.approved_by = user.id
            attendance.approved_at = datetime.now()
            message = f'Đã từ chối: {reason}'
        
        db.session.commit()
        
        return jsonify({
            'message': message,
            'status': attendance.status,
            'approved': attendance.approved
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Lỗi server: {str(e)}'}), 500

@attendance_bp.route('/api/attendance/approve-all', methods=['POST'])
@rate_limit(max_requests=10, window_seconds=60)
def approve_all_attendances():
    """Phê duyệt tất cả chấm công"""
    if 'user_id' not in session:
        return jsonify({'error': 'Không có quyền truy cập'}), 401
    
    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'Không tìm thấy người dùng'}), 404
    
    current_role = session.get('current_role', user.roles.split(',')[0])
    user_roles = user.get_roles_list()
    
    if not any(role in ['ADMIN', 'MANAGER', 'TEAM_LEADER'] for role in user_roles):
        return jsonify({'error': 'Không có quyền phê duyệt'}), 403
    
    try:
        data = request.get_json()
        action = data.get('action', 'approve')
        reason = data.get('reason', '')
        
        if action == 'reject' and not reason:
            return jsonify({'error': 'Vui lòng nhập lý do từ chối'}), 400
        
        # Query attendances based on role
        if current_role == 'ADMIN':
            attendances_query = Attendance.query.filter(
                Attendance.approved == False
            )
        elif current_role == 'MANAGER':
            attendances_query = Attendance.query.filter(
                Attendance.approved == False
            )
        else:  # TEAM_LEADER
            attendances_query = Attendance.query.join(User, Attendance.user_id == User.id).filter(
                Attendance.approved == False,
                User.department == user.department
            )
        
        attendances = attendances_query.all()
        
        if not attendances:
            return jsonify({'message': 'Không có bản ghi nào để xử lý', 'count': 0})
        
        approved_count = 0
        rejected_count = 0
        
        for attendance in attendances:
            if action == 'approve':
                if current_role == 'TEAM_LEADER':
                    attendance.status = 'pending_manager'
                    attendance.approved_by = user.id
                    attendance.approved_at = datetime.now()
                    if user.has_personal_signature():
                        attendance.team_leader_signature = user.personal_signature
                    attendance.team_leader_signer_id = user.id
                elif current_role == 'MANAGER':
                    attendance.status = 'pending_admin'
                    attendance.approved_by = user.id
                    attendance.approved_at = datetime.now()
                    if user.has_personal_signature():
                        attendance.manager_signature = user.personal_signature
                    attendance.manager_signer_id = user.id
                else:  # ADMIN
                    attendance.status = 'approved'
                    attendance.approved = True
                    attendance.approved_by = user.id
                    attendance.approved_at = datetime.now()
                
                approved_count += 1
            else:  # reject
                attendance.status = 'rejected'
                attendance.reject_reason = reason
                attendance.approved_by = user.id
                attendance.approved_at = datetime.now()
                rejected_count += 1
        
        db.session.commit()
        
        if action == 'approve':
            message = f'Đã phê duyệt {approved_count} bản ghi'
        else:
            message = f'Đã từ chối {rejected_count} bản ghi'
        
        return jsonify({
            'message': message,
            'approved_count': approved_count,
            'rejected_count': rejected_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Lỗi server: {str(e)}'}), 500
