#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script 1-click khôi phục token Google API
Chỉ cần double-click để chạy!
"""

import os
import sys
import pickle
import shutil
from datetime import datetime

# Thiết lập encoding UTF-8 cho Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

# Import Google API libraries
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("❌ Google API libraries không có sẵn!")
    print("Hãy cài đặt: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    input("Nhấn Enter để thoát...")
    sys.exit(1)

def print_header():
    """In header đẹp"""
    print("=" * 60)
    print("🔑 TOKEN RECOVERY - KHÔI PHỤC TOKEN 1-CLICK")
    print("=" * 60)
    print(f"⏰ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def check_files():
    """Kiểm tra các file cần thiết"""
    print("🔍 KIỂM TRA FILE CẦN THIẾT...")
    
    files_to_check = {
        'credentials.json': 'File cấu hình Google API',
        'token.pickle': 'File token hiện tại',
        'last_token_refresh.txt': 'File lưu thời gian refresh'
    }
    
    missing_files = []
    for file, desc in files_to_check.items():
        if os.path.exists(file):
            print(f"   ✅ {file}: {desc}")
        else:
            print(f"   ❌ {file}: {desc} - KHÔNG TÌM THẤY")
            if file != 'token.pickle':  # token.pickle có thể không có
                missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️ THIẾU FILE: {', '.join(missing_files)}")
        if 'credentials.json' in missing_files:
            print("❌ KHÔNG THỂ TIẾP TỤC: Thiếu credentials.json")
            print("Hãy tải lại file credentials.json từ Google Cloud Console")
            return False
    
    return True

def backup_old_token():
    """Backup token cũ trước khi xóa"""
    if os.path.exists('token.pickle'):
        backup_name = f"token_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pickle"
        try:
            shutil.copy2('token.pickle', backup_name)
            print(f"💾 Đã backup token cũ: {backup_name}")
            return True
        except Exception as e:
            print(f"⚠️ Không thể backup token cũ: {e}")
    return False

def try_refresh_token():
    """Thử refresh token hiện tại"""
    print("\n🔄 THỬ REFRESH TOKEN HIỆN TẠI...")
    
    try:
        if not os.path.exists('token.pickle'):
            print("❌ Không có file token.pickle")
            return False
        
        # Load token
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        
        print(f"   📊 Token status: {'Expired' if creds.expired else 'Valid'}")
        print(f"   🔑 Has refresh_token: {'Yes' if creds.refresh_token else 'No'}")
        
        if creds.expired and creds.refresh_token:
            print("   🔄 Đang refresh token...")
            creds.refresh(Request())
            
            # Lưu token mới
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            
            print("   ✅ Token đã được refresh thành công!")
            return True
        elif not creds.refresh_token:
            print("   ❌ Không có refresh_token, cần tạo token mới")
            return False
        else:
            print("   ✅ Token vẫn còn hiệu lực")
            return True
            
    except Exception as e:
        print(f"   ❌ Lỗi khi refresh token: {e}")
        return False

def test_connection():
    """Test kết nối API"""
    print("\n🔍 TEST KẾT NỐI API...")
    
    try:
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        
        # Test Drive API
        drive_service = build('drive', 'v3', credentials=creds)
        results = drive_service.files().list(pageSize=1).execute()
        files = results.get('files', [])
        
        print(f"   ✅ Drive API: OK (tìm thấy {len(files)} file)")
        
        # Test Sheets API
        sheets_service = build('sheets', 'v4', credentials=creds)
        print("   ✅ Sheets API: OK")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Lỗi kết nối API: {e}")
        return False

def clean_old_token():
    """Xóa token cũ để tạo mới"""
    print("\n🧹 XÓA TOKEN CŨ...")
    
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

def show_next_steps():
    """Hiển thị các bước tiếp theo"""
    print("\n" + "=" * 60)
    print("📋 CÁC BƯỚC TIẾP THEO")
    print("=" * 60)
    print("1️⃣ Chạy ứng dụng chính để tạo token mới:")
    print("   python app.py")
    print()
    print("2️⃣ Hoặc chạy script test token:")
    print("   python keep_token_alive.py")
    print()
    print("3️⃣ Nếu vẫn lỗi, kiểm tra:")
    print("   - File credentials.json có đúng không")
    print("   - Quyền truy cập Google Account")
    print("   - Kết nối internet")
    print()
    print("4️⃣ Setup tự động để tránh lỗi tương lai:")
    print("   python setup_auto_token.py")

def main():
    """Chương trình chính"""
    print_header()
    
    # Bước 1: Kiểm tra file cần thiết
    if not check_files():
        input("\nNhấn Enter để thoát...")
        return
    
    # Bước 2: Backup token cũ
    backup_old_token()
    
    # Bước 3: Thử refresh token
    if try_refresh_token():
        # Bước 4: Test kết nối
        if test_connection():
            print("\n🎉 THÀNH CÔNG!")
            print("Token đã được khôi phục và hoạt động bình thường!")
            print("Bạn có thể tiếp tục sử dụng ứng dụng.")
        else:
            print("\n⚠️ Token đã refresh nhưng kết nối API lỗi")
            print("Có thể do vấn đề mạng hoặc quyền truy cập")
    else:
        # Bước 5: Xóa token cũ
        clean_old_token()
        print("\n🔄 CẦN TẠO TOKEN MỚI")
        print("Token cũ không thể refresh, cần tạo token mới")
    
    # Bước 6: Hiển thị hướng dẫn
    show_next_steps()
    
    print("\n" + "=" * 60)
    print("✅ HOÀN THÀNH TOKEN RECOVERY")
    print("=" * 60)
    input("\nNhấn Enter để thoát...")

if __name__ == '__main__':
    main()
