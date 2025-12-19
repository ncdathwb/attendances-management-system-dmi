@echo off
chcp 65001 >nul
echo ========================================
echo XÓA DỮ LIỆU CHẤM CÔNG
echo ========================================
echo.

REM Kiểm tra xem có virtual environment không
if exist "venv\Scripts\python.exe" (
    echo Đang sử dụng virtual environment...
    venv\Scripts\python.exe delete_attendance_data.py
) else (
    echo Đang sử dụng Python hệ thống...
    python delete_attendance_data.py
)

pause

