# cracksteam456 Voice Studio

Phát triển và duy trì bởi **[cracksteam456](https://github.com/cracksteam456)** tại **[cracksteam456/voice-studio](https://github.com/cracksteam456/voice-studio)**. Đây là repo độc lập của cracksteam456.

Giao diện tiếng Việt chạy trên Google Colab với OmniVoice: chọn giọng, nhập kịch bản, tạo và tải âm thanh cho video.

## VietVoice Studio — giao diện ngay trong Colab

[Mở notebook VietVoice Studio](https://colab.research.google.com/github/cracksteam456/voice-studio/blob/main/VietVoice_Studio_Colab.ipynb).
Notebook có 3 ô mã, đã chạy mô hình thật trên T4; giao diện chọn giọng, văn bản, tốc độ,
khoảng nghỉ, nghe và tải WAV nằm ngay trong notebook, không cần liên kết Gradio.

**8 mẫu từ thư mục `samples/`:** Nam công nghệ, Minh Anh, Thanh niên tự tin, Nam trầm ấm,
Adam, Ngọc Huyền, Nhỏ Ngọt Ngào và Kiên. Các tệp gốc cùng SHA256 nằm trong
[samples/catalog.json](samples/catalog.json). **150 preview cũng đã tích hợp trong cùng giao diện**:
50 tiếng Việt, 50 thịnh hành toàn cầu, 50 được dùng nhiều toàn cầu — tổng cộng **158 mẫu**.
Chọn **Nhóm giọng** để lọc hoặc **Tất cả (158 giọng)** để xem toàn bộ.

Mỗi lần chạy ô 2, Colab tải gói `vietvoice-library-158.zip` từ release `vietvoice-library-158`
của chính repo này, kiểm tra SHA256 rồi đưa các giọng vào danh sách chọn. Không đọc đường dẫn
ổ E: của máy cá nhân và không tải mẫu từ repo của tác giả gốc.

Repo hiện **công khai**. Notebook VietVoice tải bộ mẫu trực tiếp từ GitHub Release,
không cần `GITHUB_TOKEN`, không cần đăng nhập GitHub hay tải mẫu từ máy lên.

Khi thay các mẫu: sửa tệp trong `samples/`, chạy lệnh dưới, commit/push các tệp rồi tải ZIP
lên cùng release (asset mới thay thế asset cũ). Colab nhận bộ mới khi chạy lại ô 2:

```text
python scripts/build_reference_pack.py samples samples vietvoice-library-158.zip --hot-voices outputs/hot-voices
gh release upload vietvoice-library-158 vietvoice-library-158.zip --clobber --repo cracksteam456/voice-studio
```

Khi sửa mã VietVoice, chạy `python scripts/build_notebook.py`. Kiểm tra bằng
`python -m unittest discover -s tests -v` (cần ipywidgets, numpy, soundfile và PyTorch).
Mẫu tham chiếu và giọng tạo ra giữ nguồn/quyền sử dụng riêng, xem ATTRIBUTION.md.

## Bộ 150 mẫu giọng hot

Đã lưu 150 preview đại diện trong [outputs/hot-voices](outputs/hot-voices), chia thành ba nhóm top 50: Trending toàn cầu, lượt sử dụng toàn cầu và tiếng Việt. [Catalog](outputs/hot-voices/catalog.json) giữ nguồn, ID, thứ hạng và trạng thái quyền sử dụng; [trang nghe](outputs/hot-voices/listen.html) dùng sau khi clone hoặc tải thư mục về máy. GitHub hiển thị mã HTML, không chạy trang nghe trực tiếp.

Gói ZIP tải sẵn nằm trong [GitHub Releases](https://github.com/cracksteam456/voice-studio/releases). Đây là snapshot preview gốc, không phải model giọng và chưa xác minh quyền clone/phân phối bên ngoài ElevenLabs. Repo được chuyển sang công khai theo yêu cầu; archive toàn bộ và audio thử clone vẫn bị loại khỏi Git.

[Mở notebook trong Colab](https://colab.research.google.com/github/cracksteam456/voice-studio/blob/main/colab_nam-cong-nghe-ban-rieng.ipynb)

Repo hiện công khai; mở trực tiếp các liên kết Colab phía trên. Bản VietVoice Studio mới tự tải đủ 158 mẫu; notebook Gradio cũ phía dưới tiếp tục sử dụng bộ 150 mẫu.

## Sử dụng

1. Chọn runtime GPU T4.
2. Chạy ô cài đặt, rồi **Runtime → Restart session**.
3. Chạy ô nạp model, sau đó ô giao diện.
4. Nạp bộ 150 mẫu từ GitHub Release hoặc ZIP trên máy, chọn giọng và tạo WAV/MP3.

Notebook kiểm tra thiết bị thực tế bằng PyTorch. Nếu Colab chỉ cấp CPU, model dùng float32 và vẫn có thể tổng hợp, nhưng chậm hơn T4. Whisper được tải khi cần chép giọng mẫu; điền đúng lời trong mẫu để tránh tải ASR. Sau khi ô cài đặt thay NumPy/SciPy, cần Restart session một lần trước khi nạp model.

Giao diện hiện thiết bị và thời gian từng giai đoạn; CPU mặc định 16 bước thay vì 32. [Phép đo CPU thực tế](research/cpu-runtime-performance.md): câu ngắn với prompt đã cache vẫn mất khoảng 198 giây. Không bấm tạo nhiều lần khi đang xử lý vì các yêu cầu sẽ phải xếp hàng.

Giao diện dùng bộ **150 preview trong repo này**, có tìm giọng theo tên, lọc ba nhóm và ngôn ngữ mẫu, nạp TXT, chỉnh tốc độ/khoảng nghỉ, 8 ngôn ngữ đầu ra, chia văn bản dài, chất lượng/seed, tải WAV/MP3 và ZIP từng đoạn. Mặc định chọn nhóm 50 giọng tiếng Việt; không tải 7 mẫu từ repo cũ.

Notebook Gradio cũ giữ hai cách nạp bộ 150 mẫu (VietVoice Studio mới tự tải đủ 158 mẫu và không cần các bước này):

- Tự tải từ GitHub: đặt `GITHUB_TOKEN` trong Colab Secrets và cho notebook quyền truy cập secret. Token cần **Contents: Read** cho riêng repo `cracksteam456/voice-studio`. Nếu chưa đặt secret, notebook có ô nhập token ẩn; token không ghi vào file.
- Không dùng token: để trống ô nhập rồi chọn `hot-voices-150.zip` đã tải từ Release. Gói chỉ khoảng 24 MB, nạp một lần mỗi máy ảo Colab. Đây là upload cục bộ, không cần gọi repo khác.

Chạy trên checkout có `outputs/hot-voices/` sẽ dùng file cục bộ ngay. Catalog kiểm tra SHA256 và đường dẫn cả 150 mẫu trước khi mở giao diện. Muốn cập nhật gói: `python build_voice_pack.py`, rồi `python build_notebook.py`.

Notebook chứa toàn bộ code giao diện nên không cần tải file `voice_studio.py` riêng. File Python đó là nguồn để sửa; chạy `python build_notebook.py` để cập nhật notebook. Model weights không được lưu trong repo; bộ 150 preview nằm riêng ở `outputs/hot-voices/`.

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

**Phạm vi đang ưu tiên: giọng hot.** Dùng `python download_voice_library.py --hot-only` để chỉ hoàn tất mẫu đại diện của 3 shortlist top 50 (Trending toàn cầu, usage toàn cầu, tiếng Việt). Tác vụ này tái sử dụng file đã tải và dừng khi hoàn tất shortlist; không tiếp tục hàng đợi toàn bộ. Kết quả ánh xạ trong `voice-library/archive/hot-voices.json`.

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
python -m unittest test_voice_assets.py test_voice_studio.py test_collect_catalog.py test_clone_pilot.py
```

Các test CPU kiểm tra chia đoạn, input tùy chọn, phân trang và xử lý key. Tạo giọng chạy trên runtime Colab CPU hoặc GPU; CPU chậm hơn đáng kể. Đã thử bộ 10 giọng tiếng Việt và xuất WAV/MP3/ZIP ở các phiên trước; chưa chạy tổng hợp đủ 150 giọng hoặc mọi ngôn ngữ.

## Nguồn và quyền sử dụng

Thông tin nguồn notebook ban đầu, model OmniVoice và các mẫu giọng được ghi trong [ATTRIBUTION.md](ATTRIBUTION.md). Tên hiển thị và phần phát triển của dự án là **cracksteam456 Voice Studio**. Chưa gán giấy phép mở chung cho mọi tài sản trong repo.
