"""
Script đơn giản để giữ token không bao giờ hết hạn
Chạy script này mỗi tuần một lần
"""

import os
import pickle
import sys
import codecs
from datetime import datetime

# Thiết lập encoding UTF-8 cho Windows
if sys.platform.startswith('win'):
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
    print("Google API libraries not available. Please install them first.")

def keep_token_alive():
    """Giữ token sống bằng cách test kết nối"""
    print("KEEP TOKEN ALIVE - GIỮ TOKEN SỐNG")
    print("="*50)
    print(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not GOOGLE_API_AVAILABLE:
        print("❌ Lỗi: Google API libraries không có sẵn!")
        return False
    
    token_file = 'token.pickle'
    
    # Kiểm tra file token
    if not os.path.exists(token_file):
        print("❌ Không tìm thấy file token.pickle")
        print("Hãy chạy script chính trước để tạo token.")
        return False
    
    try:
        # Load token
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
        
        print("✅ Token loaded successfully")
        
        # Kiểm tra token có hết hạn không
        if creds.expired and creds.refresh_token:
            print("🔄 Token đã hết hạn, đang gia hạn...")
            creds.refresh(Request())
            
            # Lưu token mới
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
            print("✅ Token đã được gia hạn và lưu")
        else:
            print("✅ Token vẫn còn hiệu lực")
        
        # Test kết nối API
        print("🔍 Đang test kết nối API...")
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Test với một query đơn giản
        results = drive_service.files().list(pageSize=1).execute()
        files = results.get('files', [])
        
        print(f"✅ Kết nối API thành công! Tìm thấy {len(files)} file")
        print("✅ Token đã được gia hạn thành công!")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def main():
    """Chương trình chính"""
    success = keep_token_alive()
    
    if success:
        print("\n🎉 HOÀN THÀNH!")
        print("Token đã được gia hạn và sẽ không hết hạn.")
        print("Hãy chạy script này mỗi tuần một lần để đảm bảo token luôn sống.")
    else:
        print("\n❌ THẤT BẠI!")
        print("Không thể gia hạn token. Vui lòng kiểm tra lại.")

if __name__ == '__main__':
    main()
