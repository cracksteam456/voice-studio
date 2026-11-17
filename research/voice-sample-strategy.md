# Chiến lược thư viện mẫu giọng cho Voice Studio

Ngày: 2026-11-17. Phạm vi hiện tại: nghiên cứu và thiết kế; chưa thu âm thanh hàng loạt hoặc tạo TTS có tính phí.

## Mục tiêu và thứ tự ưu tiên

Xây danh mục giọng có nguồn gốc rõ ràng, có thể nghe và tìm kiếm; chỉ đưa các mẫu có quyền dùng cho clone bên ngoài dịch vụ nguồn vào danh sách được chọn trong OmniVoice. Mục tiêu ban đầu là **50 giọng ứng viên phổ biến**, sau đó chọn **10–20 giọng chất lượng phù hợp video**. Các số này là đề xuất triển khai, không phải thống kê hiện có.

Ưu tiên lấy danh mục rộng và chọn lọc audio, vì “tất cả giọng ElevenLabs” không đồng nghĩa tất cả giọng công khai/tài khoản truy cập được, và mỗi giọng có thể có điều kiện khác nhau. Không gắn nhãn “hot” dựa vào tên giọng quen thuộc; lưu tiêu chí xếp hạng và thời điểm truy vấn.

## Hai loại tài sản cần tách biệt

| Tài sản | Mục đích | Điều kiện vào Voice Studio |
|---|---|---|
| Metadata/preview để đánh giá | Tìm giọng, nghe, so sánh | Lưu nguồn và phạm vi được phép; không mặc định preview là mẫu được quyền clone |
| Mẫu tham chiếu OmniVoice | Tạo giọng bên ngoài ElevenLabs | Cần quyền cụ thể phù hợp từ chủ giọng/nhà cung cấp; chỉ quyền tạo TTS trên ElevenLabs chưa đủ để tự suy ra quyền này |

Nếu điều khoản không cho phép mục tiêu clone bên ngoài hoặc chưa xác định được quyền, giữ giọng trong danh mục tham khảo hoặc dùng trực tiếp ElevenLabs TTS theo quyền tài khoản; không tự chuyển nó thành mẫu OmniVoice.

## Quy trình đề xuất

API danh mục chính thức đã xác minh: `GET https://api.elevenlabs.io/v1/shared-voices`. Ví dụ query để lập shortlist (chưa chạy):

```text
/v1/shared-voices?page=0&page_size=100&sort=trending
/v1/shared-voices?page=0&page_size=100&sort=usage_character_count_1y
/v1/shared-voices?page=0&page_size=100&sort=trending&language=vi
```

Lưu riêng cả ba thứ hạng; lấy hợp các danh sách rồi khử trùng. Bản ghi có thể có `verified_languages[].preview_url`: ưu tiên preview đúng ngôn ngữ, không chỉ URL chung. Khi quét danh mục rộng, tăng `page` từ 0 đến khi `has_more=false`. Không dùng cursor của `/v2/voices` cho endpoint này. `/v2/voices` là danh mục giọng tài khoản có thể truy cập và không phải toàn bộ thư viện.

Các endpoint này được xác minh qua [API reference](https://elevenlabs.io/docs/api-reference/voices/voice-library/get-shared.md), chưa kiểm thử bằng tài khoản. Theo [policy §12](https://elevenlabs.io/use-policy), không mặc định quyền thu thập hàng loạt hay dùng Services/Output để phát triển AI khác. Cần xác định phạm vi được phép trước khi thực thi phần audio. Reference-only inference không được policy giải thích đích danh; báo cáo không đánh đồng nó với training.

1. **Chụp danh mục:** dùng API chính thức, lưu metadata nguyên bản và bản chuẩn hóa. Đọc phân trang đến điểm dừng; ghi query/filter/ranking/time để biết phạm vi đã quét. Dừng và báo nếu yêu cầu bị từ chối; không dùng endpoint ẩn hay lách hạn mức.
2. **Lập shortlist:** đề xuất 25 ứng viên từ bảng xếp hạng công khai phù hợp và 25 ứng viên tiếng Việt/nhóm nội dung mong muốn nếu danh mục có đủ. Hợp nhất theo mã định danh, bù số lượng nếu trùng. Tách danh sách phổ biến toàn cầu khỏi danh sách phù hợp tiếng Việt.
3. **Xác định quyền:** ghi loại giọng, chủ sở hữu, điều khoản sử dụng và bằng chứng cho mục đích clone ngoài dịch vụ. Giá trị chưa biết giữ nguyên `unknown`, không coi là `allowed`.
4. **Lấy mẫu phù hợp:** chỉ lấy audio nằm trong phạm vi được phép. Giữ file gốc. Mẫu thiếu preview đánh dấu `no_preview`; lỗi mạng/auth/HTTP lưu riêng và có thể tiếp tục từ checkpoint. Chưa có quyền hoặc muốn ghi mới thì làm việc với chủ giọng/diễn viên trước.
5. **Chuẩn bị mẫu:** chọn câu hoàn chỉnh 3–10 giây, ưu tiên cùng ngôn ngữ với đầu ra. Ghi chính xác start/end; tạo WAV mono ở sample rate của model. Giữ transcript khớp đoạn cắt. Xem [kết quả OmniVoice](omnivoice-reference-findings.md).
6. **Đánh giá:** thử 10 giọng đã đủ quyền, mỗi giọng 2 đoạn mẫu × 2 đoạn văn đầu ra, cùng seed/cấu hình. Đánh giá độ giống giọng, độ rõ lời, ngữ điệu và accent riêng rẽ. Chưa khẳng định clone giống hoàn toàn giọng nguồn.
7. **Tích hợp:** Voice Studio đọc catalog có các trạng thái `reference_only`, `needs_review`, `ready`, `failed`; chỉ `ready` xuất hiện ở bộ chọn clone. Lưu prompt của các mẫu `ready` để giảm thời gian nhận dạng ở phiên sau.

## Cấu trúc dữ liệu dự kiến

```text
voice-library/
  catalog.jsonl
  snapshots/YYYY-MM-DD/
  voices/<provider>/<owner-id>/<voice-id>/
    metadata.json
    original.mp3
    reference.wav
    reference.txt
    review.json
```

Khóa giọng gồm provider/owner/voice ID, không dựa vào tên hiển thị. Các trường tối thiểu:

```json
{
  "provider": "elevenlabs",
  "voice_id": "<id>",
  "owner_id": "<public owner id when provided>",
  "name": "<display name>",
  "language": null,
  "source_url": "<official listing>",
  "preview_url": null,
  "ranking_method": null,
  "rank_at_fetch": null,
  "fetched_at": "<UTC timestamp>",
  "clone_permission": "unknown",
  "permission_evidence": null,
  "original_sha256": null,
  "reference_start": null,
  "reference_end": null,
  "reference_text": null,
  "status": "needs_review"
}
```

## Vận hành và ngân sách

- Bắt đầu 1–2 request đồng thời; điều chỉnh theo hạn mức và tài liệu tài khoản. Với 429, tôn trọng `Retry-After` nếu có; backoff có giới hạn. Không retry mù 401/403.
- Lưu checkpoint sau mỗi trang; chống trùng theo ID và checksum; không ghi API key vào notebook, URL hay catalog. Khóa dùng từ môi trường/Colab Secrets khi cần.
- Ước tính audio: WAV 24 kHz, mono, 16-bit dài 10 giây xấp xỉ 480 kB/giọng; 50 giọng xấp xỉ 24 MB, 1.000 giọng xấp xỉ 480 MB, chưa gồm bản gốc và metadata. Đây là phép tính PCM, không phải kích thước MP3 thực tế.
- Nếu được quyền và cần tạo mẫu TTS mới: ngân sách nội dung = số giọng × số ký tự mẫu × số lượt tạo. Ví dụ 50 giọng × 150 ký tự × 1 lượt = 7.500 ký tự đầu vào. Quy đổi sang credit/tiền theo model/gói thực tế; chưa thực hiện tác vụ tính phí.
- Tiêu chí hoàn tất thí điểm: có catalog và phạm vi nguồn; không trùng ID; audio mở được; reference 3–10 giây; transcript đúng; ngôn ngữ đã kiểm tra; quyền clone có căn cứ; ít nhất 10 giọng đã thử đầu ra trước khi mở rộng.

## Tài liệu đi kèm

- [Nghiên cứu ElevenLabs](elevenlabs-library-findings.md): endpoint chính thức, phạm vi danh mục, xếp hạng và quyền sử dụng.
- [Nghiên cứu OmniVoice](omnivoice-reference-findings.md): thời lượng, ngôn ngữ, transcript và câu mẫu.

Đây là thiết kế, chưa có downloader hay thay đổi thư viện giọng đang chạy.
