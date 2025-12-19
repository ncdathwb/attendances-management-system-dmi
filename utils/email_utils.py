"""
Email utilities for the attendance management system
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import threading
import time
import queue

# Queue để giao tiếp giữa async thread và main thread
db_update_queue = queue.Queue()

def _schedule_db_update(request_id, user_id, status, message):
    """Schedule database update to be processed by main thread"""
    db_update_queue.put({
        'request_id': request_id,
        'user_id': user_id,
        'status': status,
        'message': message
    })

def process_db_updates():
    """Process pending database updates from async threads"""
    while not db_update_queue.empty():
        try:
            update = db_update_queue.get_nowait()
            from app import app, upsert_email_status, publish_email_status
            with app.app_context():
                upsert_email_status(update['request_id'], update['status'], update['message'])
                publish_email_status(update['user_id'], update['request_id'], update['status'], update['message'])
        except queue.Empty:
            break
        except Exception as e:
            print(f"❌ Error processing DB update: {e}")

def send_leave_request_email(leave_request, user, action='create'):
    """
    Gửi email xin phép nghỉ đến phòng nhân sự (legacy function - kept for compatibility)
    """
    # Convert to safe format and call safe function
    user_data = {
        'id': user.id,
        'name': user.name,
        'email': getattr(user, 'email', ''),
        'employee_id': getattr(user, 'employee_id', '')
    }
    
    request_data = {
        'id': leave_request.id,
        'status': getattr(leave_request, 'status', 'unknown'),
        'leave_reason': getattr(leave_request, 'leave_reason', ''),
        'start_date': getattr(leave_request, 'start_date', ''),
        'end_date': getattr(leave_request, 'end_date', ''),
        'start_time': getattr(leave_request, 'start_time', ''),
        'end_time': getattr(leave_request, 'end_time', ''),
        'shift_code': getattr(leave_request, 'shift_code', '1'),
        'annual_leave_days': getattr(leave_request, 'annual_leave_days', 0),
        'unpaid_leave_days': getattr(leave_request, 'unpaid_leave_days', 0),
        'special_leave_days': getattr(leave_request, 'special_leave_days', 0),
        'substitute_name': getattr(leave_request, 'substitute_name', ''),
        'substitute_employee_id': getattr(leave_request, 'substitute_employee_id', ''),
        'notes': getattr(leave_request, 'notes', ''),
        'attachments': getattr(leave_request, 'attachments', None),
        'hospital_confirmation': getattr(leave_request, 'hospital_confirmation', None),
        'wedding_invitation': getattr(leave_request, 'wedding_invitation', None),
        'death_birth_certificate': getattr(leave_request, 'death_birth_certificate', None),
        'request_type': getattr(leave_request, 'request_type', 'leave'),
        'late_early_type': getattr(leave_request, 'late_early_type', '')
    }
    
    from utils.email_utils_safe import send_leave_request_email_safe
    return send_leave_request_email_safe(request_data, user_data, action)

def send_leave_request_email_async(leave_request, user, action='create'):
    """
    Gửi email xin phép nghỉ bất đồng bộ (không chặn response)
    """
    def send_email_thread():
        try:
            # Lưu thông tin cần thiết trước khi chuyển sang thread
            request_id = leave_request.id
            user_id = user.id
            user_name = user.name
            user_email = getattr(user, 'email', '')
            request_status = getattr(leave_request, 'status', 'unknown')
            
            print(f"🚀 [ASYNC] Bắt đầu gửi email bất đồng bộ cho leave_request #{request_id}", flush=True)
            print(f"📧 [ASYNC] Thông tin đơn: ID={request_id}, User={user_name}, Status={request_status}", flush=True)
            
            # Cập nhật trạng thái đang gửi - chỉ dùng global state, không dùng DB trong thread
            from state.email_state import email_status
            email_status[request_id] = {
                'status': 'sending',
                'message': 'Đang gửi email...',
                'timestamp': time.time()
            }
            print(f"📤 [ASYNC] Set global status to sending for request #{request_id}")
            
            # Tạo data dictionaries để tránh DetachedInstanceError
            # Lưu tất cả thông tin cần thiết trước khi vào thread
            user_employee_id = getattr(user, 'employee_id', '') if hasattr(user, 'employee_id') else ''
            
            user_data = {
                'id': user_id,
                'name': user_name,
                'email': user_email,
                'employee_id': user_employee_id
            }
            
            # Lưu tất cả thông tin request trước khi vào thread để tránh DetachedInstanceError
            request_leave_reason = getattr(leave_request, 'leave_reason', '') if hasattr(leave_request, 'leave_reason') else ''
            request_shift_code = getattr(leave_request, 'shift_code', '1') if hasattr(leave_request, 'shift_code') else '1'
            request_annual_leave_days = getattr(leave_request, 'annual_leave_days', 0) if hasattr(leave_request, 'annual_leave_days') else 0
            request_unpaid_leave_days = getattr(leave_request, 'unpaid_leave_days', 0) if hasattr(leave_request, 'unpaid_leave_days') else 0
            request_special_leave_days = getattr(leave_request, 'special_leave_days', 0) if hasattr(leave_request, 'special_leave_days') else 0
            request_substitute_name = getattr(leave_request, 'substitute_name', '') if hasattr(leave_request, 'substitute_name') else ''
            request_substitute_employee_id = getattr(leave_request, 'substitute_employee_id', '') if hasattr(leave_request, 'substitute_employee_id') else ''
            request_notes = getattr(leave_request, 'notes', '') if hasattr(leave_request, 'notes') else ''
            request_attachments = getattr(leave_request, 'attachments', None) if hasattr(leave_request, 'attachments') else None
            request_hospital_confirmation = getattr(leave_request, 'hospital_confirmation', None) if hasattr(leave_request, 'hospital_confirmation') else None
            request_wedding_invitation = getattr(leave_request, 'wedding_invitation', None) if hasattr(leave_request, 'wedding_invitation') else None
            request_death_birth_certificate = getattr(leave_request, 'death_birth_certificate', None) if hasattr(leave_request, 'death_birth_certificate') else None
            request_type = getattr(leave_request, 'request_type', 'leave') if hasattr(leave_request, 'request_type') else 'leave'
            late_early_type = getattr(leave_request, 'late_early_type', '') if hasattr(leave_request, 'late_early_type') else ''
            
            # Lưu thông tin ngày tháng từ các trường riêng lẻ
            request_leave_from_day = getattr(leave_request, 'leave_from_day', 1) if hasattr(leave_request, 'leave_from_day') else 1
            request_leave_from_month = getattr(leave_request, 'leave_from_month', 1) if hasattr(leave_request, 'leave_from_month') else 1
            request_leave_from_year = getattr(leave_request, 'leave_from_year', 2024) if hasattr(leave_request, 'leave_from_year') else 2024
            request_leave_from_hour = getattr(leave_request, 'leave_from_hour', 0) if hasattr(leave_request, 'leave_from_hour') else 0
            request_leave_from_minute = getattr(leave_request, 'leave_from_minute', 0) if hasattr(leave_request, 'leave_from_minute') else 0
            request_leave_to_day = getattr(leave_request, 'leave_to_day', 1) if hasattr(leave_request, 'leave_to_day') else 1
            request_leave_to_month = getattr(leave_request, 'leave_to_month', 1) if hasattr(leave_request, 'leave_to_month') else 1
            request_leave_to_year = getattr(leave_request, 'leave_to_year', 2024) if hasattr(leave_request, 'leave_to_year') else 2024
            request_leave_to_hour = getattr(leave_request, 'leave_to_hour', 0) if hasattr(leave_request, 'leave_to_hour') else 0
            request_leave_to_minute = getattr(leave_request, 'leave_to_minute', 0) if hasattr(leave_request, 'leave_to_minute') else 0
            
            request_data = {
                'id': request_id,
                'status': request_status,
                'leave_reason': request_leave_reason,
                'leave_from_day': request_leave_from_day,
                'leave_from_month': request_leave_from_month,
                'leave_from_year': request_leave_from_year,
                'leave_from_hour': request_leave_from_hour,
                'leave_from_minute': request_leave_from_minute,
                'leave_to_day': request_leave_to_day,
                'leave_to_month': request_leave_to_month,
                'leave_to_year': request_leave_to_year,
                'leave_to_hour': request_leave_to_hour,
                'leave_to_minute': request_leave_to_minute,
                'shift_code': request_shift_code,
                'annual_leave_days': request_annual_leave_days,
                'unpaid_leave_days': request_unpaid_leave_days,
                'special_leave_days': request_special_leave_days,
                'substitute_name': request_substitute_name,
                'substitute_employee_id': request_substitute_employee_id,
                'notes': request_notes,
                'attachments': request_attachments,
                'hospital_confirmation': request_hospital_confirmation,
                'wedding_invitation': request_wedding_invitation,
                'death_birth_certificate': request_death_birth_certificate,
                'request_type': request_type,
                'late_early_type': late_early_type
            }
            
            # Gửi email thực tế với data dictionaries
            from utils.email_utils_safe import send_leave_request_email_safe
            success = send_leave_request_email_safe(request_data, user_data, action)
            
            if success:
                email_status[request_id] = {
                        'status': 'success',
                    'message': 'Email đã được gửi thành công',
                        'timestamp': time.time()
                    }
                print(f"✅ [ASYNC] Email sent successfully for leave_request #{request_id}")
                
                # Cập nhật database từ main thread (scheduled task)
                _schedule_db_update(request_id, user_id, 'success', 'Email đã được gửi thành công')
            else:
                email_status[request_id] = {
                    'status': 'error',
                    'message': 'Không thể gửi email',
                    'timestamp': time.time()
                }
                
                print(f"❌ [ASYNC] Failed to send email for leave_request #{request_id}")
                
                # Cập nhật database từ main thread (scheduled task)
                _schedule_db_update(request_id, user_id, 'error', 'Không thể gửi email')
                
        except Exception as e:
            print(f"💥 [ASYNC] Lỗi trong thread gửi email: {e}", flush=True)
            from state.email_state import email_status
            email_status[request_id] = {
                'status': 'error',
                'message': f'Lỗi gửi email: {str(e)}',
                'timestamp': time.time()
            }
    
    # Tạo thread mới để gửi email
    thread = threading.Thread(target=send_email_thread, daemon=True)
    thread.start()
    print(f"📤 [ASYNC] Đã khởi tạo thread gửi email cho leave_request #{leave_request.id}", flush=True)
