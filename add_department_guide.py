#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để thêm phòng ban mới vào hệ thống
"""

import sys
import os

# Thiết lập encoding UTF-8 cho Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def add_new_department():
    """
    Hướng dẫn thêm phòng ban mới vào hệ thống
    """
    print("=" * 60)
    print("HƯỚNG DẪN THÊM PHÒNG BAN MỚI")
    print("=" * 60)
    
    print("""
📋 CÁC BƯỚC THÊM PHÒNG BAN MỚI:

1️⃣ CHẠY SCRIPT TỰ ĐỘNG
   - Chạy: python add_department_automation.py
   - Chỉ cần nhập tên phòng ban (ví dụ: MARKETING)
   - Script sẽ tự động tạo mapping và cập nhật app.py

2️⃣ TẠO FILE TIMESHEET TRÊN GOOGLE DRIVE
   - Tạo file Google Sheets mới trong folder 2025/10/
   - Đặt tên theo format: [TênPhòngBan]_TimeSheet-YYYYMM
   - Ví dụ: MARKETING_TimeSheet-202510

3️⃣ CẤU TRÚC FILE TIMESHEET
   - Sheet đầu tiên: Tên phòng ban (ví dụ: MARKETING)
   - Các sheet con: Employee ID (ví dụ: 1500, 1501, 1502...)
   - Cột A: Ngày (format: YYYY/MM/DD)
   - Cột G: Giờ vào
   - Cột K: Giờ ra
   - Cột E: Tổng nghỉ + đối ứng
   - Cột M: Giờ công
   - Cột N: Tăng ca <22h
   - Cột O: Tăng ca >22h

4️⃣ TEST HỆ THỐNG
   - Test tìm file timesheet
   - Test cập nhật dữ liệu
   - Test approve attendance
""")

def show_current_mapping():
    """Hiển thị mapping hiện tại"""
    print("\n" + "=" * 60)
    print("MAPPING PHÒNG BAN HIỆN TẠI")
    print("=" * 60)
    
    current_mapping = {
        'BUD A': 'Bud_TimeSheet',
        'BUD B': 'Bud_TimeSheet',
        'BUD C': 'Bud_TimeSheet',
        'CREEK&RIVER': 'Creek&River_timesheet', 
        'KIRI': 'KIRI TIME SHEET',
        'OFFICE': 'BACKOFFICE_TIMESHEET',
        'YORK': 'Chirashi_TimeSheet',
        'COMO': 'Chirashi_TimeSheet',
        'IT': 'IT_TimeSheet',
        'SCOPE': 'SCOPE_TimeSheet'
    }
    
    for dept, file_name in current_mapping.items():
        print(f"   {dept:15} → {file_name}")

def show_example_new_department():
    """Ví dụ thêm phòng ban mới"""
    print("\n" + "=" * 60)
    print("VÍ DỤ THÊM PHÒNG BAN MARKETING")
    print("=" * 60)
    
    print("""
🚀 CÁCH THÊM PHÒNG BAN MỚI (ĐƠN GIẢN):

1️⃣ CHẠY SCRIPT:
   python add_department_automation.py
   
2️⃣ NHẬP TÊN PHÒNG BAN:
   Nhập tên phòng ban (ví dụ: MARKETING): MARKETING
   
3️⃣ XÁC NHẬN:
   Bạn có chắc chắn muốn thêm phòng ban này? (y/n): y

✅ SCRIPT SẼ TỰ ĐỘNG:
   - Tạo mapping: 'MARKETING' → 'MARKETING_TimeSheet'
   - Cập nhật app.py
   - Hiển thị thông tin cần thiết

📁 FILE TIMESHEET CẦN TẠO:
   - Tên file: MARKETING_TimeSheet-202510
   - Vị trí: Google Drive folder 2025/10/
   - Sheets: MARKETING, 1500, 1501, 1502, ...

🎯 KẾT QUẢ:
   - Mapping đã được thêm vào app.py
   - Hệ thống sẽ tự động tìm file timesheet
   - Không cần cập nhật database thủ công
""")

if __name__ == "__main__":
    add_new_department()
    show_current_mapping()
    show_example_new_department()
