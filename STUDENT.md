# Thông tin học viên

- Họ và tên: Nguyễn Thùy Lam
- MSSV: 2A202603632
- Lớp: L3A 
- Chủ đề và corpus: Phương pháp Học sâu cho bài toán phát hiện ảnh giả mạo; PDF `data/data-for-lab.pdf` (60 trang vật lý, pipeline trích xuất được 60 trang có text; quyền sử dụng được khai trong `data/manifest.json`).
- Repo bài nộp: thư mục dự án DataIngestionEngineering này; pipeline trong `starter/`.
- Commit chốt bài: Chưa chốt.

## Tiến độ đã xác nhận

- Đã chuẩn bị manifest corpus và benchmark 20 câu trong `data/format.json` (15 dev / 5 test; 3 câu có metadata filter, gồm 1 câu test).
- Đã chạy ingest và xuất log trang cùng chunks A/B: 0 trang lỗi, 0 trang rỗng; A fixed-size (500 ký tự, overlap 50) có 277 chunks; B paragraph (tối đa 800 ký tự) có 221 chunks.
- Docker Compose/PostgreSQL + pgvector setup được người thực hiện xác nhận thành công.
- Đã embed và lưu thành công `gemini-embedding-2`, 768 chiều: A=277 vectors, B=221 vectors.
- Đã chạy retrieval cho 20 câu × A/B/C và lưu `starter/results/retrieval_traces.jsonl`, `starter/results/retrieval_summary.json`.
- Đã đo latency embedding mẫu không chứa header tên tác giả: A 3 chunks trung bình 0,623 giây/call; B 3 chunks trung bình 0,455 giây/call. 
- Đã điền `artifacts/experiment_log.csv`
- Đã có audit coherence trên 10 vị trí cùng nhau từ trang 1–10: A trung bình 1,0/2; B/C 1,6/2. Grounding test: A trung bình 1,8/2; B/C 2,0/2. Tác giả cần xác nhận nhãn trước khi nộp.
- Audit metadata test: A 14/15 đúng/đủ, B 15/15, C 14/14 kết quả trả về; filter C tuân thủ 1/1 câu test có filter (2/2 kết quả). Phát hiện metadata `section` sai ở q18/A.

Chi tiết và artifact được liệt kê trong [`report/individual/2A202603632_NguyenThuyLam.md`](report/individual/2A202603632_NguyenThuyLam.md).
