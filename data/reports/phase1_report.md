# Báo Cáo Pha 1: Baseline Pipeline & Data Observability

> **Ngày tạo:** Tự động sinh bởi Data Pipeline  
> **Chế độ:** Baseline (Dữ liệu sạch chuẩn)  
> **Trạng thái kiểm tra chất lượng (GX 1.x):** ✅ PASS (Đạt chuẩn)  
> **Trạng thái độ tươi mới (Freshness SLA):** 🟢 FRESH (Tươi mới)  

---

## 1. Tóm Tắt Nguồn & Quá Trình Thu Thập Dữ Liệu
Hệ thống kết nối và bảo toàn bản sao dữ liệu thô (Data Lineage) trước khi tiến hành chuẩn hóa schema và lọc sạch văn bản.

| Thuộc tính | Giá trị ghi nhận |
| :--- | :--- |
| **Nguồn dữ liệu (Source API)** | `Crossref REST API` |
| **Truy vấn tìm kiếm (Search Query)** | `agentic retrieval augmented generation large language model` |
| **Bộ lọc (Filter)** | `from-pub-date:2026-03-29,has-abstract:true` |
| **Số bản ghi thô (Raw Records)** | `24` |
| **Số bản ghi sau làm sạch (Clean Rows)** | `24` |
| **ChromaDB Vector Collection** | `papers-baseline` |

---

## 2. Trạm Kiểm Soát Dữ Liệu Great Expectations 1.x (Data Quality Gate)
Data Quality Gate vận hành trên RAM (ephemeral mode) thiết lập 4 hàng rào kiểm soát chất lượng nghiêm ngặt trước khi nhúng vector:

- **Kết quả tổng quát:** `✅ PASS (Toàn bộ Expectations thành công)`
- **Số Expectations đánh giá:** `6`
- **Số Expectations thành công:** `6`
- **Số Expectations thất bại:** `0`
- **Tỷ lệ thành công:** `100.0%`

### Bảng chi tiết từng kỳ vọng kiểm thử:
| STT | Tên kỳ vọng (Expectation) | Cột / Phạm vi kiểm tra | Trạng thái |
| :---: | :--- | :--- | :---: |
| 1 | `expect_table_row_count_to_be_between` | `Table` | ✅ PASS |
| 2 | `expect_column_values_to_not_be_null` | `paper_id` | ✅ PASS |
| 3 | `expect_column_values_to_be_unique` | `paper_id` | ✅ PASS |
| 4 | `expect_column_values_to_not_be_null` | `title` | ✅ PASS |
| 5 | `expect_column_values_to_not_be_null` | `text_for_embedding` | ✅ PASS |
| 6 | `expect_column_value_lengths_to_be_between` | `summary` | ✅ PASS |

---

## 3. Giám Sát Độ Tươi Mới Dữ Liệu (Freshness SLA)
Chính sách Freshness SLA quy định cảnh báo dữ liệu bị mốc nếu tỷ lệ bài báo cũ (`age_days > 180 ngày`) vượt quá ngưỡng 25%.

| Thuộc tính giám sát | Kết quả đo lường | Ngưỡng cam kết (SLA) | Trạng thái |
| :--- | :---: | :---: | :---: |
| **Tổng số bài báo theo dõi** | `24` | - | - |
| **Số bài báo cũ (> 180 ngày)** | `1` | - | - |
| **Tỷ lệ bài báo cũ** | `4.2%` | `<= 25.0%` | `✅ Đạt chuẩn SLA` |
| **Thời điểm xuất bản mới nhất** | `2026-07-22` | - | - |
| **Thời điểm xuất bản cũ nhất** | `2026-03-28` | - | - |
| **Kết luận độ tươi mới** | `is_fresh = True` | `is_fresh = True` | `🟢 FRESH` |

---

## 4. Hiệu Năng Truy Vấn & Trả Lời Của Baseline RAG (Benchmark Metrics)
Bộ đề thi chuẩn gồm các câu hỏi bao quát 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`) được dùng để thiết lập mốc đo lường ban đầu:

| Chỉ số đánh giá | Điểm số Baseline | Ý nghĩa kỹ thuật |
| :--- | :---: | :--- |
| **`retrieval_hit_rate`** | `1.0000` | Tỷ lệ context tìm kiếm chứa đúng mã DOI của bài báo mục tiêu |
| **`mean_token_f1`** | `1.0000` | Độ chính xác trùng khớp từ vựng giữa câu trả lời và Ground Truth |
| **`judge_accuracy`** | `1.0000` | Tỷ lệ câu trả lời được LLM Judge công nhận đúng về nội dung |
| **`mean_judge_score`** | `5.0000` | Điểm đánh giá chất lượng câu trả lời trung bình (thang điểm 1 - 5) |
| **Số lượng câu hỏi kiểm thử** | `10` | Quy mô bộ đề kiểm thử chuẩn hóa |
