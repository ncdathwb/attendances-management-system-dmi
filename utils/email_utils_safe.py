"""
Safe email utilities - không phụ thuộc vào SQLAlchemy objects
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

def send_leave_request_email_safe(request_data, user_data, action='create'):
    """
    Gửi email xin phép nghỉ với dữ liệu đã được serialize (tránh SQLAlchemy DetachedInstanceError)
    """
    try:
        print("=== BẮT ĐẦU GỬI EMAIL XIN PHÉP NGHỈ (SAFE) ===", flush=True)
        print(f"User: {user_data['name']} (ID: {user_data['id']})")
        print(f"Leave Request ID: {request_data['id']}")
        
        # ========================================
        # CẤU HÌNH EMAIL - THAY ĐỔI TẠI ĐÂY
        # ========================================
        ENABLE_EMAIL_SENDING = True  # ⚠️ Đặt True để gửi email thực tế
        
        smtp_server = 'smtp.gmail.com'           # Server SMTP (Gmail)
        smtp_port = 587                          # Port SMTP (587 cho TLS)
        smtp_user = 'ncdat.hwb@gmail.com'        # Email đăng nhập SMTP
        smtp_password = 'qhgc xqcd tchm prsx'    # App Password Gmail
        # ========================================
        
        # ========================================
        # CHIẾN LƯỢC GỬI EMAIL
        # ========================================
        # Option 1: Dùng email công ty chung (Khuyến nghị)
        USE_COMPANY_EMAIL_ONLY = True  # ✅ Dùng email công ty cho tất cả
        
        if USE_COMPANY_EMAIL_ONLY:
            # Tất cả email đều gửi từ email hệ thống (ncdat.hwb@gmail.com)
            from_email = 'ncdat.hwb@gmail.com'
            print(f"📧 Using system email for all: {from_email}")
        else:
            # Gửi từ email cá nhân (cần App Password cho mỗi nhân viên)
            employee_email = (user_data.get('email', '') or '').strip()
            from_email = employee_email if employee_email else 'ncdat.hwb@gmail.com'
            print(f"📧 Using personal email: {from_email}")
        
        hr_email = 'dmihue-nhansu01@acraft.jp'  # Email nhân sự nhận thông báo
        
        print(f"SMTP Server: {smtp_server}", flush=True)
        print(f"SMTP Port: {smtp_port}", flush=True)
        print(f"SMTP User: {smtp_user}", flush=True)
        print(f"SMTP Password: {'***' if smtp_password else 'None'}", flush=True)
        print(f"From Email: {from_email}", flush=True)
        print(f"HR Email: {hr_email}", flush=True)
        
        # Kiểm tra email có tồn tại không
        if not from_email:
            print('⚠️ User email not found, using default system email')
            from_email = 'ncdat.hwb@gmail.com'
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
