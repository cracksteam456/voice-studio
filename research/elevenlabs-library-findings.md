# ElevenLabs Voice Library: kiểm kê giọng và preview, giới hạn khi dùng cho OmniVoice

Ngày nghiên cứu: **17/11/2026**. Chỉ sử dụng tài liệu, API reference và điều khoản chính thức của ElevenLabs. Đây là nghiên cứu chiến lược; không gọi API danh mục trực tiếp, không đăng nhập/đọc thông tin xác thực, không tải audio và không triển khai công cụ thu thập.

## Kết luận phục vụ quyết định

- **Có endpoint được tài liệu hóa để khám phá danh mục giọng chia sẻ:** `GET https://api.elevenlabs.io/v1/shared-voices`. Endpoint trả metadata, các chỉ số phổ biến và `preview_url`; hỗ trợ phân trang theo số trang. Đây là lựa chọn đúng cho kiểm kê Voice Library, thay vì coi danh sách giọng tài khoản là toàn bộ thư viện. [S1, S2]
- **Có thể xây dựng danh sách giọng phổ biến** bằng `sort=trending`, `sort=usage_character_count_1y` hoặc `sort=cloned_by_count`. Không có giá trị sort mang tên `popular` trong API reference đã kiểm tra. [S1]
- **Không thể cam kết “tất cả giọng ElevenLabs”.** `/v2/voices` chỉ liệt kê giọng khả dụng cho người dùng; `/v1/shared-voices` liệt kê giọng chia sẻ, không hứa bao gồm giọng riêng tư, mọi giọng chia sẻ bằng link, giọng đã rút khỏi thư viện hay mọi biến thể/sản phẩm/khu vực. [S1–S3, S7, S11]
- **Chưa có cơ sở cấp phép cho kế hoạch lấy preview hàng loạt để clone sang OmniVoice.** Voice Library License cho phép truy cập/sử dụng giọng thông qua Voice Library để tạo Output. Prohibited Use Policy §12 cấm dùng Services/Output để phát triển, huấn luyện, fine-tune hoặc cải thiện mô hình/dịch vụ AI, hoặc đưa Output vào dataset cho những mục đích đó, trừ khi điều khoản áp dụng cho phép rõ ràng; đồng thời cấm dùng chúng để nghiên cứu/phát triển sản phẩm hoặc dịch vụ cạnh tranh. Không được suy từ “nghe được preview”, “giọng public” hay “có gói trả phí” thành quyền clone ngoài nền tảng. [S8 §2, S9 §§3, 9, 12, S10 §§4–5]
- **Hướng thực tế cho OmniVoice:** dùng thư viện để tham khảo và lập shortlist trong phạm vi được phép; lấy bản ghi gốc từ người nói với quyền clone ngoài ElevenLabs được thỏa thuận riêng. Nếu muốn dùng chính preview/Output của ElevenLabs cho AI khác, phải có quyền/ngoại lệ áp dụng từ ElevenLabs và quyền thích hợp từ người nói/chủ bản ghi. Đây là khuyến nghị dựa trên phạm vi giấy phép được công bố, không phải kết luận rằng tài liệu đã cấp các quyền đó. [S8–S10]

## 1. Endpoint và phạm vi đã xác minh từ tài liệu

| Mục tiêu | Endpoint chính thức | Phạm vi và điểm cần nhớ |
| --- | --- | --- |
| Khám phá Voice Library | `GET /v1/shared-voices` | Danh sách shared voices, có metadata phổ biến và preview; không đồng nghĩa danh sách mọi voice model của nền tảng. [S1] |
| Kiểm kê giọng người dùng có thể truy cập | `GET /v2/voices` | Tài liệu ghi rõ “all available voices for a user”; có search, filter, cursor pagination. [S2] |
| Danh sách tài khoản theo API cũ | `GET /v1/voices` | Legacy; ngừng hoạt động khi workspace vượt 500 voices. Không phù hợp làm nền tảng kiểm kê quy mô lớn. `show_legacy=true` có thể bao gồm legacy premade voices. [S3] |
| Thêm shared voice vào danh sách tài khoản | `POST /v1/voices/add/{public_user_id}/{voice_id}` | Thay đổi collection giọng của tài khoản; không phải tải model hay tải preview. Không cần thực hiện thao tác này chỉ để đọc trường preview trong phản hồi danh mục. [S1, S4] |
| Lấy audio của sample gắn với một voice | `GET /v1/voices/{voice_id}/samples/{sample_id}/audio` | Endpoint riêng cho sample có ID; không phải endpoint “tải preview của tất cả giọng public”. Tài liệu không cấp quyền truy cập sample nguồn của mọi chủ giọng. [S5] |
| Tạo audio mới từ văn bản | `POST /v1/text-to-speech/{voice_id}` | Nhận `text`, model và thiết lập; trả audio được tạo mới. Có usage/billing theo gói và điều kiện truy cập. Khác việc lấy file preview có sẵn. [S6, S11 §1.3] |

Base URL production mặc định là `https://api.elevenlabs.io`. Tài liệu còn liệt kê server US/EU/India/Singapore; không được tự suy mọi môi trường có cùng danh mục/quyền truy cập. ElevenAPI Terms §1.3 nói availability phụ thuộc gói, entitlements và khu vực; môi trường regional isolated là workspace riêng, có thể ít tính năng hơn. [S1, S2, S11]

### Xác thực và gói dịch vụ

Tài liệu API Authentication yêu cầu API key trong header `xi-api-key`, đồng thời cho phép giới hạn scope/quota/IP. Một số ví dụ code tự sinh trên trang endpoint không hiển thị header này; việc ví dụ bỏ header **không chứng minh endpoint hỗ trợ truy cập ẩn danh**. Báo cáo không kiểm thử HTTP ẩn danh và không đọc key của người dùng. [S12]

Trang Voice Library cảnh báo: **giọng Voice Library không khả dụng qua API cho người dùng free tier**. Cảnh báo này không giải thích riêng liệu thao tác khám phá metadata hay URL preview có ngoại lệ nào; không nên tự khẳng định rằng danh mục/preview có thể được thu thập ẩn danh hoặc bằng gói free. Trường `free_users_allowed` thể hiện điều kiện của giọng, không xóa bỏ điều kiện gói/quyền truy cập API. [S1, S7]

## 2. Phân trang và sắp xếp shared voices

### Các trường được tài liệu hóa

`GET /v1/shared-voices` có: [S1]

- `page`: integer, mặc định **0**.
- `page_size`: mặc định **30**, tối đa **100**.
- `sort`: mặc định `created_date`; enum gồm `created_date`, `usage_character_count_1y`, `trending`, `cloned_by_count`.
- Phản hồi `voices`, `has_more`; `total_count` optional, mặc định trong schema là 0; `last_sort_id` optional/nullable.

**Chiến lược phân trang theo tài liệu:** giữ nguyên query/filter, bắt đầu `page=0`, tăng lần lượt 1, 2, … và dừng khi `has_more=false`. Khử trùng lặp bằng `(public_owner_id, voice_id)` cho bản ghi library gốc. Đây là đề xuất thiết kế dựa trên hợp đồng phân trang, chưa được chạy kiểm thử. [S1]

**Không dùng `last_sort_id` như cursor đầu vào:** tài liệu có trường phản hồi này nhưng danh sách query parameters không công bố tham số tương ứng. Không thay bằng `next_page_token` vì token đó thuộc `/v2/voices`. Tài liệu không công bố snapshot isolation, thứ tự tie-break, giới hạn trang sâu hoặc bảo đảm không bỏ sót khi danh mục/xếp hạng thay đổi. Do đó, duyệt hết trang là kiểm kê kết quả API tại thời điểm khảo sát, không phải bằng chứng có bản sao đầy đủ và nhất quán của thư viện. [S1, S2]

### Chọn cách hiểu “phổ biến”

| Nhu cầu | Giá trị sort / cách chọn | Mức xác minh |
| --- | --- | --- |
| Giọng đang thịnh hành | `trending` | Guide mô tả Trending là xếp theo popularity; công thức và cửa sổ thời gian không được công bố trong nguồn đã đọc. [S1, S7] |
| Giọng được dùng nhiều để tạo lời nói | `usage_character_count_1y` | Trường tương ứng là số ký tự sử dụng trong năm qua. Có `usage_character_count_7d` trong phản hồi nhưng không có sort 7 ngày trong enum. [S1] |
| Giọng có nhiều người dùng/lượt thêm | `cloned_by_count` | API gọi đây là số lần voice được “cloned”; guide UI có mục Most users. Việc ánh xạ Most users sang trường này là suy luận hợp lý, chưa phải định nghĩa chi tiết được tài liệu xác nhận. Không phải số người đã clone giọng sang AI bên ngoài. [S1, S4, S7] |
| Giọng mới | `created_date` | Có trong enum; không phải tiêu chí phổ biến. [S1] |
| Giọng được tuyển chọn | `featured=true` hoặc Handpicked Collections trên UI | Là bộ lọc/tuyển chọn, không đồng nghĩa thứ hạng phổ biến toàn thư viện. [S1, S7] |

API shared-voices không tài liệu hóa `sort_direction`. Hướng sắp xếp chính xác và xử lý đồng hạng chưa được xác minh qua runtime; không nên bổ sung query không được công bố. Có thể lưu thứ hạng trả về cùng thời điểm truy vấn; nếu cần xếp theo giá trị số tự tính, phải gọi rõ đó là thứ hạng tự tính trên tập đã thu được. [S1]

### Bộ lọc liên quan độ phủ

Các query gồm `category`, `gender`, `age`, `accent`, `language`, `locale`, `search`, `use_cases`, `descriptives`, `featured`, `min_notice_period_days`, `include_custom_rates`, `include_live_moderated`, `reader_app_enabled`, `owner_id`. `category` đầu vào hiện chấp nhận `professional`, `famous`, `high_quality`; enum category trong phản hồi rộng hơn. [S1]

Khi muốn kiểm kê rộng, bỏ các bộ lọc lựa chọn như `search`, `owner_id`, `language`, `category`, `featured=true`, `reader_app_enabled=true`. Các boolean optional/default không được mô tả đủ rõ để coi omission, false và “bao gồm mọi giá trị” là tương đương trong mọi trường hợp. Cần ghi lại query và defaults khi báo cáo độ phủ; không tự tuyên bố “all” chỉ vì không truyền filter. Có thể tách một shortlist tiếng Việt bằng `language=vi`, nhưng đây chỉ là tập con theo metadata ngôn ngữ, không phải toàn bộ giọng có thể nói tiếng Việt. [S1, S7]

## 3. Phân trang danh sách account-accessible

`GET /v2/voices` hỗ trợ `page_size` mặc định **10**, tối đa **100**; trang đầu có thể nhiều hơn vì kèm default voices. Lấy `next_page_token` từ phản hồi trước và kết hợp `has_more`; không tự tạo token. `total_count` là snapshot sống, có thể đổi khi tạo/sửa/xóa voice và không nên dùng làm điều kiện kết thúc. [S2]

`voice_type` có `personal`, `community`, `default`, `workspace`, `non-default`, `non-community`, `saved`. Bộ lọc này nằm trong phạm vi “available voices for a user”; `community` không phải cam kết liệt kê toàn bộ Voice Library. Sắp xếp tại endpoint này chỉ công bố `created_at_unix` hoặc `name`, với `sort_direction=asc|desc`; không hỗ trợ sort popularity được công bố như shared-voices. [S2]

Để đối chiếu default/premade và giọng đã lưu, có thể thiết kế inventory tài khoản riêng, sau khi có quyền dùng tài khoản. Dùng `sharing.public_owner_id` và `sharing.original_voice_id` khi có để liên kết bản giọng được thêm với bản library gốc; không chỉ khử trùng lặp bằng tên hiển thị. Đây là khuyến nghị thiết kế, không phải thao tác đã thực hiện. [S2, S4]

## 4. `preview_url`, sample nguồn và audio tạo mới

**Preview có sẵn:** cả LibraryVoiceResponseModel và VoiceResponseModel có `preview_url` optional/nullable. `verified_languages[]` cũng có `language`, `model_id`, `accent`, `locale` và `preview_url` optional/nullable. Một giọng có thể có preview tổng quát và nhiều preview ngôn ngữ; không nên mặc định một giọng bằng đúng một file hoặc mọi giọng đều có preview. [S1, S2]

Guide chính thức nói người dùng có thể bấm giọng để nghe sample và chọn ngôn ngữ preview. Chủ Professional Voice Clone có thể chọn **audio đã generate từ prompt dài 70–150 ký tự** làm custom preview. Vì vậy, preview có thể là audio tổng hợp, không chứng minh là bản ghi tự nhiên gốc của người nói, không bảo đảm một transcript chung, độ dài giây chung hoặc cùng model cho mọi giọng. [S7]

**Sample gắn với voice:** `samples[]` có sample ID, filename, MIME type, kích thước…; endpoint sample-audio lấy audio tương ứng sample đó. Việc một public voice có preview không đồng nghĩa người khác có quyền lấy dữ liệu sample/huấn luyện gốc. Không dùng endpoint này để thử lấy dữ liệu nguồn của chủ giọng. [S2, S5, S10 §§4–5]

**Audio tạo mới:** TTS nhận nội dung `text` do bên gọi cung cấp và trả file audio mới, có thể chọn `output_format` theo điều kiện gói. Đó là một hoạt động generate có tính usage, không phải thao tác tải preview. Không đề xuất dùng TTS làm fallback tự động khi preview thiếu nếu mục tiêu là kiểm kê preview có sẵn; quyền dùng Output cho AI khác vẫn phải xét riêng. [S6, S9 §12, S11 §1.3]

**Nếu sau này có quyền tải/lưu preview cho mục đích cụ thể:** thiết kế nên lấy đúng URL hiện API trả về, lưu nguồn/thời điểm/ngôn ngữ/model và căn cứ cấp phép, xử lý URL null hoặc không còn khả dụng, tránh đoán cấu trúc CDN hay dò bucket. Tài liệu chỉ mô tả đây là preview URL; chưa tìm thấy cam kết về thời hạn URL, định dạng/codec/duration cố định, checksum, băng thông tải hàng loạt hoặc giấy phép tái phân phối preview. Các ví dụ URL `.mp3` không phải hợp đồng định dạng cho mọi file. [S1, S2, S11 §3.1]

## 5. “Tất cả giọng” có thể hiểu đến đâu?

**Đã biết:** có API danh mục shared voices và API giọng khả dụng cho user. Voice Library hiện cho cộng đồng publish Professional Voice Clones. Guide nói Instant Voice Clones và Voice Design chỉ chia sẻ trong workspace; PVC có thể chia sẻ riêng bằng link. Giọng rút khỏi thư viện có thể không còn hiện trong library nhưng vẫn dùng được với người đã lưu/dùng trong notice period. [S1, S2, S7, S8 §4]

**Không được chứng minh:** mọi PVC chia sẻ riêng bằng link đều hiện trong `/v1/shared-voices`; mọi giọng premade/default đều nằm trong shared catalog; mọi category trong schema đang có bản ghi thực tế; danh mục này bao gồm giọng riêng tư/workspace, giọng bị gỡ, giọng chỉ dành cho sản phẩm riêng hoặc mọi giọng ở các region. Không có endpoint quản trị toàn cục “all ElevenLabs voices” nào được xác minh trong nguồn đã đọc. [S1–S3, S7, S11 §1.3]

Do đó, tên đầu ra chính xác nên là **“inventory shared voices do API trả về cho query/quyền truy cập/khu vực/thời điểm X”** hoặc **“top N theo sort X”**. Một inventory default/account-accessible là tập bổ sung có nguồn riêng, không tự biến hợp hai tập thành toàn bộ nền tảng.

## 6. Giấy phép, clone và tái phân phối

### Phạm vi quyền đã được công bố

1. **Voice Library License là quyền dùng qua dịch vụ.** Addendum §2 nói chủ giọng cho phép người khác access/use User Voice Models “through the Voice Library Service” và generate Output. Không có điều khoản trong nguồn này cấp người xem quyền xuất model, clone giọng sang OmniVoice hoặc tái cấp phép danh tính giọng nói. [S8]
2. **Output của bạn và preview của người khác là hai đối tượng khác nhau.** Terms §4(c) nói quyền đối với Output của bạn, theo quan hệ giữa bạn và ElevenLabs, vẫn thuộc bạn trừ ngoại lệ; §10 nói phản hồi được yêu cầu/tạo cho user khác không phải Output của bạn và bạn không có right/title đối với nó. Vì custom preview có thể là generation do chủ giọng chọn, không thể dựa vào quyền Output của chính bạn để nhận quyền sở hữu preview đó. Đây là cách áp dụng các điều khoản vào tình huống preview, không phải giấy phép preview riêng. [S7, S10]
3. **Có điều khoản cấm sử dụng cho AI khác.** Policy §12: “Using our Services or Output to develop, train, fine-tune, or improve any AI model or service, or including Output in a dataset used for any of those purposes, except as expressly permitted under the applicable terms”. Cũng tại §12: cấm dùng Services/Output để research/develop sản phẩm hoặc dịch vụ cạnh tranh. Pipeline thu preview để xây kho clone/huấn luyện/đánh giá phát triển OmniVoice không có sự cho phép mặc định trong các nguồn đã đọc. [S9]
4. **Clone một người thật cần consent/authorization thích hợp.** Policy §3 cấm clone/synthesize/impersonate voice của người đang sống mà thiếu “explicit and informed consent or other valid authorization”; §9 bảo vệ IP/publicity rights. Việc người nói publish giọng trong Voice Library chỉ chứng minh họ cấp phạm vi Library License, không chứng minh họ đồng ý cho người khác clone ngoài ElevenLabs. [S8 §2, S9]
5. **Paid commercial license không phải ngoại lệ AI-training.** FAQ cho phép commercial use với nội dung bạn generate trên gói trả phí khi có các quyền cần thiết và tuân thủ điều khoản/policy; free plan không có commercial license và có yêu cầu attribution khi publish nội dung. FAQ không cấp giấy phép download/rehost toàn bộ preview của người khác hoặc dùng chúng làm dữ liệu AI. [S13, S9 §12]
6. **Không có giấy phép mở được xác minh cho bộ preview.** Terms §5 dành quyền đối với nội dung dịch vụ cho ElevenLabs/licensors, với license truy cập dịch vụ hạn chế, non-transferable/non-sublicensable/revocable. Policy §12 cấm cung cấp Services/Output cho bên thứ ba với điều kiện rộng hơn điều kiện của mình. Không nên phân phối lại một bộ preview/voice-cloning dataset chỉ dựa vào public URL. Đây là kết luận về việc chưa có quyền được chứng minh, không khẳng định mọi cách phân phối mọi Output đều bị cấm. [S9, S10]
7. **Tự động hóa phải xét điều kiện áp dụng.** Policy §12 cấm bots/scraping/automated extraction trừ phần được `robots.txt` cho phép, cấm truy cập ngoài interfaces/APIs được cung cấp và cấm né limits. `robots.txt` tại `elevenlabs.io` hiện có `Disallow: /app/` và `/v1/` cho user-agent `*`; file cũng có Content-Signal cho AI nhưng không phải giấy phép rõ ràng cho mọi audio/CDN hay quyền clone. File này thuộc host website, không tự xác định chính sách của host API hoặc CDN khác. Vì vậy nên dùng API được công bố trong phạm vi hợp đồng, xác nhận phạm vi inventory/bulk caching nếu chưa rõ; không crawl app hoặc coi robots là sự đồng ý của người nói. [S9, S11 §1, S14]

### Những điểm cần phân biệt là chưa rõ

- **Zero-shot/reference-only inference:** tài liệu đọc được không giải thích đích danh “đưa một preview làm reference cho OmniVoice tại inference mà không cập nhật weights”. Không thể kết luận mọi reference inference chính là training; cũng không có cơ sở kết luận nó được cho phép. Quyền bản ghi/giọng, phạm vi Library License và điều khoản cạnh tranh vẫn cần xem xét. [S8–S10]
- **Giấy phép cache/rehost preview:** chưa tìm thấy preview-specific license hoặc hạn mức bulk download. URL truy cập được về kỹ thuật không giải quyết câu hỏi quyền dùng/lưu/phân phối. [S1, S10]
- **Ngoại lệ hợp đồng riêng:** Policy cho phép ngoại lệ khi applicable terms expressly permit; chưa có hợp đồng riêng nào được xem trong nghiên cứu này. Không kết luận doanh nghiệp có hợp đồng riêng cũng bị ràng buộc y hệt ở mọi chi tiết. [S9, S11]
- **Hạn mức request:** có nghĩa vụ tuân thủ limits trong API Terms, nhưng nguồn đã đọc không cho con số request/giây riêng của shared-voices hoặc băng thông preview. Không tự đặt một con số rồi mô tả là hạn mức chính thức. [S11 §§1.1, 1.3]

## 7. Chiến lược đề xuất, chưa triển khai

1. **Tách hai mục đích:** inventory/shortlist giọng để lựa chọn trong ElevenLabs; bộ audio có quyền dùng cho OmniVoice. Tài liệu không cấp quyền biến tập thứ nhất thành dataset của tập thứ hai. [S8–S10]
2. **Với inventory được phép:** chọn shared catalog hoặc account-accessible theo mục tiêu; ghi query, sort, region, timestamp và version nguồn tài liệu. Dùng shared pagination hoặc account cursor đúng loại; ghi số bản ghi duy nhất, `has_more` cuối, lỗi và tỷ lệ thiếu preview. Đây là quy trình đề xuất để báo cáo độ phủ trung thực. [S1–S3]
3. **Với popular shortlist:** chốt top N theo `trending` hoặc `usage_character_count_1y`; có thể lưu thêm snapshot `cloned_by_count` và usage 7 ngày. Không gọi top N này là “mọi giọng nổi tiếng” hay dùng category `famous` như đồng nghĩa popularity. [S1, S7]
4. **Chỉ lưu metadata cần thiết:** `public_owner_id`, `voice_id`, tên, category, language/locale/accent, description/use_case, các chỉ số popularity, preview URL tổng quát và từng verified language, notice period, điều kiện free/rate/moderation và thời điểm quan sát. Giữ license/consent status riêng, mặc định chưa xác minh cho external cloning. Đây là thiết kế đề xuất; các trường dữ liệu được công bố ở [S1, S2].
5. **Với audio OmniVoice:** ưu tiên tự thu hoặc đặt người nói thu bản ghi mới, với thỏa thuận nêu rõ external cloning, inference/fine-tuning, commercial use và redistribution nếu cần. Nếu chọn dùng ElevenLabs preview/Output, cần văn bản/quyền áp dụng cho đúng file, giọng và mục đích AI; không xem gói trả phí hay consent dùng trong Library là đủ. [S8–S10, S13]

## 8. Nguồn chính thức và độ tin cậy

Các endpoint/field ở trên được **xác minh từ API reference**, chưa được xác minh hành vi runtime. Các giới hạn quyền được trích từ văn bản chính thức đang hiển thị tại ngày nghiên cứu; phần “đề xuất/suy luận/chưa rõ” được ghi riêng. Không dùng blog bên thứ ba, danh sách voice ID cộng đồng, reverse engineering giao diện hay audio tải về.

- **[S1] List shared voices:** https://elevenlabs.io/docs/api-reference/voices/voice-library/get-shared — bản văn đọc: https://elevenlabs.io/docs/api-reference/voices/voice-library/get-shared.md
- **[S2] List voices, v2:** https://elevenlabs.io/docs/api-reference/voices/search — bản văn: https://elevenlabs.io/docs/api-reference/voices/search.md
- **[S3] Legacy List voices, v1:** https://elevenlabs.io/docs/api-reference/legacy/voices/get-all — bản văn: https://elevenlabs.io/docs/api-reference/legacy/voices/get-all.md
- **[S4] Add shared voice:** https://elevenlabs.io/docs/api-reference/voices/voice-library/share — bản văn: https://elevenlabs.io/docs/api-reference/voices/voice-library/share.md
- **[S5] Get voice sample audio:** https://elevenlabs.io/docs/api-reference/voices/samples/get — bản văn: https://elevenlabs.io/docs/api-reference/voices/samples/get.md
- **[S6] Create speech:** https://elevenlabs.io/docs/api-reference/text-to-speech/convert — bản văn: https://elevenlabs.io/docs/api-reference/text-to-speech/convert.md
- **[S7] Voice Library guide:** https://elevenlabs.io/docs/eleven-creative/voices/voice-library — bản văn: https://elevenlabs.io/docs/eleven-creative/voices/voice-library.md
- **[S8] Voice Library Addendum:** https://elevenlabs.io/vla — trang ghi cập nhật **06/03/2026**; trọng tâm §§2, 4, 8.
- **[S9] Prohibited Use Policy:** https://elevenlabs.io/use-policy — trang ghi cập nhật **09/10/2026**; trọng tâm §§3, 8, 9, 12.
- **[S10] Terms of Service, non-EEA:** https://elevenlabs.io/terms-of-use — trang ghi cập nhật **09/10/2026**; trọng tâm §§1(c), 4, 5, 10. Đây là phiên bản dùng để phân tích cho người cư trú Việt Nam; người cư trú EEA/Switzerland/UK cần đối chiếu https://elevenlabs.io/terms-of-use-eu và https://elevenlabs.io/vlaeu; hai bản EU không được phân tích chi tiết trong nghiên cứu này.
- **[S11] ElevenAPI Terms:** https://elevenlabs.io/elevenapi-terms — trang ghi cập nhật **09/10/2026**; trọng tâm §§1, 3, 4. Index Service-Specific Terms: https://elevenlabs.io/service-specific-terms
- **[S12] API Authentication:** https://elevenlabs.io/docs/api-reference/authentication — bản văn: https://elevenlabs.io/docs/api-reference/authentication.md
- **[S13] Can I publish the content I generate on the platform?:** https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform — bản văn: https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform.md
- **[S14] robots.txt của website:** https://elevenlabs.io/robots.txt — quan sát **17/11/2026**, không coi là license audio hoặc license giọng nói.

**Lưu ý về nguồn mâu thuẫn/lỗi thời:** bài giới thiệu cũ chính thức “ElevenLabs Voices: A comprehensive guide” (https://elevenlabs.io/elevenlabs-voices-a-comprehensive-guide) trong kết quả tìm kiếm nói Voice Design có thể chia sẻ và “all voices ... free commercial use license”. Guide hiện hành [S7] chỉ cho publish PVC; FAQ commercial hiện hành [S13] phân biệt free/paid. Vì vậy không dùng bài cũ làm bằng chứng cấp phép blanket cho toàn bộ preview hoặc external cloning. Điều khoản pháp lý và tài liệu hiện hành được ưu tiên trong báo cáo này.
