# Báo cáo cá nhân — Nguyễn Nhân Sâm

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Nhân Sâm |
| MSSV | 2A202602672 |
| Khóa/Lớp | K4-L3 |
| Tên nhóm | 7Goat |
| Vai trò chính | Ingestion, làm sạch và giữ raw để repair |
| Repository | https://github.com/GiangDA881/K4-L3-DAY10-7Goat-DataPipeline |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Parse và fetch Crossref | `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | Payload API hoặc snapshot | `data/raw/crossref_records.json` | Hoàn thành |
| Cleaning | `build_clean_dataframe` | List `PaperRecord`, `run_date` | Dataframe 24 dòng có `age_days` và `text_for_embedding` | Hoàn thành |

Người tích hợp dùng `load_raw_records` khi repair. Mình không sửa file corrupted.

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/artifact | Kết quả | Cách xác minh |
| --- | --- | --- | --- |
| Giữ lineage | `data/raw/crossref_response.json`, `crossref_records.json` | Raw gốc còn nguyên để đọc lại | Repair ra lại 24 dòng |
| Làm sạch | `data/clean/papers_clean.csv` | 24 dòng, dedupe theo DOI | Phase 1 in `Clean: 24 dong` |

## 4. Giải thích phần kỹ thuật đã thực hiện

Ingestion đọc Crossref, bỏ tag JATS trong abstract, map DOI thành `paper_id`. Khi API lỗi 429 hoặc mất mạng, hàm đọc snapshot local thay vì làm pipeline chết. Cleaning bỏ trùng `paper_id`, tính `age_days`, và ghép `text_for_embedding` thành năm dòng Title, Authors, Published, Categories, Summary. Dataframe được sort ngày xuất bản mới nhất trước.

| Thành phần | Mô tả |
| --- | --- |
| Input | JSON Crossref hoặc file raw records |
| Output | `PaperRecord` và dataframe sạch |
| Module phụ thuộc | `core.config.Settings` cho đường dẫn |
| Module sử dụng output | Index, quality, test set, repair |
| Lỗi cần xử lý | Record thiếu DOI hoặc abstract thì không đưa vào clean |

```bash
python script/run_phase1.py
```

- **Kết quả mong đợi:** 24 dòng sạch.
- **Kết quả thực tế:** `papers_clean.csv` có 24 dòng.
- **Artifact:** `data/clean/papers_clean.csv`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Repair có thể sửa trên dataframe bẩn hoặc làm lại từ raw.
- **Phương án:** Vá từng ô bị corruption, hoặc parse lại snapshot.
- **Đã chọn:** Giữ raw bất biến và để pipeline clean lại từ đó.
- **Lý do:** Vá tay không idempotent. Raw là nguồn duy nhất còn đáng tin sau khi file sạch đã bị tiêm lỗi.
- **Bằng chứng:** `papers_clean_repaired.json` có 24 dòng, trùng schema baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Abstract Crossref còn tag `<jats:p>`.
- **Nguyên nhân:** API trả abstract dạng JATS, không phải plain text.
- **Cách xử lý:** Gỡ tag khi parse, rồi normalize khoảng trắng lúc clean.
- **Xác minh:** Cột `summary` trong CSV không còn tag XML; expectation độ dài summary pass ở baseline.
- **Bài học:** Dữ liệu học thuật trông như text nhưng vẫn là markup.

## 7. Hiểu biết về luồng end-to-end

1. Raw JSON thành record, record thành dataframe, dataframe thành document trong Chroma.
2. Test set lấy DOI làm `ground_truth_doc_ids`. Retrieval đúng khi DOI đó được tìm thấy.
3. Quality Gate nhìn null, unique, độ dài. Freshness chỉ nhìn `age_days` do cleaning tính.
4. Cùng test set thì repair chỉ được tính là hồi phục nếu điểm tăng nhờ dữ liệu, không nhờ đổi đề.
5. Repair thành công khi raw được clean lại thành 24 dòng và metric bằng baseline.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.00 | 0.80 | 1.00 | Dữ liệu sạch tìm đủ DOI |
| `mean_token_f1` | 1.00 | 0.87 | 1.00 | Summary bẩn làm câu trả lời lệch |
| `judge_accuracy` | 1.00 | 0.80 | 1.00 | Khớp chiều giảm của Hit Rate |
| `mean_judge_score` | 5.00 | 4.40 | 5.00 | Hồi đủ sau repair |
| Quality checks | Pass | Fail | Pass | File bẩn không qua unique và độ dài summary |
| Freshness status | Fresh | Stale | Fresh | `age_days` bị sửa ở nhánh corruption, raw không bị sửa |

1. Summary rỗng và DOI trùng làm Gate fail, đồng thời Hit Rate giảm.
2. Đọc lại raw và clean lại đưa freshness về 4.17% và Hit Rate về 1.00.

Corruption rõ nhất với phần dữ liệu của mình là blank summary, vì cột này vừa fail expectation vừa là phần Summary trong `text_for_embedding`.

## 9. Điều học được và hướng cải thiện

1. Raw phải được đóng băng trước mọi bước biến đổi.
2. `age_days` là cầu nối giữa cleaning và Freshness SLA.
3. Agent chỉ tốt khi `text_for_embedding` còn đủ năm phần.

Nếu có thêm thời gian, ghi số record bị loại vì thiếu DOI vào một lineage log riêng, để biết 24 dòng là phần còn lại hay là toàn bộ payload.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Nhân Sâm
**Ngày xác nhận:** 2026-09-25
