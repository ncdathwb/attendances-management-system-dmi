"""
Leave request routes
"""
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify
from database.models import db, User, LeaveRequest
from utils.session import check_session_timeout, update_session_activity
from datetime import datetime
import json

leave_bp = Blueprint('leave', __name__)

@leave_bp.route('/leave-request', methods=['GET', 'POST'])
def leave_request():
    """Tạo đơn xin nghỉ phép"""
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
        return redirect(url_for('auth.login'))
    
    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('auth.login'))
    
    if check_session_timeout():
        flash('Phiên đăng nhập đã hết hạn!', 'error')
        return redirect(url_for('auth.login'))
    
    update_session_activity()
    
    if request.method == 'POST':
        try:
            # Get form data
            leave_reason = request.form.get('leave_reason', '').strip()
            leave_from_hour = int(request.form.get('leave_from_hour', 0))
            leave_from_minute = int(request.form.get('leave_from_minute', 0))
            leave_from_day = int(request.form.get('leave_from_day', 0))
            leave_from_month = int(request.form.get('leave_from_month', 0))
            leave_from_year = int(request.form.get('leave_from_year', 0))
            
            leave_to_hour = int(request.form.get('leave_to_hour', 0))
            leave_to_minute = int(request.form.get('leave_to_minute', 0))
            leave_to_day = int(request.form.get('leave_to_day', 0))
            leave_to_month = int(request.form.get('leave_to_month', 0))
            leave_to_year = int(request.form.get('leave_to_year', 0))
            
            annual_leave_days = float(request.form.get('annual_leave_days', 0))
            unpaid_leave_days = float(request.form.get('unpaid_leave_days', 0))
            special_leave_days = float(request.form.get('special_leave_days', 0))
            special_leave_type = request.form.get('special_leave_type', '')
            
            substitute_name = request.form.get('substitute_name', '').strip()
            substitute_employee_id = request.form.get('substitute_employee_id', '').strip()
            shift_code = request.form.get('shift_code', '')
            applicant_signature = request.form.get('applicant_signature', '')
            
            # Validation
            if not leave_reason:
                flash('Vui lòng nhập lý do nghỉ phép!', 'error')
                return render_template('leave_request_form.html', user=user)
            
            if annual_leave_days + unpaid_leave_days + special_leave_days <= 0:
                flash('Vui lòng chọn ít nhất một loại nghỉ phép!', 'error')
                return render_template('leave_request_form.html', user=user)
            
            # Create leave request
            leave_request = LeaveRequest(
                user_id=user.id,
                employee_name=user.name,
                team=user.department,
                employee_code=user.employee_id,
                leave_reason=leave_reason,
                leave_from_hour=leave_from_hour,
                leave_from_minute=leave_from_minute,
                leave_from_day=leave_from_day,
                leave_from_month=leave_from_month,
                leave_from_year=leave_from_year,
                leave_to_hour=leave_to_hour,
                leave_to_minute=leave_to_minute,
                leave_to_day=leave_to_day,
                leave_to_month=leave_to_month,
                leave_to_year=leave_to_year,
                annual_leave_days=annual_leave_days,
                unpaid_leave_days=unpaid_leave_days,
                special_leave_days=special_leave_days,
                special_leave_type=special_leave_type,
                substitute_name=substitute_name,
                substitute_employee_id=substitute_employee_id,
                shift_code=shift_code,
                applicant_signature=applicant_signature,
                status='pending'
            )
            
            db.session.add(leave_request)
            db.session.commit()
            
            flash('Đơn xin nghỉ phép đã được tạo thành công!', 'success')
            return redirect(url_for('leave.leave_history'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi tạo đơn xin nghỉ phép: {str(e)}', 'error')
    
    return render_template('leave_request_form.html', user=user)

@leave_bp.route('/leave-request/<int:request_id>/approve', methods=['POST'])
def approve_leave_request(request_id):
    """Phê duyệt hoặc từ chối đơn xin nghỉ phép với logic phân cấp như chấm công"""
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
        return redirect(url_for('auth.login'))
    
    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('auth.login'))
    
    current_role = session.get('current_role', user.roles.split(',')[0])
    user_roles = user.get_roles_list()
    if not any(role in ['ADMIN', 'MANAGER', 'TEAM_LEADER'] for role in user_roles):
        flash('Không có quyền phê duyệt!', 'error')
        return redirect(url_for('leave.view_leave_request', request_id=request_id))
    
    leave_request = LeaveRequest.query.get_or_404(request_id)
    action = request.form.get('action')
    rejection_reason = request.form.get('rejection_reason')
    
    try:
        if action == 'approve':
            if current_role == 'TEAM_LEADER':
                if leave_request.status != 'pending':
                    flash('Đơn không ở trạng thái chờ duyệt', 'error')
                    return redirect(url_for('leave.view_leave_request', request_id=request_id))
                leave_request.status = 'pending_manager'
                leave_request.approved_by = user.id
                leave_request.approved_at = datetime.now()
                flash('Đã chuyển lên Quản lý phê duyệt!', 'success')
            elif current_role == 'MANAGER':
                if leave_request.status != 'pending_manager':
                    flash('Đơn chưa được Trưởng nhóm phê duyệt', 'error')
                    return redirect(url_for('leave.view_leave_request', request_id=request_id))
                leave_request.status = 'pending_admin'
                leave_request.approved_by = user.id
                leave_request.approved_at = datetime.now()
                flash('Đã chuyển lên Admin phê duyệt!', 'success')
            elif current_role == 'ADMIN':
                if leave_request.status not in ['pending_manager', 'pending_admin']:
                    flash('Đơn chưa được cấp dưới phê duyệt', 'error')
                    return redirect(url_for('leave.view_leave_request', request_id=request_id))
                leave_request.status = 'approved'
                leave_request.approved_by = user.id
                leave_request.approved_at = datetime.now()
                flash('Đơn xin nghỉ phép đã được phê duyệt hoàn tất!', 'success')
        elif action == 'reject':
            leave_request.status = 'rejected'
            leave_request.approved_by = user.id
            leave_request.approved_at = datetime.now()
            if rejection_reason:
                leave_request.notes = f"Lý do từ chối: {rejection_reason}"
            flash('Đơn xin nghỉ phép đã bị từ chối!', 'warning')
        else:
            flash('Hành động không hợp lệ!', 'error')
            return redirect(url_for('leave.view_leave_request', request_id=request_id))
        
        db.session.commit()
        return redirect(url_for('leave.view_leave_request', request_id=request_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xử lý đơn xin nghỉ phép: {str(e)}', 'error')
        return redirect(url_for('leave.view_leave_request', request_id=request_id))

@leave_bp.route('/leave-history')
def leave_history():
    """Lịch sử đơn xin nghỉ phép"""
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
        return redirect(url_for('auth.login'))
    
    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('auth.login'))
    
    if check_session_timeout():
        flash('Phiên đăng nhập đã hết hạn!', 'error')
        return redirect(url_for('auth.login'))
    
    update_session_activity()
    
    # Get leave requests for current user
    leave_requests = LeaveRequest.query.filter_by(user_id=user.id).order_by(LeaveRequest.created_at.desc()).all()
    
    return render_template('leave_history.html', user=user, leave_requests=leave_requests)

@leave_bp.route('/leave-requests')
def leave_requests_list():
    """Danh sách đơn xin nghỉ phép cần phê duyệt"""
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
        return redirect(url_for('auth.login'))
    
    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('auth.login'))
    
    current_role = session.get('current_role', user.roles.split(',')[0])
    user_roles = user.get_roles_list()
    
    if not any(role in ['ADMIN', 'MANAGER', 'TEAM_LEADER'] for role in user_roles):
        flash('Không có quyền truy cập!', 'error')
        return redirect(url_for('dashboard'))
    
    if check_session_timeout():
        flash('Phiên đăng nhập đã hết hạn!', 'error')
        return redirect(url_for('auth.login'))
    
    update_session_activity()
    
    # Get leave requests based on role
    if current_role == 'TEAM_LEADER':
        leave_requests = LeaveRequest.query.filter_by(status='pending').order_by(LeaveRequest.created_at.desc()).all()
    elif current_role == 'MANAGER':
        leave_requests = LeaveRequest.query.filter_by(status='pending_manager').order_by(LeaveRequest.created_at.desc()).all()
    else:  # ADMIN
        leave_requests = LeaveRequest.query.filter_by(status='pending_admin').order_by(LeaveRequest.created_at.desc()).all()
    
    return render_template('leave_requests_list.html', user=user, leave_requests=leave_requests, current_role=current_role)

@leave_bp.route('/leave-request/<int:request_id>')
def view_leave_request(request_id):
    """Xem chi tiết đơn xin nghỉ phép"""
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để sử dụng chức năng này', 'error')
        return redirect(url_for('auth.login'))
    
    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('auth.login'))
    
    if check_session_timeout():
        flash('Phiên đăng nhập đã hết hạn!', 'error')
        return redirect(url_for('auth.login'))
    
    update_session_activity()
    
    leave_request = LeaveRequest.query.get_or_404(request_id)
    current_role = session.get('current_role', user.roles.split(',')[0])
    
    return render_template('view_leave_request.html', 
                         user=user, 
                         leave_request=leave_request, 
                         current_role=current_role)
