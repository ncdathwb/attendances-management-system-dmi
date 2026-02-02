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

        # Xác định màu và icon theo loại action
        if action_lower == 'create':
            action_color = '#28a745'  # Xanh lá - tạo mới
            action_icon = '🆕'
            action_bg = '#d4edda'
        elif action_lower == 'delete':
            action_color = '#dc3545'  # Đỏ - xóa
            action_icon = '🗑️'
            action_bg = '#f8d7da'
        else:  # update
            action_color = '#ffc107'  # Vàng - cập nhật
            action_icon = '✏️'
            action_bg = '#fff3cd'

        # Xác định màu và icon theo loại đơn
        if request_type == 'late_early':
            if late_early_type == 'late':
                type_color = '#fd7e14'  # Cam - đi trễ
                type_icon = '⏰'
                type_label = 'ĐI TRỄ'
            else:
                type_color = '#6f42c1'  # Tím - về sớm
                type_icon = '🏃'
                type_label = 'VỀ SỚM'
        elif request_type == '30min_break':
            type_color = '#17a2b8'  # Xanh dương - nghỉ 30p
            type_icon = '☕'
            type_label = 'NGHỈ 30 PHÚT'
        else:
            type_color = '#007bff'  # Xanh - nghỉ phép
            type_icon = '📅'
            type_label = 'NGHỈ PHÉP'

        # Tạo nội dung HTML - thiết kế mới gọn gàng và rõ ràng
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f0f2f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
                .header {{ padding: 25px; text-align: center; }}
                .action-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-weight: bold; font-size: 14px; margin-bottom: 10px; background-color: {action_bg}; color: {action_color}; border: 2px solid {action_color}; }}
                .type-badge {{ display: inline-block; padding: 10px 25px; border-radius: 25px; font-weight: bold; font-size: 16px; background-color: {type_color}; color: white; }}
                .employee-info {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }}
                .employee-name {{ font-size: 22px; font-weight: bold; margin: 0 0 5px 0; }}
                .employee-id {{ font-size: 14px; opacity: 0.9; }}
                .content {{ padding: 25px; }}
                .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }}
                .info-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; }}
                .info-label {{ font-size: 12px; color: #6c757d; text-transform: uppercase; margin-bottom: 5px; }}
                .info-value {{ font-size: 16px; font-weight: 600; color: #212529; }}
                .reason-box {{ background: #e7f3ff; padding: 20px; border-radius: 8px; border-left: 4px solid {type_color}; margin-bottom: 20px; }}
                .reason-label {{ font-size: 12px; color: #6c757d; text-transform: uppercase; margin-bottom: 8px; }}
                .reason-text {{ font-size: 16px; color: #212529; line-height: 1.5; }}
                .leave-days {{ background: #fff3e0; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
                .leave-days-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; text-align: center; }}
                .leave-day-item {{ padding: 10px; background: white; border-radius: 6px; }}
                .leave-day-value {{ font-size: 24px; font-weight: bold; color: {type_color}; }}
                .leave-day-label {{ font-size: 11px; color: #6c757d; }}
                .substitute-box {{ background: #f0f7ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
                .substitute-title {{ font-size: 14px; font-weight: 600; color: #0066cc; margin-bottom: 10px; }}
                .notes-box {{ background: #fffbeb; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b; margin-bottom: 20px; }}
                .attachment-box {{ background: #dcfce7; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
                .attachment-icon {{ font-size: 20px; margin-right: 10px; }}
                .cancel-notice {{ background: #fee2e2; padding: 20px; border-radius: 8px; border: 2px solid #dc3545; margin-bottom: 20px; }}
                .cancel-title {{ color: #dc3545; font-weight: bold; font-size: 16px; margin-bottom: 10px; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #6c757d; }}
                .timestamp {{ font-size: 12px; color: #6c757d; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header với Action và Type badges -->
                <div class="header">
                    <div class="action-badge">{action_icon} {action_label}</div>
                    <br><br>
                    <div class="type-badge">{type_icon} {type_label}</div>
                </div>

                <!-- Thông tin nhân viên -->
                <div class="employee-info">
                    <p class="employee-name">{user_data['name']}</p>
                    <p class="employee-id">Mã NV: {user_data.get('employee_id', 'N/A')} | {user_data.get('email', '')}</p>
                </div>

                <div class="content">
                    {'<div class="cancel-notice"><div class="cancel-title">⚠️ THÔNG BÁO HỦY ĐƠN</div><p>Nhân viên xác nhận <strong>không còn nhu cầu</strong>. Vui lòng hủy xử lý đơn này.</p><p style="margin:0;font-size:13px;color:#666;">Mã đơn: #' + str(request_data['id']) + '</p></div>' if action_lower == 'delete' else ''}

                    <!-- Lý do -->
                    <div class="reason-box">
                        <div class="reason-label">Lý do</div>
                        <div class="reason-text">{request_data['leave_reason']}</div>
                    </div>

                    <!-- Thông tin thời gian -->
                    <div class="info-grid">
                        <div class="info-box">
                            <div class="info-label">{'Ngày' if request_type == '30min_break' or (from_date == to_date) else 'Từ ngày'}</div>
                            <div class="info-value">{from_date}</div>
                        </div>
                        {'<div class="info-box"><div class="info-label">Đến ngày</div><div class="info-value">' + to_date + '</div></div>' if from_date != to_date and request_type == 'leave' else '<div class="info-box"><div class="info-label">Ca làm việc</div><div class="info-value">Ca ' + str(request_data.get('shift_code', '1')) + '</div></div>'}
                    </div>

                    <div class="info-grid">
                        <div class="info-box">
                            <div class="info-label">{'Thời gian nghỉ' if request_type == '30min_break' else 'Giờ đi trễ' if request_type == 'late_early' and late_early_type == 'late' else 'Giờ về sớm' if request_type == 'late_early' else 'Từ giờ'}</div>
                            <div class="info-value" style="color: {type_color};">{from_time}{' - ' + to_time if request_type == '30min_break' else ''}</div>
                        </div>
                        {'<div class="info-box"><div class="info-label">Đến giờ</div><div class="info-value">' + to_time + '</div></div>' if request_type == 'leave' else '<div class="info-box"><div class="info-label">Ca làm việc</div><div class="info-value">Ca ' + str(request_data.get('shift_code', '1')) + '</div></div>' if request_type != '30min_break' else ''}
                    </div>

                    {'<div class="leave-days"><div class="info-label" style="margin-bottom:10px;">📊 Phân bổ ngày nghỉ</div><div class="leave-days-grid"><div class="leave-day-item"><div class="leave-day-value">' + str(request_data.get('annual_leave_days', 0)) + '</div><div class="leave-day-label">Phép năm</div></div><div class="leave-day-item"><div class="leave-day-value">' + str(request_data.get('unpaid_leave_days', 0)) + '</div><div class="leave-day-label">Không lương</div></div><div class="leave-day-item"><div class="leave-day-value">' + str(request_data.get('special_leave_days', 0)) + '</div><div class="leave-day-label">Đặc biệt</div></div></div><div style="text-align:center;margin-top:15px;font-size:18px;font-weight:bold;color:' + type_color + ';">Tổng: ' + str(total_days) + ' ngày</div></div>' if request_type == 'leave' else ''}

                    <!-- Người thay thế -->
                    <div class="substitute-box">
                        <div class="substitute-title">👥 Người thay thế</div>
                        <div style="font-size:15px;">{request_data.get('substitute_name', 'Chưa chỉ định') or 'Chưa chỉ định'} {'(' + request_data.get('substitute_employee_id', '') + ')' if request_data.get('substitute_employee_id') else ''}</div>
                    </div>

                    {f'<div class="notes-box"><div class="info-label">📝 Ghi chú</div><div style="margin-top:8px;">{request_data.get("notes", "")}</div></div>' if request_data.get('notes') else ''}

                    {f'<div class="attachment-box"><span class="attachment-icon">📎</span><strong>{len(json.loads(request_data["attachments"]))} file đính kèm</strong> trong email này</div>' if request_data.get('attachments') else ''}

                    <div class="timestamp">
                        Mã đơn: #{request_data['id']} | Gửi lúc: {datetime.now().strftime('%d/%m/%Y %H:%M')}
                    </div>
                </div>

                <div class="footer">
                    <strong>Hệ thống quản lý chấm công DMI</strong><br>
                    Email tự động - Vui lòng không trả lời trực tiếp
                </div>
            </div>
        </body>
        </html>
        """

        # Tạo nội dung text (plain text version) - gọn gàng hơn
        text_content = f"""
{'=' * 50}
{action_icon} {action_label} | {type_icon} {type_label}
{'=' * 50}

NHÂN VIÊN: {user_data['name']}
Mã NV: {user_data.get('employee_id', 'N/A')}
Email: {user_data.get('email', '')}

{'⚠️ THÔNG BÁO HỦY ĐƠN' if action_lower == 'delete' else ''}
{'Nhân viên xác nhận KHÔNG CÒN NHU CẦU. Vui lòng hủy xử lý đơn này.' if action_lower == 'delete' else ''}

LÝ DO: {request_data['leave_reason']}

THỜI GIAN:
{'- Ngày: ' + from_date if request_type == '30min_break' or from_date == to_date else '- Từ: ' + from_date + ' ' + from_time}
{'- Thời gian nghỉ: ' + from_time + ' - ' + to_time if request_type == '30min_break' else '- Đến: ' + to_date + ' ' + to_time if request_type == 'leave' else '- Giờ ' + ('đi trễ' if late_early_type == 'late' else 'về sớm') + ': ' + (from_time if late_early_type == 'late' else to_time)}
- Ca làm việc: Ca {request_data.get('shift_code', '1')}

{'PHÂN BỔ NGÀY NGHỈ:' if request_type == 'leave' else ''}
{'- Phép năm: ' + str(request_data.get('annual_leave_days', 0)) + ' ngày' if request_type == 'leave' else ''}
{'- Không lương: ' + str(request_data.get('unpaid_leave_days', 0)) + ' ngày' if request_type == 'leave' else ''}
{'- Đặc biệt: ' + str(request_data.get('special_leave_days', 0)) + ' ngày' if request_type == 'leave' else ''}
{'- TỔNG: ' + str(total_days) + ' ngày' if request_type == 'leave' else ''}

NGƯỜI THAY THẾ: {request_data.get('substitute_name', 'Chưa chỉ định') or 'Chưa chỉ định'} {('(' + request_data.get('substitute_employee_id', '') + ')') if request_data.get('substitute_employee_id') else ''}

{f'GHI CHÚ: {request_data.get("notes", "")}' if request_data.get('notes') else ''}

{f'📎 CÓ {len(json.loads(request_data["attachments"]))} FILE ĐÍNH KÈM' if request_data.get('attachments') else ''}

--
Mã đơn: #{request_data['id']}
Gửi lúc: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Hệ thống quản lý chấm công DMI
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
