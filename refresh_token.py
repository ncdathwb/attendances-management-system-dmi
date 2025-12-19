#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script gia hạn token Google API
Xử lý lỗi invalid_grant và tự động tạo token mới nếu cần
"""

import os
import sys
import pickle
import shutil
from datetime import datetime

# Thiết lập encoding UTF-8 cho Windows
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import Google API libraries
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request as GoogleRequest
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("❌ Google API libraries không có sẵn!")
    print("Hãy cài đặt: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    input("Nhấn Enter để thoát...")
    sys.exit(1)

# Phạm vi quyền truy cập Google API
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

def print_header():
    """In header đẹp"""
    print("=" * 70)
    print("🔄 GIA HẠN TOKEN GOOGLE API")
    print("=" * 70)
    print(f"⏰ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def check_credentials():
    """Kiểm tra file credentials.json"""
    if not os.path.exists('credentials.json'):
        print("❌ Không tìm thấy file credentials.json!")
        print("Hãy tải file credentials.json từ Google Cloud Console")
        return False
    print("✅ File credentials.json tồn tại")
    return True

def backup_token():
    """Backup token cũ trước khi xóa"""
    if os.path.exists('token.pickle'):
        backup_dir = 'token_backups'
        os.makedirs(backup_dir, exist_ok=True)
        backup_name = os.path.join(backup_dir, f"token_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pickle")
        try:
            shutil.copy2('token.pickle', backup_name)
            print(f"💾 Đã backup token cũ: {backup_name}")
            return True
        except Exception as e:
            print(f"⚠️ Không thể backup token cũ: {e}")
    return False

def try_refresh_existing_token():
    """Thử refresh token hiện tại"""
    print("\n🔄 BƯỚC 1: THỬ REFRESH TOKEN HIỆN TẠI...")
    print("-" * 70)
    
    if not os.path.exists('token.pickle'):
        print("⚠️ Không có file token.pickle, cần tạo token mới")
        return False
    
    try:
        # Load token
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        
        print(f"   📊 Trạng thái token: {'Hết hạn' if creds.expired else 'Còn hiệu lực'}")
        print(f"   🔑 Có refresh_token: {'Có' if creds.refresh_token else 'Không'}")
        
        # Nếu token hết hạn và có refresh_token
        if creds.expired and creds.refresh_token:
            print("   🔄 Đang thử refresh token...")
            try:
                creds.refresh(GoogleRequest())
                
                # Lưu token mới
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
                
                # Lưu thời gian refresh
                with open('last_token_refresh.txt', 'w') as f:
                    f.write(datetime.now().isoformat())
                
                print("   ✅ Token đã được refresh thành công!")
                return True
            except Exception as e:
                error_str = str(e)
                if 'invalid_grant' in error_str.lower():
                    print(f"   ❌ Lỗi invalid_grant: Refresh token không hợp lệ")
                    print("   💡 Cần tạo token mới bằng cách xác thực lại")
                else:
                    print(f"   ❌ Lỗi khi refresh: {e}")
                return False
        elif not creds.refresh_token:
            print("   ❌ Không có refresh_token, cần tạo token mới")
            return False
        else:
            print("   ✅ Token vẫn còn hiệu lực, không cần refresh")
            return True
            
    except Exception as e:
        print(f"   ❌ Lỗi khi load token: {e}")
        return False

def test_token():
    """Test token có hoạt động không"""
    print("\n🔍 BƯỚC 2: TEST TOKEN...")
    print("-" * 70)
    
    try:
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        
        # Test Drive API
        print("   🔍 Đang test Drive API...")
        drive_service = build('drive', 'v3', credentials=creds)
        results = drive_service.files().list(pageSize=1).execute()
        files = results.get('files', [])
        print(f"   ✅ Drive API: OK (tìm thấy {len(files)} file)")
        
        # Test Sheets API
        print("   🔍 Đang test Sheets API...")
        sheets_service = build('sheets', 'v4', credentials=creds)
        print("   ✅ Sheets API: OK")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Lỗi test token: {e}")
        return False

def create_new_token():
    """Tạo token mới bằng cách xác thực lại"""
    print("\n🔄 BƯỚC 3: TẠO TOKEN MỚI...")
    print("-" * 70)
    
    try:
        print("   📋 Đang khởi tạo flow xác thực...")
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', GOOGLE_SCOPES)
        
        print("   🌐 Đang mở browser để xác thực...")
        print("   ⚠️  LƯU Ý: Hãy đăng nhập và cấp quyền trong browser!")
        creds = flow.run_local_server(port=0)
        
        # Lưu token mới
        print("   💾 Đang lưu token mới...")
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
        
        # Lưu thời gian refresh
        with open('last_token_refresh.txt', 'w') as f:
            f.write(datetime.now().isoformat())
        
        print("   ✅ Token mới đã được tạo và lưu thành công!")
        return True
        
    except Exception as e:
        print(f"   ❌ Lỗi khi tạo token mới: {e}")
        return False

def clean_old_token():
    """Xóa token cũ để tạo mới"""
    print("\n🧹 XÓA TOKEN CŨ...")
    print("-" * 70)
    
    files_to_remove = ['token.pickle', 'last_token_refresh.txt']
    removed_files = []
    
    for file in files_to_remove:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"   ✅ Đã xóa: {file}")
                removed_files.append(file)
            except Exception as e:
                print(f"   ⚠️ Không thể xóa {file}: {e}")
    
    return removed_files

def main():
    """Chương trình chính"""
    print_header()
    
    # Kiểm tra credentials
    if not check_credentials():
        input("\nNhấn Enter để thoát...")
        return
    
    # Backup token cũ
    backup_token()
    
    # Thử refresh token hiện tại
    if try_refresh_existing_token():
        # Test token
        if test_token():
            print("\n" + "=" * 70)
            print("🎉 THÀNH CÔNG!")
            print("=" * 70)
            print("Token đã được gia hạn và hoạt động bình thường!")
            print("Bạn có thể tiếp tục sử dụng ứng dụng.")
        else:
            print("\n⚠️ Token đã refresh nhưng test API lỗi")
            print("Có thể do vấn đề mạng hoặc quyền truy cập")
    else:
        # Token không thể refresh, cần tạo mới
        print("\n" + "=" * 70)
        print("🔄 CẦN TẠO TOKEN MỚI")
        print("=" * 70)
        print("Token cũ không thể refresh (lỗi invalid_grant)")
        print("Cần xác thực lại để tạo token mới")
        print()
        
        user_input = input("Bạn có muốn tạo token mới ngay bây giờ? (y/n): ")
        if user_input.lower() in ['y', 'yes', 'có', 'c']:
            # Xóa token cũ
            clean_old_token()
            
            # Tạo token mới
            if create_new_token():
                # Test token mới
                if test_token():
                    print("\n" + "=" * 70)
                    print("🎉 THÀNH CÔNG!")
                    print("=" * 70)
                    print("Token mới đã được tạo và hoạt động bình thường!")
                    print("Bạn có thể tiếp tục sử dụng ứng dụng.")
                else:
                    print("\n⚠️ Token mới đã tạo nhưng test API lỗi")
                    print("Vui lòng kiểm tra lại kết nối mạng và quyền truy cập")
            else:
                print("\n❌ Không thể tạo token mới")
                print("Vui lòng kiểm tra lại file credentials.json và thử lại")
        else:
            print("\n📋 HƯỚNG DẪN TẠO TOKEN MỚI:")
            print("1. Chạy lại script này: python refresh_token.py")
            print("2. Hoặc chạy ứng dụng chính: python app.py")
            print("3. Ứng dụng sẽ tự động yêu cầu xác thực lại")
    
    print("\n" + "=" * 70)
    print("✅ HOÀN THÀNH")
    print("=" * 70)
    input("\nNhấn Enter để thoát...")

if __name__ == '__main__':
    main()

