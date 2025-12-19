#!/usr/bin/env python3
"""
Test script for Smart Signature System with Role-based Signature Reuse
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import User, Attendance
from utils.signature_manager import signature_manager
from datetime import datetime, date, time
import base64

def create_test_signature():
    """Tạo chữ ký test đơn giản"""
    # Tạo một chữ ký base64 đơn giản (hình ảnh 1x1 pixel màu đen)
    signature_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    return signature_data

def test_signature_reuse():
    """Test tính năng tái sử dụng chữ ký từ vai trò thấp hơn"""
    print("🧪 Testing Signature Reuse from Lower Roles...")
    
    with app.app_context():
        # Tạo user test với nhiều vai trò
        test_user = User(
            employee_id=99999,
            name="Test User Multi-Role",
            department="IT",
            roles="EMPLOYEE,TEAM_LEADER,MANAGER",
            is_active=True
        )
        test_user.set_password("test123")
        
        # Kiểm tra user đã tồn tại chưa
        existing_user = User.query.filter_by(employee_id=99999).first()
        if existing_user:
            test_user = existing_user
        else:
            db.session.add(test_user)
            db.session.commit()
        
        print(f"✅ Test user created: {test_user.name} (ID: {test_user.id})")
        print(f"   Roles: {test_user.roles}")
        
        # Tạo attendance record với chữ ký employee
        test_date = date.today()
        test_signature = create_test_signature()
        
        attendance = Attendance(
            user_id=test_user.id,
            date=test_date,
            check_in=datetime.combine(test_date, time(8, 0)),
            check_out=datetime.combine(test_date, time(17, 0)),
            break_time=1.0,
            is_holiday=False,
            holiday_type='normal',
            status='pending',
            signature=test_signature,  # Chữ ký employee
            shift_code='1',
            shift_start=time(8, 0),
            shift_end=time(17, 0)
        )
        
        # Kiểm tra attendance đã tồn tại chưa
        existing_attendance = Attendance.query.filter_by(
            user_id=test_user.id, 
            date=test_date
        ).first()
        
        if existing_attendance:
            attendance = existing_attendance
            attendance.signature = test_signature  # Cập nhật chữ ký
        else:
            db.session.add(attendance)
        
        db.session.commit()
        print(f"✅ Attendance record created: ID {attendance.id}")
        print(f"   Employee signature: {'Yes' if attendance.signature else 'No'}")
        
        # Test 1: Kiểm tra chữ ký khi user ở vai trò TEAM_LEADER
        print("\n🔍 Test 1: TEAM_LEADER role signature check")
        signature_status = signature_manager.check_signature_status(
            test_user.id, 'TEAM_LEADER', attendance.id
        )
        print(f"   Signature status: {signature_status}")
        
        # Test 2: Lấy chữ ký từ database cho TEAM_LEADER
        print("\n🔍 Test 2: Getting signature for TEAM_LEADER")
        team_leader_signature = signature_manager.get_signature_from_database(
            test_user.id, 'TEAM_LEADER', attendance.id
        )
        print(f"   Found signature: {'Yes' if team_leader_signature else 'No'}")
        if team_leader_signature:
            print(f"   Signature type: {'Employee signature (reused)' if team_leader_signature == test_signature else 'Team leader signature'}")
        
        # Test 3: Kiểm tra chữ ký khi user ở vai trò MANAGER
        print("\n🔍 Test 3: MANAGER role signature check")
        signature_status = signature_manager.check_signature_status(
            test_user.id, 'MANAGER', attendance.id
        )
        print(f"   Signature status: {signature_status}")
        
        # Test 4: Lấy chữ ký từ database cho MANAGER
        print("\n🔍 Test 4: Getting signature for MANAGER")
        manager_signature = signature_manager.get_signature_from_database(
            test_user.id, 'MANAGER', attendance.id
        )
        print(f"   Found signature: {'Yes' if manager_signature else 'No'}")
        if manager_signature:
            print(f"   Signature type: {'Employee signature (reused)' if manager_signature == test_signature else 'Manager signature'}")
        
        # Test 5: Tạo chữ ký team leader và test lại
        print("\n🔍 Test 5: Creating team leader signature and testing manager")
        team_leader_signature_data = create_test_signature()
        attendance.team_leader_signature = team_leader_signature_data
        attendance.approved_by = test_user.id
        attendance.status = 'pending_manager'
        db.session.commit()
        
        # Test lại cho MANAGER
        manager_signature = signature_manager.get_signature_from_database(
            test_user.id, 'MANAGER', attendance.id
        )
        print(f"   Manager signature after team leader signed: {'Yes' if manager_signature else 'No'}")
        if manager_signature:
            print(f"   Signature type: {'Team leader signature (reused)' if manager_signature == team_leader_signature_data else 'Manager signature'}")
        
        # Test 6: Kiểm tra thứ tự ưu tiên
        print("\n🔍 Test 6: Testing priority order")
        print("   Priority for TEAM_LEADER: 1. Team leader signature, 2. Employee signature")
        print("   Priority for MANAGER: 1. Manager signature, 2. Team leader signature, 3. Employee signature")
        
        # Tạo manager signature
        manager_signature_data = create_test_signature()
        attendance.manager_signature = manager_signature_data
        attendance.status = 'pending_admin'
        db.session.commit()
        
        # Test lại cho MANAGER - nên lấy manager signature
        final_manager_signature = signature_manager.get_signature_from_database(
            test_user.id, 'MANAGER', attendance.id
        )
        print(f"   Final manager signature: {'Manager signature' if final_manager_signature == manager_signature_data else 'Other signature'}")
        
        print("\n✅ All tests completed!")
        
        # Cleanup (optional)
        # db.session.delete(attendance)
        # db.session.delete(test_user)
        # db.session.commit()
        # print("🧹 Test data cleaned up")

def test_signature_status_detection():
    """Test việc phát hiện chữ ký được tái sử dụng"""
    print("\n🧪 Testing Signature Reuse Detection...")
    
    with app.app_context():
        # Tìm user test
        test_user = User.query.filter_by(employee_id=99999).first()
        if not test_user:
            print("❌ Test user not found. Run test_signature_reuse() first.")
            return
        
        # Tìm attendance test
        test_attendance = Attendance.query.filter_by(user_id=test_user.id).first()
        if not test_attendance:
            print("❌ Test attendance not found. Run test_signature_reuse() first.")
            return
        
        print(f"✅ Using test attendance: ID {test_attendance.id}")
        
        # Test detection cho TEAM_LEADER
        print("\n🔍 Testing TEAM_LEADER reuse detection:")
        status = signature_manager.check_signature_status(
            test_user.id, 'TEAM_LEADER', test_attendance.id
        )
        print(f"   Is reused signature: {status.get('is_reused_signature', False)}")
        print(f"   Message: {status.get('message', 'No message')}")
        
        # Test detection cho MANAGER
        print("\n🔍 Testing MANAGER reuse detection:")
        status = signature_manager.check_signature_status(
            test_user.id, 'MANAGER', test_attendance.id
        )
        print(f"   Is reused signature: {status.get('is_reused_signature', False)}")
        print(f"   Message: {status.get('message', 'No message')}")

if __name__ == '__main__':
    print("🚀 Starting Smart Signature System Tests...")
    print("=" * 50)
    
    try:
        test_signature_reuse()
        test_signature_status_detection()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc() 