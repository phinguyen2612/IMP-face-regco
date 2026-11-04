# Kết nối DroidCam qua Wi-Fi

1. Mở DroidCam trên điện thoại và cho phép ứng dụng sử dụng camera.
2. Kết nối điện thoại và máy chạy worker vào cùng mạng Wi-Fi.
3. Trong web, mở **Camera → Thêm camera**, chọn **DroidCam (Wi-Fi)**.
4. Nhập tên và **Địa chỉ video DroidCam**, ví dụ
   `http://192.168.1.100:4747/video`. Thay IP và cổng bằng giá trị trong ứng dụng.
5. Bấm **Lưu camera**, sau đó **Bật camera và nhận diện**. Mở phần giám sát
   để xem hình và trạng thái nhận diện.

Định dạng URL `/video` được mô tả trong
[hướng dẫn chính thức DroidCam](https://www.dev47apps.com/droidcam/connect/).
Một số phiên bản cung cấp URL `/video/1280x720`; có thể nhập nguyên URL đó.

Worker đọc MJPEG trực tiếp từ điện thoại và gửi preview vào API hiện có.
Nguồn này không cần driver DroidCam trên Windows hoặc GStreamer. Cần giữ
worker chạy và DroidCam trên điện thoại đang hoạt động. Model và ảnh tham chiếu
vẫn phải được cấu hình để có kết quả nhận diện danh tính.

Để sửa kết nối, chọn **Chỉnh sửa** trên camera, nhập địa chỉ mới rồi lưu và áp dụng
cấu hình. Để trống địa chỉ khi sửa sẽ giữ kết nối hiện tại.

Nếu chưa có hình, thử mở URL video trong trình duyệt trên máy tính. Kiểm tra
IP, cổng, Wi-Fi và quyền camera trên điện thoại. Mạng khách có thể chặn kết nối
giữa thiết bị. Mục **Chẩn đoán camera** hiển thị lỗi timeout, không truy cập được
hoặc yêu cầu xác thực từ worker; trạng thái áp dụng cấu hình chưa có nghĩa là
đã nhận được hình.

Nếu dùng DroidCam Client trên Windows, vẫn có thể dùng các nguồn webcam
hiện có thay cho kết nối Wi-Fi trực tiếp.
