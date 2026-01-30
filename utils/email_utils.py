"""
Email utilities for the attendance management system
Consolidated: email_utils.py + email_utils_safe.py
"""
import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
import mimetypes
from datetime import datetime
import threading
import time
import queue
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Queue để giao tiếp giữa async thread và main thread
db_update_queue = queue.Queue()

def _safe_print(message):
    """Print an toàn, tránh lỗi I/O operation on closed file trong thread"""
    try:
        if sys.stdout and not sys.stdout.closed:
            print(message, flush=True)
    except (ValueError, IOError, OSError):
        # Bỏ qua lỗi khi stdout đã bị đóng
        pass

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
            _safe_print(f"❌ Error processing DB update: {e}")


def send_leave_request_email_safe(request_data, user_data, action='create'):
    """
    Gửi email xin phép nghỉ với dữ liệu đã được serialize (tránh SQLAlchemy DetachedInstanceError)
    """
    try:
        print("=== BẮT ĐẦU GỬI EMAIL XIN PHÉP NGHỈ (SAFE) ===", flush=True)
        print(f"User: {user_data['name']} (ID: {user_data['id']})")
        print(f"Leave Request ID: {request_data['id']}")

        # ========================================
        # ĐỌC CẤU HÌNH TỪ ENVIRONMENT VARIABLES
        # ========================================
        # Email settings
        ENABLE_EMAIL_SENDING = os.getenv('ENABLE_EMAIL_SENDING', 'False').lower() == 'true'
        USE_COMPANY_EMAIL_ONLY = os.getenv('USE_COMPANY_EMAIL_ONLY', 'True').lower() == 'true'

        # SMTP configuration
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')

        # Email addresses
        hr_email = os.getenv('HR_EMAIL')
        from_email = os.getenv('MAIL_FROM')

        # Validate required environment variables
        required_vars = {
            'SMTP_SERVER': smtp_server,
            'SMTP_USER': smtp_user,
            'SMTP_PASSWORD': smtp_password,
            'HR_EMAIL': hr_email,
            'MAIL_FROM': from_email
        }
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("⚠️ Please check your .env file and ensure all required variables are set.")
            return False
        # ========================================

        # ========================================
        # CHIẾN LƯỢC GỬI EMAIL
        # ========================================
        if USE_COMPANY_EMAIL_ONLY:
            # Tất cả email đều gửi từ email hệ thống
            print(f"📧 Using system email for all: {from_email}")
        else:
            # Gửi từ email cá nhân (cần App Password cho mỗi nhân viên)
            employee_email = (user_data.get('email', '') or '').strip()
            from_email = employee_email if employee_email else from_email
            print(f"📧 Using personal email: {from_email}")

        print(f"SMTP Server: {smtp_server}", flush=True)
        print(f"SMTP Port: {smtp_port}", flush=True)
        print(f"SMTP User: {smtp_user}", flush=True)
        print(f"SMTP Password: {'***' if smtp_password else 'None'}", flush=True)
        print(f"From Email: {from_email}", flush=True)
        print(f"HR Email: {hr_email}", flush=True)

        # Email validation (already checked above in required_vars)
        if not from_email:
            print('❌ No email configuration found. Cannot send email.')
            return False

        # Kiểm tra xem có bật gửi email không
        if not ENABLE_EMAIL_SENDING:
            print('📧 Email sending is DISABLED. Simulating email send...')
            print('✅ Email simulation completed successfully!')
            return True  # Trả về True để UI hiển thị thành công

        # Kiểm tra cấu hình SMTP
        if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
            print('❌ SMTP configuration incomplete. Cannot send email.')
            return False

        # Tạo nội dung email
        action_lower = str(action).lower()
        if action_lower == 'create':
            action_label = 'TẠO ĐƠN'
        elif action_lower == 'delete':
            action_label = 'HUỶ/XÓA ĐƠN'
        else:
            action_label = 'CẬP NHẬT'

        # Xác định loại đơn và tạo tiêu đề phù hợp
        request_type = request_data.get('request_type', 'leave')
        late_early_type = request_data.get('late_early_type', '')

        if request_type == 'late_early':
            if late_early_type == 'late':
                request_type_label = 'ĐI TRỄ'
            elif late_early_type == 'early':
                request_type_label = 'VỀ SỚM'
            else:
                request_type_label = 'ĐI TRỄ/VỀ SỚM'
        elif request_type == '30min_break':
            request_type_label = 'NGHỈ 30 PHÚT'
        else:
            request_type_label = 'NGHỈ PHÉP'

        if action_lower == 'delete':
            if request_type == 'late_early':
                subject = f"[HUỶ/XÓA] [ĐƠN {request_type_label}] {user_data['name']} - Không còn nhu cầu"
            elif request_type == '30min_break':
                subject = f"[HUỶ/XÓA] [ĐƠN {request_type_label}] {user_data['name']} - Không còn nhu cầu"
            else:
                subject = f"[HUỶ/XÓA] [ĐƠN NGHỈ PHÉP] {user_data['name']} - Không còn nhu cầu nghỉ"
        else:
            if request_type == 'late_early':
                subject = f"[{action_label}] [ĐƠN {request_type_label}] {user_data['name']} - {request_data['leave_reason']}"
            elif request_type == '30min_break':
                subject = f"[{action_label}] [ĐƠN {request_type_label}] {user_data['name']} - {request_data['leave_reason']}"
            else:
                subject = f"[{action_label}] [ĐƠN NGHỈ PHÉP] {user_data['name']} - {request_data['leave_reason']}"
        print(f"Email Subject: {subject}", flush=True)

        # Định dạng ngày tháng từ các trường riêng lẻ
        from_date = f"{request_data.get('leave_from_day', '')}/{request_data.get('leave_from_month', '')}/{request_data.get('leave_from_year', '')}"
        to_date = f"{request_data.get('leave_to_day', '')}/{request_data.get('leave_to_month', '')}/{request_data.get('leave_to_year', '')}"
        from_time = f"{request_data.get('leave_from_hour', 0):02d}:{request_data.get('leave_from_minute', 0):02d}"
        to_time = f"{request_data.get('leave_to_hour', 0):02d}:{request_data.get('leave_to_minute', 0):02d}"

        # Tính tổng số ngày nghỉ
        total_days = (request_data.get('annual_leave_days', 0) or 0) + (request_data.get('unpaid_leave_days', 0) or 0) + (request_data.get('special_leave_days', 0) or 0)

        # Thông tin bổ sung cho HR
        has_docs = bool(request_data.get('attachments') or request_data.get('hospital_confirmation') or request_data.get('wedding_invitation') or request_data.get('death_birth_certificate'))

        # Tạo nội dung HTML
        cancel_notice_html = ""
        if action_lower == 'delete':
            cancel_notice_html = f"""
                <div class="highlight">
                    <h3>⚠️ Thông báo huỷ/xóa đơn</h3>
                    <p>Nhân viên xác nhận <strong>không còn nhu cầu nghỉ</strong>. Vui lòng:</p>
                    <ul>
                        <li>Ngừng xử lý/phê duyệt đơn này</li>
                        <li>Xóa/huỷ ghi nhận đơn nghỉ trong các hệ thống liên quan (nếu đã tạo)</li>
                        <li>Cập nhật lịch/phân ca nếu đã bố trí người thay thế</li>
                    </ul>
                    <p><em>Mã đơn:</em> #{request_data['id']}</p>
                </div>
            """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .highlight {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 10px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; font-weight: bold; }}
                .footer {{ margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; font-size: 14px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📧 THÔNG BÁO ĐƠN XIN NGHỈ PHÉP</h1>
                    <h2>📋 ĐƠN XIN NGHỈ PHÉP</h2>
                    <p><strong>Loại email:</strong> {action_label}</p>
                    <p><strong>Nhân viên:</strong> {user_data['name']} ({user_data.get('employee_id', '')})</p>
                    <p><strong>Email nhân viên:</strong> {user_data.get('email', 'Chưa cập nhật')}</p>
                    <p><strong>Gửi từ hệ thống:</strong> {from_email}</p>
                    <p><strong>Thời gian gửi:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                </div>

                {cancel_notice_html}

                <div class="highlight">
                    <h3>📅 Thông tin {'đi trễ/về sớm' if request_type == 'late_early' else 'nghỉ 30 phút' if request_type == '30min_break' else 'nghỉ phép'}</h3>
                    <table>
                        <tr>
                            <th>Lý do</th>
                            <td>{'[Đi trễ]: ' if request_type == 'late_early' and late_early_type == 'late' else '[Về sớm]: ' if request_type == 'late_early' and late_early_type == 'early' else '[Nghỉ 30 phút]: ' if request_type == '30min_break' else ''}{request_data['leave_reason']}</td>
                        </tr>
                        <tr>
                            <th>Khoảng thời gian</th>
                            <td>{from_date} {from_time} - {to_date} {to_time}</td>
                        </tr>
                        <tr>
                            <th>Ca làm việc</th>
                            <td>Ca {request_data.get('shift_code', '1')}</td>
                        </tr>
                        {'<tr><th>Thời gian đi trễ/về sớm</th><td><strong>' + ('Đi trễ: ' + from_time if late_early_type == 'late' else 'Về sớm: ' + to_time) + '</strong></td></tr>' if request_type == 'late_early' else '<tr><th>Thời gian nghỉ 30 phút</th><td><strong>' + from_time + ' - ' + to_time + '</strong></td></tr>' if request_type == '30min_break' else '<tr><th>Tổng số ngày nghỉ</th><td><strong>' + str(total_days) + ' ngày</strong></td></tr>'}
                    </table>

                    {'<h3>📊 Phân bổ ngày nghỉ</h3><table><tr><th>Phép năm</th><td>' + str(request_data.get('annual_leave_days', 0)) + ' ngày</td></tr><tr><th>Nghỉ không lương</th><td>' + str(request_data.get('unpaid_leave_days', 0)) + ' ngày</td></tr><tr><th>Nghỉ đặc biệt</th><td>' + str(request_data.get('special_leave_days', 0)) + ' ngày</td></tr></table>' if request_type == 'leave' else ''}

                    <h3>👥 Thông tin thay thế</h3>
                    <table>
                        <tr>
                            <th>Người thay thế</th>
                            <td>{request_data.get('substitute_name', 'Chưa chỉ định')}</td>
                        </tr>
                        <tr>
                            <th>Mã nhân viên thay thế</th>
                            <td>{request_data.get('substitute_employee_id', 'Chưa chỉ định')}</td>
                        </tr>
                    </table>
                </div>

                {f'<h3>📝 Ghi chú</h3><div class="highlight"><p>{request_data.get("notes", "")}</p></div>' if request_data.get('notes') else ''}

                <h3>ℹ️ Thông tin bổ sung</h3>
                <p>• Tài liệu đính kèm: {'Có' if has_docs else 'Không có'}</p>
                {f'<p>• <strong>📎 CÓ {len(json.loads(request_data["attachments"]))} FILE(S) ĐÍNH KÈM TRONG EMAIL NÀY</strong></p>' if request_data.get('attachments') else ''}
                <p>• Đơn này được gửi tự động từ hệ thống quản lý chấm công</p>
                <p>• Vui lòng phản hồi trong thời gian sớm nhất</p>

                <div class="footer">
                    <p><strong>Hệ thống quản lý chấm công DMI</strong></p>
                    <p>Email này được gửi tự động, vui lòng không trả lời trực tiếp.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Tạo nội dung text
        cancel_notice_text = ""
        if action_lower == 'delete':
            cancel_notice_text = (
                "\nTHÔNG BÁO HUỶ/XÓA ĐƠN:\n"
                "- Nhân viên không còn nhu cầu nghỉ.\n"
                "- Vui lòng ngừng xử lý và xoá/cập nhật các ghi nhận liên quan.\n"
                "- Cập nhật lịch/phân ca nếu đã sắp xếp thay thế.\n"
            )
        text_content = f"""
THÔNG BÁO ĐƠN XIN NGHỈ PHÉP

LOẠI EMAIL: {action_label}

Gửi từ: {user_data['name']} ({user_data.get('employee_id', '')})
Email: {from_email}
Thời gian gửi: {datetime.now().strftime('%d/%m/%Y %H:%M')}

{cancel_notice_text}

THÔNG TIN {'ĐI TRỄ/VỀ SỚM' if request_type == 'late_early' else 'NGHỈ 30 PHÚT' if request_type == '30min_break' else 'NGHỈ PHÉP'}:
- Lý do: {'[Đi trễ]: ' if request_type == 'late_early' and late_early_type == 'late' else '[Về sớm]: ' if request_type == 'late_early' and late_early_type == 'early' else '[Nghỉ 30 phút]: ' if request_type == '30min_break' else ''}{request_data['leave_reason']}
- Khoảng thời gian: {from_date} {from_time} - {to_date} {to_time}
- Ca làm việc: Ca {request_data.get('shift_code', '1')}
{'THỜI GIAN ĐI TRỄ/VỀ SỚM: ' + ('Đi trễ: ' + from_time if late_early_type == 'late' else 'Về sớm: ' + to_time) if request_type == 'late_early' else 'THỜI GIAN NGHỈ 30 PHÚT: ' + from_time + ' - ' + to_time if request_type == '30min_break' else 'TỔNG SỐ NGÀY NGHỈ: ' + str(total_days) + ' ngày'}

{'PHÂN BỔ NGÀY NGHỈ:' if request_type == 'leave' else ''}
{'- Phép năm: ' + str(request_data.get('annual_leave_days', 0)) + ' ngày' if request_type == 'leave' else ''}
{'- Nghỉ không lương: ' + str(request_data.get('unpaid_leave_days', 0)) + ' ngày' if request_type == 'leave' else ''}
{'- Nghỉ đặc biệt: ' + str(request_data.get('special_leave_days', 0)) + ' ngày' if request_type == 'leave' else ''}

THÔNG TIN THAY THẾ:
- Người thay thế: {request_data.get('substitute_name', 'Chưa chỉ định')}
- Mã nhân viên thay thế: {request_data.get('substitute_employee_id', 'Chưa chỉ định')}

{f'GHI CHÚ: {request_data.get("notes", "")}' if request_data.get('notes') else ''}

{f'📎 CÓ {len(json.loads(request_data["attachments"]))} FILE(S) ĐÍNH KÈM TRONG EMAIL NÀY' if request_data.get('attachments') else ''}

Lưu ý: Đơn xin nghỉ phép này đã được gửi tự động từ hệ thống quản lý chấm công.
        """

        # Tạo email message
        msg = MIMEMultipart('alternative')
        if USE_COMPANY_EMAIL_ONLY:
            # Hiển thị tên nhân viên trong From field
            display_from = f"{user_data['name']} (via DMI System) <{from_email}>"
        else:
            display_from = f"{user_data['name']} <{from_email}>"

        msg['From'] = display_from
        msg['To'] = hr_email
        msg['Subject'] = subject

        # Thêm nội dung
        text_part = MIMEText(text_content, 'plain', 'utf-8')
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(text_part)
        msg.attach(html_part)

        # Đính kèm file attachments nếu có
        attachments_added = 0
        if request_data.get('attachments'):
            try:
                attachments_list = json.loads(request_data['attachments'])
                upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'leave_requests')

                for attachment in attachments_list:
                    file_path = os.path.join(upload_dir, attachment['saved_name'])
                    original_name = attachment.get('original_name') or os.path.basename(file_path)
                    if os.path.exists(file_path):
                        try:
                            ctype, encoding = mimetypes.guess_type(original_name)
                            if ctype is None:
                                ctype = 'application/octet-stream'
                            maintype, subtype = ctype.split('/', 1)

                            with open(file_path, 'rb') as f:
                                # Dùng MIMEApplication để tự set Content-Type chuẩn
                                attachment_part = MIMEApplication(f.read(), _subtype=subtype)
                                # Mã hóa base64 để tránh hỏng file khi gửi
                                encoders.encode_base64(attachment_part)
                                # Thiết lập tên file sử dụng RFC2231 để hỗ trợ tiếng Việt/Unicode
                                attachment_part.add_header('Content-Disposition', 'attachment', filename=('utf-8', '', original_name))
                                # Một số client cần cả tham số name ở Content-Type
                                attachment_part.add_header('Content-Type', f'{ctype}; name="{original_name}"')
                                msg.attach(attachment_part)
                                attachments_added += 1
                                print(f"📎 Đã đính kèm file: {original_name}")
                        except Exception as e:
                            print(f"⚠️ Không thể đính kèm file {original_name}: {e}")
                    else:
                        print(f"⚠️ File không tồn tại: {file_path}")

                if attachments_added > 0:
                    print(f"📎 Tổng cộng đã đính kèm {attachments_added} file(s)")

            except Exception as e:
                print(f"⚠️ Lỗi khi xử lý attachments: {e}")

        # Gửi email
        print(f"📤 Đang gửi email đến {hr_email}...", flush=True)
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        print("✅ Email đã được gửi thành công!", flush=True)
        print("=== KẾT THÚC GỬI EMAIL (THÀNH CÔNG) ===")
        return True

    except Exception as e:
        print(f"❌ Lỗi khi gửi email xin phép nghỉ: {e}")
        print("=== KẾT THÚC GỬI EMAIL (LỖI) ===")
        return False


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
    
    # Call the local safe function (no import needed - consolidated)
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
            
            _safe_print(f"🚀 [ASYNC] Bắt đầu gửi email bất đồng bộ cho leave_request #{request_id}")
            _safe_print(f"📧 [ASYNC] Thông tin đơn: ID={request_id}, User={user_name}, Status={request_status}")
            
            # Cập nhật trạng thái đang gửi - chỉ dùng global state, không dùng DB trong thread
            from state.email_state import email_status
            email_status[request_id] = {
                'status': 'sending',
                'message': 'Đang gửi email...',
                'timestamp': time.time()
            }
            _safe_print(f"📤 [ASYNC] Set global status to sending for request #{request_id}")
            
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
            
            # Gửi email thực tế với data dictionaries (call local function)
            success = send_leave_request_email_safe(request_data, user_data, action)
            
            if success:
                email_status[request_id] = {
                        'status': 'success',
                    'message': 'Email đã được gửi thành công',
                        'timestamp': time.time()
                    }
                _safe_print(f"✅ [ASYNC] Email sent successfully for leave_request #{request_id}")
                
                # Cập nhật database từ main thread (scheduled task)
                _schedule_db_update(request_id, user_id, 'success', 'Email đã được gửi thành công')
            else:
                email_status[request_id] = {
                    'status': 'error',
                    'message': 'Không thể gửi email',
                    'timestamp': time.time()
                }
                
                _safe_print(f"❌ [ASYNC] Failed to send email for leave_request #{request_id}")
                
                # Cập nhật database từ main thread (scheduled task)
                _schedule_db_update(request_id, user_id, 'error', 'Không thể gửi email')
                
        except Exception as e:
            _safe_print(f"💥 [ASYNC] Lỗi trong thread gửi email: {e}")
            try:
                from state.email_state import email_status
                email_status[request_id] = {
                    'status': 'error',
                    'message': f'Lỗi gửi email: {str(e)}',
                    'timestamp': time.time()
                }
            except Exception:
                pass
    
    # Tạo thread mới để gửi email
    thread = threading.Thread(target=send_email_thread, daemon=True)
    thread.start()
    _safe_print(f"📤 [ASYNC] Đã khởi tạo thread gửi email cho leave_request #{leave_request.id}")
