#!/usr/bin/env python3
"""
Script để copy Chrome browser vào folder dự án
"""

import os
import shutil
import platform
import subprocess
from pathlib import Path

def find_chrome_system():
    """Tìm Chrome trong hệ thống"""
    if platform.system() == "Windows":
        chrome_paths = [
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
            os.path.expanduser("~/AppData/Local/Google/Chrome/Application/chrome.exe")
        ]
    else:
        chrome_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium"
        ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            return path
    return None

def copy_chrome_to_project():
    """Copy Chrome vào folder dự án"""
    try:
        print("🔍 Finding Chrome in system...")
        chrome_system = find_chrome_system()
        
        if not chrome_system:
            print("❌ Chrome not found in system")
            return False
        
        print(f"✅ Found Chrome at: {chrome_system}")
        
        # Tạo thư mục browsers trong dự án
        project_dir = Path(__file__).parent
        browsers_dir = project_dir / "browsers"
        browsers_dir.mkdir(exist_ok=True)
        
        # Copy Chrome vào folder dự án
        if platform.system() == "Windows":
            chrome_dest = browsers_dir / "chrome.exe"
        else:
            chrome_dest = browsers_dir / "chrome"
        
        print(f"📁 Copying Chrome to: {chrome_dest}")
        shutil.copy2(chrome_system, chrome_dest)
        
        # Kiểm tra file đã copy
        if chrome_dest.exists():
            file_size = chrome_dest.stat().st_size
            print(f"✅ Chrome copied successfully! Size: {file_size} bytes")
            print(f"📍 Location: {chrome_dest}")
            return True
        else:
            print("❌ Failed to copy Chrome")
            return False
            
    except Exception as e:
        print(f"❌ Error copying Chrome: {e}")
        return False

def create_chrome_folder():
    """Tạo cấu trúc thư mục cho Chrome"""
    try:
        project_dir = Path(__file__).parent
        
        # Tạo thư mục browsers
        browsers_dir = project_dir / "browsers"
        browsers_dir.mkdir(exist_ok=True)
        
        # Tạo thư mục chrome
        chrome_dir = project_dir / "chrome"
        chrome_dir.mkdir(exist_ok=True)
        
        print(f"📁 Created folders:")
        print(f"   - {browsers_dir}")
        print(f"   - {chrome_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating folders: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Chrome Setup Tool for Project")
    print("=" * 40)
    
    print("1. Creating Chrome folders...")
    if create_chrome_folder():
        print("✅ Folders created successfully")
    else:
        print("❌ Failed to create folders")
        return
    
    print("\n2. Copying Chrome to project...")
    if copy_chrome_to_project():
        print("✅ Chrome setup completed!")
        print("\n💡 Now you can run:")
        print("   python test_selenium.py")
    else:
        print("❌ Chrome setup failed!")
        print("\n💡 You can still use system Chrome")

if __name__ == "__main__":
    main()
