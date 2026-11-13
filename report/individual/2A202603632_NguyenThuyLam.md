# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline

- **Chủ đề/corpus:** “Phương pháp Học sâu cho bài toán phát hiện ảnh giả mạo”, file `data/data-for-lab.pdf`. Manifest khai quyền sử dụng thuộc người dùng.
- **Số trang và quy tắc tính:** PDF có 60 trang vật lý. Pipeline trích xuất được 60/60 trang có text, 0 trang lỗi, 0 trang rỗng. 
- **Chuẩn hóa, lỗi và giới hạn:** dùng `pypdf` để trích xuất; chuẩn hóa Unicode NFC, chuẩn hóa xuống dòng và khoảng trắng. Nhật ký ingest ghi trạng thái, số ký tự và lỗi theo trang. Lần chạy ghi nhận không có lỗi/rỗng. Chưa có OCR.
- **Embedding/vector store/metric/lệnh/chi phí:** Google Gemini API, `gemini-embedding-2`, 768 chiều; document dùng prefix `title: ... | text: ...`, query dùng `task: search result | query: ...`. Kết quả xác nhận `Stored vectors: A=277, B=221`. SDK version chưa được khóa/ghi lại. PostgreSQL + pgvector được cấu hình bằng Docker Compose (image `pgvector/pgvector:0.8.7-pg16`); setup/check kết nối được người thực hiện xác nhận. Code xếp hạng cosine distance (`<=>`), chưa tạo ANN index nên truy vấn là exact scan. Lệnh ingest/embed: `python -m src.run` từ `starter/`; evaluation-only: đặt `$env:EVALUATE_ONLY = "1"` rồi chạy `python -m src.run`. Upsert xóa chunk cũ cùng strategy/document trước khi insert; chưa có kiểm tra riêng bằng lần nạp lặp. Chi phí thực tế chưa được kiểm tra/ghi nhận; không coi là 0.
- **Metadata:** mỗi chunk có `document_id`, `source`, `page`; metadata bổ sung gồm `section`, `status`, `extraction_error`, `character_count`, `start_char`, `end_char`. `section` được nhận diện từ heading và dùng để filter trong C. 

## Cấu hình và benchmark

- **A:** fixed-size, 500 ký tự, overlap 50.
- **B:** chia theo paragraph, nhóm/tách đoạn tối đa 800 ký tự.
- **C:** đã chạy trong retrieval evaluation bằng chính vectors/chunks B; chỉ áp dụng metadata filter khi câu hỏi có filter, không tạo vectors riêng.
- **Benchmark:** `data/format.json` có 20 câu (15 dev / 5 test), trong đó 3 câu có filter và 1 câu filter thuộc test. Evidence của 5 câu test đã được đối chiếu với PDF. Kiểm tra exact quote tự động theo trang gold khớp 16/20; q04, q07 và q14 dùng dấu `...` để nối đoạn không liền nhau, q08 có khác biệt chép lại “bản g”/“bản ghi”. Cần sửa/ghi các đoạn evidence thành các quote hợp lệ trước khi xem các chỉ số exact-match là gold đã chuẩn hóa. Bộ câu dev chưa được audit đầy đủ.

## Kết quả

Ingest/chunk và lưu embedding A/B đã hoàn tất. Retrieval chạy đủ 20 câu × 3 cấu hình và sinh trace. Hit@ được tính tự động bằng kiểm tra exact normalized `evidence_quote` trong một chunk; chấm thủ công grounding bên dưới chấp nhận evidence tương đương/đủ nghĩa, nên có thể khác Hit@ tự động.

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---:|---:|---:|---|---|
| A | dev | 5/15 (33,3%) | 5/15 (33,3%) | 277 | Embedding mẫu 0,623 s/call (n=3); tổng ingest chưa đo | Chi phí tài khoản chưa truy xuất |
| A | test | 2/5 (40%) | 2/5 (40%) | 277 | Embedding mẫu 0,623 s/call (n=3); tổng ingest chưa đo | Chi phí tài khoản chưa truy xuất |
| B | dev | 8/15 (53,3%) | 9/15 (60%) | 221 | Embedding mẫu 0,455 s/call (n=3); tổng ingest chưa đo | Chi phí tài khoản chưa truy xuất |
| B | test | 1/5 (20%) | 3/5 (60%) | 221 | Embedding mẫu 0,455 s/call (n=3); tổng ingest chưa đo | Chi phí tài khoản chưa truy xuất |
| C (lọc trên B) | dev | 7/15 (46,7%) | 8/15 (53,3%) | 221 | Dùng lại B; không embed riêng; tổng retrieval chưa đo | Chi phí tài khoản chưa truy xuất |
| C (lọc trên B) | test | 1/5 (20%) | 3/5 (60%) | 221 | Dùng lại B; không embed riêng; tổng retrieval chưa đo | Chi phí tài khoản chưa truy xuất |

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | 1,0/2 (10 vị trí) | 14/15 | N/A (baseline không lọc) | 0: 0, 1: 1, 2: 4; trung bình 1,8/2 |
| B | 1,6/2 (10 vị trí) | 15/15 | N/A (baseline không lọc) | 0: 0, 1: 0, 2: 5; trung bình 2,0/2 |
| C | 1,6/2 (cùng chunks B) | 14/14 kết quả trả về | 1/1 câu filter; 2/2 hit tuân thủ section | 0: 0, 1: 0, 2: 5; trung bình 2,0/2 |


| Trang | Passage/offset chuẩn hóa | A /2 | B=C /2 | Lý do |
|---:|---|---:|---:|---|
| 1 | “Trong kỷ nguyên công nghệ số” / 146 | 1 | 2 | A cắt giữa phần giới thiệu; B giữ trọn ý chính về vai trò phổ biến và giá trị của ảnh. |
| 2 | “Hay trong một vụ việc khác” / 227 | 1 | 1 | A cắt phần mô tả; B giữ gần đủ câu chuyện nhưng chunk mở/đóng bằng câu dở dang. |
| 3 | “Lịch sử nghiên cứu về bài toán” / 468 | 0 | 1 | A chỉ còn đầu câu ở mép chunk; B có nội dung rõ hơn nhưng vẫn bị cắt ở cuối. |
| 4 | “Dua et al. (2020)” / 93 | 1 | 2 | A cắt mô tả phương pháp; B giữ trọn phương pháp DCT/SVM và dễ hiểu độc lập. |
| 5 | “Trong một nghiên cứu khác, Qazi et al.” / 432 | 0 | 1 | A chỉ chứa phần mở đầu trước khi bị cắt; B có một phần phương pháp nhưng cắt mất tiếp nối. |
| 6 | “Muley el al. (2024)” / 200 | 1 | 1 | Cả A và B đều mở từ câu/đoạn nối trước đó; B giữ được phần lớn ý về framework nhưng ranh giới vẫn chưa sạch. |
| 7 | “Để giải quyết trọn vẹn vấn đề đó” / 93 | 2 | 2 | Cả hai chunk đều truyền đạt được mục tiêu so sánh và danh sách kiến trúc CNN. |
| 8 | “Thứ nhất, nghiên cứu bị giới hạn” / 117 | 1 | 2 | A cắt cuối ý về tính khái quát; B giữ các giới hạn chính trong ngữ cảnh đầy đủ hơn. |
| 9 | “Ngày nay, trong thời đại công nghệ” / 160 | 1 | 2 | A dừng giữa phần giới thiệu; B giữ trọn đoạn về vai trò ảnh làm bằng chứng. |
| 10 | “Copy-Move được xem” / 94 | 2 | 2 | Cả hai giữ đủ lời giải thích vì sao Copy-Move khó phát hiện. |


- **Ghi chú audit:** q16/A chỉ có ngữ cảnh ELA/CNN liên quan nhưng top-3 không trả về trang 28 chứa lý do trực tiếp, chấm grounding 1. q16/B và C có đoạn trả lời ở hạng 3. q20 có gold evidence bị chia qua ranh giới chunk nên exact-quote Hit@3 chấm trượt, nhưng top-3 vẫn đủ nội dung để trả lời khi đọc thủ công. q18/C lọc đúng `section=3.3.2` nhưng chỉ có 2 kết quả; cả hai tuân thủ filter và có đoạn đủ nêu Train 70%, Validation 15%, Test 15%. q18/A top-1 có evidence đúng nhưng metadata `section="5"` không khớp heading 3.3.2, là một lỗi metadata.

- **Ghi chú metadata toàn corpus:** kiểm tra định dạng sơ bộ thấy 39/277 chunk A và 32/221 chunk B có giá trị `section` không khớp mẫu ID phân cấp như `2.4.5` hoặc `CHƯƠNG 2` (các giá trị đáng ngờ gồm `0`, `5`, `2019`). Đây là cờ rà soát, không khẳng định mọi giá trị đó đều sai; cần sửa regex/đối chiếu heading nguồn trước khi dựa vào filter C rộng hơn.

| Câu test | A grounding /2* | B grounding /2* | C grounding /2* | Lý do audit top-3 |
|---|---:|---:|---:|---|
| q16 | 1 | 2 | 2 | A trả về nội dung liên quan ELA/CNN nhưng thiếu lý do dùng dấu vết nén thay cho ngữ nghĩa; B/C có đoạn trả lời trực tiếp ở rank 3, trang 28. |
| q17 | 2 | 2 | 2 | Top-3 có bằng chứng về lợi ích Transfer Learning khi dữ liệu ít, trang 35. |
| q18 | 2 | 2 | 2 | Top-3 nêu đủ tỉ lệ Train 70%, Validation 15%, Test 15%, trang 46. C trả 2 hit thay vì 3; cả 2 có section 3.3.2. |
| q19 | 2 | 2 | 2 | Top-3 có bằng chứng chỉ augmentation Train và giữ nguyên Validation/Test, trang 48. |
| q20 | 2 | 2 | 2 | Top-3 đủ nêu mất cân bằng lớp, hạn chế Accuracy và AUC qua nhiều ngưỡng, trang 60; exact quote bị chia giữa chunk nên bộ chấm tự động đánh trượt. |


## Phân tích và kết luận

- Trên dev, B cao nhất (Hit@1 8/15, Evidence Hit@3 9/15). Trên test, B/C cùng đạt Evidence Hit@3 3/5 và A đạt 2/5; A có Hit@1 2/5 so với 1/5 của B/C. Với chỉ 5 câu test, một câu làm thay đổi tỷ lệ 20 điểm phần trăm.
- C không tăng điểm tự động so với B trên test; q18 là test có filter duy nhất. Audit thủ công thấy C tuân thủ filter, nhưng section metadata cần rà soát vì A/q18 có giá trị section sai. Không kết luận cấu hình thắng chung.
- Ví dụ retrieval thiếu rõ nhất: q16/A (gold trang 28, top-3 ở trang 29/26/27 nên thiếu lý do cụ thể). Trường hợp q20 là false negative của exact-quote metric do evidence bị cắt qua chunk, không ghi nhận là retrieval thiếu sau audit thủ công.
- Hạn chế: test nhỏ; tiêu chí chọn chưa được ghi trước khi xem test; thời gian ingest/embed và chi phí chưa ghi đầy đủ; section metadata có giá trị đáng ngờ; bốn evidence quote chưa khớp exact source.


