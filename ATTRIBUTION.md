# Nguồn và ghi nhận

## Dự án hiện tại

**cracksteam456 Voice Studio** được phát triển và duy trì tại [cracksteam456/voice-studio](https://github.com/cracksteam456/voice-studio). Repo này có lịch sử riêng, không phải GitHub fork. Giao diện mở rộng, công cụ kiểm kê/tải mẫu, notebook thử nghiệm và báo cáo trong repo là phần phát triển của dự án hiện tại.

## Nguồn ban đầu và phụ thuộc

- Notebook ban đầu được tham khảo và điều chỉnh từ [doanquangkien/voice-notebooks](https://github.com/doanquangkien/voice-notebooks). Luồng chạy hiện tại đã thay bộ 7 giọng và loại bỏ các bước tải tài nguyên từ repo đó; phần ghi nhận này mô tả nguồn phát triển ban đầu.
- Model tổng hợp là [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice), package đang khóa `omnivoice==0.2.1`. Model không do cracksteam456 huấn luyện từ đầu; giấy phép và thông báo tác giả của OmniVoice vẫn áp dụng cho thành phần tương ứng.
- Bộ 150 preview được lấy từ ElevenLabs. ID, URL nguồn, nhóm xếp hạng và trạng thái quyền được giữ trong `outputs/hot-voices/catalog.json`. Không coi thay đổi nhận diện dự án là chuyển quyền sở hữu bản ghi hay giọng nói.

Tên tác giả của thành phần kế thừa và lịch sử đóng góp được giữ đúng nguồn. Thay đổi thương hiệu không phải tuyên bố viết lại toàn bộ mã hoặc sở hữu mọi tài sản âm thanh.
