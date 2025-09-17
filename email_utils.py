import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import threading
import time

def send_leave_request_email(leave_request, user, action='create'):
    """
    Gửi email xin phép nghỉ đến phòng nhân sự
    """
    try:
        print("=== BẮT ĐẦU GỬI EMAIL XIN PHÉP NGHỈ ===", flush=True)
        print(f"User: {user.name} (ID: {user.id})")
        print(f"Leave Request ID: {leave_request.id}")
        
        # Cấu hình SMTP từ config (không dùng current_app)
        from config import Config
        smtp_server = Config.SMTP_SERVER
        smtp_port = Config.SMTP_PORT
        smtp_user = Config.SMTP_USER
        smtp_password = Config.SMTP_PASSWORD
        # Lấy email từ thông tin cá nhân của người gửi đơn
        employee_email = (user.email or '').strip() if hasattr(user, 'email') else ''
        allowed_domain = '@dmi-acraft.net'
        print(f"Employee email: {employee_email}")
        print(f"Allowed domain: {allowed_domain}")
        # YÊU CẦU: dùng mail cá nhân (nhân viên) để gửi
        # Chọn From = email nhân viên nếu có; fallback MAIL_FROM nếu không có
        use_personal_sender = bool(employee_email)
        from_email = employee_email if use_personal_sender else Config.MAIL_FROM
        print(f"Chosen From email (personal mode): {from_email}")
        hr_email = Config.HR_EMAIL
        
        print(f"SMTP Server: {smtp_server}", flush=True)
        print(f"SMTP Port: {smtp_port}", flush=True)
        print(f"SMTP User: {smtp_user}", flush=True)
        print(f"SMTP Password: {'***' if smtp_password else 'None'}", flush=True)
        print(f"From Email: {from_email}", flush=True)
        print(f"HR Email: {hr_email}", flush=True)
        
        # Kiểm tra email có tồn tại không (ưu tiên email cá nhân, fallback về MAIL_FROM)
        if not from_email:
            print('⚠️ User email not found, using default MAIL_FROM')
            from_email = Config.MAIL_FROM
            if not from_email:
                print('❌ No email configuration found. Cannot send email.')
                return False
            
        # Kiểm tra cấu hình SMTP
        if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
            print('❌ SMTP configuration incomplete. Cannot send email.')
            print(f"Missing: SMTP_SERVER={smtp_server}, SMTP_PORT={smtp_port}, SMTP_USER={smtp_user}, SMTP_PASSWORD={'***' if smtp_password else 'None'}")
            return False
            
        # Tạo nội dung email
        action_label = 'TẠO ĐƠN' if str(action).lower() == 'create' else 'CẬP NHẬT'
        subject = f"[{action_label}] [XIN PHÉP NGHỈ] {user.name} - {leave_request.leave_reason}"
        print(f"Email Subject: {subject}", flush=True)
        
        # Định dạng ngày tháng (tương thích với model hiện tại)
        def _safe_get_datetimes(lr):
            get_from = getattr(lr, 'get_leave_from_datetime', None)
            get_to = getattr(lr, 'get_leave_to_datetime', None)
            if callable(get_from) and callable(get_to):
                try:
                    return get_from(), get_to()
                except Exception:
                    pass
            try:
                from_dt = datetime(
                    int(lr.leave_from_year), int(lr.leave_from_month), int(lr.leave_from_day),
                    int(lr.leave_from_hour or 0), int(lr.leave_from_minute or 0)
                )
                to_dt = datetime(
                    int(lr.leave_to_year), int(lr.leave_to_month), int(lr.leave_to_day),
                    int(lr.leave_to_hour or 0), int(lr.leave_to_minute or 0)
                )
                return from_dt, to_dt
            except Exception:
                now = datetime.now()
                return now, now

        from_dt, to_dt = _safe_get_datetimes(leave_request)
        from_date = from_dt.strftime('%d/%m/%Y')
        to_date = to_dt.strftime('%d/%m/%Y')
        from_time = from_dt.strftime('%H:%M')
        to_time = to_dt.strftime('%H:%M')
        
        # Tính tổng số ngày nghỉ
        total_days = (leave_request.annual_leave_days or 0) + (leave_request.unpaid_leave_days or 0) + (leave_request.special_leave_days or 0)
        # Thông tin bổ sung cho HR
        has_docs = bool(getattr(leave_request, 'attachments', None) or getattr(leave_request, 'hospital_confirmation', None) or getattr(leave_request, 'wedding_invitation', None) or getattr(leave_request, 'death_birth_certificate', None))
        status = getattr(leave_request, 'status', 'pending')
        created_at = getattr(leave_request, 'created_at', None)
        updated_at = getattr(leave_request, 'updated_at', None)
        
        # Tạo HTML content
        # Tính badge trạng thái
        status_text = 'Chờ phê duyệt'
        status_style = 'display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;background:#fff7e6;color:#ad6800;border:1px solid #ffe58f;'
        if status == 'approved':
            status_text = 'Đã phê duyệt'
            status_style = 'display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;background:#f6ffed;color:#237804;border:1px solid #b7eb8f;'
        elif status == 'rejected':
            status_text = 'Từ chối'
            status_style = 'display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;background:#fff1f0;color:#a8071a;border:1px solid #ffa39e;'

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #f8f9fa; padding: 20px; border-left: 4px solid #007bff; }}
                .content {{ padding: 20px; }}
                .info-table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin: 15px 0; 
                    table-layout: fixed;
                }}
                .info-table th, .info-table td {{ 
                    border: 1px solid #ddd; 
                    padding: 15px; 
                    text-align: left; 
                    vertical-align: top;
                    word-wrap: break-word;
                }}
                .info-table th {{ 
                    background-color: #f8f9fa; 
                    font-weight: bold; 
                    width: 30%;
                    min-width: 120px;
                }}
                .info-table td {{ 
                    width: 70%;
                    background-color: #ffffff;
                }}
                .highlight {{ background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 15px 0; }}
                .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📋 ĐƠN XIN NGHỈ PHÉP</h2>
                <p><strong>Loại email:</strong> {action_label}</p>
                <p><strong>Gửi từ:</strong> {user.name} ({getattr(user, 'employee_id', '')})</p>
                <p><strong>Email:</strong> {from_email}</p>
                <p><strong>Thời gian gửi:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
            
            <div class="content">
                <h3>📅 Thông tin nghỉ phép</h3>
                <table class="info-table">
                    <tr>
                        <th>Lý do nghỉ</th>
                        <td>{leave_request.leave_reason}</td>
                    </tr>
                    <tr>
                        <th>Khoảng thời gian</th>
                        <td>{from_date} {from_time} - {to_date} {to_time}</td>
                    </tr>
                    <tr>
                        <th>Ca làm việc</th>
                        <td>Ca {leave_request.shift_code or '1'}</td>
                    </tr>
                    <tr>
                        <th>Tổng số ngày nghỉ</th>
                        <td><strong>{total_days} ngày</strong></td>
                    </tr>
                </table>
                
                <h3>📊 Phân bổ ngày nghỉ</h3>
                <table class="info-table">
                    <tr>
                        <th>Phép năm</th>
                        <td>{leave_request.annual_leave_days or 0} ngày</td>
                    </tr>
                    <tr>
                        <th>Nghỉ không lương</th>
                        <td>{leave_request.unpaid_leave_days or 0} ngày</td>
                    </tr>
                    <tr>
                        <th>Nghỉ đặc biệt</th>
                        <td>{leave_request.special_leave_days or 0} ngày</td>
                    </tr>
                </table>
                
                <h3>👥 Thông tin thay thế</h3>
                <table class="info-table">
                    <tr>
                        <th>Người thay thế</th>
                        <td>{leave_request.substitute_name or 'Chưa chỉ định'}</td>
                    </tr>
                    <tr>
                        <th>Mã nhân viên thay thế</th>
                        <td>{getattr(leave_request, 'substitute_employee_id', None) or 'Chưa chỉ định'}</td>
                    </tr>
                </table>
                
                {f'<h3>📝 Ghi chú</h3><div class="highlight"><p>{leave_request.notes}</p></div>' if leave_request.notes else ''}
                
                <h3>ℹ️ Thông tin bổ sung</h3>
                <table class="info-table">
                    <tr>
                        <th>Chứng từ</th>
                        <td>{'Có' if has_docs else 'Không'}</td>
                    </tr>
                    <tr>
                        <th>Thời gian tạo</th>
                        <td>{created_at.strftime('%d/%m/%Y %H:%M') if created_at else '-'}</td>
                    </tr>
                    <tr>
                        <th>Thời gian cập nhật</th>
                        <td>{updated_at.strftime('%d/%m/%Y %H:%M') if updated_at else '-'}</td>
                    </tr>
                </table>
                <div class="highlight" style="background:#fff3cd; padding:10px; border-left: 4px solid #ffc107; margin: 15px 0;">
                    <p><strong>⚠️ Lưu ý:</strong> Đơn xin nghỉ phép này đã được gửi tự động từ hệ thống quản lý chấm công. Vui lòng xem xét và phản hồi trong thời gian sớm nhất.</p>
                </div>
            </div>
            
            <div class="footer">
                <p>Email được gửi tự động từ Hệ thống Quản lý Chấm công DMI</p>
                <p>Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        
        # Tạo plain text content
        text_content = f"""
ĐƠN XIN NGHỈ PHÉP

LOẠI EMAIL: {action_label}

Gửi từ: {user.name} ({getattr(user, 'employee_id', '')})
Email: {from_email}
Thời gian gửi: {datetime.now().strftime('%d/%m/%Y %H:%M')}

THÔNG TIN NGHỈ PHÉP:
- Lý do nghỉ: {leave_request.leave_reason}
- Khoảng thời gian: {from_date} {from_time} - {to_date} {to_time}
- Ca làm việc: Ca {leave_request.shift_code or '1'}
- Tổng số ngày nghỉ: {total_days} ngày

PHÂN BỔ NGÀY NGHỈ:
- Phép năm: {leave_request.annual_leave_days or 0} ngày
- Nghỉ không lương: {leave_request.unpaid_leave_days or 0} ngày
- Nghỉ đặc biệt: {leave_request.special_leave_days or 0} ngày

THÔNG TIN THAY THẾ:
- Người thay thế: {leave_request.substitute_name or 'Chưa chỉ định'}
- Mã nhân viên thay thế: {getattr(leave_request, 'substitute_employee_id', None) or 'Chưa chỉ định'}

{f'GHI CHÚ: {leave_request.notes}' if leave_request.notes else ''}

Lưu ý: Đơn xin nghỉ phép này đã được gửi tự động từ hệ thống quản lý chấm công.

---
Email được gửi tự động từ Hệ thống Quản lý Chấm công DMI
Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        """
        
        # Tạo message
        msg = MIMEMultipart('alternative')
        # Đặt From hiển thị tên nhân viên; ưu tiên email cá nhân
        display_from = f"{user.name} <{from_email}>" if from_email else from_email
        msg['From'] = display_from
        msg['To'] = hr_email
        msg['Subject'] = subject
        # Luôn để Reply-To là nhân viên
        if employee_email:
            msg['Reply-To'] = employee_email
        print(f"Mail headers -> From: {display_from}, To: {hr_email}, Reply-To: {employee_email}", flush=True)
        
        # Thêm nội dung
        text_part = MIMEText(text_content, 'plain', 'utf-8')
        html_part = MIMEText(html_content, 'html', 'utf-8')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Gửi email
        print("🔄 Đang kết nối SMTP...", flush=True)
        try:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            print("✅ Kết nối SMTP thành công", flush=True)
        except Exception as e:
            print(f"❌ Lỗi kết nối SMTP: {e}")
            return False
        
        try:
            print("🔄 EHLO...", flush=True)
            server.ehlo()
            print("🔄 Đang bật TLS...", flush=True)
            server.starttls()
            server.ehlo()
            print("✅ TLS đã được bật", flush=True)
        except Exception as e:
            print(f"❌ Lỗi bật TLS: {e}")
            server.quit()
            return False
        
        try:
            print("🔄 Đang đăng nhập SMTP...", flush=True)
            server.login(smtp_user, smtp_password)
            print("✅ Đăng nhập SMTP thành công", flush=True)
        except Exception as e:
            print(f"❌ Lỗi đăng nhập SMTP: {e}")
            server.quit()
            return False
        
        try:
            print("🔄 Đang gửi email...", flush=True)
            # Envelope sender: ưu tiên email nhân viên theo yêu cầu; fallback MAIL_FROM
            envelope_from = from_email or Config.MAIL_FROM or smtp_user
            print(f"Envelope From: {envelope_from}", flush=True)
            try:
                server.sendmail(envelope_from, [hr_email], msg.as_string())
            except Exception as e_first:
                print(f"❌ Gửi với envelope nhân viên thất bại: {e_first}", flush=True)
                # Fallback gửi bằng MAIL_FROM để tăng tỉ lệ thành công
                fallback_from = Config.MAIL_FROM or smtp_user
                print(f"🔁 Thử lại với envelope: {fallback_from}", flush=True)
                server.sendmail(fallback_from, [hr_email], msg.as_string())
            print("✅ Email đã được gửi", flush=True)
        except Exception as e:
            print(f"❌ Lỗi gửi email: {e}")
            server.quit()
            return False
        
        try:
            print("🔄 Đang đóng kết nối...", flush=True)
            server.quit()
            print("✅ Kết nối đã được đóng", flush=True)
        except Exception as e:
            print(f"⚠️ Lỗi đóng kết nối: {e}")
        
        print(f"🎉 Email xin phép nghỉ đã được gửi thành công đến {hr_email}", flush=True)
        print("=== KẾT THÚC GỬI EMAIL ===", flush=True)
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi gửi email xin phép nghỉ: {str(e)}")
        print(f"❌ Loại lỗi: {type(e).__name__}")
        import traceback
        print(f"❌ Chi tiết lỗi: {traceback.format_exc()}")
        print("=== KẾT THÚC GỬI EMAIL (LỖI) ===")
        return False


def send_leave_request_email_async(leave_request, user, action='create'):
    """
    Gửi email xin phép nghỉ bất đồng bộ (không chặn response)
    """
    def send_email_thread():
        try:
            print(f"🚀 [ASYNC] Bắt đầu gửi email bất đồng bộ cho leave_request #{leave_request.id}", flush=True)
            print(f"📧 [ASYNC] Thông tin đơn: ID={leave_request.id}, User={user.name}, Status={getattr(leave_request, 'status', 'unknown')}", flush=True)
            
            # Cập nhật trạng thái đang gửi
            from app import app, upsert_email_status, publish_email_status
            from state.email_state import email_status
            email_status[leave_request.id] = {
                'status': 'sending',
                'message': 'Đang gửi email...',
                'timestamp': time.time()
            }
            print(f"📤 [ASYNC] Set global status to sending for request #{leave_request.id}")
            # Persist to DB as well
            try:
                with app.app_context():
                    upsert_email_status(leave_request.id, 'sending', 'Đang gửi email...')
                    publish_email_status(user.id, leave_request.id, 'sending', 'Đang gửi email...')
            except Exception as _:
                pass
            
            # Tạo application context cho thread
            with app.app_context():
                result = send_leave_request_email(leave_request, user, action)
                if result:
                    print(f"✅ [ASYNC] Email gửi thành công cho leave_request #{leave_request.id}", flush=True)
                    email_status[leave_request.id] = {
                        'status': 'success',
                        'message': 'Email đã được gửi thành công!',
                        'timestamp': time.time()
                    }
                    print(f"✅ [ASYNC] Set global status to success for request #{leave_request.id}")
                    upsert_email_status(leave_request.id, 'success', 'Email đã được gửi thành công!')
                    publish_email_status(user.id, leave_request.id, 'success', 'Email đã được gửi thành công!')
                else:
                    print(f"❌ [ASYNC] Email gửi thất bại cho leave_request #{leave_request.id}", flush=True)
                    email_status[leave_request.id] = {
                        'status': 'error',
                        'message': 'Gửi email thất bại. Vui lòng kiểm tra cấu hình SMTP.',
                        'timestamp': time.time()
                    }
                    print(f"❌ [ASYNC] Set global status to error for request #{leave_request.id}")
                    upsert_email_status(leave_request.id, 'error', 'Gửi email thất bại. Vui lòng kiểm tra cấu hình SMTP.')
                    publish_email_status(user.id, leave_request.id, 'error', 'Gửi email thất bại. Vui lòng kiểm tra cấu hình SMTP.')
        except Exception as e:
            print(f"💥 [ASYNC] Lỗi trong thread gửi email: {e}", flush=True)
            from app import email_status
            email_status[leave_request.id] = {
                'status': 'error',
                'message': f'Lỗi gửi email: {str(e)}',
                'timestamp': time.time()
            }
    
    # Tạo thread mới để gửi email
    thread = threading.Thread(target=send_email_thread, daemon=True)
    thread.start()
    print(f"📤 [ASYNC] Đã khởi tạo thread gửi email cho leave_request #{leave_request.id}", flush=True)
