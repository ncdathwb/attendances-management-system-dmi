"""
Authentication routes
"""
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from database.models import db, User, PasswordResetToken
from utils.session import check_session_timeout, update_session_activity
from utils.security import generate_csrf_token
from utils.validators import validate_email
from email_utils import send_password_reset_email
import secrets
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Đăng nhập"""
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', '').strip()
        password = request.form.get('password', '')
        
        if not employee_id or not password:
            flash('Vui lòng nhập đầy đủ thông tin!', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(employee_id=employee_id).first()
        
        if not user:
            flash('Mã nhân viên không tồn tại!', 'error')
            return render_template('login.html')
        
        if not user.is_active:
            flash('Tài khoản đã bị khóa!', 'error')
            return render_template('login.html')
        
        if not user.check_password(password):
            flash('Mật khẩu không đúng!', 'error')
            return render_template('login.html')
        
        session['user_id'] = user.id
        session['employee_id'] = user.employee_id
        session['name'] = user.name
        session['roles'] = user.roles
        session['current_role'] = user.roles.split(',')[0]
        session['department'] = user.department
        session['last_activity'] = datetime.now().isoformat()
        session['csrf_token'] = generate_csrf_token()
        
        flash(f'Chào mừng {user.name}!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Đăng xuất"""
    session.clear()
    flash('Đã đăng xuất thành công!', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Quên mật khẩu"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Vui lòng nhập email!', 'error')
            return render_template('forgot_password.html')
        
        if not validate_email(email):
            flash('Email không hợp lệ!', 'error')
            return render_template('forgot_password.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=expires_at
            )
            
            try:
                db.session.add(reset_token)
                db.session.commit()
                
                send_password_reset_email(user.email, user.name, token)
                flash('Email đặt lại mật khẩu đã được gửi!', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash('Có lỗi xảy ra khi gửi email!', 'error')
        else:
            flash('Email không tồn tại trong hệ thống!', 'error')
    
    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Đặt lại mật khẩu"""
    reset_token = PasswordResetToken.query.filter_by(
        token=token,
        used=False
    ).first()
    
    if not reset_token or reset_token.is_expired():
        flash('Link đặt lại mật khẩu không hợp lệ hoặc đã hết hạn!', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not password or not confirm_password:
            flash('Vui lòng nhập đầy đủ thông tin!', 'error')
            return render_template('reset_password.html', token=token)
        
        if len(password) < 6:
            flash('Mật khẩu phải có ít nhất 6 ký tự!', 'error')
            return render_template('reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp!', 'error')
            return render_template('reset_password.html', token=token)
        
        try:
            user = User.query.get(reset_token.user_id)
            user.set_password(password)
            reset_token.used = True
            
            db.session.commit()
            flash('Đặt lại mật khẩu thành công!', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Có lỗi xảy ra khi đặt lại mật khẩu!', 'error')
    
    return render_template('reset_password.html', token=token)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Đổi mật khẩu (yêu cầu đăng nhập)"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if check_session_timeout():
        flash('Phiên đăng nhập đã hết hạn!', 'error')
        return redirect(url_for('auth.login'))
    
    update_session_activity()
    
    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        flash('Phiên đăng nhập không hợp lệ!', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not current_password or not new_password or not confirm_password:
            flash('Vui lòng điền đầy đủ thông tin!', 'error')
            return render_template('change_password.html', user=user)
        
        if not user.check_password(current_password):
            flash('Mật khẩu hiện tại không đúng!', 'error')
            return render_template('change_password.html', user=user)
        
        if len(new_password) < 6:
            flash('Mật khẩu mới phải có ít nhất 6 ký tự!', 'error')
            return render_template('change_password.html', user=user)
        
        if new_password != confirm_password:
            flash('Mật khẩu mới và xác nhận mật khẩu không khớp!', 'error')
            return render_template('change_password.html', user=user)
        
        try:
            user.set_password(new_password)
            db.session.commit()
            flash('Đổi mật khẩu thành công!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Đã xảy ra lỗi khi đổi mật khẩu!', 'error')
    
    return render_template('change_password.html', user=user)
