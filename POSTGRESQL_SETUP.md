# Hướng Dẫn Cài Đặt PostgreSQL

## 1. Cài Đặt PostgreSQL

### Windows
1. Tải PostgreSQL từ trang chủ: https://www.postgresql.org/download/windows/
2. Chạy installer và làm theo hướng dẫn
3. Ghi nhớ mật khẩu cho user `postgres`
4. Cài đặt pgAdmin (GUI tool) nếu muốn

### macOS
```bash
# Sử dụng Homebrew
brew install postgresql
brew services start postgresql
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

## 2. Cấu Hình Database

### Tạo Database
1. Chạy script tạo database:
```bash
python create_database.py
```

2. Hoặc tạo thủ công:
```sql
-- Kết nối vào PostgreSQL
psql -U postgres

-- Tạo database
CREATE DATABASE attendance_db;

-- Tạo user (tùy chọn)
CREATE USER attendance_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE attendance_db TO attendance_user;
```

## 3. Cấu Hình Môi Trường

1. Tạo file `.env` từ `env_example.txt`:
```bash
cp env_example.txt .env
```

2. Chỉnh sửa file `.env`:
```env
# Flask Configuration
FLASK_CONFIG=development
SECRET_KEY=your-secret-key-here

# PostgreSQL Database Configuration
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=attendance_db
```

## 4. Khởi Tạo Database

```bash
# Tạo database
python create_database.py

# Khởi tạo dữ liệu
python init_db.py
```

## 5. Chạy Ứng Dụng

```bash
python app.py
```

## 6. Kiểm Tra Kết Nối

### Sử dụng psql
```bash
psql -U postgres -d attendance_db -h localhost
```

### Sử dụng pgAdmin
1. Mở pgAdmin
2. Kết nối đến server PostgreSQL
3. Mở database `attendance_db`
4. Kiểm tra các bảng đã được tạo

## 7. Xử Lý Lỗi Thường Gặp

### Lỗi kết nối
```
psycopg2.OperationalError: could not connect to server
```
**Giải pháp:**
- Kiểm tra PostgreSQL service đang chạy
- Kiểm tra thông tin kết nối trong file `.env`
- Kiểm tra firewall

### Lỗi quyền truy cập
```
psycopg2.OperationalError: permission denied for database
```
**Giải pháp:**
- Đảm bảo user có quyền truy cập database
- Kiểm tra cấu hình pg_hba.conf

### Lỗi database không tồn tại
```
psycopg2.OperationalError: database "attendance_db" does not exist
```
**Giải pháp:**
- Chạy `python create_database.py` để tạo database
- Kiểm tra tên database trong file `.env`

## 8. Backup và Restore

### Backup
```bash
pg_dump -U postgres -h localhost attendance_db > backup.sql
```

### Restore
```bash
psql -U postgres -h localhost attendance_db < backup.sql
```

## 9. Monitoring

### Kiểm tra trạng thái service
```bash
# Windows
sc query postgresql

# Linux/macOS
sudo systemctl status postgresql
```

### Xem log
```bash
# Windows: Kiểm tra Event Viewer
# Linux/macOS
sudo tail -f /var/log/postgresql/postgresql-*.log
``` 