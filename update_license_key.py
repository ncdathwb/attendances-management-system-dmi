#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script để cập nhật hoặc xóa license key trong database.
Sử dụng: python update_license_key.py [--key KEY] [--clear]
"""

import sys
import os

# Thêm thư mục hiện tại vào path để import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from database.models import Activation

def update_license_key(new_key=None, clear=False):
    """
    Cập nhật hoặc xóa license key trong database.
    
    Args:
        new_key: Key mới để cập nhật (None nếu muốn xóa)
        clear: Nếu True, xóa key (set về None)
    """
    with app.app_context():
        try:
            activation = Activation.query.get(1)
            
            if not activation:
                print("❌ Không tìm thấy activation record. Đang tạo mới...")
                activation = Activation(id=1, is_activated=False)
                db.session.add(activation)
            
            if clear:
                # Xóa key cũ
                old_key = activation.license_key
                activation.license_key = None
                activation.is_activated = False
                activation.activated_at = None
                db.session.commit()
                print(f"✅ Đã xóa key cũ: {old_key}")
                print("   - license_key: None")
                print("   - is_activated: False")
                print("   - activated_at: None")
            elif new_key:
                # Cập nhật key mới
                old_key = activation.license_key
                activation.license_key = new_key.strip()
                activation.is_activated = True
                from datetime import datetime
                activation.activated_at = datetime.utcnow()
                db.session.commit()
                print(f"✅ Đã cập nhật license key:")
                print(f"   - Key cũ: {old_key}")
                print(f"   - Key mới: {activation.license_key}")
                print(f"   - is_activated: {activation.is_activated}")
                print(f"   - activated_at: {activation.activated_at}")
            else:
                # Hiển thị key hiện tại
                print("📋 Thông tin license key hiện tại:")
                print(f"   - license_key: {activation.license_key}")
                print(f"   - is_activated: {activation.is_activated}")
                print(f"   - activated_at: {activation.activated_at}")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Lỗi: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Cập nhật hoặc xóa license key trong database')
    parser.add_argument('--key', type=str, help='Key mới để cập nhật (ví dụ: LIC-W8B61JUL-F7OD)')
    parser.add_argument('--clear', action='store_true', help='Xóa key cũ (set về None)')
    
    args = parser.parse_args()
    
    if args.clear:
        print("🗑️  Đang xóa license key cũ...")
        update_license_key(clear=True)
    elif args.key:
        print(f"🔄 Đang cập nhật license key thành: {args.key}")
        update_license_key(new_key=args.key)
    else:
        print("ℹ️  Hiển thị thông tin license key hiện tại:")
        print("   (Sử dụng --key KEY để cập nhật hoặc --clear để xóa)")
        print()
        update_license_key()

