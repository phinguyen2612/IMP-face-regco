# Kế hoạch giao diện sản phẩm — 04/11/2026

Trạng thái: phương án thiết kế và kế hoạch triển khai, chưa thay giao diện ứng dụng.
Phác thảo đi kèm: [Bảng định hướng đồ họa](./2026-11-04-product-ui-board.html).

## 1. Mục tiêu và căn cứ

Thiết kế một sản phẩm quản lý camera, nhận diện và điểm danh cho trường học, đủ rõ để người vận hành thực hiện công việc thường ngày. Ba câu hỏi chính: camera nào cần chú ý, sự kiện gì đã xảy ra, cần làm gì tiếp theo?

Kế hoạch này cập nhật bản `docs/superpowers/plans/2026-11-02-product-ui-redesign.md` theo mã nguồn ngày 04/11. Không coi các vấn đề trong bản cũ là vẫn còn tồn tại khi chưa kiểm chứng lại.

Đã có: phân quyền ADMIN/TEACHER/STUDENT; giám sát và Livewall; chuông thông báo; liên kết tới sự kiện theo ID; trang evidence người lạ; bộ lọc camera/ngày; xuất CSV trang hiện tại; theme sáng/tối. Những luồng này là nền tảng của thiết kế mới.

Phát hiện từ mã nguồn: các trang vẫn có nhiều cách dựng form, nút, danh sách và thông báo khác nhau; CSS có lớp nền và lớp ghi đè; một số màn quản lý đặt form tạo mới ngay cạnh danh sách; nội dung kỹ thuật còn xuất hiện trong các luồng thường dùng. Cần kiểm tra bằng ảnh chụp trước khi kết luận về lỗi hiển thị cụ thể.

Chưa thực hiện audit trực quan trong lượt lập kế hoạch này. Bảng HTML là phác thảo với dữ liệu minh họa, không phải ảnh chụp sản phẩm hoặc kết quả nhận diện thực tế.

## 2. Người dùng và tác vụ chính

| Vai trò hiện có | Công việc | Điểm vào ưu tiên |
|---|---|---|
| ADMIN — vận hành | Theo dõi camera, mở thông báo, kiểm tra evidence | Giám sát / Livewall |
| ADMIN — cấu hình | Thêm camera, chỉnh ROI, áp dụng cấu hình, kiểm tra model | Camera / Thiết lập |
| TEACHER | Mở lớp, tạo buổi, xem điểm danh, duyệt ảnh | Lớp của tôi |
| STUDENT | Đăng ký ảnh, xem trạng thái duyệt và điểm danh cá nhân | Hồ sơ của tôi |

Không thêm vai trò mới trong đợt đồ họa. Menu và thao tác phải tuân theo quyền API hiện có.

## 3. Định hướng đồ họa

**Hướng chọn: bàn điều hành trường học — bình tĩnh, chính xác, dễ quan sát lâu.**

- Ngữ cảnh: cổng trường, hành lang, phòng học, ca giám sát, vùng ROI, hồ sơ sinh viên, ảnh minh chứng, buổi điểm danh.
- Thế giới màu: trắng giấy, xám thiết bị, than màn hình video, cam nhận diện FPT, xanh trạng thái đã xác minh, hổ phách cần chú ý, đỏ lỗi.
- Dấu hiệu nhận diện riêng: cụm **Camera → thời điểm → trạng thái → ảnh minh chứng** xuất hiện nhất quán ở ô camera, chuông, dòng evidence, chi tiết sự kiện và lịch sử.
- Bố cục theo nhiệm vụ: video lớn ở giám sát; ảnh và dòng thời gian ở evidence; bảng ở danh mục; form có nhóm ở cấu hình.
- Một hành động chính trong mỗi vùng thao tác. Các thông số chẩn đoán đặt trong phần mở rộng.

| Thành phần | Đặc tả đề xuất | Lý do |
|---|---|---|
| Nền trang | `#F5F6F8` | Phân tách vùng làm việc mà không làm nặng màn hình |
| Bề mặt | `#FFFFFF`; đường chia `#E2E6EC` | Nhóm thông tin bằng khoảng cách và viền nhẹ |
| Chữ | Chính `#202B3B`; phụ `#596679` | Đọc tốt thông tin tiếng Việt và bảng dữ liệu |
| Hành động chính | Cam trầm `#A8440C`, chữ trắng | Tiếp nối màu hiện có; kiểm tra tương phản trước khi chốt |
| Vùng camera | Than `#13181F` | Khung hình và overlay giữ vai trò trung tâm |
| Trạng thái | Xanh `#16734A`, vàng nâu `#8A4C00`, đỏ `#B42336` | Luôn có nhãn chữ; không chỉ phân biệt bằng màu |
| Chữ | Đề xuất Be Vietnam Pro; fallback Segoe UI, sans-serif | Cần thử trực tiếp dấu tiếng Việt, tên dài và số liệu; chỉ tự lưu font sau khi kiểm tra giấy phép |
| Cỡ chữ | Tiêu đề trang 28; phần 20; nội dung 15–16; dữ liệu bảng 14; metadata 13 px | Tạo thứ bậc rõ, giữ mật độ vừa phải |
| Kích thước | Sidebar 240 px; topbar 64 px; lề nội dung 24–32 px | Dành diện tích cho video và dữ liệu |
| Nhịp khoảng cách | 4 / 8 / 12 / 16 / 24 / 32 px | Cùng một nhịp cho toàn bộ sản phẩm |
| Bo góc | Control 6; panel 10; dialog 14 px | Gọn, nhất quán với hình thức công cụ vận hành |
| Độ nổi | Viền mảnh; bóng nhẹ chỉ cho popover/dialog | Tập trung vào nội dung; giữ nền làm việc ổn định |
| Chuyển động | 120–200 ms cho phản hồi; 180–240 ms cho panel | Không làm chậm thao tác; không animate video/overlay |

Đồ họa cần sản xuất: bộ icon SVG thống nhất nét 1.75–2 px; mẫu ảnh camera và evidence; sơ đồ hướng dẫn chụp ảnh đăng ký bằng SVG; biểu tượng trạng thái rỗng/lỗi; biến thể sáng/tối. Giữ nguyên logo FPT và tỉ lệ ảnh. Không đưa ảnh người giả thành bằng chứng thật.

## 4. Cấu trúc điều hướng

ADMIN:
- Vận hành: Tổng quan; Giám sát (một camera / Livewall); Evidence người lạ; Lịch sử & điểm danh.
- Quản lý: Camera; Hồ sơ khuôn mặt; Lớp học; Tài khoản.
- Thiết lập: Mô hình nhận diện; Trạng thái hệ thống.

TEACHER: Lớp của tôi; Duyệt ảnh. STUDENT: Hồ sơ; Đăng ký khuôn mặt; Điểm danh; Lịch sử cá nhân.

Topbar: vị trí đang xem, chuông, theme, menu tài khoản. Trạng thái kết nối ngắn gọn và tách khỏi sức khỏe camera. Chuyển chức năng ít dùng vào menu tài khoản để thanh trên không chật.

Chuông giữ luồng đã làm: bấm một sự kiện → URL có ID → đúng bản ghi → ảnh/trạng thái evidence. Chỉ đánh dấu đã đọc sau thao tác tương ứng. Trạng thái đã đọc hiện chỉ lưu trên trình duyệt theo tài khoản; không đặt tên là “đã xử lý”.

## 5. Thiết kế từng màn

| Màn hình | Bố cục và hành động chính | Điểm cần nghiệm thu |
|---|---|---|
| Tổng quan | Tóm tắt camera, lối vào giám sát và các tình huống cần chú ý | Chỉ hiển thị số tổng có API hoặc phép tính đầy đủ, đúng ngữ nghĩa; không lấy 50 sự kiện gần nhất làm tổng toàn hệ thống |
| Giám sát | Thanh chọn camera gọn; video chiếm phần lớn màn; dải trạng thái dưới video; chẩn đoán mở rộng | Không biến trang thành form cài đặt; hình và bbox khớp frame; thông báo nằm ở chuông |
| Livewall | Chọn 2/3 cột; mỗi tile có tên, trạng thái, hình, mở lớn; toàn màn hình | Camera dọc/ngang không bị cắt sai; ô offline không giả làm đang phát |
| Evidence người lạ | Bộ lọc một hàng; danh sách ảnh có thời điểm/camera/trạng thái; chọn mở chi tiết | Chỉ UNKNOWN_ALERT; hỗ trợ ảnh đang lưu/lỗi/hết hạn; xuất CSV trang hiện tại phải ghi rõ phạm vi |
| Chi tiết sự kiện | Ảnh lớn bên trái; thông tin và trạng thái bên phải; nút trở lại | Mở đúng ID từ chuông, reload/Back vẫn đúng; sự kiện không còn có thông báo rõ |
| Camera | Danh mục dễ quét; form thêm riêng; cấu hình nhóm Nguồn hình / ROI / Chính sách | Phân biệt đang chạy, đã lưu, chờ áp dụng; không hứa lưu nháp không gián đoạn nếu backend chưa hỗ trợ |
| Hồ sơ khuôn mặt | Bảng người; chi tiết hồ sơ và gallery ảnh; đăng ký có hướng dẫn từng bước | Phân biệt ảnh đăng ký và evidence; lỗi từng ảnh không xóa toàn bộ dữ liệu nhập |
| Điểm danh | Lớp/buổi/ngày là bộ lọc đầu tiên; bảng kết quả; xuất báo cáo | Không trộn buổi học và sổ nhận diện theo ngày; đúng phạm vi quyền |
| Mô hình / hệ thống | Phần đang dùng rõ nhất; bản tải lên và chẩn đoán ở phần phụ | Tên model, khả năng CPU/GPU và revision theo dữ liệu runtime thực |
| Giáo viên / sinh viên | Mỗi trang dẫn bằng việc cần làm; hướng dẫn ngắn tại chỗ | Không đưa bảng điều khiển vận hành của ADMIN sang các vai trò này |

Màn evidence ưu tiên bố cục danh sách–chi tiết ở desktop. URL vẫn giữ ID khi mở panel; mobile chuyển thành trang chi tiết toàn chiều rộng. Mở ảnh gốc là hành động riêng, không thay cho màn chi tiết có ngữ cảnh.

## 6. Hệ component dùng chung

Đợt đầu: AppShell, PageHeader, Button, IconButton, Field, StatusBadge, FilterBar, DataTable, Pagination, EmptyState, ErrorState, LoadingState, Dialog, NotificationPanel.

Sau đó: CameraTile, CameraStatusStrip, EventRow, EvidencePreview, EventDetails, PersonSummary, ConfigurationSection. Chỉ trích component khi có tái sử dụng thực tế.

Mỗi component có: kích thước, khoảng cách, chữ, icon, trạng thái hover/focus/pressed/disabled/loading, hành vi bàn phím, sáng/tối và mobile. Control tiêu chuẩn dùng semantic HTML; hành vi overlay phức tạp đánh giá primitive có sẵn trước khi tự viết.

Không tiếp tục thêm lớp ghi đè vào cuối CSS. Chuyển từng cụm đã nghiệm thu sang token và style sở hữu bởi component; gỡ quy tắc cũ tương ứng khi không còn nơi dùng.

## 7. Trạng thái phải thiết kế trước khi code

| Tài nguyên | Trạng thái cần có |
|---|---|
| Danh sách | Đang tải; có dữ liệu; chưa có dữ liệu; không khớp bộ lọc; lỗi; dữ liệu cũ |
| Camera | Tắt; chưa áp dụng; chờ hình; có hình; mất kết nối; dữ liệu cũ |
| Nhận diện | Đang xác minh; đã xác minh; chưa xác định chắc chắn; người lạ theo backend |
| Evidence | PENDING; READY; FAILED; EXPIRED; không tìm thấy sự kiện |
| Form | Chưa sửa; có thay đổi; đang lưu; lỗi field; lỗi API; xung đột revision |
| Quyền | Có quyền; không có quyền; phiên hết hạn |

Mỗi trạng thái phải trả lời được: chuyện gì xảy ra, dữ liệu còn đáng tin đến đâu, người dùng có thể làm gì. Không thêm nút “thử lưu evidence lại”, “xử lý xong” hoặc “khôi phục” khi API chưa hỗ trợ.

## 8. Các đợt thực hiện và đầu ra

Ước lượng cho một người thiết kế kiêm triển khai, API hiện có ổn định: **12–18 ngày làm việc**; đây là ước lượng để chia việc, không phải lịch cam kết. Nâng cấp API ngoài phạm vi được ước lượng riêng.

| Đợt | Thời gian | Đầu ra cụ thể | Điều kiện xong |
|---|---|---|---|
| 1. Audit và sơ đồ luồng | 1–2 ngày | Ảnh hiện trạng ở 1366/1920/390 px; sitemap; 5 luồng tác vụ; danh sách vấn đề có bằng chứng | Chốt phạm vi đợt đầu và dữ liệu API dùng được |
| 2. Đồ họa và prototype | 2–3 ngày | Bảng màu/chữ/icon; component sheet; mockup Giám sát, chuông, Evidence, chi tiết sự kiện; trạng thái lỗi/rỗng; mobile | Nhìn được hướng thiết kế và đi qua được luồng chuông → sự kiện |
| 3. Khung và luồng vận hành | 3–4 ngày | Token, AppShell, component nền; Giám sát/Livewall; thông báo/evidence/chi tiết nối dữ liệu thật | Không mất deep link, quyền, cập nhật trạng thái và ảnh |
| 4. Nghiệp vụ và cấu hình | 4–6 ngày | Camera, hồ sơ, lớp/tài khoản, điểm danh, giáo viên/sinh viên, model/hệ thống | Mỗi vai trò hoàn thành tác vụ chính; form và thông báo thống nhất |
| 5. Hoàn thiện và nghiệm thu | 2–3 ngày | Responsive, sáng/tối, bàn phím, lỗi mạng; ảnh nghiệm thu; test và build | Đạt các tiêu chí bên dưới; ghi rõ những kiểm tra chưa làm được |

Phạm vi triển khai đầu tiên nên là **khung ứng dụng + Giám sát + chuông + Evidence + chi tiết sự kiện**. Dùng cụm này để xác lập tiêu chuẩn, sau đó áp dụng cho các màn còn lại.

## 9. Tổ chức mã nguồn và phụ thuộc

- Giữ React/Vite và lớp API hiện tại. Tách JSX lớn khi thay đúng màn, không viết lại toàn ứng dụng cùng lúc.
- Tách style thành nền/token, bố cục, component, đặc thù từng feature; giữ ThemeProvider hiện tại.
- Chuẩn hóa route có tham số sự kiện/bộ lọc. Quyền được kiểm tra trước khi tải dữ liệu màn chi tiết.
- Lưu filter và vị trí danh sách khi mở/đóng chi tiết để người vận hành tiếp tục việc đang làm.
- Request có hủy khi rời trang; polling không nhân đôi; danh sách thông báo có giới hạn.
- Hợp đồng đã có cần giữ: `event_id`, camera/ngày/kind, phân trang, trạng thái evidence, phân quyền.
- Phần mở rộng cần backend riêng: đồng bộ đã đọc nhiều thiết bị; giao xử lý/ghi chú/đóng cảnh báo; xuất toàn bộ kết quả lọc; tổng quan aggregate; lịch sử audit thao tác. Không dựng số liệu hay trạng thái thay thế trên frontend.

## 10. Tiêu chí nghiệm thu

- Nhấn thông báo mở đúng sự kiện trong một thao tác; refresh và Back/Forward giữ đúng ngữ cảnh.
- Camera cần xem tiếp cận trong tối đa ba thao tác; video là vùng chính của màn giám sát.
- Cảnh báo người lạ, ảnh khuôn mặt mới và điểm danh có nhãn khác nhau, không dùng chung một trạng thái.
- Mỗi evidence có camera, thời điểm theo giờ Việt Nam và trạng thái ảnh; ảnh lỗi không làm mất bản ghi sự kiện.
- Không cuộn ngang toàn trang ở 360/390/768/1366/1920 px; bảng rộng có vùng cuộn riêng.
- Tên tiếng Việt dài, camera dọc, nhiều khuôn mặt, dữ liệu rỗng và lỗi mạng đều có mẫu nghiệm thu.
- Focus rõ, điều hướng bàn phím, Escape/hoàn trả focus, tương phản mục tiêu AA, reduced motion.
- Không có thao tác giả; không coi đã đọc trên trình duyệt là đã xử lý nghiệp vụ.
- Test các luồng đã sửa; typecheck/build; test backend khi thay hợp đồng; kiểm tra trực quan trình duyệt cho cả hai theme.
- Hiệu năng video/polling được so với hiện trạng; không tuyên bố tăng FPS do thay đồ họa.

## 11. Bộ bàn giao đồ họa

1. Bảng định hướng màu/chữ/chất liệu và bố cục.
2. Sitemap và luồng click chính của ba vai trò.
3. Mockup desktop/mobile cho cụm vận hành; mẫu sáng/tối.
4. Component sheet và state matrix.
5. Danh sách icon, asset và quy tắc dùng logo/ảnh.
6. Checklist nghiệm thu có ảnh trước–sau và giới hạn còn lại.

Bảng HTML đi kèm hiện chỉ là bước 1 và phác thảo bố cục cho bước 3. Khi chọn triển khai, các quyết định đã thống nhất sẽ được ghi thành hệ thiết kế dùng chung cho các đợt sau.
