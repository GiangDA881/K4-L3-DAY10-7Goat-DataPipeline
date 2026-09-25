# Báo Cáo Đối Chiếu 3 Trạng Thái: Baseline vs Corrupted vs Repaired

> **Mục tiêu:** Chứng minh hiện tượng **Silent Failure** khi dữ liệu bị lỗi và kiểm chứng năng lực **Tự Phục Hồi An Toàn (Idempotent Repair)** từ bản sao lưu dữ liệu gốc (Raw Preservation).

---

## 1. Bảng So Sánh Hiệu Năng 3 Trạng Thái (Three-State Comparison Table)

| Chỉ số / Tín hiệu đo lường | Baseline (Chuẩn sạch) | Corrupted (Tiêm lỗi) | Repaired (Sau phục hồi) | Tác động của lỗi (Δ) | Tỷ lệ phục hồi (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`retrieval_hit_rate`** | `1.0000` | `0.8000` | `1.0000` | `-0.2000` | `100.0%` |
| **`mean_token_f1`** | `1.0000` | `0.8741` | `1.0000` | `-0.1259` | `100.0%` |
| **`judge_accuracy`** | `1.0000` | `0.8000` | `1.0000` | `-0.2000` | `100.0%` |
| **`mean_judge_score`** | `5.0000` | `4.4000` | `5.0000` | `-0.6000` | `100.0%` |
| **Quality Gate (GX 1.x)** | `✅ PASS` | `❌ FAIL` | `✅ PASS` | Báo động đỏ khi có lỗi | Khôi phục 100% Expectations |
| **Freshness SLA (`is_fresh`)** | `🟢 FRESH` | `🔴 STALE` | `🟢 FRESH` | Tỷ lệ cũ: 33.3% | Tỷ lệ cũ: 4.2% |

---

## 2. Phân Tích Chốt Kiểm Soát Chất Lượng (Great Expectations 1.x Gate)
- **Khi dữ liệu bị tiêm lỗi (Corrupted State):**  
  Quality Gate lập tức phát hiện các vi phạm cấu trúc nghiêm trọng (kết quả `success = False`):
  - Lỗi trùng lặp dữ liệu bị bắt bởi `ExpectColumnValuesToBeUnique(column='paper_id')`.
  - Lỗi xóa trắng tóm tắt bị bắt bởi `ExpectColumnValuesToNotBeNull` và `ExpectColumnValueLengthsToBeBetween(column='summary', min_value=30)`.
  - Lỗi mất bản ghi mới làm thay đổi số dòng bị bắt bởi `ExpectTableRowCountToBeBetween`.
- **Sau khi chạy quy trình phục hồi (Repaired State):**  
  Quality Gate xác nhận trạng thái hoàn toàn lành lặn với `success = True`. Tất cả các kỳ vọng đều vượt qua trước khi dữ liệu được phép nạp lại vào Vector Database.

---

## 3. Phân Tích Độ Tươi Mới (Freshness SLA Monitoring)
- **Tập dữ liệu Corrupted:** Tỷ lệ bài báo cũ (`age_days > 180`) tăng lên **33.3%**, kích hoạt cờ cảnh báo `is_fresh = False` do vượt quá hạn mức 25%.
- **Tập dữ liệu Repaired:** Dữ liệu chuẩn được khôi phục, tỷ lệ quá hạn đưa về mức an toàn **4.2%**, trạng thái `is_fresh = True`.

---

## 4. Nhận Định Kỹ Thuật: Silent Failure & Idempotent Repair
1. **Căn bệnh Silent Failure trong RAG:**  
   Khi dữ liệu bị hỏng hóc, Agent AI không đưa ra bất kỳ exception hay mã lỗi runtime nào mà vẫn tự tin sinh ra câu trả lời sai lệch (Hallucination) do vector context bị nhiễu. Bảng đối chiếu số liệu ở trên chứng minh rõ ràng: `retrieval_hit_rate` và `mean_token_f1` bị suy giảm đáng kể. Điều này khẳng định tầm quan trọng sống còn của Data Observability Gate.
2. **Năng lực Phục Hồi Bất Biến (Idempotent Repair):**  
   Quy trình phục hồi không vá víu tạm bợ trên tập dữ liệu đã ô nhiễm, mà khởi động lại từ nguồn lưu trữ nguyên thủy `data/raw/crossref_records.json`. Cơ chế này đảm bảo tính Idempotent: chạy bao nhiêu lần thì kết quả cuối cùng vẫn đồng nhất, đưa các chỉ số hiệu năng RAG trở lại nguyên vẹn như mốc Baseline ban đầu.
