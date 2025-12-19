"""
Script kiểm tra mapping phòng ban với Google Sheet thực tế
So sánh mapping trong database với file Google Sheet thực tế trên Google Drive
"""
import sys
import os

# Thêm thư mục hiện tại vào path để import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app
    from app import GoogleDriveAPI
    from database.models import db, Department
    
    with app.app_context():
        # Lấy folder ID từ config
        GOOGLE_DRIVE_FOLDER_ID = '1dHF_x6fCJEs9krtmaZPabBIWiTr5xpB3'  # Từ app.py line 304
        
        print("=" * 80)
        print("KIỂM TRA MAPPING PHÒNG BAN VỚI GOOGLE SHEET")
        print("=" * 80)
        print()
        
        # 1. Lấy danh sách phòng ban từ database
        print("📋 Bước 1: Lấy danh sách phòng ban từ database...")
        departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
        
        if not departments:
            print("⚠️  Không có phòng ban nào trong database")
            sys.exit(1)
        
        print(f"✅ Tìm thấy {len(departments)} phòng ban")
        print()
        
        # 2. Lấy mapping từ database
        db_mapping = {}
        for dept in departments:
            db_mapping[dept.name] = dept.timesheet_file or "Chưa cấu hình"
        
        # 3. Lấy danh sách file Google Sheet thực tế
        print("📁 Bước 2: Lấy danh sách file Google Sheet từ Google Drive...")
        try:
            google_api = GoogleDriveAPI()
            if not google_api.ensure_valid_token():
                print("❌ Không thể xác thực với Google Drive API")
                print("⚠️  Chạy ở chế độ demo - chỉ hiển thị mapping từ database")
                timesheets = []
            else:
                timesheets = google_api.list_all_timesheets(GOOGLE_DRIVE_FOLDER_ID)
            
            if not timesheets:
                print("⚠️  Không tìm thấy file Google Sheet nào trong folder")
            else:
                print(f"✅ Tìm thấy {len(timesheets)} file Google Sheet")
        except Exception as e:
            print(f"❌ Lỗi khi lấy danh sách file: {e}")
            timesheets = []
        
        print()
        
        # 4. Tạo danh sách tên file từ Google Drive (loại bỏ phần -YYYYMM)
        drive_files = {}
        for file in timesheets:
            name = file.get('name', '')
            # Loại bỏ phần -YYYYMM ở cuối (ví dụ: Bud_TimeSheet-202510)
            base_name = name
            if '-' in name:
                parts = name.rsplit('-', 1)
                if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 6:
                    base_name = parts[0]
            
            if base_name not in drive_files:
                drive_files[base_name] = []
            drive_files[base_name].append(name)
        
        print("=" * 80)
        print("KẾT QUẢ SO SÁNH")
        print("=" * 80)
        print()
        
        # 5. So sánh và hiển thị kết quả
        print(f"{'STT':<5} {'Phòng Ban':<25} {'Mapping DB':<30} {'Trạng thái':<20}")
        print("-" * 80)
        
        found_count = 0
        not_found_count = 0
        no_mapping_count = 0
        
        for idx, dept in enumerate(departments, 1):
            mapping_name = dept.timesheet_file or "Chưa cấu hình"
            
            if mapping_name == "Chưa cấu hình":
                status = "❌ Chưa cấu hình"
                no_mapping_count += 1
            elif mapping_name in drive_files:
                status = f"✅ Tìm thấy ({len(drive_files[mapping_name])} file)"
                found_count += 1
            else:
                # Tìm kiếm tương đối (case-insensitive, partial match)
                found = False
                for drive_name in drive_files.keys():
                    if mapping_name.lower() in drive_name.lower() or drive_name.lower() in mapping_name.lower():
                        status = f"⚠️  Tương tự: {drive_name}"
                        found = True
                        break
                
                if not found:
                    status = "❌ Không tìm thấy"
                    not_found_count += 1
                else:
                    found_count += 1
            
            print(f"{idx:<5} {dept.name:<25} {mapping_name:<30} {status:<20}")
        
        print()
        print("=" * 80)
        print("TỔNG KẾT")
        print("=" * 80)
        print(f"✅ Tìm thấy file: {found_count}/{len(departments)}")
        print(f"❌ Không tìm thấy: {not_found_count}/{len(departments)}")
        print(f"⚠️  Chưa cấu hình: {no_mapping_count}/{len(departments)}")
        print()
        
        # 6. Hiển thị danh sách file Google Sheet thực tế
        if drive_files:
            print("=" * 80)
            print("DANH SÁCH FILE GOOGLE SHEET THỰC TẾ")
            print("=" * 80)
            print()
            for base_name, files in sorted(drive_files.items()):
                print(f"📄 {base_name}")
                for file_name in files[:3]:  # Chỉ hiển thị 3 file đầu
                    print(f"   └─ {file_name}")
                if len(files) > 3:
                    print(f"   └─ ... và {len(files) - 3} file khác")
                print()
        
        print("=" * 80)

except ImportError as e:
    print(f"❌ Lỗi import: {e}")
    print("Hãy chạy script này từ thư mục gốc của project")
    sys.exit(1)
except Exception as e:
    print(f"❌ Lỗi: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

