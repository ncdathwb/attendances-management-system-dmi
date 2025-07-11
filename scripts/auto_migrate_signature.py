import os
import sys
import subprocess

def run_cmd(cmd):
    print(f"Chạy lệnh: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Lỗi khi chạy: {cmd}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    # Bước 1: migrate
    run_cmd('flask db migrate -m "add signature field to attendance"')
    # Bước 2: upgrade
    run_cmd("flask db upgrade")
    print("Đã hoàn tất migrate và upgrade cột signature cho attendances!") 