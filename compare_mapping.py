"""
So sánh mapping phòng ban trong database với mapping hardcoded
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app
    from database.models import db, Department
    
    with app.app_context():
        # Mapping hardcoded từ app.py
        HARDCODED_MAPPING = {
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
        
        print("=" * 90)
        print("SO SÁNH MAPPING PHÒNG BAN: DATABASE vs HARDCODED")
        print("=" * 90)
        print()
        
        # Lấy mapping từ database
        departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
        db_mapping = {}
        for dept in departments:
            db_mapping[dept.name] = dept.timesheet_file or "Chưa cấu hình"
        
        # So sánh
        print(f"{'STT':<5} {'Phòng Ban':<20} {'Database Mapping':<35} {'Hardcoded Mapping':<35} {'Khác nhau':<10}")
        print("-" * 90)
        
        all_depts = set(list(db_mapping.keys()) + list(HARDCODED_MAPPING.keys()))
        same_count = 0
        diff_count = 0
        only_db_count = 0
        only_hardcoded_count = 0
        
        idx = 1
        for dept_name in sorted(all_depts):
            db_value = db_mapping.get(dept_name, "Không có trong DB")
            hardcoded_value = HARDCODED_MAPPING.get(dept_name, "Không có trong code")
            
            if dept_name not in db_mapping:
                status = "⚠️  Chỉ có trong code"
                only_hardcoded_count += 1
            elif dept_name not in HARDCODED_MAPPING:
                status = "⚠️  Chỉ có trong DB"
                only_db_count += 1
            elif db_value == hardcoded_value:
                status = "✅ Giống nhau"
                same_count += 1
            else:
                status = "❌ Khác nhau"
                diff_count += 1
            
            print(f"{idx:<5} {dept_name:<20} {db_value:<35} {hardcoded_value:<35} {status:<10}")
            idx += 1
        
        print()
        print("=" * 90)
        print("TỔNG KẾT")
        print("=" * 90)
        print(f"✅ Giống nhau: {same_count}")
        print(f"❌ Khác nhau: {diff_count}")
        print(f"⚠️  Chỉ có trong Database: {only_db_count}")
        print(f"⚠️  Chỉ có trong Hardcoded: {only_hardcoded_count}")
        print()
        
        # Hiển thị các mapping khác nhau chi tiết
        if diff_count > 0:
            print("=" * 90)
            print("CHI TIẾT CÁC MAPPING KHÁC NHAU:")
            print("=" * 90)
            for dept_name in sorted(all_depts):
                if dept_name in db_mapping and dept_name in HARDCODED_MAPPING:
                    db_value = db_mapping[dept_name]
                    hardcoded_value = HARDCODED_MAPPING[dept_name]
                    if db_value != hardcoded_value:
                        print(f"📌 {dept_name}:")
                        print(f"   Database:   {db_value}")
                        print(f"   Hardcoded:  {hardcoded_value}")
                        print()
        
        # Gợi ý
        print("=" * 90)
        print("GỢI Ý:")
        print("=" * 90)
        if diff_count > 0 or only_hardcoded_count > 0:
            print("⚠️  Có sự khác biệt giữa database và hardcoded mapping!")
            print("   - Code sẽ ưu tiên sử dụng mapping từ database")
            print("   - Nếu database có mapping, sẽ dùng mapping đó")
            print("   - Nếu database không có, sẽ fallback về hardcoded")
            print()
            print("💡 Khuyến nghị:")
            print("   1. Cập nhật database để có đầy đủ mapping")
            print("   2. Hoặc cập nhật hardcoded mapping để khớp với database")
        else:
            print("✅ Tất cả mapping đều khớp nhau!")
        
        print("=" * 90)

except Exception as e:
    print(f"❌ Lỗi: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

