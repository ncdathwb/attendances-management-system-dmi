#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script để xóa dữ liệu nghỉ phép
Hỗ trợ xóa theo nhiều tiêu chí: tất cả, theo user, theo khoảng thời gian
"""

import sys
import os
from datetime import datetime, timedelta

# Thêm thư mục hiện tại vào path để import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import từ app
from app import app, db
from database.models import LeaveRequest, User, AuditLog

def delete_all_leave_requests():
    """Xóa tất cả dữ liệu nghỉ phép"""
    try:
        with app.app_context():
            count = LeaveRequest.query.count()
            print(f"\n📊 Tổng số đơn nghỉ phép: {count}")
            
            if count == 0:
                print("ℹ️ Không có dữ liệu nghỉ phép để xóa")
                return True
            
            # Xác nhận
            print(f"\n⚠️  CẢNH BÁO: Bạn sắp xóa {count} đơn nghỉ phép!")
            confirm = input("Nhập 'YES' để xác nhận xóa: ")
            
            if confirm != 'YES':
                print("❌ Đã hủy thao tác xóa")
                return False
            
            # Xóa tất cả
            print(f"\n🗑️  Đang xóa {count} đơn nghỉ phép...")
            deleted = LeaveRequest.query.delete()
            db.session.commit()
            
            print(f"✅ Đã xóa thành công {deleted} đơn nghỉ phép")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi khi xóa dữ liệu: {e}")
        db.session.rollback()
        return False

def delete_by_user(employee_id):
    """Xóa dữ liệu nghỉ phép của một user cụ thể"""
    try:
        with app.app_context():
            user = User.query.filter_by(employee_id=employee_id).first()
            if not user:
                print(f"❌ Không tìm thấy user với employee_id: {employee_id}")
                return False
            
            count = LeaveRequest.query.filter_by(user_id=user.id).count()
            print(f"\n📊 Số đơn nghỉ phép của {user.name} ({employee_id}): {count}")
            
            if count == 0:
                print("ℹ️ Không có dữ liệu nghỉ phép để xóa")
                return True
            
            # Xác nhận
            print(f"\n⚠️  CẢNH BÁO: Bạn sắp xóa {count} đơn nghỉ phép của {user.name}!")
            confirm = input("Nhập 'YES' để xác nhận xóa: ")
            
            if confirm != 'YES':
                print("❌ Đã hủy thao tác xóa")
                return False
            
            # Xóa
            print(f"\n🗑️  Đang xóa {count} đơn nghỉ phép của {user.name}...")
            deleted = LeaveRequest.query.filter_by(user_id=user.id).delete()
            db.session.commit()
            
            print(f"✅ Đã xóa thành công {deleted} đơn nghỉ phép của {user.name}")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi khi xóa dữ liệu: {e}")
        db.session.rollback()
        return False

def delete_by_date_range(start_date, end_date):
    """Xóa dữ liệu nghỉ phép trong khoảng thời gian (dựa trên ngày bắt đầu)"""
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
            
            # Đếm số đơn có ngày bắt đầu trong khoảng thời gian
            count = 0
            all_requests = LeaveRequest.query.all()
            matching_requests = []
            
            for req in all_requests:
                try:
                    req_start_date = datetime(
                        req.leave_from_year,
                        req.leave_from_month,
                        req.leave_from_day
                    ).date()
                    if start <= req_start_date <= end:
                        count += 1
                        matching_requests.append(req.id)
                except (ValueError, AttributeError):
                    continue
            
            print(f"\n📊 Số đơn nghỉ phép từ {start_date} đến {end_date}: {count}")
            
            if count == 0:
                print("ℹ️ Không có dữ liệu nghỉ phép trong khoảng thời gian này")
                return True
            
            # Xác nhận
            print(f"\n⚠️  CẢNH BÁO: Bạn sắp xóa {count} đơn nghỉ phép từ {start_date} đến {end_date}!")
            confirm = input("Nhập 'YES' để xác nhận xóa: ")
            
            if confirm != 'YES':
                print("❌ Đã hủy thao tác xóa")
                return False
            
            # Xóa
            print(f"\n🗑️  Đang xóa {count} đơn nghỉ phép...")
            deleted = LeaveRequest.query.filter(LeaveRequest.id.in_(matching_requests)).delete(synchronize_session=False)
            db.session.commit()
            
            print(f"✅ Đã xóa thành công {deleted} đơn nghỉ phép từ {start_date} đến {end_date}")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi khi xóa dữ liệu: {e}")
        db.session.rollback()
        return False

def delete_by_user_and_date_range(employee_id, start_date, end_date):
    """Xóa dữ liệu nghỉ phép của một user trong khoảng thời gian"""
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
            
            # Đếm số đơn của user có ngày bắt đầu trong khoảng thời gian
            count = 0
            user_requests = LeaveRequest.query.filter_by(user_id=user.id).all()
            matching_requests = []
            
            for req in user_requests:
                try:
                    req_start_date = datetime(
                        req.leave_from_year,
                        req.leave_from_month,
                        req.leave_from_day
                    ).date()
                    if start <= req_start_date <= end:
                        count += 1
                        matching_requests.append(req.id)
                except (ValueError, AttributeError):
                    continue
            
            print(f"\n📊 Số đơn nghỉ phép của {user.name} ({employee_id}) từ {start_date} đến {end_date}: {count}")
            
            if count == 0:
                print("ℹ️ Không có dữ liệu nghỉ phép để xóa")
                return True
            
            # Xác nhận
            print(f"\n⚠️  CẢNH BÁO: Bạn sắp xóa {count} đơn nghỉ phép của {user.name} từ {start_date} đến {end_date}!")
            confirm = input("Nhập 'YES' để xác nhận xóa: ")
            
            if confirm != 'YES':
                print("❌ Đã hủy thao tác xóa")
                return False
            
            # Xóa
            print(f"\n🗑️  Đang xóa {count} đơn nghỉ phép...")
            deleted = LeaveRequest.query.filter(
                LeaveRequest.user_id == user.id,
                LeaveRequest.id.in_(matching_requests)
            ).delete(synchronize_session=False)
            db.session.commit()
            
            print(f"✅ Đã xóa thành công {deleted} đơn nghỉ phép của {user.name} từ {start_date} đến {end_date}")
            return True
            
    except Exception as e:
        print(f"❌ Lỗi khi xóa dữ liệu: {e}")
        db.session.rollback()
        return False

def show_statistics():
    """Hiển thị thống kê dữ liệu nghỉ phép"""
    try:
        with app.app_context():
            total = LeaveRequest.query.count()
            print(f"\n📊 THỐNG KÊ DỮ LIỆU NGHỈ PHÉP")
            print(f"{'='*60}")
            print(f"Tổng số đơn: {total}")
            
            if total > 0:
                # Thống kê theo user
                user_stats = db.session.query(
                    User.name,
                    User.employee_id,
                    db.func.count(LeaveRequest.id).label('count')
                ).join(LeaveRequest).group_by(User.id).order_by(db.func.count(LeaveRequest.id).desc()).limit(10).all()
                
                print(f"\nTop 10 người có nhiều đơn nghỉ phép nhất:")
                for name, emp_id, count in user_stats:
                    print(f"  - {name} ({emp_id}): {count} đơn")
                
                # Thống kê theo tháng (dựa trên ngày bắt đầu)
                month_stats_dict = {}
                all_requests = LeaveRequest.query.all()
                
                for req in all_requests:
                    try:
                        month_key = f"{req.leave_from_year}-{req.leave_from_month:02d}"
                        month_stats_dict[month_key] = month_stats_dict.get(month_key, 0) + 1
                    except (ValueError, AttributeError):
                        continue
                
                print(f"\nThống kê theo tháng (ngày bắt đầu):")
                for month in sorted(month_stats_dict.keys()):
                    print(f"  - {month}: {month_stats_dict[month]} đơn")
                
                # Thống kê theo trạng thái
                status_stats = db.session.query(
                    LeaveRequest.status,
                    db.func.count(LeaveRequest.id).label('count')
                ).group_by(LeaveRequest.status).all()
                
                print(f"\nThống kê theo trạng thái:")
                for status, count in status_stats:
                    status_name = {
                        'pending': 'Chờ duyệt',
                        'pending_manager': 'Chờ quản lý',
                        'pending_admin': 'Chờ admin',
                        'approved': 'Đã duyệt',
                        'rejected': 'Từ chối'
                    }.get(status, status)
                    print(f"  - {status_name} ({status}): {count} đơn")
            
            print(f"{'='*60}\n")
            
    except Exception as e:
        print(f"❌ Lỗi khi lấy thống kê: {e}")

def main():
    """Hàm main để chạy script"""
    print("="*70)
    print("🗑️  SCRIPT XÓA DỮ LIỆU NGHỈ PHÉP")
    print("="*70)
    
    # Hiển thị thống kê
    show_statistics()
    
    print("Chọn chức năng:")
    print("1. Xóa TẤT CẢ dữ liệu nghỉ phép")
    print("2. Xóa dữ liệu nghỉ phép của một user")
    print("3. Xóa dữ liệu nghỉ phép theo khoảng thời gian")
    print("4. Xóa dữ liệu nghỉ phép của một user trong khoảng thời gian")
    print("5. Xem thống kê")
    print("0. Thoát")
    
    choice = input("\nNhập lựa chọn (0-5): ").strip()
    
    if choice == '0':
        print("👋 Đã thoát")
        return
    
    elif choice == '1':
        delete_all_leave_requests()
    
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

