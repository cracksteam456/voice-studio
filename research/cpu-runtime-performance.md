# Kiểm tra chạy chậm trên Colab CPU

Ngày kiểm tra: 2026-11-17. Colab hiển thị `No backend with GPU available`; Python xác nhận `torch.cuda.is_available() == False`. Không có thay đổi nào trong app có thể cấp GPU thay cho Colab.

## Các phép đo thực tế

- Một yêu cầu trên giao diện hoàn tất trong 319,3 giây và xuất WAV 1,11 giây (mono 24 kHz PCM 16-bit). Không có log tách thời gian cho lần này nên chưa quy được bao nhiêu giây cho Whisper, prompt hay synthesis.
- Đo trực tiếp `Xin chào bạn.` với mẫu Tuấn Anh đã được cache: lấy prompt 0,0008 giây, tổng hợp 16 bước mất **198,25 giây**, đầu ra **0,97 giây**. Vì prompt đã có trong cache, nhận dạng mẫu không phải nút thắt của lần đo này.
- Thử `Test.` ở 8 bước: 1 thread 97,95 giây, 2 threads 89,76 giây, 4 threads 94,55 giây. Không cố định seed và thời lượng đầu ra thay đổi 0,65–0,68 giây, nên phép đo này chỉ mang tính thăm dò, không đủ để chọn thread tối ưu. Không giữ thay đổi cấu hình thread theo thử nghiệm này.

## Thay đổi ứng dụng

- Hiển thị thiết bị thực tế ngay trên giao diện; báo CPU có thể mất vài phút mỗi câu.
- CPU mặc định 16 bước, GPU mặc định 32; người dùng vẫn chọn được 16/32/64. Đây là mức mặc định ưu tiên tốc độ cho CPU, không cam kết chất lượng bằng 32 bước.
- Hiển thị tiến độ tải Whisper, mã hóa mẫu và tổng hợp; giữ cache prompt theo đường dẫn/mtime/transcript.
- Kết quả tách thời gian chuẩn bị mẫu và tạo giọng. Không hứa tăng tốc khi chỉ cải thiện báo trạng thái.

Chưa có phép đo tăng tốc trước/sau trên GPU vì Colab không cấp GPU trong phiên này. Muốn thời gian đáp ứng ngắn cần runtime GPU được cấp thực tế; chọn T4 trong cấu hình chưa đủ nếu Colab vẫn trả runtime CPU.
