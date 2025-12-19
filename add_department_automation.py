#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tự động thêm phòng ban mới vào hệ thống
"""

import sys
import os
import re

# Thiết lập encoding UTF-8 cho Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def add_department_to_app_py(department_name, file_name):
    """
    Tự động thêm phòng ban mới vào file app.py
    """
    print(f"🔧 Đang thêm phòng ban {department_name} vào app.py...")
    
    try:
        # Đọc file app.py
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Thêm vào get_department_file_mapping
        mapping_pattern = r"(mapping = \{[^}]+)(\})"
        mapping_match = re.search(mapping_pattern, content, re.DOTALL)
        
        if mapping_match:
            # Thêm dòng mới vào mapping
            new_mapping_line = f"    '{department_name}': '{file_name}',\n"
            new_mapping = mapping_match.group(1) + new_mapping_line + mapping_match.group(2)
            content = content.replace(mapping_match.group(0), new_mapping)
            print(f"✅ Đã thêm {department_name} vào get_department_file_mapping")
        
        # Thêm vào get_all_department_mappings
        return_pattern = r"(return \{[^}]+)(\})"
        return_match = re.search(return_pattern, content, re.DOTALL)
        
        if return_match:
            # Thêm dòng mới vào return
            new_return_line = f"    '{department_name}': '{file_name}',\n"
            new_return = return_match.group(1) + new_return_line + return_match.group(2)
            content = content.replace(return_match.group(0), new_return)
            print(f"✅ Đã thêm {department_name} vào get_all_department_mappings")
        
        # Ghi lại file
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Hoàn thành cập nhật app.py cho phòng ban {department_name}")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi cập nhật app.py: {e}")
        return False

def generate_file_name(department_name):
    """
    Tự động tạo tên file timesheet theo format chuẩn
    """
    # Format chuẩn: DEPARTMENT_TimeSheet
    return f"{department_name}_TimeSheet"

def show_mapping_info(department_name, file_name):
    """
    Hiển thị thông tin mapping đã tạo
    """
    print(f"\n📋 THÔNG TIN MAPPING ĐÃ TẠO:")
    print(f"   - Phòng ban: {department_name}")
    print(f"   - File timesheet: {file_name}")
    print(f"   - Mapping: '{department_name}' → '{file_name}'")
    
    print(f"\n📁 FILE TIMESHEET CẦN TẠO:")
    print(f"   - Tên file: {file_name}-202510")
    print(f"   - Vị trí: Google Drive folder 2025/10/")
    print(f"   - Sheet đầu tiên: {department_name}")
    print(f"   - Các sheet con: Employee ID của nhân viên")

def main():
    """
    Hàm chính để thêm phòng ban mới
    """
    print("=" * 60)
    print("SCRIPT TỰ ĐỘNG THÊM PHÒNG BAN MỚI")
    print("=" * 60)
    
    # Nhập tên phòng ban
    department_name = input("Nhập tên phòng ban (ví dụ: MARKETING): ").strip().upper()
    if not department_name:
        print("❌ Tên phòng ban không được để trống")
        return
    
    # Tự động tạo tên file timesheet
    file_name = generate_file_name(department_name)
    
    print(f"\n📋 THÔNG TIN PHÒNG BAN MỚI:")
    print(f"   - Tên phòng ban: {department_name}")
    print(f"   - Tên file timesheet: {file_name}")
    
    confirm = input("\nBạn có chắc chắn muốn thêm phòng ban này? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Hủy bỏ thao tác")
        return
    
    # Thực hiện cập nhật app.py
    print(f"\n🚀 BẮT ĐẦU THÊM PHÒNG BAN {department_name}...")
    
    if add_department_to_app_py(department_name, file_name):
        print(f"✅ Cập nhật app.py thành công")
        
        # Hiển thị thông tin mapping
        show_mapping_info(department_name, file_name)
        
        print(f"\n🎉 HOÀN THÀNH THÊM PHÒNG BAN {department_name}!")
        print(f"\n📋 CÁC BƯỚC TIẾP THEO:")
        print(f"1. Tạo file Google Sheets: {file_name}-202510")
        print(f"2. Đặt file vào folder Google Drive: 2025/10/")
        print(f"3. Test hệ thống với phòng ban mới")
    else:
        print(f"❌ Lỗi khi cập nhật app.py")
        return

if __name__ == "__main__":
    main()
