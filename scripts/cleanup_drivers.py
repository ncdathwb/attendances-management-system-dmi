#!/usr/bin/env python3
"""
Script cleanup để xóa Chrome driver cũ và cài mới
"""

import os
import shutil
import platform
from pathlib import Path

def cleanup_chrome_drivers():
    """Xóa Chrome driver cũ và cài mới"""
    try:
        print("🧹 Starting Chrome driver cleanup...")
        
        # Tìm thư mục .wdm (webdriver-manager cache)
        home = Path.home()
        
        if platform.system() == "Windows":
            wdm_path = home / ".wdm"
        else:
            wdm_path = home / ".wdm"
        
        if wdm_path.exists():
            print(f"🗑️ Found .wdm folder at: {wdm_path}")
            
            # Xóa thư mục .wdm
            shutil.rmtree(wdm_path)
            print("✅ Deleted .wdm folder")
        else:
            print("ℹ️ No .wdm folder found")
        
        # Tìm và xóa Chrome driver cũ trong thư mục hiện tại
        current_dir = Path.cwd()
        chrome_drivers = list(current_dir.glob("chromedriver*"))
        
        for driver in chrome_drivers:
            try:
                driver.unlink()
                print(f"🗑️ Deleted old driver: {driver}")
            except Exception as e:
                print(f"⚠️ Could not delete {driver}: {e}")
        
        print("🧹 Cleanup completed!")
        print("💡 Now run: pip install --upgrade webdriver-manager")
        print("💡 Then run: python test_selenium.py")
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")

def force_reinstall_webdriver_manager():
    """Force reinstall webdriver-manager"""
    try:
        print("📦 Force reinstalling webdriver-manager...")
        
        # Uninstall
        os.system("pip uninstall webdriver-manager -y")
        print("✅ Uninstalled webdriver-manager")
        
        # Install latest
        os.system("pip install webdriver-manager --upgrade --force-reinstall")
        print("✅ Installed latest webdriver-manager")
        
    except Exception as e:
        print(f"❌ Reinstall error: {e}")

if __name__ == "__main__":
    print("🚀 Chrome Driver Cleanup Tool")
    print("=" * 40)
    
    choice = input("Choose action:\n1. Cleanup old drivers\n2. Force reinstall webdriver-manager\n3. Both\nEnter choice (1-3): ")
    
    if choice == "1":
        cleanup_chrome_drivers()
    elif choice == "2":
        force_reinstall_webdriver_manager()
    elif choice == "3":
        cleanup_chrome_drivers()
        force_reinstall_webdriver_manager()
    else:
        print("❌ Invalid choice")
