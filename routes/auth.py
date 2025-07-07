from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, get_flashed_messages
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from functools import wraps
import secrets
from database.models import db, User, AuditLog
from utils.validators import validate_employee_id, validate_input_sanitize
from utils.decorators import rate_limit
from utils.session import check_session_timeout, update_session_activity, log_audit_action

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=5, window_seconds=300)  # 5 attempts per 5 minutes
def login():
    if request.method == 'POST':
        employee_id_str = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        # Validate input
        if not employee_id_str or not password:
            flash('Vui lòng nhập đầy đủ mã nhân viên và mật khẩu!', 'error')
            return render_template('login.html', messages=get_flashed_messages(with_categories=False))
        
        employee_id = validate_employee_id(employee_id_str)
        if not employee_id:
            flash('Mã nhân viên không hợp lệ!', 'error')
            return render_template('login.html', messages=get_flashed_messages(with_categories=False))
        
        if not validate_input_sanitize(password):
            flash('Mật khẩu không hợp lệ!', 'error')
            return render_template('login.html', messages=get_flashed_messages(with_categories=False))
        
        try:
            user = User.query.filter_by(employee_id=employee_id).first()
            
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['name'] = user.name
                session['employee_id'] = user.employee_id
                session['roles'] = user.roles.split(',')
                session['current_role'] = user.roles.split(',')[0]
                session['last_activity'] = datetime.now().isoformat()
                response = redirect(url_for('dashboard'))
                
                log_audit_action(
                    user_id=user.id,
                    action='LOGIN',
                    table_name='users',
                    record_id=user.id,
                    new_values={'login_time': datetime.now().isoformat()}
                )
                
                if remember:
                    # Generate secure remember token instead of storing password
                    remember_token = secrets.token_urlsafe(32)
                    user.remember_token = remember_token
                    user.remember_token_expires = datetime.now() + timedelta(days=30)
                    db.session.commit()
                    response.set_cookie('remember_token', remember_token, max_age=30*24*60*60, httponly=True, secure=False)  # Set secure=False for development
                else:
                    response.delete_cookie('remember_username')
                    response.delete_cookie('remember_password')
                
                flash('Đăng nhập thành công!', 'success')
                return response
            
            flash('Mã nhân viên hoặc mật khẩu không đúng!', 'error')
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash('Đã xảy ra lỗi khi đăng nhập!', 'error')
    
    return render_template('login.html', messages=get_flashed_messages(with_categories=False))

@auth_bp.route('/logout')
def logout():
    # Log logout if user was logged in
    if 'user_id' in session:
        log_audit_action(
            user_id=session['user_id'],
            action='LOGOUT',
            table_name='users',
            record_id=session['user_id'],
            new_values={'logout_time': datetime.now().isoformat()}
        )
    session.clear()
    return redirect(url_for('auth.login')) 