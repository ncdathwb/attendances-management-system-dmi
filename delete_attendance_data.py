#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script để xóa dữ liệu chấm công
Hỗ trợ xóa theo nhiều tiêu chí: tất cả, theo user, theo khoảng thời gian
"""

import sys
import os
from datetime import datetime, timedelta

# Thêm thư mục hiện tại vào path để import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import từ app
from app import app, db
from database.models import Attendance, User, AuditLog

def delete_all_attendances():
    """Xóa tất cả dữ liệu chấm công"""
    try:
        with app.app_context():
            count = Attendance.query.count()
            print(f"\n📊 Tổng số bản ghi chấm công: {count}")
            
            if count == 0:
                print("ℹ️ Không có dữ liệu chấm công để xóa")
                return True
            
            # Xác nhận
            print(f"\n⚠️  CẢNH BÁO: Bạn sắp xóa {count} bản ghi chấm công!")
            confirm = input("Nhập 'YES' để xác nhận xóa: ")
            
            if confirm != 'YES':
                print("❌ Đã hủy thao tác xóa")
                return False
            
            # Xóa tất cả
            print(f"\n🗑️  Đang xóa {count} bản ghi chấm công...")
            deleted = Attendance.query.delete()
            db.session.commit()
            
            print(f"✅ Đã xóa thành công {deleted} bản ghi chấm công")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi khi xóa dữ liệu: {e}")
        db.session.rollback()
        return False

def delete_by_user(employee_id):
    """Xóa dữ liệu chấm công của một user cụ thể"""
    try:
        with app.app_context():
            user = User.query.filter_by(employee_id=employee_id).first()
            if not user:
                print(f"❌ Không tìm thấy user với employee_id: {employee_id}")
                return False
            
            count = Attendance.query.filter_by(user_id=user.id).count()
            print(f"\n📊 Số bản ghi chấm công của {user.name} ({employee_id}): {count}")
            
            if count == 0:
                print("ℹ️ Không có dữ liệu chấm công để xóa")
                return True
            
            # Xác nhận
            print(f"\n⚠️  CẢNH BÁO: Bạn sắp xóa {count} bản ghi chấm công của {user.name}!")
            confirm = input("Nhập 'YES' để xác nhận xóa: ")
            
            if confirm != 'YES':
                print("❌ Đã hủy thao tác xóa")
                return False
            
            # Xóa
            print(f"\n🗑️  Đang xóa {count} bản ghi chấm công của {user.name}...")
            deleted = Attendance.query.filter_by(user_id=user.id).delete()
            db.session.commit()
            
            print(f"✅ Đã xóa thành công {deleted} bản ghi chấm công của {user.name}")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi khi xóa dữ liệu: {e}")
        db.session.rollback()
        return False

def delete_by_date_range(start_date, end_date):
    """Xóa dữ liệu chấm công trong khoảng thời gian"""
    try:
        with app.app_context():
            # Parse dates
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                print("❌ Định dạng ngày không hợp lệ. Sử dụng YYYY-MM-DD")
                return False
            
            if start > end:
                print("❌ Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc")
                return False
            
            count = Attendance.query.filter(
                Attendance.date >= start,
                Attendance.date <= end
            ).count()
            
            print(f"\n📊 Số bản ghi chấm công từ {start_date} đến {end_date}: {count}")
            
            if count == 0:
                print("ℹ️ Không có dữ liệu chấm công trong khoảng thời gian này")
                return True
            
            # Xác nhận
            print(f"\n⚠️  CẢNH BÁO: Bạn sắp xóa {count} bản ghi chấm công từ {start_date} đến {end_date}!")
            confirm = input("Nhập 'YES' để xác nhận xóa: ")
            
            if confirm != 'YES':
                print("❌ Đã hủy thao tác xóa")
                return False
            
            # Xóa
            print(f"\n🗑️  Đang xóa {count} bản ghi chấm công...")
            deleted = Attendance.query.filter(
                Attendance.date >= start,
                Attendance.date <= end
            ).delete()
            db.session.commit()
            
            print(f"✅ Đã xóa thành công {deleted} bản ghi chấm công từ {start_date} đến {end_date}")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi khi xóa dữ liệu: {e}")
        db.session.rollback()
        return False

def delete_by_user_and_date_range(employee_id, start_date, end_date):
    """Xóa dữ liệu chấm công của một user trong khoảng thời gian"""
    try:
        with app.app_context():
            user = User.query.filter_by(employee_id=employee_id).first()
            if not user:
                print(f"❌ Không tìm thấy user với employee_id: {employee_id}")
                return False
            
            # Parse dates
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                print("❌ Định dạng ngày không hợp lệ. Sử dụng YYYY-MM-DD")
                return False
            
            if start > end:
                print("❌ Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc")
                return False
            
            count = Attendance.query.filter(
                Attendance.user_id == user.id,
                Attendance.date >= start,
                Attendance.date <= end
            ).count()
            
            print(f"\n📊 Số bản ghi chấm công của {user.name} ({employee_id}) từ {start_date} đến {end_date}: {count}")
            
            if count == 0:
                print("ℹ️ Không có dữ liệu chấm công để xóa")
                return True
            
            # Xác nhận
            print(f"\n⚠️  CẢNH BÁO: Bạn sắp xóa {count} bản ghi chấm công của {user.name} từ {start_date} đến {end_date}!")
            confirm = input("Nhập 'YES' để xác nhận xóa: ")
            
            if confirm != 'YES':
                print("❌ Đã hủy thao tác xóa")
                return False
            
            # Xóa
            print(f"\n🗑️  Đang xóa {count} bản ghi chấm công...")
            deleted = Attendance.query.filter(
                Attendance.user_id == user.id,
                Attendance.date >= start,
                Attendance.date <= end
            ).delete()
            db.session.commit()
            
            print(f"✅ Đã xóa thành công {deleted} bản ghi chấm công của {user.name} từ {start_date} đến {end_date}")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi khi xóa dữ liệu: {e}")
        db.session.rollback()
        return False

def show_statistics():
    """Hiển thị thống kê dữ liệu chấm công"""
    try:
        with app.app_context():
            total = Attendance.query.count()
            print(f"\n📊 THỐNG KÊ DỮ LIỆU CHẤM CÔNG")
            print(f"{'='*60}")
            print(f"Tổng số bản ghi: {total}")
            
            if total > 0:
                # Thống kê theo user
                user_stats = db.session.query(
                    User.name,
                    User.employee_id,
                    db.func.count(Attendance.id).label('count')
                ).join(Attendance).group_by(User.id).order_by(db.func.count(Attendance.id).desc()).limit(10).all()
                
                print(f"\nTop 10 người có nhiều bản ghi nhất:")
                for name, emp_id, count in user_stats:
                    print(f"  - {name} ({emp_id}): {count} bản ghi")
                
                # Thống kê theo tháng
                month_stats = db.session.query(
                    db.func.strftime('%Y-%m', Attendance.date).label('month'),
                    db.func.count(Attendance.id).label('count')
                ).group_by('month').order_by('month').all()
                
                print(f"\nThống kê theo tháng:")
                for month, count in month_stats:
                    print(f"  - {month}: {count} bản ghi")
            
            print(f"{'='*60}\n")
            
    except Exception as e:
        print(f"❌ Lỗi khi lấy thống kê: {e}")

def main():
    """Hàm main để chạy script"""
    print("="*70)
    print("🗑️  SCRIPT XÓA DỮ LIỆU CHẤM CÔNG")
    print("="*70)
    
    # Hiển thị thống kê
    show_statistics()
    
    print("Chọn chức năng:")
    print("1. Xóa TẤT CẢ dữ liệu chấm công")
    print("2. Xóa dữ liệu chấm công của một user")
    print("3. Xóa dữ liệu chấm công theo khoảng thời gian")
    print("4. Xóa dữ liệu chấm công của một user trong khoảng thời gian")
    print("5. Xem thống kê")
    print("0. Thoát")
    
    choice = input("\nNhập lựa chọn (0-5): ").strip()
    
    if choice == '0':
        print("👋 Đã thoát")
        return
    
    elif choice == '1':
        delete_all_attendances()
    
    elif choice == '2':
        employee_id = input("Nhập mã nhân viên (employee_id): ").strip()
        if employee_id:
            delete_by_user(employee_id)
        else:
            print("❌ Mã nhân viên không được để trống")
    
    elif choice == '3':
        start_date = input("Nhập ngày bắt đầu (YYYY-MM-DD): ").strip()
        end_date = input("Nhập ngày kết thúc (YYYY-MM-DD): ").strip()
        if start_date and end_date:
            delete_by_date_range(start_date, end_date)
        else:
            print("❌ Ngày không được để trống")
    
    elif choice == '4':
        employee_id = input("Nhập mã nhân viên (employee_id): ").strip()
        start_date = input("Nhập ngày bắt đầu (YYYY-MM-DD): ").strip()
        end_date = input("Nhập ngày kết thúc (YYYY-MM-DD): ").strip()
        if employee_id and start_date and end_date:
            delete_by_user_and_date_range(employee_id, start_date, end_date)
        else:
            print("❌ Thông tin không được để trống")
    
    elif choice == '5':
        show_statistics()
    
    else:
        print("❌ Lựa chọn không hợp lệ")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Đã hủy bởi người dùng")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Lỗi không mong đợi: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

