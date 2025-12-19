"""
Signature Management System for Smart Approval Workflow
"""
import base64
import json
import hashlib
import hmac
from datetime import datetime, timedelta, time
from typing import Optional, Dict, Any, Tuple
from cryptography.fernet import Fernet, InvalidToken
import os
from flask import session, request
import logging
from database.models import Attendance
from utils.signature_processor import signature_processor
from utils.signature_fit_adapter import signature_fit_adapter

logger = logging.getLogger(__name__)

class SignatureManager:
    """Quản lý chữ ký thông minh cho hệ thống phê duyệt"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Khởi tạo với Flask app"""
        self.app = app
        # Tạo secret key cho mã hóa nếu chưa có
        if 'SIGNATURE_SECRET_KEY' not in app.config:
            app.config['SIGNATURE_SECRET_KEY'] = Fernet.generate_key()
        
        self.cipher = Fernet(app.config['SIGNATURE_SECRET_KEY'])
        self.session_timeout = app.config.get('SIGNATURE_SESSION_TIMEOUT', 1800)  # 30 phút
    
    def encrypt_signature(self, signature_data: str) -> str:
        """Mã hóa chữ ký"""
        try:
            if not signature_data:
                return ""
            
            # 处理签名图像质量
            processed_signature = signature_processor.process_signature(signature_data)
            
            encrypted = self.cipher.encrypt(processed_signature.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encrypting signature: {e}")
            return ""
    
    def decrypt_signature(self, encrypted_signature: str) -> str:
        """Giải mã chữ ký"""
        try:
            if not encrypted_signature:
                return ""
            # Normalize and fix base64 padding before decode to avoid "Incorrect padding"
            normalized = encrypted_signature.strip()
            # Some transports may replace '+' with space
            normalized = normalized.replace(' ', '+')
            # Ensure length is multiple of 4
            padding_needed = (-len(normalized)) % 4
            if padding_needed:
                normalized += '=' * padding_needed

            # Try urlsafe decode first, then fall back to standard base64
            try:
                encrypted_bytes = base64.urlsafe_b64decode(normalized.encode('utf-8'))
            except Exception:
                encrypted_bytes = base64.b64decode(normalized.encode('utf-8'))
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            if isinstance(e, InvalidToken):
                # Silent fail for InvalidToken to avoid noisy logs; logic unchanged (return empty string)
                return ""
            else:
                logger.error(f"Error decrypting signature: {type(e).__name__}: {repr(e)}")
                return ""
    
    def get_session_signature_key(self, user_id: int, role: str) -> str:
        """Tạo key cho session signature"""
        return f"signature_{user_id}_{role}"
    
    def get_session_signature_meta_key(self, user_id: int, role: str) -> str:
        """Tạo key cho metadata của session signature"""
        return f"signature_meta_{user_id}_{role}"
    
    def save_signature_to_session(self, user_id: int, role: str, signature: str, 
                                signature_type: str = "new", dont_ask_again: bool = False) -> bool:
        """Lưu chữ ký vào session với metadata"""
        try:
            if not signature:
                return False
            
            # Mã hóa chữ ký
            encrypted_signature = self.encrypt_signature(signature)
            
            # Tạo metadata
            metadata = {
                'created_at': datetime.now().isoformat(),
                'type': signature_type,  # 'new', 'reused', 'session_reused', 'database_reused'
                'ip_address': request.remote_addr if request else None,
                'user_agent': request.headers.get('User-Agent') if request else None,
                'expires_at': (datetime.now() + timedelta(seconds=self.session_timeout)).isoformat(),
                'dont_ask_again': dont_ask_again
            }
            
            # Lưu vào session
            session_key = self.get_session_signature_key(user_id, role)
            meta_key = self.get_session_signature_meta_key(user_id, role)
            
            session[session_key] = encrypted_signature
            session[meta_key] = metadata
            
            # Lưu flag không hỏi lại nếu được yêu cầu
            if dont_ask_again:
                self.set_dont_ask_again(user_id, role, True)
            
            logger.info(f"✅ SIGNATURE SAVED: User {user_id} ({role}) saved {signature_type} signature to session")
            return True
            
        except Exception as e:
            logger.error(f"❌ ERROR SAVING SIGNATURE: {e}")
            return False
    
    def get_signature_from_session(self, user_id: int, role: str) -> Tuple[Optional[str], Optional[Dict]]:
        """Lấy chữ ký từ session với metadata"""
        try:
            session_key = self.get_session_signature_key(user_id, role)
            meta_key = self.get_session_signature_meta_key(user_id, role)
            
            encrypted_signature = session.get(session_key)
            metadata = session.get(meta_key)
            
            if not encrypted_signature or not metadata:
                return None, None
            
            # Kiểm tra hết hạn
            expires_at = datetime.fromisoformat(metadata['expires_at'])
            if datetime.now() > expires_at:
                # Xóa chữ ký hết hạn
                self.clear_session_signature(user_id, role)
                logger.info(f"⏰ SIGNATURE EXPIRED: User {user_id} ({role}) session signature expired")
                return None, None
            
            # Giải mã chữ ký
            signature = self.decrypt_signature(encrypted_signature)
            logger.info(f"📄 SIGNATURE RETRIEVED: User {user_id} ({role}) retrieved {metadata.get('type', 'unknown')} signature from session")
            return signature, metadata
            
        except Exception as e:
            logger.error(f"❌ ERROR GETTING SIGNATURE: {e}")
            return None, None
    
    def clear_session_signature(self, user_id: int, role: str) -> bool:
        """Xóa chữ ký khỏi session"""
        try:
            session_key = self.get_session_signature_key(user_id, role)
            meta_key = self.get_session_signature_meta_key(user_id, role)
            
            session.pop(session_key, None)
            session.pop(meta_key, None)
            
            # Xóa flag không hỏi lại
            self.set_dont_ask_again(user_id, role, False)
            
            logger.info(f"🗑️ SIGNATURE CLEARED: User {user_id} ({role}) cleared session signature")
            return True
            
        except Exception as e:
            logger.error(f"❌ ERROR CLEARING SIGNATURE: {e}")
            return False
    
    def has_valid_session_signature(self, user_id: int, role: str) -> bool:
        """Kiểm tra có chữ ký hợp lệ trong session không"""
        signature, metadata = self.get_signature_from_session(user_id, role)
        return signature is not None and metadata is not None
    
    def get_signature_from_database(self, user_id: int, role: str, attendance_id: int = None) -> Optional[str]:
        """Lấy chữ ký từ database dựa trên role và kiểm tra chữ ký từ vai trò thấp hơn"""
        try:
            from database.models import Attendance, User, db
            
            user = db.session.get(User, user_id)
            if not user:
                return None
            
            # Ưu tiên 1: Chữ ký cá nhân của user
            if user.has_personal_signature():
                logger.info(f"✅ PERSONAL SIGNATURE: User {user_id} ({role}) using personal signature")
                return user.personal_signature
            
            # Nếu có attendance_id, lấy chữ ký từ attendance record
            if attendance_id:
                attendance = Attendance.query.get(attendance_id)
                if not attendance:
                    return None
                
                # Ưu tiên 2: Chữ ký từ vai trò hiện tại trong attendance này
                if role == 'TEAM_LEADER' and attendance.team_leader_signature:
                    logger.info(f"💾 CURRENT ROLE SIGNATURE: User {user_id} ({role}) found signature in attendance {attendance_id}")
                    return attendance.team_leader_signature
                elif role == 'MANAGER' and attendance.manager_signature:
                    logger.info(f"💾 CURRENT ROLE SIGNATURE: User {user_id} ({role}) found signature in attendance {attendance_id}")
                    return attendance.manager_signature
                elif role == 'EMPLOYEE' and attendance.signature:
                    logger.info(f"💾 CURRENT ROLE SIGNATURE: User {user_id} ({role}) found signature in attendance {attendance_id}")
                    return attendance.signature
                
                # Ưu tiên 3: Tái sử dụng chữ ký từ vai trò thấp hơn (chỉ của chính user đó)
                if role == 'TEAM_LEADER' and attendance.signature and attendance.user_id == user_id:
                    logger.info(f"🔄 REUSE LOWER ROLE: User {user_id} ({role}) reusing employee signature from attendance {attendance_id}")
                    return attendance.signature
                elif role == 'MANAGER':
                    # Kiểm tra chữ ký team leader trước (nếu user này đã từng là team leader)
                    if attendance.team_leader_signature and attendance.approved_by == user_id:
                        logger.info(f"🔄 REUSE LOWER ROLE: User {user_id} ({role}) reusing team leader signature from attendance {attendance_id}")
                        return attendance.team_leader_signature
                    # Sau đó kiểm tra chữ ký employee
                    elif attendance.signature and attendance.user_id == user_id:
                        logger.info(f"🔄 REUSE LOWER ROLE: User {user_id} ({role}) reusing employee signature from attendance {attendance_id}")
                        return attendance.signature
                
                return None
            
            # Nếu không có attendance_id, tìm chữ ký gần nhất của user hiện tại
            # Ưu tiên chữ ký từ vai trò hiện tại trước
            if role == 'TEAM_LEADER':
                # Tìm chữ ký team leader gần nhất của user hiện tại
                attendance = Attendance.query.filter(
                    Attendance.team_leader_signature.isnot(None),
                    Attendance.team_leader_signature != '',
                    Attendance.approved_by == user_id
                ).order_by(Attendance.updated_at.desc()).first()
                
                if attendance:
                    logger.info(f"💾 RECENT ROLE SIGNATURE: User {user_id} ({role}) found recent signature")
                    return attendance.team_leader_signature
                
                # Nếu không có, tìm chữ ký employee gần nhất
                attendance = Attendance.query.filter(
                    Attendance.signature.isnot(None),
                    Attendance.signature != '',
                    Attendance.user_id == user_id
                ).order_by(Attendance.updated_at.desc()).first()
                
                if attendance:
                    logger.info(f"🔄 REUSE RECENT LOWER ROLE: User {user_id} ({role}) reusing recent employee signature")
                    return attendance.signature
                
            elif role == 'MANAGER':
                # Tìm chữ ký manager gần nhất của user hiện tại
                attendance = Attendance.query.filter(
                    Attendance.manager_signature.isnot(None),
                    Attendance.manager_signature != '',
                    Attendance.approved_by == user_id
                ).order_by(Attendance.updated_at.desc()).first()
                
                if attendance:
                    logger.info(f"💾 RECENT ROLE SIGNATURE: User {user_id} ({role}) found recent signature")
                    return attendance.manager_signature
                
                # Nếu không có, tìm chữ ký team leader gần nhất
                attendance = Attendance.query.filter(
                    Attendance.team_leader_signature.isnot(None),
                    Attendance.team_leader_signature != '',
                    Attendance.approved_by == user_id
                ).order_by(Attendance.updated_at.desc()).first()
                
                if attendance:
                    logger.info(f"🔄 REUSE RECENT LOWER ROLE: User {user_id} ({role}) reusing recent team leader signature")
                    return attendance.team_leader_signature
                
                # Nếu không có, tìm chữ ký employee gần nhất
                attendance = Attendance.query.filter(
                    Attendance.signature.isnot(None),
                    Attendance.signature != '',
                    Attendance.user_id == user_id
                ).order_by(Attendance.updated_at.desc()).first()
                
                if attendance:
                    logger.info(f"🔄 REUSE RECENT LOWER ROLE: User {user_id} ({role}) reusing recent employee signature")
                    return attendance.signature
                
            else:  # EMPLOYEE
                # Tìm chữ ký employee gần nhất của user hiện tại
                attendance = Attendance.query.filter(
                    Attendance.signature.isnot(None),
                    Attendance.signature != '',
                    Attendance.user_id == user_id
                ).order_by(Attendance.updated_at.desc()).first()
                
                if attendance:
                    logger.info(f"💾 RECENT ROLE SIGNATURE: User {user_id} ({role}) found recent signature")
                    return attendance.signature
            
            logger.info(f"❌ NO DATABASE SIGNATURE: User {user_id} ({role}) no signature found in database")
            return None
                
        except Exception as e:
            logger.error(f"❌ ERROR GETTING DATABASE SIGNATURE: {e}")
            return None
    
    def should_use_session_signature(self, user_id: int, role: str) -> bool:
        """Kiểm tra có nên sử dụng chữ ký trong session không"""
        # Kiểm tra flag "don't ask again" trong session
        dont_ask_key = f"dont_ask_signature_{user_id}_{role}"
        return session.get(dont_ask_key, False)
    
    def set_dont_ask_again(self, user_id: int, role: str, value: bool = True) -> None:
        """Đặt flag không hỏi lại chữ ký trong phiên"""
        dont_ask_key = f"dont_ask_signature_{user_id}_{role}"
        session[dont_ask_key] = value
        logger.info(f"🔒 DONT ASK AGAIN SET: User {user_id} ({role}) set to {value}")
    
    def check_signature_status(self, user_id: int, role: str, attendance_id: int = None) -> Dict[str, Any]:
        """Kiểm tra trạng thái chữ ký cho phê duyệt"""
        try:
            from database.models import User, db
            
            user = db.session.get(User, user_id)
            if not user:
                return {
                    'need_signature': True,
                    'is_admin': False,
                    'has_session_signature': False,
                    'has_db_signature': False,
                    'should_use_session': False,
                    'session_signature_available': False,
                    'message': 'Không tìm thấy người dùng'
                }
            
            # Kiểm tra nếu là admin
            if role == 'ADMIN':
                return {
                    'need_signature': False,
                    'is_admin': True,
                    'has_session_signature': False,
                    'has_db_signature': False,
                    'should_use_session': False,
                    'session_signature_available': False,
                    'message': 'Admin không cần chữ ký để phê duyệt'
                }
            
            # Kiểm tra chữ ký cá nhân
            has_personal_signature = user.has_personal_signature()
            
            # Kiểm tra chữ ký trong session
            session_signature, session_meta = self.get_signature_from_session(user_id, role)
            has_session_signature = session_signature is not None
            should_use_session = self.should_use_session_signature(user_id, role)
            
            # Kiểm tra chữ ký trong database (bao gồm cả chữ ký từ vai trò thấp hơn)
            logger.info(f"🔍 CHECKING DB SIGNATURE: User {user_id} ({role}), attendance_id: {attendance_id}")
            db_signature = self.get_signature_from_database(user_id, role, attendance_id)
            has_db_signature = db_signature is not None
            logger.info(f"🔍 DB SIGNATURE RESULT: {'Found' if has_db_signature else 'Not found'}, length: {len(db_signature) if db_signature else 0}")
            
            # Xác định có thể sử dụng chữ ký session không
            session_signature_available = has_session_signature and should_use_session
            
            # Tạo message phù hợp
            if has_personal_signature:
                message = 'Có thể sử dụng chữ ký cá nhân'
            elif has_session_signature and should_use_session:
                message = 'Có thể sử dụng chữ ký từ phiên hiện tại'
            elif has_db_signature:
                if attendance_id:
                    # Kiểm tra xem có phải tái sử dụng từ vai trò thấp hơn không
                    attendance = Attendance.query.get(attendance_id)
                    if attendance:
                        is_reused = False
                        if role == 'TEAM_LEADER' and attendance.signature and attendance.signature == db_signature and attendance.user_id == user_id:
                            is_reused = True
                            message = 'Có thể tái sử dụng chữ ký từ vai trò nhân viên'
                        elif role == 'MANAGER':
                            if attendance.team_leader_signature and attendance.team_leader_signature == db_signature and attendance.approved_by == user_id:
                                is_reused = True
                                message = 'Có thể tái sử dụng chữ ký từ vai trò trưởng nhóm'
                            elif attendance.signature and attendance.signature == db_signature and attendance.user_id == user_id:
                                is_reused = True
                                message = 'Có thể tái sử dụng chữ ký từ vai trò nhân viên'
                        else:
                            message = 'Có thể sử dụng chữ ký từ database'
                else:
                    message = 'Có thể sử dụng chữ ký từ database'
            else:
                message = 'Cần tạo chữ ký mới'
            
            # Xác định có phải chữ ký tái sử dụng không
            is_reused_signature = False
            if has_db_signature and attendance_id:
                attendance = Attendance.query.get(attendance_id)
                if attendance:
                    if role == 'TEAM_LEADER' and attendance.signature and attendance.signature == db_signature and attendance.user_id == user_id:
                        is_reused_signature = True
                    elif role == 'MANAGER':
                        if (attendance.team_leader_signature and attendance.team_leader_signature == db_signature and attendance.approved_by == user_id) or \
                           (attendance.signature and attendance.signature == db_signature and attendance.user_id == user_id):
                            is_reused_signature = True
            
            result = {
                'need_signature': not has_personal_signature,  # Chỉ cần chữ ký cá nhân là bắt buộc
                'is_admin': False,
                'has_personal_signature': has_personal_signature,
                'has_session_signature': has_session_signature,
                'has_db_signature': has_db_signature,
                'should_use_session': should_use_session,
                'session_signature_available': session_signature_available,
                'is_reused_signature': is_reused_signature,
                'message': message
            }
            
            logger.info(f"🔍 SIGNATURE STATUS: User {user_id} ({role}) - Personal: {has_personal_signature}, Session: {has_session_signature}, DB: {has_db_signature}, Reused: {is_reused_signature}, Use Session: {session_signature_available}")
            return result
            
        except Exception as e:
            logger.error(f"❌ ERROR CHECKING SIGNATURE STATUS: {e}")
            return {
                'need_signature': True,
                'is_admin': False,
                'has_session_signature': False,
                'has_db_signature': False,
                'should_use_session': False,
                'session_signature_available': False,
                'is_reused_signature': False,
                'message': 'Lỗi kiểm tra trạng thái chữ ký'
            }
    
    def validate_signature_quality(self, signature_data: str) -> Dict[str, Any]:
        """验证签名质量并返回详细报告"""
        try:
            return signature_processor.validate_signature_quality(signature_data)
        except Exception as e:
            logger.error(f"Error validating signature quality: {e}")
            return {
                'valid': False,
                'error': f'Lỗi kiểm tra chất lượng: {str(e)}',
                'score': 0
            }
    
    def process_signature_for_display(self, signature_data: str, 
                                    target_size: Tuple[int, int] = (400, 150)) -> str:
        """处理签名用于显示"""
        try:
            return signature_processor.process_signature(signature_data, target_size)
        except Exception as e:
            logger.error(f"Error processing signature for display: {e}")
            return signature_data
    
    def create_signature_preview(self, signature_data: str) -> str:
        """创建签名预览"""
        try:
            return signature_processor.create_signature_preview(signature_data)
        except Exception as e:
            logger.error(f"Error creating signature preview: {e}")
            return signature_data
    
    def fit_signature_to_form_box(self, signature_data: str, box_type: str = 'default') -> str:
        """Điều chỉnh chữ ký vừa khít với ô ký trong biểu mẫu"""
        try:
            return signature_fit_adapter.fit_signature_to_box(signature_data, box_type)
        except Exception as e:
            logger.error(f"Error fitting signature to form box: {e}")
            return signature_data
    
    def create_form_signatures(self, signatures: Dict[str, str]) -> Dict[str, str]:
        """Tạo chữ ký cho toàn bộ biểu mẫu"""
        try:
            return signature_fit_adapter.create_form_signatures(signatures)
        except Exception as e:
            logger.error(f"Error creating form signatures: {e}")
            return {}
    
    def validate_signature_fit(self, signature_data: str, box_type: str = 'default') -> Dict[str, Any]:
        """Kiểm tra xem chữ ký có vừa khít với ô không"""
        try:
            return signature_fit_adapter.validate_signature_fit(signature_data, box_type)
        except Exception as e:
            logger.error(f"Error validating signature fit: {e}")
            return {
                'fits': False,
                'error': f'Lỗi kiểm tra: {str(e)}',
                'recommendation': 'Thử lại sau'
            }
    
    def log_signature_action(self, user_id: int, action: str, signature_type: str, 
                           attendance_id: int = None, request_id: int = None, 
                           additional_data: Dict = None) -> None:
        """Ghi log hành động chữ ký chi tiết"""
        try:
            from utils.session import log_audit_action
            
            log_data = {
                'action': action,
                'signature_type': signature_type,
                'timestamp': datetime.now().isoformat(),
                'ip_address': request.remote_addr if request else None,
                'user_agent': request.headers.get('User-Agent') if request else None,
                'session_id': session.get('session_id', 'unknown') if session else 'unknown'
            }
            
            # Thêm dữ liệu bổ sung nếu có
            if additional_data:
                log_data.update(additional_data)
            
            if attendance_id:
                log_audit_action(
                    user_id=user_id,
                    action=f'SIGNATURE_{action.upper()}',
                    table_name='attendances',
                    record_id=attendance_id,
                    new_values=log_data
                )
            elif request_id:
                log_audit_action(
                    user_id=user_id,
                    action=f'SIGNATURE_{action.upper()}',
                    table_name='requests',
                    record_id=request_id,
                    new_values=log_data
                )
            else:
                log_audit_action(
                    user_id=user_id,
                    action=f'SIGNATURE_{action.upper()}',
                    table_name='users',
                    record_id=user_id,
                    new_values=log_data
                )
            
            logger.info(f"📝 SIGNATURE LOGGED: User {user_id} - {action} ({signature_type})")
                
        except Exception as e:
            logger.error(f"❌ ERROR LOGGING SIGNATURE ACTION: {e}")

# Global instance
signature_manager = SignatureManager() 