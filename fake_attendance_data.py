import random
from datetime import datetime, timedelta
from app import app, db, User, Attendance

# Số lượng bản ghi giả muốn tạo cho mỗi user
RECORDS_PER_USER = 50

# Hàm tạo dữ liệu chấm công giả
def add_fake_attendance():
    with app.app_context():
        users = User.query.all()
        for user in users:
            for i in range(RECORDS_PER_USER):
                # Sinh ngày ngẫu nhiên trong vòng 2 năm trở lại đây
                days_ago = random.randint(0, 730)
                date = datetime.now().date() - timedelta(days=days_ago)
                # Sinh giờ vào/ra hợp lệ
                shift = random.choice([
                    (7, 30, 16, 30),
                    (8, 0, 17, 0),
                    (9, 0, 18, 0),
                    (11, 0, 22, 0)
                ])
                check_in = datetime.combine(date, datetime.min.time().replace(hour=shift[0], minute=shift[1]))
                # Đi trễ hoặc về sớm/nghỉ ngẫu nhiên
                late = random.choice([0, 0, 0, 15, 30, 60])  # đa số đúng giờ, đôi khi trễ
                early = random.choice([0, 0, 0, 10, 20, 30])
                check_in = check_in + timedelta(minutes=late)
                check_out = datetime.combine(date, datetime.min.time().replace(hour=shift[2], minute=shift[3])) - timedelta(minutes=early)
                break_time = 1.0
                note = random.choice(['', 'Dự án A', 'Báo cáo tuần', 'Làm thêm', ''])
                att = Attendance(
                    user_id=user.id,
                    date=date,
                    check_in=check_in,
                    check_out=check_out,
                    break_time=break_time,
                    is_holiday=False,
                    holiday_type='normal',
                    note=note,
                    approved=True,
                    status='approved'
                )
                att.update_work_hours()
                db.session.add(att)
        db.session.commit()
        print(f"Đã tạo dữ liệu chấm công giả cho {len(users)} nhân viên, mỗi người {RECORDS_PER_USER} bản ghi.")

# Hàm xóa toàn bộ dữ liệu chấm công giả (approved=True và note có trong danh sách note giả)
def delete_fake_attendance():
    with app.app_context():
        notes_fake = ['', 'Dự án A', 'Báo cáo tuần', 'Làm thêm']
        deleted = Attendance.query.filter(Attendance.approved == True, Attendance.note.in_(notes_fake)).delete(synchronize_session=False)
        db.session.commit()
        print(f"Đã xóa {deleted} bản ghi chấm công giả.")

# Hàm tạo dữ liệu chấm công giả đủ từng ngày cho mỗi tháng
def add_fake_attendance_full_month():
    with app.app_context():
        users = User.query.all()
        # Khoảng thời gian muốn sinh dữ liệu (ví dụ: từ 1/2023 đến 6/2025)
        start_date = datetime(2023, 1, 1).date()
        end_date = datetime(2025, 6, 30).date()
        for user in users:
            date = start_date
            while date <= end_date:
                is_weekend = date.weekday() >= 5  # 5: Thứ 7, 6: Chủ nhật
                if is_weekend and random.random() < 0.5:
                    date += timedelta(days=1)
                    continue  # 50% cuối tuần nghỉ
                shift = random.choice([
                    (7, 30, 16, 30),
                    (8, 0, 17, 0),
                    (9, 0, 18, 0),
                    (11, 0, 22, 0)
                ])
                check_in = datetime.combine(date, datetime.min.time().replace(hour=shift[0], minute=shift[1]))
                late = random.choice([0, 0, 0, 15, 30, 60])
                early = random.choice([0, 0, 0, 10, 20, 30])
                check_in = check_in + timedelta(minutes=late)
                check_out = datetime.combine(date, datetime.min.time().replace(hour=shift[2], minute=shift[3])) - timedelta(minutes=early)
                break_time = 1.0
                note = random.choice(['', 'Dự án A', 'Báo cáo tuần', 'Làm thêm', ''])
                att = Attendance(
                    user_id=user.id,
                    date=date,
                    check_in=check_in,
                    check_out=check_out,
                    break_time=break_time,
                    is_holiday=is_weekend,
                    holiday_type='weekend' if is_weekend else 'normal',
                    note=note,
                    approved=True,
                    status='approved'
                )
                att.update_work_hours()
                db.session.add(att)
                date += timedelta(days=1)
        db.session.commit()
        print(f"Đã tạo dữ liệu chấm công full tháng cho {len(users)} nhân viên.")

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        while True:
            print("\n=== MENU DỮ LIỆU GIẢ CHẤM CÔNG ===")
            print("1. Thêm dữ liệu chấm công giả")
            print("2. Xóa dữ liệu chấm công giả")
            print("3. Thêm dữ liệu full tháng cho từng ngày")
            print("0. Thoát")
            choice = input("Chọn chức năng (0-3): ").strip()
            if choice == '1':
                add_fake_attendance()
            elif choice == '2':
                delete_fake_attendance()
            elif choice == '3':
                add_fake_attendance_full_month()
            elif choice == '0':
                print("Thoát.")
                break
            else:
                print("Lựa chọn không hợp lệ. Vui lòng chọn lại!")
    elif sys.argv[1] == 'add':
        add_fake_attendance()
    elif sys.argv[1] == 'delete':
        delete_fake_attendance()
    elif sys.argv[1] == 'full':
        add_fake_attendance_full_month()
    else:
        print("Tham số không hợp lệ. Dùng: add, delete, full hoặc chạy không tham số để hiện menu.") 