# Voice Studio

Giao diện tiếng Việt chạy trên Google Colab với OmniVoice: chọn giọng, nhập kịch bản, tạo và tải âm thanh cho video.

[Mở notebook trong Colab](https://colab.research.google.com/github/cracksteam456/voice-studio/blob/main/colab_nam-cong-nghe-ban-rieng.ipynb)

Repo hiện là private. Nếu Colab không truy cập được repo private, tải file `.ipynb` về rồi dùng **File → Upload notebook** trong Colab. Không cần công khai repo để sử dụng.

## Sử dụng

1. Chọn runtime GPU T4.
2. Chạy ô cài đặt, rồi **Runtime → Restart session**.
3. Chạy ô nạp model, sau đó ô giao diện.
4. Nhập nội dung, chọn giọng hoặc tải giọng mẫu riêng, rồi tạo WAV/MP3.

Giao diện có 7 lựa chọn mẫu từ upstream, nạp TXT, chỉnh tốc độ/khoảng nghỉ, 8 ngôn ngữ, chia văn bản dài, chất lượng/seed, tải WAV/MP3 và ZIP từng đoạn. Các giọng catalog ElevenLabs chưa được thêm vào bộ chọn clone.

Notebook chứa toàn bộ code giao diện nên không cần tải file `voice_studio.py` riêng. File Python đó là nguồn để sửa; chạy `python build_notebook.py` để cập nhật notebook. Model weights và audio không được lưu trong repo này.

## Kế hoạch clone

Đợt thử kỹ thuật đã chạy: **10 giọng, 40 WAV**, Whisper kiểm tra đủ 40 file. Xem [báo cáo đợt thử](research/pilot-results.md). Chưa chấm độ giống giọng bằng nghe và chưa xác minh quyền clone ngoài ElevenLabs. Audio thử nghiệm giữ cục bộ, không đưa vào GitHub.

[Notebook thử nghiệm](colab_clone_pilot.ipynb) gồm bước nạp model, tạo câu thử và kiểm tra transcript. Chạy `python prepare_clone_pilot.py` để chuẩn bị lại từ shortlist; tác vụ này tải 10 preview. Chạy `python build_pilot_review.py` sau khi tải/extract kết quả vào `pilot/results/` để tạo trang nghe so sánh cục bộ.

Đọc [kế hoạch thực thi](research/clone-execution-plan.md). Mục tiêu thí điểm 10 giọng có quyền clone, mỗi giọng hai reference × hai đoạn đầu ra × hai seed, rồi mở rộng theo đợt.

- [Chiến lược danh mục](research/voice-sample-strategy.md)
- [Khuyến nghị reference của OmniVoice](research/omnivoice-reference-findings.md)
- [Nghiên cứu API/quyền ElevenLabs](research/elevenlabs-library-findings.md)
- [Danh sách ưu tiên có link preview](voice-library/snapshots/20261117T103929553845Z/shortlists.md)
- [150 ứng viên và trạng thái xét mẫu clone](voice-library/snapshots/20261117T103929553845Z/clone-candidates.json)
- [Catalog metadata 2.274 giọng](voice-library/snapshots/20261117T103929553845Z/catalog.json)
- [Báo cáo độ phủ](voice-library/snapshots/20261117T103929553845Z/coverage-report.json)

Catalog chỉ chứa metadata và liên kết audio. Chưa nghe chấm chất lượng, tải audio catalog hay xác minh quyền clone ngoài ElevenLabs. Ngôn ngữ filter API có thể bao gồm giọng chính ngôn ngữ khác nhưng có preview tiếng Việt.

## Làm mới catalog

### Tải toàn bộ preview khả dụng

```text
python download_voice_library.py
```

Để tải ngay trong khi tiếp tục duyệt danh mục, chạy hai tiến trình: `python download_voice_library.py --catalog-only` (có API key) và `python download_voice_library.py --audio-only` (không cần key). Hai tiến trình dùng SQLite WAL, lưu tiến độ riêng trong `catalog-progress.json` và `summary.json`. Bộ tải ưu tiên preview đại diện của từng giọng trước các biến thể ngôn ngữ/model.

Cần `ELEVENLABS_API_KEY` trong môi trường để duyệt catalog chia sẻ. Công cụ duyệt `created_date` đến `has_more=false`, hợp metadata đã có, rồi tải preview chung và các preview ngôn ngữ/model. Không gọi TTS tạo audio mới. Phạm vi là danh mục chia sẻ API trả về tại thời điểm duyệt, không phải giọng riêng tư/toàn bộ nền tảng.

Dữ liệu cục bộ ở `voice-library/archive/`: `inventory.sqlite` nối ID giọng/ngôn ngữ/model với URL và checksum; `audio/` chứa file gốc; `summary.json` ghi tiến độ. Chạy lại tiếp tục các URL pending. Audio trùng checksum dùng chung file. Tác vụ dừng khi có 401/403/429 hoặc dung lượng trống dưới 10 GiB; không tự chuyển tài khoản hay vượt giới hạn. File lỗi được giữ trạng thái failed để xem riêng, không tự retry vô hạn.

Giữ thư mục archive ngoài Git. Tải được preview không xác nhận quyền clone/phân phối; trường quyền hiện vẫn là unknown. Công cụ chỉ kiểm tra dấu hiệu định dạng audio khi tải, không chạy benchmark hoặc tổng hợp thử.

Mở `collect-voices.cmd` trên Windows để nhập API key ẩn, hoặc đặt `ELEVENLABS_API_KEY` trong môi trường rồi chạy:

```text
python collect_elevenlabs_catalog.py --limit 1000
```

Công cụ chỉ gọi GET API Voice Library chính thức, lưu 3 danh sách và loại trùng. Không gọi TTS hoặc tải audio. Không ghi key vào file. Nếu thiếu quyền `voices_read`, chỉnh scope trong ElevenLabs. Không dùng nhiều tài khoản để vượt hạn mức.

## Kiểm tra

```text
python -m unittest test_voice_studio.py test_collect_catalog.py test_clone_pilot.py
```

Các test CPU kiểm tra chia đoạn, input tùy chọn, phân trang và xử lý key. Tạo giọng cần runtime Colab và GPU. Đã thử giọng Nam công nghệ, Minh Anh, tải reference riêng và xuất WAV/MP3/ZIP trong phiên Colab trước; chưa thử đủ 7 giọng hoặc mọi ngôn ngữ.

## Nguồn và quyền sử dụng

Giao diện ban đầu được phát triển từ notebook [doanquangkien/voice-notebooks](https://github.com/doanquangkien/voice-notebooks). Các lựa chọn giọng có sẵn vẫn tải mẫu từ upstream khi người dùng chọn. Không sao chép các file mẫu đó vào repo này; sự hiện diện công khai của mẫu không tự cấp quyền clone hoặc phân phối lại.

OmniVoice: [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice), package đang khóa 0.2.1. Giấy phép code/model, quyền giọng nói và điều khoản dịch vụ nguồn là các phạm vi riêng. Chưa gán giấy phép mở chung cho repo vì quyền của mọi tài sản upstream chưa được xác nhận.
