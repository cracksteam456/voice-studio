# Kế hoạch clone và đánh giá giọng cho Voice Studio

## Mục tiêu

Từ catalog 2.274 giọng đã kiểm kê, xây thư viện mẫu được phép dùng với OmniVoice, ưu tiên tiếng Việt và giọng dùng cho thuyết minh video. Catalog chứa thông tin và liên kết preview; chưa phải bộ audio đã được nghe hoặc bộ giọng được cấp quyền clone.

## Trạng thái ban đầu

- Snapshot: `20261117T103929553845Z`.
- 1.000 kết quả cho mỗi query Trending toàn cầu, usage toàn cầu và Trending có preview tiếng Việt; hợp lại còn 2.274 ID duy nhất.
- 361 bản ghi trong nhóm tiếng Việt có tiếng Việt là ngôn ngữ chính.
- Có 3 shortlist, mỗi nhóm 50 bản ghi; giữa các nhóm có trùng nhau.
- Chưa tải audio danh mục, chưa xác minh quyền clone, chưa đánh giá chất lượng các giọng catalog.

## Các bước và điều kiện hoàn thành

| Bước | Việc thực hiện | Kết quả có thể kiểm tra |
|---|---|---|
| 1. Chốt ứng viên | Hợp 3 shortlist; giữ riêng nhãn ngôn ngữ chính, preview tiếng Việt và thứ hạng | Danh sách ưu tiên, không trùng owner/voice ID |
| 2. Xác định nguồn mẫu | Xác nhận quyền external voice cloning và mục đích sử dụng cho từng mẫu; ưu tiên bản ghi gốc được người nói cấp quyền | `permission_evidence`, người cấp quyền, phạm vi và ngày xác nhận |
| 3. Chuẩn bị audio | Chỉ xử lý mẫu đủ quyền; giữ bản gốc, chọn câu hoàn chỉnh 3–10 giây, WAV mono theo sample rate model | `reference.wav`, `reference.txt`, SHA256, thời gian cắt, thông số audio |
| 4. Thử 10 giọng | Mỗi giọng 2 reference × 2 đoạn đầu ra × 2 seed = 80 lần tổng hợp | File WAV, cấu hình, thời gian tạo và phiếu nghe |
| 5. Chọn mẫu tốt | So sánh độ giống, độ rõ lời, accent, ngữ điệu, lỗi lặp/bỏ từ | Bảng điểm và lý do chọn/loại, không chỉ dựa độ hot |
| 6. Mở rộng | Chạy theo đợt 25 giọng đã đủ điều kiện; kiểm tra lỗi trước đợt tiếp theo | Báo cáo số đạt, lỗi, chi phí/thời gian thực tế |
| 7. Tích hợp | Chỉ thêm mẫu đạt chuẩn vào bộ chọn Voice Studio, hiển thị nguồn và ngôn ngữ | Giọng chọn được, nghe mẫu được, tái sử dụng prompt |

Không chạy các bước 3–7 cho mẫu chưa rõ quyền. Chỉ có URL preview hoặc gói trả phí không tự chứng minh quyền clone ngoài ElevenLabs; xem `elevenlabs-library-findings.md`. Không dùng nhiều tài khoản để vượt hạn mức.

## Tiêu chí mẫu và câu thử

Khuyến nghị chính thức OmniVoice: reference 3–10 giây, cùng ngôn ngữ đầu ra và transcript đúng audio. Repo không đưa ra một câu tốt nhất được kiểm chứng. Xem `omnivoice-reference-findings.md`.

Với bản ghi mới được phép thu, câu đề xuất ban đầu:

> Buổi sáng, nắng nhẹ qua cửa sổ. Tôi mở trang sách, lắng nghe câu chuyện và bắt đầu một ngày mới.

Đo thời lượng rồi chọn câu hoàn chỉnh trong khoảng 3–10 giây. Không gán câu này vào transcript của preview nói câu khác. Không đổi pitch hoặc tốc độ reference để ép đủ thời lượng.

Hai đoạn đầu ra cố định để đánh giá tiếng Việt:

1. `Hôm nay, chúng ta tìm hiểu cách âm thanh truyền qua không khí. Mỗi dao động nhỏ đều có thể mang theo một thông điệp.`
2. `Nếu Mặt Trăng biến mất, điều gì sẽ xảy ra với thủy triều? Hãy cùng xem những thay đổi đầu tiên trên Trái Đất.`

Ghi riêng khả năng đọc số, tên riêng và từ tiếng Anh bằng bài kiểm tra bổ sung; không sửa bài rồi so điểm như cùng một bài.

## Cấu hình thí điểm

- Model: `k2-fsa/OmniVoice`, package `omnivoice==0.2.1` như notebook đang dùng; ghi revision model thực tải khi chạy.
- Bắt đầu `num_step=32`, `guidance_scale=1.8`, `speed=1.0`, hai seed 42 và 123.
- Giữ cùng thiết lập khi so reference; chỉ điều chỉnh một yếu tố mỗi lần.
- Lưu prompt cùng SHA256 reference, transcript, phiên bản package và revision model. Đổi reference/transcript phải tạo prompt mới.
- GPU: dùng phiên Colab T4 hiện có; tốc độ thực tế phụ thuộc độ dài đoạn, không suy từ lần thử ngắn ra tốc độ cả thư viện.

## Phiếu đánh giá

Đánh giá riêng từng mục 1–5: độ giống màu giọng, độ rõ lời, ngữ điệu, độ ổn định giữa hai seed. Ghi accent và mọi lỗi bỏ/lặp từ. Hai người nghe độc lập nếu có thể; điểm nghe là đánh giá chủ quan, không phải benchmark được chuẩn hóa.

Tiêu chí đề xuất để đưa vào app: không có lỗi bỏ/lặp từ nghiêm trọng trong bài thử; độ rõ lời ít nhất 4/5; không cắt đầu/cuối từ; reference đúng transcript và quyền sử dụng đã được ghi nhận. Điểm giống giọng thấp thì giữ trạng thái cần xem xét dù phát âm rõ. Các ngưỡng này do dự án đặt, chưa được thực nghiệm hiệu chỉnh.

Nếu dùng WER/CER và speaker similarity thì ghi ASR/embedding model, phiên bản, cách chuẩn hóa chữ và cùng tập kiểm tra. Không coi điểm cao từ duy nhất một bộ nhận dạng là đủ.

## Lưu trữ và GitHub

- Repo GitHub ban đầu để **private**, chứa source, notebook không có output, tài liệu, catalog metadata, shortlist, báo cáo độ phủ và hàng đợi đánh giá.
- Không đưa API key, cookie, token, `.env`, cache, prompt `.pt`, model weights hoặc âm thanh chưa xác minh quyền vào Git.
- Audio và model chỉ đưa vào kho lưu trữ phù hợp khi đã rõ quyền phân phối; không mặc định quyền clone riêng tư cho phép công khai mẫu.
- Catalog là snapshot thời điểm lấy; preview có thể đổi hoặc hết hiệu lực. Không khẳng định sở hữu giọng hoặc bảo đảm URL luôn hoạt động.

## Việc cần từ người dùng trước khi chạy audio

1. Căn cứ quyền dùng audio ElevenLabs với OmniVoice, hoặc bộ giọng/bản ghi riêng được cấp quyền clone bên ngoài.
2. Nếu cần tạo mẫu mới có usage tính phí: xác nhận model và ngân sách trước tác vụ tạo.

Chưa cần thêm key cho việc lưu catalog đã lấy lên repo. Các key đã gửi trong hội thoại nên thu hồi và thay mới; repo không lưu chúng.
