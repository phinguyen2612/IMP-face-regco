# Khôi phục nhận camera — 04/11/2026

## Lỗi tái hiện được

- `GET /api/v1/internal/cameras/active` trả 500; worker liên tục báo `CONTROL_API_UNAVAILABLE`.
- Các repository camera/model giữ kết nối PostgreSQL đã đóng sau khi mất kết nối. Truy vấn tiếp theo tiếp tục thất bại, dù database đã trở lại.
- `/health` chỉ kiểm tra object storage và cấu hình, vẫn trả `ok` khi repository camera không đọc được database.
- WebSocket đóng trong lúc gửi/thu hồi session tạo traceback `WebSocketDisconnect`.
- Vitest trên Windows gặp `spawn UNKNOWN` khi tạo nhiều tiến trình kiểm thử.
- Proxy HTTPS được cấu hình cho preview nhưng chưa áp dụng cùng quy tắc cho dev; header cố định có thể làm localhost sai origin khi dùng đồng thời.

## Thay đổi

- Kết nối dài hạn của camera/model/event/vector thay phiên PostgreSQL đã mất ở lần truy vấn kế tiếp. Không chạy lại câu lệnh hoặc commit bị mất kết nối; thao tác đó vẫn báo thất bại. Không nối lại giữa một transaction đang diễn ra.
- Health đọc repository camera; database không khả dụng trả 503. Lỗi kết nối tại endpoint được trả bằng `DATABASE_UNAVAILABLE`, có `Retry-After`, thay vì lỗi 500 chung.
- WebSocket xử lý peer disconnect như kết thúc kết nối bình thường.
- Bộ test web dùng threads, tối đa hai worker.
- Proxy HTTP và WebSocket của dev/preview chỉ khôi phục host/scheme từ origin công khai được khai báo rõ; localhost vẫn giữ host/scheme của nó. Kiểm tra origin và CSRF của API được giữ nguyên.
- Webcam trình duyệt có chọn thiết bị/hướng camera, lỗi quyền/không có thiết bị/thiết bị bận rõ ràng, timeout gửi frame 8 giây.
- `start-local.ps1` bật worker mặc định và tránh khởi động lại worker/web đang chạy. `-WithWorker:$false` giữ lựa chọn chạy không có worker.
- `run-web.ps1 -PublicOrigin ...` hỗ trợ khai báo reverse proxy HTTPS có sẵn; không tự tạo public tunnel.

## Bằng chứng đã thực hiện

| Hạng mục | Trạng thái | Kết quả và phạm vi |
|---|---|---|
| API thực tế | TESTED | Đã nạp lại API; `/health` trả 200 với `database: ready`, `object_storage: ready` |
| Worker config | TESTED | Các endpoint active camera, assigned/pending model chuyển từ 500 sang 200 |
| Mất kết nối PostgreSQL | TESTED | Chủ động đóng một backend session kiểm thử riêng bằng `pg_terminate_backend`; truy vấn mất kết nối báo lỗi; thao tác kế tiếp kết nối lại và SELECT thành công. Không dừng database hay phiên của người dùng |
| Webcam phần cứng | PARTIALLY_TESTED | Windows nhận HD Webcam; OpenCV mở device 0 và đọc được frame 640×480; giải phóng ngay, không lưu ảnh. Chưa xác nhận toàn pipeline model trên nguồn vật lý này |
| Webcam trình duyệt | TESTED — luồng truyền hình | Edge headless dùng camera tổng hợp → đăng nhập app kiểm thử → getUserMedia → JPEG upload → FastAPI BrowserStreamStore thật → endpoint recognition trả preview → dừng stream. Tài nguyên kiểm thử nằm riêng dưới `.runtime`; inference dùng stub no-face |
| DroidCam | PARTIALLY_TESTED | Backend thật đọc MJPEG qua một HTTP server kiểm thử trên localhost, giải mã RGB đúng kích thước. Kiểm thử phân mảnh, lỗi HTTP và nguồn worker có trong pytest. Chưa có URL DroidCam điện thoại của người dùng để kiểm tra Wi-Fi thực |
| HTTPS proxy | TESTED — local harness | Vite thật trên port kiểm thử chuyển localhost sang upstream với HTTP, chuyển origin HTTPS được cấu hình đúng host/scheme, không tin scheme do request không tin cậy cung cấp. Chưa kiểm tra lại tunnel công khai trên điện thoại |
| Python lint/types | TESTED | Ruff toàn repository và mypy 101 file nguồn không báo lỗi |
| Kiểm thử tự động | TESTED | Pytest: 365 passed, 23 skipped theo điều kiện môi trường; Vitest: 69 passed; production build/typecheck web thành công |
| PowerShell | PARTIALLY_TESTED | Parser kiểm tra cú pháp hai script đã sửa. Không khởi động thêm toàn stack khi các dịch vụ thật đang chạy |

Các probe không đổi nguồn camera đang lưu và không thay mật khẩu/tài khoản của người dùng. Không dùng các kết quả truyền hình này để khẳng định độ chính xác nhận diện, FPS hoặc khả năng chạy GPU.

## Sử dụng

1. Mở web tại `http://127.0.0.1:5173` và đăng nhập.
2. Với nguồn Webcam trình duyệt, vào Giám sát, chọn camera, bấm **Bắt đầu realtime** và cho phép thiết bị. Camera điện thoại cần HTTPS; IP LAN qua HTTP không có quyền getUserMedia.
3. Với webcam trên máy worker, chọn đúng device index, bật/áp dụng cấu hình và để worker chạy.
4. Với DroidCam, dùng URL `/video` đang hiển thị trên điện thoại; worker phải truy cập được URL đó.

Những phần cần thiết bị/địa chỉ thật nhưng chưa có bằng chứng ở bảng trên vẫn chưa được xác nhận. Đây là kiểm chứng sửa lỗi local, không phải kết luận sẵn sàng production.
