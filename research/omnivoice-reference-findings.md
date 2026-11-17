# Khuyến nghị chọn mẫu cho OmniVoice

Ngày kiểm tra: 2026-11-17. Đây là nghiên cứu tài liệu và mã nguồn, chưa phải phép đo chất lượng clone.

## Nguồn chính thức đã kiểm tra

Repo `k2-fsa/OmniVoice`, nhánh mặc định `master`, commit `08be0b4ccbac3e13e374e86fbfead4b4cac343e2`.

Đã kiểm tra thêm [README bản 0.2.1](https://github.com/k2-fsa/OmniVoice/blob/0.2.1/README.md#voice-cloning) và [mã nguồn bản 0.2.1](https://github.com/k2-fsa/OmniVoice/blob/0.2.1/omnivoice/models/omnivoice.py), đúng bản đang khóa trong notebook: khuyến nghị 3–10 giây, cùng ngôn ngữ, lưu/tải prompt và cắt mẫu trên 20 giây cũng có ở bản này.

- [README — Voice Cloning](https://github.com/k2-fsa/OmniVoice/blob/08be0b4ccbac3e13e374e86fbfead4b4cac343e2/README.md#voice-cloning).
- [Tips & Notes](https://github.com/k2-fsa/OmniVoice/blob/08be0b4ccbac3e13e374e86fbfead4b4cac343e2/docs/tips.md).
- [Generation Parameters](https://github.com/k2-fsa/OmniVoice/blob/08be0b4ccbac3e13e374e86fbfead4b4cac343e2/docs/generation-parameters.md).
- [Mã nguồn create_voice_clone_prompt](https://github.com/k2-fsa/OmniVoice/blob/08be0b4ccbac3e13e374e86fbfead4b4cac343e2/omnivoice/models/omnivoice.py).
- [Evaluation](https://github.com/k2-fsa/OmniVoice/blob/08be0b4ccbac3e13e374e86fbfead4b4cac343e2/docs/evaluation.md).

## Kết luận được nguồn xác nhận

1. README khuyên dùng mẫu **3–10 giây**. Mẫu dài hơn có thể làm chậm và giảm chất lượng clone.
2. README khuyên mẫu **cùng ngôn ngữ** với giọng đầu ra để phát âm chuẩn hơn. Clone chéo ngôn ngữ có thể mang accent của mẫu.
3. `ref_text` là bản chép đúng nội dung mẫu âm thanh. Không phải mô tả chất giọng hay câu muốn tạo. Nếu bỏ trống, OmniVoice dùng Whisper để chép lại; có thể lưu `VoiceClonePrompt` để tái sử dụng, không phải nhận dạng lại mỗi lần.
4. Trong `create_voice_clone_prompt`, mặc định âm thanh được nạp về sample rate của model; mẫu nhiều kênh được chuyển mono trong nhánh đầu vào waveform. Hàm tiền xử lý loại khoảng lặng và thêm dấu câu cho transcript.
5. Khi mẫu dài hơn 20 giây và không truyền `ref_text`, mã nguồn có bước cắt ở khoảng lặng. Nếu đã truyền `ref_text`, bước cắt dài được bỏ qua để tránh làm lệch transcript; mẫu trên 20 giây vẫn có cảnh báo. Vì vậy nên tự chọn đoạn hoàn chỉnh 3–10 giây và chép đúng đoạn đó.
6. Trong README, tips và hướng dẫn inference đã kiểm tra **không thấy khuyến nghị một câu mẫu chuẩn/tối ưu duy nhất**. Ví dụ `Hello, this is a test of zero-shot voice cloning.` là `text` cần tổng hợp trong ví dụ API, không phải câu tham chiếu được chứng minh tốt nhất. `Nice to meet you.` trong code là fallback ước lượng thời lượng, không phải câu khuyên dùng để clone.
7. Tài liệu đánh giá của repo dùng WER/CER cho độ rõ lời và speaker embedding similarity cho độ giống giọng. Đây là hai khía cạnh riêng; giống màu giọng không đảm bảo phát âm chính xác.

## Đề xuất vận hành của dự án (không phải quy chuẩn của OmniVoice)

- Giữ file gốc; tạo thêm bản WAV PCM 16-bit mono 24 kHz nếu model đang dùng 24 kHz. Chuyển MP3 sang WAV không khôi phục thông tin đã mất.
- Chọn một câu hoàn chỉnh, khoảng 6–10 giây; một người nói; ít nhạc, tiếng vọng và cắt xén. Không time-stretch, đổi pitch hay khử nhiễu mạnh trước lần thử đầu.
- Lưu transcript theo từng đoạn cắt, nguồn gốc, ngôn ngữ, mã giọng, thời điểm lấy và bằng chứng quyền dùng cho clone bên ngoài dịch vụ nguồn.
- Dùng mẫu A/B và cùng văn bản đầu ra/cấu hình để so sánh, thay vì mặc định mẫu dài hoặc nhiều âm tiết luôn tốt hơn.
- Nếu được quyền tạo mẫu mới, có thể thử câu do dự án đề xuất: **“Buổi sáng, nắng nhẹ qua cửa sổ. Tôi mở trang sách, lắng nghe câu chuyện và bắt đầu một ngày mới.”** Đo thời lượng thực tế; nếu quá 10 giây, chọn một câu hoàn chỉnh ngắn hơn. Không gọi câu này là “câu tối ưu của OmniVoice”.
- Với mẫu preview có sẵn, dùng đúng nội dung preview; không gán câu chuẩn vào `ref_text` nếu nó không có trong audio.

## Giới hạn

Tài liệu trên được kiểm tra ở commit nêu trên. Chưa so sánh thực nghiệm chất lượng các mẫu ElevenLabs. Phiên Voice Studio đang khóa OmniVoice 0.2.1; trước khi dùng các tính năng từ nhánh master cần xác nhận API tương ứng có trong bản cài.
