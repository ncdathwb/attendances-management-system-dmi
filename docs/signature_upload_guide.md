# Hướng dẫn sử dụng chức năng Upload Ảnh Chữ Ký

## Tổng quan
Chức năng upload ảnh chữ ký cho phép người dùng tải lên ảnh chữ ký viết tay và tự động xử lý để tạo chữ ký số phù hợp cho hệ thống.

## Tính năng chính

### 1. Upload ảnh chữ ký
- Hỗ trợ các định dạng: JPG, PNG, GIF, JFIF
- Kích thước file tối đa: 10MB
- Tự động xử lý và tối ưu hóa ảnh

### 2. Xử lý ảnh tự động
- **Tách nền trắng**: Loại bỏ nền giấy trắng
- **Chuyển nét sang đen**: Chuyển đổi chữ ký thành màu đen
- **Điều chỉnh kích thước**: Scale về kích thước chuẩn (500x180px)
- **Tối ưu hóa chất lượng**: Đảm bảo chữ ký rõ nét

### 3. Xem trước và áp dụng
- Xem trước ảnh gốc và ảnh đã xử lý
- Áp dụng chữ ký đã xử lý vào hệ thống
- Lưu chữ ký để sử dụng cho các bản ghi chấm công

## Cách sử dụng

### Bước 1: Truy cập trang Settings
1. Đăng nhập vào hệ thống
2. Vào menu **Cài đặt** (Settings)
3. Tìm phần **Chữ ký cá nhân**

### Bước 2: Chọn phương thức tạo chữ ký
- **Tab "Vẽ chữ ký"**: Vẽ chữ ký trực tiếp bằng chuột/touch
- **Tab "Upload ảnh"**: Tải lên ảnh chữ ký viết tay

### Bước 3: Upload và xử lý ảnh
1. Chọn tab **"Upload ảnh"**
2. Nhấn **"Chọn ảnh chữ ký"**
3. Chọn file ảnh chữ ký từ máy tính
4. Hệ thống tự động xử lý và hiển thị kết quả

### Bước 4: Xem trước và áp dụng
1. Xem ảnh gốc và ảnh đã xử lý
2. Nếu hài lòng, nhấn **"Áp dụng chữ ký này"**
3. Chữ ký sẽ được lưu và hiển thị trên canvas

### Bước 5: Lưu chữ ký
1. Nhấn **"Lưu chữ ký"** để lưu vào hệ thống
2. Chữ ký sẽ được sử dụng cho các bản ghi chấm công

## Lưu ý quan trọng

### Yêu cầu về ảnh
- **Chất lượng**: Ảnh rõ nét, không mờ
- **Nền**: Nền trắng hoặc sáng để dễ tách
- **Chữ ký**: Nét đậm, màu tối (đen, xanh đậm)
- **Góc chụp**: Chụp thẳng, không nghiêng

### Kết quả xử lý
- **Nền trắng**: Được làm sạch hoàn toàn
- **Nét chữ ký**: Chuyển thành màu đen
- **Kích thước**: Tự động scale về 500x180px
- **Định dạng**: PNG với nền trong suốt

### Sử dụng chữ ký
- Chữ ký được lưu dưới dạng base64
- Tự động sử dụng cho các bản ghi chấm công
- Có thể test hiển thị trên PDF phiếu tăng ca

## Xử lý sự cố

### Ảnh không được xử lý đúng
- Kiểm tra chất lượng ảnh gốc
- Đảm bảo nền sáng và chữ ký tối
- Thử với ảnh khác có độ tương phản cao hơn

### Chữ ký bị mờ hoặc không rõ
- Sử dụng ảnh có độ phân giải cao hơn
- Đảm bảo ánh sáng đủ khi chụp
- Thử vẽ lại chữ ký với nét đậm hơn

### Lỗi upload
- Kiểm tra kích thước file (tối đa 10MB)
- Đảm bảo định dạng file được hỗ trợ (JPG, PNG, GIF, JFIF)
- Thử refresh trang và upload lại

## Công nghệ sử dụng

### Frontend
- **HTML5 Canvas**: Xử lý ảnh
- **JavaScript**: Logic xử lý và tương tác
- **Bootstrap 5**: Giao diện người dùng

### Xử lý ảnh
- **Pixel manipulation**: Xử lý từng pixel
- **Brightness calculation**: Tính độ sáng
- **Color thresholding**: Phân ngưỡng màu sắc
- **Image scaling**: Thay đổi kích thước

### Backend
- **Flask**: Xử lý request
- **SQLAlchemy**: Lưu trữ dữ liệu
- **Base64 encoding**: Mã hóa chữ ký

## Bảo mật

### Dữ liệu
- Chữ ký được mã hóa base64
- Lưu trữ an toàn trong database
- Không lưu file ảnh gốc

### Quyền truy cập
- Chỉ người dùng đã đăng nhập mới có thể upload
- Mỗi người dùng chỉ có thể quản lý chữ ký của mình
- Session timeout bảo vệ tài khoản

## Tương lai

### Tính năng dự kiến
- Hỗ trợ nhiều định dạng ảnh hơn
- Cải thiện thuật toán xử lý ảnh
- Thêm tùy chọn điều chỉnh thủ công
- Hỗ trợ chữ ký vector (SVG)

### Tối ưu hóa
- Giảm thời gian xử lý ảnh
- Cải thiện chất lượng output
- Tăng độ chính xác tách nền
- Hỗ trợ ảnh có nền phức tạp hơn 