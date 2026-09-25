# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `7Goat`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3-DAY10-7Goat-DataPipeline`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Nguyễn Xuân Trường Giang (trưởng nhóm) | 2A202602446 | | Trưởng nhóm / Tích hợp pipeline và kiểm thử cuối (`phase1.py`, `corruption_flow.py`) | `report/2A202602446_NguyenXuanTruongGiang.md` |
| 2 | Nguyễn Nhân Sâm | 2A202602672 | | Ingestion, làm sạch & phục hồi (`crossref.py`, `cleaning.py`) | `report/2A202602672_NguyenNhanSam.md` |
| 3 | Phan Trọng Hoàn | 2A202602954 | | RAG & Vector Index (`embeddings.py`, `index.py`, `qa.py`, `agent.py`) | `report/2A202602954_PhanTrongHoan.md` |
| 4 | Đào Đức Hải | 2A202602752 | | Data Observability & Báo cáo (`quality.py`, `reporting.py`) | `report/2A202602752_DaoDucHai.md` |
| 5 | Võ Doanh Nhân | 2A202602770 | | Evaluation & Synthetic Corruption (`testset.py`, `metrics.py`, `corruption.py`) | `report/2A202602770_VoDoanhNhan.md` |

---

## # Cá nhân

### ## NguyenXuanTruongGiang-2A202602446
- **Vai trò:** Trưởng nhóm, tích hợp các module của cả nhóm và kiểm thử cuối.
- **Công việc chi tiết đã hoàn thành:**
  - Ghép module của các thành viên vào `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Repair idempotent: dựng lại data sạch từ `data/raw/`, không sửa tay.
  - Kiểm thử cuối end-to-end: `python script/run_phase1.py` và `python script/run_corruption_flow.py`.
  - Đối chiếu artifact sau khi chạy: `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `phase1_report.md`, `corruption_report.md`.
- **Điều học được / Đóng góp chính:**
  - Tích hợp pipeline nhiều người và kiểm thử toàn tuyến trước khi nộp, gồm cả lúc Quality Gate và Freshness SLA bắt dữ liệu bẩn.
- **Tín hiệu xong:** Hai lệnh chạy thành công. Hit Rate baseline 1.00, corrupted 0.80, repaired 1.00. Data sạch `success=True`; data bẩn `success=False` và `is_fresh=False`.

### ## NguyenNhanSam-2A202602672
- **Vai trò:** Phụ trách Ingestion, Làm sạch & Phục hồi dữ liệu.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với cơ chế fallback offline trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, tính `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Giữ raw snapshot để repair đọc lại qua `load_raw_records`.
- **Điều học được / Đóng góp chính:**
  - Truy vết nguồn gốc dữ liệu và bảo toàn raw snapshot trước khi biến đổi.
- **Tín hiệu xong:** Đã tải 24 bài báo và clean thành công 24 dòng (`data/clean/papers_clean.csv`).

### ## PhanTrongHoan-2A202602954
- **Vai trò:** Phụ trách RAG, Vector Database & Embedding.
- **Công việc chi tiết đã hoàn thành:**
  - Quản lý mô hình embedding `sentence-transformers/all-MiniLM-L6-v2`.
  - Nạp và quản lý 3 collection riêng biệt trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
  - Xây dựng QA Agent truy vấn ngữ cảnh theo tài liệu.
- **Điều học được / Đóng góp chính:**
  - Cách cô lập các không gian vector để so sánh khách quan giữa dữ liệu sạch và dữ liệu bị lỗi.
- **Tín hiệu xong:** Collection `papers-baseline` có 24 documents. MiniLM embed được `text_for_embedding`.

### ## DaoDucHai-2A202602752
- **Vai trò:** Phụ trách Data Observability & Báo cáo.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate theo chuẩn **Great Expectations 1.x** trong `src/observability/quality.py`: `gx.get_context(mode="ephemeral")`, `add_pandas()`, 4 expectations (row count, not null, unique `paper_id`, summary dài tối thiểu 30 ký tự).
  - Freshness SLA: `is_fresh = False` khi tỷ lệ bài có `age_days > 180` vượt 25%.
  - Viết `generate_phase1_report` và `generate_corruption_report` trong `src/observability/reporting.py` (bảng 3 cột Baseline / Corrupted / Repaired).
- **Điều học được / Đóng góp chính:**
  - Cách thiết lập hệ thống cảnh báo sớm chặn đứng hiện tượng Silent Failure trước khi dữ liệu vào serving layer.
- **Tín hiệu xong:** Quality check `success=True` trên data sạch. Data bẩn có `success=False` và `is_fresh=False`. `data/reports/phase1_report.md` và `data/reports/corruption_report.md` có đủ số liệu.

### ## VoDoanhNhan-2A202602770
- **Vai trò:** Phụ trách Evaluation & Synthetic Corruption.
- **Công việc chi tiết đã hoàn thành:**
  - Sinh 10 câu test trong `src/evaluation/testset.py`, phủ 4 nhóm `summary`, `authors`, `date`, `categories`, ghi `data/eval/test_set.json`.
  - Rà soát Hit Rate và Token F1 trong `src/evaluation/metrics.py`.
  - Tiêm 6 lỗi trong `src/ingestion/corruption.py`: drop 20% bản ghi mới, blank summary, inject noise, truncate title dưới 8 ký tự, stale date, duplicate rows; rebuild `text_for_embedding` và ghi `data/results/corruption_log.json`.
- **Điều học được / Đóng góp chính:**
  - Cách đo mức suy giảm của RAG khi dữ liệu bẩn và chứng minh Quality Gate bắt được lỗi.
- **Tín hiệu xong:** Sinh được 10 câu hỏi test. `corruption_log.json` ghi đủ 6 dạng lỗi. Hit Rate giảm từ 1.00 xuống 0.80 rồi hồi về 1.00 sau repair.
