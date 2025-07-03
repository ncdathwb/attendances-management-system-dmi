from app import app, db, User, Attendance, Request
import sqlite3
import re
from datetime import datetime, timedelta
import os
import random
import time

def create_sample_users():
    """Tạo dữ liệu mẫu cho bảng users"""
    with app.app_context():
        departments = [
            'BUD', 'SCOPE', 'KIRI', 'CREEK&RIVER', 'COMO', 'OFFICE', 'YORK'
        ]
        # Danh sách họ, tên đệm, tên phổ biến của người Việt
        ho_list = [
            'Nguyễn', 'Trần', 'Lê', 'Phạm', 'Hoàng', 'Phan', 'Vũ', 'Đặng', 'Bùi', 'Đỗ', 'Hồ', 'Ngô', 'Dương', 'Lý'
        ]
        tendem_list = [
            'Văn', 'Thị', 'Hữu', 'Đức', 'Minh', 'Thanh', 'Xuân', 'Quang', 'Ngọc', 'Trọng', 'Phước', 'Gia', 'Tuấn', 'Thành', 'Công', 'Thái', 'Anh', 'Kim', 'Quốc', 'Thảo', 'Hải', 'Khánh', 'Chí', 'Tiến', 'Thúy', 'Thu', 'Lan', 'Mai', 'Hà', 'Hương', 'Tú'
        ]
        ten_list = [
            'An', 'Bình', 'Châu', 'Dũng', 'Duy', 'Giang', 'Hà', 'Hải', 'Hạnh', 'Hiếu', 'Hoa', 'Hòa', 'Hùng', 'Khánh', 'Lan', 'Linh', 'Loan', 'Long', 'Mai', 'Minh', 'Nam', 'Nga', 'Ngân', 'Ngọc', 'Nhung', 'Phát', 'Phú', 'Phúc', 'Quang', 'Quân', 'Quyên', 'Sơn', 'Tâm', 'Tân', 'Thảo', 'Thành', 'Thắng', 'Thảo', 'Thịnh', 'Thu', 'Thủy', 'Trang', 'Trí', 'Trinh', 'Trung', 'Tú', 'Tuấn', 'Tuyết', 'Vân', 'Việt', 'Yến'
        ]
        users = []
        employee_id_counter = 2000
        used_names = set()
        def random_vietnamese_name():
            while True:
                ho = random.choice(ho_list)
                tendem = random.choice(tendem_list)
                ten = random.choice(ten_list)
                name = f"{ho} {tendem} {ten}"
                if name not in used_names:
                    used_names.add(name)
                    return name
        for dept in departments:
            dept_users = []
            for i in range(10):
                name = random_vietnamese_name()
                emp_id = employee_id_counter
                employee_id_counter += 1
                dept_users.append({
                    'name': name,
                    'employee_id': emp_id,
                    'password': '123456',
                    'roles': 'EMPLOYEE',
                    'department': dept
                })
            # Random 1 người làm TEAM_LEADER
            team_leader_idx = random.randint(0, 9)
            dept_users[team_leader_idx]['roles'] += ',TEAM_LEADER'
            users.extend(dept_users)
        # Thêm Nguyễn Công Đạt làm Admin/Manager/Team Leader  trong đội OFFICE duy nhất
        users.append({
            'name': 'Nguyễn Công Đạt',
            'employee_id': 1395,
            'password': '123456',
            'roles': 'EMPLOYEE,TEAM_LEADER,MANAGER,ADMIN',
            'department': 'OFFICE'
        })
        # Tạo từng người dùng
        for user_data in users:
            user = User(
                name=user_data['name'],
                employee_id=user_data['employee_id'],
                roles=user_data['roles'],
                department=user_data['department']
            )
            user.set_password(user_data['password'])
            db.session.add(user)
        db.session.commit()
        print("Đã tạo dữ liệu mẫu cho bảng users!")

        # Ghi danh sách user ra file
        with open('danhsach.txt', 'w', encoding='utf-8') as f:
            f.write('Tên | Mã NV | Mật khẩu | Phòng ban | Vai trò\n')
            for user in users:
                f.write(f"{user['name']} | {user['employee_id']} | {user['password']} | {user['department']} | {user['roles']}\n")
        print("Đã ghi file danhsach.txt!")

def create_new_user():
    """Tạo người dùng mới"""
    print("\n=== TẠO NGƯỜI DÙNG MỚI ===")
    
    # Nhập thông tin người dùng
    name = input("Nhập tên: ")
    while not name:
        print("Tên không được để trống!")
        name = input("Nhập tên: ")

    while True:
        employee_id = input("Nhập mã nhân viên (chỉ nhập số): ")
        if not employee_id:
            print("Mã nhân viên không được để trống!")
            continue
        if not employee_id.isdigit():
            print("Mã nhân viên phải là số!")
            continue
        break

    password = input("Nhập mật khẩu: ")
    while not password:
        print("Mật khẩu không được để trống!")
        password = input("Nhập mật khẩu: ")
    
    print("\nChọn vai trò (có thể chọn nhiều vai trò, phân cách bằng dấu phẩy):")
    print("1. Nhân viên")
    print("2. Team Lead")
    print("3. Quản lý")
    print("4. Admin")
    
    while True:
        roles = input("Nhập số vai trò (ví dụ: 1,2,3): ")
        if not roles:
            print("Vai trò không được để trống!")
            continue
        break

    print("\nChọn phòng ban:")
    print("1. BUD")
    print("2. SCOPE")
    print("3. KIRI")
    print("4. CREEK&RIVER")
    print("5. COMO")
    print("6. OFFICE")
    print("7. YORK")
    
    while True:
        department = input("Nhập số phòng ban: ")
        if not department:
            print("Phòng ban không được để trống!")
            continue
        if department not in ['1', '2', '3', '4', '5', '6', '7']:
            print("Phòng ban không hợp lệ!")
            continue
        break

    with app.app_context():
        try:
            # Chuyển đổi vai trò từ số sang text
            role_map = {
                '1': 'EMPLOYEE',
                '2': 'TEAM_LEADER',
                '3': 'MANAGER',
                '4': 'ADMIN'
            }
            role_list = [r.strip() for r in roles.split(',')]
            roles_text = []
            for role in role_list:
                if role not in role_map:
                    raise ValueError(f"Vai trò '{role}' không hợp lệ")
                roles_text.append(role_map[role])
            roles_str = ','.join(roles_text)

            # Chuyển đổi phòng ban từ số sang text
            department_map = {
                '1': 'BUD',
                '2': 'SCOPE',
                '3': 'KIRI',
                '4': 'CREEK&RIVER',
                '5': 'COMO',
                '6': 'OFFICE',
                '7': 'YORK'
            }
            department_str = department_map[department]

            # Kiểm tra mã nhân viên đã tồn tại chưa
            existing_user = User.query.filter_by(employee_id=int(employee_id)).first()
            if existing_user:
                raise ValueError("Mã nhân viên đã tồn tại")

            # Tạo user mới
            user = User(
                name=name,
                employee_id=int(employee_id),
                roles=roles_str,
                department=department_str
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            print("\nĐã tạo người dùng mới thành công!")
            print(f"Mã nhân viên: {user.employee_id}")
            print(f"Họ tên: {user.name}")
            print(f"Vai trò: {user.roles}")
            print(f"Phòng ban: {user.department}")

        except ValueError as e:
            print(f"\nLỗi: {e}")
            db.session.rollback()
        except Exception as e:
            print(f"\nLỗi không xác định: {e}")
            db.session.rollback()

def find_password_by_employee_id():
    """Tìm mật khẩu theo mã nhân viên"""
    print("\n=== TÌM THÔNG TIN ĐĂNG NHẬP ===")
    employee_id = input("Nhập mã nhân viên cần tìm: ")
    if not employee_id:
        print("Mã nhân viên không được để trống!")
        return

    try:
        employee_id = int(employee_id)
        with app.app_context():
            user = User.query.filter_by(employee_id=employee_id).first()
            if user:
                print("\n" + "="*50)
                print("THÔNG TIN ĐĂNG NHẬP".center(50))
                print("="*50)
                print(f"Mã nhân viên: {user.employee_id}")
                print(f"Họ tên: {user.name}")
                print(f"Vai trò: {user.roles}")
                print(f"Phòng ban: {user.department}")
                print(f"Mật khẩu: {user.original_password}")
                print("="*50)
            else:
                print(f"\nKhông tìm thấy nhân viên có mã {employee_id}!")
    except ValueError:
        print("Mã nhân viên không hợp lệ!")
    except Exception as e:
        print(f"Lỗi không xác định: {e}")

def delete_employees(employee_ids):
    """Xóa một hoặc nhiều nhân viên dựa trên mã nhân viên"""
    print("\n=== XÓA NHÂN VIÊN ===")
    
    # Chuyển đổi input thành list nếu là một mã nhân viên
    if isinstance(employee_ids, str):
        employee_ids = [id.strip() for id in employee_ids.split(",")]
    
    deleted_count = 0
    
    with app.app_context():
        try:
            # Hiển thị tất cả nhân viên trong database
            all_users = User.query.all()
            print("\nDanh sách nhân viên trong database:")
            for user in all_users:
                print(f"Mã NV: {user.employee_id}, Tên: {user.name}")
            
            print("\nBắt đầu xóa nhân viên...")
            for emp_id in employee_ids:
                try:
                    # Chuyển đổi mã nhân viên thành số
                    emp_id = int(emp_id)
                    print(f"\nĐang tìm nhân viên có mã: {emp_id}")
                    
                    # Tìm user theo mã nhân viên
                    user = User.query.filter_by(employee_id=emp_id).first()
                    
                    if user:
                        print(f"Tìm thấy nhân viên: {user.name}")
                        # Xóa tất cả dữ liệu chấm công của nhân viên này
                        Attendance.query.filter_by(user_id=user.id).delete()
                        # Xóa tất cả yêu cầu của nhân viên này
                        Request.query.filter_by(user_id=user.id).delete()
                        # Xóa nhân viên
                        db.session.delete(user)
                        db.session.commit()
                        print(f"Đã xóa nhân viên {user.name} và tất cả dữ liệu liên quan!")
                        deleted_count += 1
                    else:
                        print(f"Không tìm thấy nhân viên có mã {emp_id}")
                except ValueError:
                    print(f"Mã nhân viên {emp_id} không hợp lệ!")
                except Exception as e:
                    print(f"Lỗi khi xóa nhân viên {emp_id}: {e}")
                    db.session.rollback()
            
            print(f"\nTổng số nhân viên đã xóa: {deleted_count}")
            
        except Exception as e:
            print(f"Lỗi không xác định: {e}")
            db.session.rollback()

def create_fake_attendance_data():
    """Tạo dữ liệu giả về lịch sử chấm công cho các nhân viên"""
    print("\n=== TẠO DỮ LIỆU GIẢ CHẤM CÔNG ===")
    
    # Sử dụng tháng hiện tại
    current_date = datetime.now()
    start_date = current_date.replace(day=1).date()
    end_date = current_date.date()  # Chỉ tạo đến ngày hiện tại
    
    print(f"\nTạo dữ liệu chấm công từ {start_date.strftime('%d/%m/%Y')} đến {end_date.strftime('%d/%m/%Y')}")
    confirm = input("Bạn có chắc chắn muốn tạo dữ liệu chấm công cho khoảng thời gian này? (y/n): ")
    if confirm.lower() != 'y':
        print("Đã hủy thao tác tạo dữ liệu.")
        return
    
    with app.app_context():
        try:
            # Xóa dữ liệu chấm công cũ trong khoảng thời gian này
            print(f"Đang xóa dữ liệu chấm công cũ từ {start_date.strftime('%d/%m/%Y')} đến {end_date.strftime('%d/%m/%Y')}...")
            deleted = Attendance.query.filter(
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).delete()
            db.session.commit()
            print(f"Đã xóa {deleted} bản ghi chấm công cũ.")
            
            # Lấy danh sách tất cả nhân viên
            users = User.query.all()
            if not users:
                print("Không có nhân viên nào trong hệ thống!")
                return
                
            attendance_count = 0
            for user in users:
                print(f"Đang tạo dữ liệu cho nhân viên: {user.name}")
                
                current_date = start_date
                while current_date <= end_date:
                    # Kiểm tra xem có phải cuối tuần không (0 là thứ 2, 6 là chủ nhật)
                    is_weekend = current_date.weekday() >= 5
                    
                    # 90% khả năng nhân viên sẽ đi làm vào ngày thường, 30% vào cuối tuần
                    should_work = random.random() < 0.9 if not is_weekend else random.random() < 0.3
                    
                    # Tạo bản ghi chấm công cho mọi ngày, kể cả ngày nghỉ
                    # Chọn ngẫu nhiên một trong ba ca làm việc
                    shift = random.randint(1, 3)
                    
                    if shift == 1:  # Ca 1: 7:30-16:30
                        check_in_time = datetime.combine(current_date, datetime.min.time().replace(hour=7, minute=30))
                        check_out_time = datetime.combine(current_date, datetime.min.time().replace(hour=16, minute=30))
                    elif shift == 2:  # Ca 2: 8:00-17:00
                        check_in_time = datetime.combine(current_date, datetime.min.time().replace(hour=8, minute=0))
                        check_out_time = datetime.combine(current_date, datetime.min.time().replace(hour=17, minute=0))
                    else:  # Ca 3: 9:00-18:00
                        check_in_time = datetime.combine(current_date, datetime.min.time().replace(hour=9, minute=0))
                        check_out_time = datetime.combine(current_date, datetime.min.time().replace(hour=18, minute=0))
                    
                    # Thời gian nghỉ trưa cố định 1 giờ
                    break_time = 1.0
                    
                    # Tạo ghi chú
                    notes = ["", "Dự án A", "Báo cáo tuần", "Làm thêm giờ", "Meeting with client"]
                    note = random.choice(notes)
                    
                    # Xác định loại ngày
                    holiday_type = "normal"  # Mặc định là ngày thường
                    is_holiday = False
                    
                    if is_weekend:
                        is_holiday = True
                        holiday_type = "weekend"
                    elif random.random() < 0.1:  # 10% cơ hội là ngày lễ
                        is_holiday = True
                        holiday_type = random.choice(["vietnamese_holiday", "japanese_holiday"])
                    
                    # Nếu là ngày nghỉ hoặc không đi làm, đặt check_in và check_out là None
                    if not should_work:
                        check_in_time = None
                        check_out_time = None
                        note = "Nghỉ phép" if not is_holiday else "Nghỉ lễ" if holiday_type != "weekend" else "Nghỉ cuối tuần"
                    else:
                        # 30% khả năng có tăng ca
                        has_overtime = random.random() < 0.3
                        if has_overtime:
                            # Tăng ca từ 1-3 giờ
                            overtime_hours = random.randint(1, 3)
                            # 70% khả năng tăng ca trước 22h, 30% sau 22h
                            if random.random() < 0.7:
                                # Tăng ca trước 22h
                                check_out_time = check_out_time + timedelta(hours=overtime_hours)
                                note = "Tăng ca dự án" if not note else note
                            else:
                                # Tăng ca sau 22h
                                check_out_time = check_out_time + timedelta(hours=overtime_hours)
                                note = "Tăng ca khẩn cấp" if not note else note
                    
                    # Trạng thái phê duyệt
                    approved = random.random() < 0.8  # 80% đã phê duyệt
                    status = 'approved' if approved else 'pending'
                    
                    # Tạo bản ghi chấm công
                    attendance = Attendance(
                        user_id=user.id,
                        date=current_date,
                        check_in=check_in_time,
                        check_out=check_out_time,
                        break_time=break_time,
                        is_holiday=is_holiday,
                        holiday_type=holiday_type,
                        note=note,
                        approved=approved,
                        status=status
                    )
                    
                    # Tính tổng giờ làm và overtime
                    attendance.update_work_hours()
                    
                    db.session.add(attendance)
                    attendance_count += 1
                    
                    current_date += timedelta(days=1)
                
            db.session.commit()
            print(f"\nHoàn thành! Đã tạo {attendance_count} bản ghi chấm công cho {len(users)} nhân viên.")
            
        except ValueError as e:
            print(f"Lỗi: {e}")
            db.session.rollback()
        except Exception as e:
            print(f"Lỗi không xác định: {e}")
            db.session.rollback()

def delete_all_fake_attendance_data():
    """Xóa tất cả dữ liệu chấm công giả"""
    print("\n=== XÓA TẤT CẢ DỮ LIỆU CHẤM CÔNG GIẢ ===")
    
    with app.app_context():
        try:
            # Xóa tất cả dữ liệu chấm công
            deleted = Attendance.query.delete()
            db.session.commit()
            print(f"Đã xóa thành công {deleted} bản ghi chấm công.")
            
        except Exception as e:
            print(f"Lỗi khi xóa dữ liệu: {e}")
            db.session.rollback()

def show_menu():
    while True:
        print("\n=== MENU QUẢN LÝ DỮ LIỆU ===")
        print("1. Tạo dữ liệu mẫu")
        print("2. Tạo nhân viên mới")
        print("3. Tìm mật khẩu theo mã nhân viên")
        print("4. Xóa nhân viên")
        print("5. Xem tất cả nhân viên")
        print("6. Xóa toàn bộ dữ liệu")
        print("7. Tạo dữ liệu chấm công giả")
        print("8. Xóa tất cả dữ liệu chấm công giả")
        print("9. Xóa dữ liệu chấm công theo thời gian")
        print("0. Thoát")
        
        choice = input("\nChọn chức năng (0-9): ")
        
        if choice == '1':
            create_sample_data()
        elif choice == '2':
            create_new_user()
        elif choice == '3':
            find_password_by_employee_id()
        elif choice == '4':
            view_users()
            employee_ids = input("Nhập mã nhân viên cần xóa (phân cách bằng dấu phẩy): ")
            delete_employees([int(id.strip()) for id in employee_ids.split(',')])
        elif choice == '5':
            show_all_users()
        elif choice == '6':
            confirm = input("Bạn có chắc chắn muốn xóa TOÀN BỘ dữ liệu? (y/n): ")
            if confirm.lower() == 'y':
                clear_database()
            else:
                print("Đã hủy thao tác xóa.")
        elif choice == '7':
            create_fake_attendance_data()
        elif choice == '8':
            confirm = input("Bạn có chắc chắn muốn xóa TẤT CẢ dữ liệu chấm công? (y/n): ")
            if confirm.lower() == 'y':
                delete_all_fake_attendance_data()
            else:
                print("Đã hủy thao tác xóa.")
        elif choice == '9':
            delete_attendance_by_date_range()
        elif choice == '0':
            print("Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ. Vui lòng chọn lại.")

def show_all_users():
    """Hiển thị danh sách tất cả nhân viên"""
    print("\n=== DANH SÁCH NHÂN VIÊN ===")
    
    with app.app_context():
        try:
            users = User.query.all()
            if not users:
                print("Không có nhân viên nào trong hệ thống!")
                return
                
            print("\n{:<5} {:<10} {:<30} {:<15} {:<20}".format(
                "ID", "Mã NV", "Tên", "Phòng ban", "Vai trò"
            ))
            print("-" * 85)
            
            for user in users:
                print("{:<5} {:<10} {:<30} {:<15} {:<20}".format(
                    user.id,
                    user.employee_id,
                    user.name,
                    user.department,
                    user.roles
                ))
                
        except Exception as e:
            print(f"Lỗi khi hiển thị danh sách nhân viên: {e}")
            db.session.rollback()

def clear_database():
    """Xóa toàn bộ dữ liệu trong database"""
    print("\n=== XÓA TOÀN BỘ DỮ LIỆU ===")
    
    with app.app_context():
        try:
            # Xóa tất cả dữ liệu theo thứ tự để tránh lỗi khóa ngoại
            print("Đang xóa dữ liệu chấm công...")
            Attendance.query.delete()
            print("Đang xóa dữ liệu yêu cầu...")
            Request.query.delete()
            print("Đang xóa dữ liệu người dùng...")
            User.query.delete()
            
            db.session.commit()
            print("\nĐã xóa toàn bộ dữ liệu thành công!")
            
        except Exception as e:
            print(f"Lỗi khi xóa dữ liệu: {e}")
            db.session.rollback()

def view_users():
    """Hiển thị danh sách nhân viên để chọn xóa"""
    print("\n=== DANH SÁCH NHÂN VIÊN ===")
    
    with app.app_context():
        try:
            users = User.query.all()
            if not users:
                print("Không có nhân viên nào trong hệ thống!")
                return
                
            print("\n{:<5} {:<10} {:<30} {:<15} {:<20}".format(
                "ID", "Mã NV", "Tên", "Phòng ban", "Vai trò"
            ))
            print("-" * 85)
            
            for user in users:
                print("{:<5} {:<10} {:<30} {:<15} {:<20}".format(
                    user.id,
                    user.employee_id,
                    user.name,
                    user.department,
                    user.roles
                ))
                
        except Exception as e:
            print(f"Lỗi khi hiển thị danh sách nhân viên: {e}")
            db.session.rollback()

def delete_attendance_by_date_range():
    """Xóa dữ liệu chấm công trong khoảng thời gian"""
    print("\n=== XÓA DỮ LIỆU CHẤM CÔNG THEO THỜI GIAN ===")
    
    try:
        start_date_str = input("Nhập ngày bắt đầu (định dạng DD/MM/YYYY): ")
        end_date_str = input("Nhập ngày kết thúc (định dạng DD/MM/YYYY): ")
        
        # Chuyển đổi chuỗi ngày thành đối tượng date
        start_date = datetime.strptime(start_date_str, "%d/%m/%Y").date()
        end_date = datetime.strptime(end_date_str, "%d/%m/%Y").date()
        
        with app.app_context():
            # Xóa dữ liệu chấm công trong khoảng thời gian
            deleted = Attendance.query.filter(
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).delete()
            
            db.session.commit()
            print(f"\nĐã xóa thành công {deleted} bản ghi chấm công từ {start_date_str} đến {end_date_str}")
            
    except ValueError as e:
        print(f"Lỗi định dạng ngày: {e}")
    except Exception as e:
        print(f"Lỗi không xác định: {e}")
        db.session.rollback()

def create_sample_data():
    """Tạo dữ liệu mẫu"""
    with app.app_context():
        # Xóa tất cả các bảng cũ
        db.drop_all()
        # Tạo lại các bảng với schema mới
        db.create_all()
        # Tạo dữ liệu mẫu
        create_sample_users()
    print("Đã tạo dữ liệu mẫu!")

if __name__ == '__main__':
    show_menu() 