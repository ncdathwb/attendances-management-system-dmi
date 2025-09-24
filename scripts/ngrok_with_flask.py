#!/usr/bin/env python3
"""
🚀 NGROK + FLASK AUTO LAUNCHER
Tự động khởi động Flask app và tạo ngrok tunnel
"""

import subprocess
import time
import sys
import os
import webbrowser
import threading
from pathlib import Path

def find_ngrok():
    """Tìm ngrok.exe trong các thư mục có thể"""
    possible_paths = [
        "ngrok.exe",                    # Thư mục hiện tại
        "scripts/ngrok.exe",            # Thư mục scripts
        "ngrok/ngrok.exe",              # Thư mục ngrok
        "C:/ngrok/ngrok.exe",           # C:/
        "C:/Users/Thinkpad/Downloads/ngrok.exe",  # Downloads
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def start_flask_app():
    """Khởi động Flask app"""
    try:
        print("🚀 Đang khởi động Flask app...")
        
        # Kiểm tra app.py có tồn tại không
        if not os.path.exists("app.py"):
            print("❌ Không tìm thấy app.py!")
            return None
        
        # Khởi động Flask app trong background
        process = subprocess.Popen(
            [sys.executable, "app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Đợi Flask khởi động
        print("⏳ Đang đợi Flask khởi động...")
        time.sleep(5)
        
        return process
        
    except Exception as e:
        print(f"❌ Lỗi khi khởi động Flask: {e}")
        return None

def create_ngrok_tunnel(ngrok_path, port=5000):
    """Tạo ngrok tunnel"""
    try:
        print(f"🌐 Đang tạo ngrok tunnel cho port {port}...")
        
        # Tạo tunnel với ngrok
        cmd = [ngrok_path, "http", str(port)]
        print(f"📡 Lệnh: {' '.join(cmd)}")
        
        # Chạy ngrok trong background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Đợi ngrok khởi động
        print("⏳ Đang đợi ngrok khởi động...")
        time.sleep(3)
        
        return process
        
    except Exception as e:
        print(f"❌ Lỗi khi tạo tunnel: {e}")
        return None

def get_tunnel_url():
    """Lấy URL từ ngrok API"""
    try:
        import requests
        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
        if response.status_code == 200:
            tunnels = response.json()['tunnels']
            if tunnels:
                return tunnels[0]['public_url']
    except:
        pass
    return None

def check_flask_running(port=5000):
    """Kiểm tra Flask app có đang chạy không"""
    try:
        import requests
        response = requests.get(f'http://localhost:{port}', timeout=3)
        return response.status_code == 200
    except:
        return False

def main():
    """Hàm chính"""
    print("=" * 70)
    print("🚀 NGROK + FLASK AUTO LAUNCHER")
    print("=" * 70)
    
    # Lấy port từ command line
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"⚠️ Port không hợp lệ: {sys.argv[1]}, sử dụng port mặc định: 5000")
    
    print(f"📋 Cấu hình:")
    print(f"   - Port: {port}")
    print(f"   - Local URL: http://localhost:{port}")
    print()
    
    # Kiểm tra Flask app có đang chạy không
    print("🔍 Kiểm tra Flask app...")
    if check_flask_running(port):
        print("✅ Flask app đã đang chạy!")
        flask_process = None
    else:
        print("⚠️ Flask app chưa chạy, đang khởi động...")
        flask_process = start_flask_app()
        if not flask_process:
            print("❌ Không thể khởi động Flask app!")
            input("Nhấn Enter để thoát...")
            return
        
        # Đợi thêm để Flask khởi động hoàn toàn
        print("⏳ Đợi Flask khởi động hoàn toàn...")
        time.sleep(3)
        
        # Kiểm tra lại
        if not check_flask_running(port):
            print("❌ Flask app vẫn chưa sẵn sàng!")
            if flask_process:
                flask_process.terminate()
            input("Nhấn Enter để thoát...")
            return
        
        print("✅ Flask app đã sẵn sàng!")
    
    # Tìm ngrok
    print("\n🔍 Đang tìm ngrok.exe...")
    ngrok_path = find_ngrok()
    
    if not ngrok_path:
        print("❌ Không tìm thấy ngrok.exe!")
        print()
        print("📥 HƯỚNG DẪN TẢI NGROK:")
        print("   1. Truy cập: https://ngrok.com/download")
        print("   2. Tải phiên bản Windows")
        print("   3. Giải nén và copy ngrok.exe vào thư mục scripts/")
        print("   4. Chạy lại script này")
        print()
        if flask_process:
            flask_process.terminate()
        input("Nhấn Enter để thoát...")
        return
    
    print(f"✅ Tìm thấy ngrok: {ngrok_path}")
    
    # Tạo ngrok tunnel
    ngrok_process = create_ngrok_tunnel(ngrok_path, port)
    if not ngrok_process:
        if flask_process:
            flask_process.terminate()
        input("Nhấn Enter để thoát...")
        return
    
    # Kiểm tra tunnel
    print("\n🔍 Đang kiểm tra tunnel...")
    time.sleep(2)
    
    tunnel_url = get_tunnel_url()
    
    print()
    print("🎉 HOÀN THÀNH!")
    print("✅ Flask app đang chạy")
    print("✅ Ngrok tunnel đã được tạo")
    print(f"🔗 Local URL: http://localhost:{port}")
    print(f"🌐 Ngrok Dashboard: http://localhost:4040")
    
    if tunnel_url:
        print(f"🌍 Public URL: {tunnel_url}")
    else:
        print("💡 Để lấy public URL, hãy mở dashboard")
    
    print()
    
    # Lưu thông tin vào file
    try:
        info = f"""Ngrok + Flask Info
==================
Port: {port}
Local URL: http://localhost:{port}
Ngrok Dashboard: http://localhost:4040
Public URL: {tunnel_url or 'Kiểm tra dashboard'}
Thời gian tạo: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        with open('ngrok_flask_info.txt', 'w', encoding='utf-8') as f:
            f.write(info)
        print("💾 Đã lưu thông tin vào file: ngrok_flask_info.txt")
    except Exception as e:
        print(f"⚠️ Không thể lưu file: {e}")
    
    print()
    print("💡 Để dừng:")
    print("   - Dừng ngrok: đóng cửa sổ ngrok hoặc Ctrl+C")
    print("   - Dừng Flask: Ctrl+C trong terminal Flask")
    print()
    
    # Mở URL ngrok trực tiếp
    if tunnel_url:
        try:
            webbrowser.open(tunnel_url)
            print(f"🌐 Đã mở URL ngrok trực tiếp: {tunnel_url}")
        except:
            print(f"💡 Mở thủ công: {tunnel_url}")
    else:
        try:
            webbrowser.open('http://localhost:4040')
            print("🌐 Đã mở ngrok dashboard để lấy URL")
        except:
            print("💡 Mở thủ công: http://localhost:4040")
    
    print()
    print("🔄 Đang duy trì cả Flask và ngrok... (Ctrl+C để dừng)")
    
    try:
        # Giữ script chạy để duy trì cả hai
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Đang dừng...")
        
        if ngrok_process:
            ngrok_process.terminate()
            print("✅ Đã dừng ngrok")
        
        if flask_process:
            flask_process.terminate()
            print("✅ Đã dừng Flask")
        
        print("✅ Hoàn thành!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Đã dừng script!")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        input("Nhấn Enter để thoát...")
