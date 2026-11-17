# Kết quả đợt thử clone 10 giọng tiếng Việt

Ngày chạy: 2026-11-17. Runtime Google Colab GPU Tesla T4. Notebook Drive: https://colab.research.google.com/drive/1Uf6UQxZ504cmVLppzpmqjOf_qpimqwDj

## Kết quả thực tế

- Đã tải và kiểm tra 10 preview từ danh sách ưu tiên tiếng Việt.
- 10/10 giọng tạo được đầu ra, mỗi giọng một reference × hai văn bản × hai seed = **40 WAV**.
- Chỉ tìm được một cửa sổ reference không chồng lấn phù hợp ở mỗi preview; chưa thử hai reference cho mỗi giọng như phương án tối đa 80 lượt.
- 40/40 file WAV đọc được, mono, 24.000 Hz, PCM 16-bit; thời lượng đầu ra từ **5,62 đến 10,08 giây**.
- Whisper kiểm tra đủ 40 file: **15 file WER = 0**, WER từng file **0–8%**, tổng cộng **28 sai khác trên 980 token**, WER gộp **2,86%**.
- Quyền clone ngoài ElevenLabs chưa được xác minh; kết quả chỉ ở trạng thái thử nghiệm kỹ thuật. Audio chưa đưa lên GitHub và chưa được thêm vào danh sách giọng phát hành trong app.

## Cấu hình và khả năng tái lập

- Package `omnivoice==0.2.1`; model `k2-fsa/OmniVoice`.
- `num_step=32`, `guidance_scale=1.8`, `speed=1.0`, `class_temperature=0.2`, `position_temperature=5.0`, denoise/preprocess/postprocess bật; seed **42**, **123**.
- Whisper chọn mốc segment để lấy reference 3–10 giây. Mốc segment không bảo đảm là câu hoàn chỉnh trong mọi trường hợp; transcript/mốc cắt vẫn cần nghe kiểm tra.
- SHA256 preview và khoảng cắt được lưu trong metadata/báo cáo. **Revision model không lấy được (`null`)**, vì vậy đợt này chưa đủ thông tin để cam kết tái lập chính xác weights ở lần chạy sau.
- Rerun dùng lại WAV đã có; thời gian xử lý trong báo cáo tải xuống có thể là thời gian đọc cache, không dùng làm benchmark tốc độ tổng hợp.

## Kết quả ASR theo giọng

Mỗi giọng có 4 đầu ra và 98 token kỳ vọng. WER tiếng Việt ở đây tính theo token tách bằng khoảng trắng, Unicode NFC, không phân biệt hoa thường và bỏ dấu câu; không phải phép tách từ tiếng Việt theo nghĩa ngôn ngữ học.

| Giọng | WAV | WER gộp |
|---|---:|---:|
| Tuan Anh — Deep & Powerful Vietnamese | 4 | 3,06% |
| Mai Anh — Vietnamese News Anchor | 4 | 3,06% |
| Thieuthattha — Casual | 4 | 3,06% |
| Quang Toan — Deep Vietnamese Storyteller | 4 | 3,06% |
| Ba Luc — Warm, Clear, Storytelling | 4 | 2,04% |
| Thảo — Soft, Calm and Gentle | 4 | 3,06% |
| Giang — Podcast | 4 | 3,06% |
| Trieu Duong — Deep, Calm and Resonant | 4 | 2,04% |
| Hạ Vi — Calm & Trustworthy | 4 | 3,06% |
| Gia Huy — Southern TV Host | 4 | 3,06% |

Không dùng bảng này làm bảng xếp hạng độ giống giọng. Sai khác phổ biến là Whisper nhận `dao động` thành `giao động`; không thể chỉ từ transcript kết luận người đọc đã phát âm sai. Một đầu ra của Hạ Vi có thêm từ `Vâng` trong transcript ASR; cần nghe để xác nhận có thêm lời thật hay lỗi nhận dạng.

## Nghe đối chiếu và vị trí file

Trên máy làm việc:

- `pilot/results/listen.html`: trang nghe preview, reference và bốn đầu ra cho từng giọng, kèm transcript ASR.
- `pilot/clone-pilot-reviewed.zip`: gói audio và báo cáo đã tải từ Colab.
- `pilot/report.json`: manifest đầu ra, reference, cấu hình.
- `pilot/asr-evaluation.json`: transcript kỳ vọng, transcript nhận dạng và sai khác từng file.
- `pilot/audio-validation.json`: kiểm tra định dạng và thời lượng WAV.

Audio và trang nghe chứa liên kết audio cục bộ được giữ ngoài Git. Mã tạo trang nghe và báo cáo JSON có trong repo. Trang `listen.html` chỉ hoạt động đầy đủ khi nằm cạnh các thư mục `voice-01` đến `voice-10`.

## Việc chưa hoàn tất

- Chưa nghe và chấm độ giống màu giọng, sự tự nhiên, accent hoặc ổn định giữa seed.
- Chưa có kiểm tra speaker embedding similarity.
- Chưa xác minh thủ công transcript reference và tất cả ranh giới cắt.
- Chưa thử nội dung dài, số, tên riêng hoặc từ tiếng Anh.
- Chưa xác minh quyền external cloning/phân phối audio.

Do đó, chưa chọn một giọng là “tốt nhất” và chưa tự nâng giọng nào thành `ready`. Bước tiếp theo là nghe đối chiếu, ghi nhận quyền dùng và chọn reference tốt hơn cho các giọng cần sửa.
