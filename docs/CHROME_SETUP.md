# 🚀 Hướng dẫn Setup Chrome trong Folder Dự án

## 📋 **Mục đích**
Để Selenium sử dụng Chrome browser từ cùng folder dự án thay vì tìm trong hệ thống, giúp tránh lỗi tương thích và dễ quản lý.

## 🔧 **Các bước thực hiện**

### 1. **Chạy script setup**
```bash
python setup_chrome.py
```

Script này sẽ:
- Tạo thư mục `browsers/` và `chrome/` trong dự án
- Copy Chrome từ hệ thống vào folder dự án
- Hiển thị thông tin chi tiết quá trình

### 2. **Cấu trúc thư mục sau khi setup**
```
attendances-management-system-dmi/
├── browsers/
│   └── chrome.exe          # Chrome browser (Windows)
├── chrome/
│   └── chrome.exe          # Chrome browser (Windows)
├── app.py                   # Main application
├── test_selenium.py         # Test script
├── setup_chrome.py          # Setup script
└── CHROME_SETUP.md          # Hướng dẫn này
```

### 3. **Test Selenium**
```bash
python test_selenium.py
```

## 🎯 **Ưu điểm của cách này**

### **A. Tránh lỗi tương thích**
- Chrome và Chrome driver cùng version
- Không bị ảnh hưởng bởi Chrome system updates
- Dễ dàng quản lý version

### **B. Portable**
- Có thể copy toàn bộ dự án sang máy khác
- Không cần cài Chrome trên máy mới
- Hoạt động offline

### **C. Version control**
- Kiểm soát được version Chrome
- Dễ dàng rollback nếu cần
- Consistent environment

## 🚨 **Lưu ý quan trọng**

### **1. File size**
- Chrome browser khá lớn (~100-200MB)
- Đảm bảo đủ disk space
- Có thể thêm vào `.gitignore` nếu cần

### **2. Permissions**
- Cần quyền copy file từ system
- Chạy với quyền admin nếu cần
- Kiểm tra antivirus không block

### **3. Updates**
- Chrome trong dự án không tự update
- Cần chạy lại `setup_chrome.py` khi muốn update
- Hoặc copy Chrome mới thủ công

## 🔍 **Troubleshooting**

### **A. Chrome không được copy**
```bash
# Kiểm tra quyền
# Chạy với quyền admin
# Kiểm tra antivirus
```

### **B. Selenium vẫn lỗi**
```bash
# Chạy cleanup
python cleanup_drivers.py

# Upgrade dependencies
pip install --upgrade selenium webdriver-manager

# Test lại
python test_selenium.py
```

### **C. Chrome không tìm thấy**
```bash
# Kiểm tra file tồn tại
ls -la browsers/
ls -la chrome/

# Chạy lại setup
python setup_chrome.py
```

## 📱 **Sử dụng trong code**

### **A. Trong app.py**
```python
# Tìm Chrome trong cùng folder dự án
current_dir = os.path.dirname(os.path.abspath(__file__))
chrome_paths = [
    os.path.join(current_dir, "browsers", "chrome.exe"),
    os.path.join(current_dir, "chrome", "chrome.exe"),
    # ... fallback paths
]
```

### **B. Trong test_selenium.py**
```python
# Tương tự app.py
chrome_options.binary_location = chrome_path
```

## 🎉 **Kết quả mong đợi**

Sau khi setup thành công:
1. ✅ Chrome được copy vào folder dự án
2. ✅ Selenium tìm thấy Chrome local
3. ✅ Test script chạy thành công
4. ✅ Browser mở và hiển thị Google page

## 🔄 **Cập nhật Chrome**

Khi muốn update Chrome:
```bash
# 1. Xóa Chrome cũ
rm -rf browsers/chrome.exe
rm -rf chrome/chrome.exe

# 2. Chạy setup lại
python setup_chrome.py
```

---

> **Lưu ý**: Cách này giúp tránh lỗi `WinError 193` và các vấn đề tương thích khác giữa Chrome browser và Chrome driver.
