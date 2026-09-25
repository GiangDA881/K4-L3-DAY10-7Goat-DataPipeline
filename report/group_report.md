# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3 |
| Tên nhóm | 7Goat |
| Repository | https://github.com/GiangDA881/K4-L3-DAY10-7Goat-DataPipeline |
| Ngày hoàn thành | 2026-09-25 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Xuân Trường Giang | 2A202602446 | Trưởng nhóm, tích hợp và kiểm thử cuối | `phase1.py`, `corruption_flow.py`, artifact end-to-end |
| 2 | Nguyễn Nhân Sâm | 2A202602672 | Ingestion và cleaning | `crossref.py`, `cleaning.py`, `data/raw/`, `data/clean/papers_clean.csv` |
| 3 | Phan Trọng Hoàn | 2A202602954 | RAG và vector index | `embeddings.py`, `index.py`, `qa.py`, `agent.py`, 3 collection Chroma |
| 4 | Đào Đức Hải | 2A202602752 | Observability và báo cáo | `quality.py`, `reporting.py`, `data/quality/`, `data/reports/` |
| 5 | Võ Doanh Nhân | 2A202602770 | Evaluation và corruption | `testset.py`, `metrics.py`, `corruption.py`, `data/eval/test_set.json` |

## 2. Tóm tắt kết quả

Nhóm xây dựng pipeline RAG cho 24 bài báo Crossref: giữ raw, làm sạch, chấm chất lượng bằng Great Expectations 1.x, embed MiniLM vào ChromaDB, rồi đánh giá trên một test set 10 câu. Baseline đạt Hit Rate 1.00 và Token F1 1.00. Quality Gate `success=True`, freshness `is_fresh=True` vì chỉ 1/24 bài có `age_days > 180` (4.17%).

Corruption tiêm 6 lỗi trên cùng bảng sạch: bỏ 5 bài mới nhất, xóa 3 summary, nhiễu 2 summary, cắt 1 title, lùi 6 ngày xuất bản về 2015-01-01, nhân 2 dòng. Quality Gate chuyển `success=False` vì `paper_id` không unique và summary ngắn hơn 30 ký tự. Freshness chuyển `is_fresh=False` vì 7/21 dòng quá hạn (33.33%). Hit Rate giảm còn 0.80, Token F1 còn 0.87.

Repair không sửa tay file bẩn. Pipeline đọc lại `data/raw/crossref_records.json`, clean lại và index collection `papers-repaired`. Cả bốn metric và hai tín hiệu chất lượng trở về đúng mức baseline. Ragas không chạy vì chưa bật `RUN_RAGAS=1`.

## 3. Kiến trúc và luồng dữ liệu

```text
Crossref snapshot data/raw/crossref_response.json
    -> data/raw/crossref_records.json
    -> cleaning
    -> data/clean/papers_clean.csv
    -> MiniLM + Chroma papers-baseline
    -> data/eval/test_set.json
    -> baseline_metrics.json + quality/freshness
    -> corruption_log.json + papers-corrupted
    -> repair từ raw records
    -> papers-repaired
    -> corruption_report.md
```

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Snapshot Crossref hoặc API | Parse DOI, title, abstract, authors, date; fallback offline | `data/raw/crossref_records.json` | Nguyễn Nhân Sâm |
| Cleaning | `PaperRecord` | Dedupe `paper_id`, `age_days`, `text_for_embedding` 5 phần | `data/clean/papers_clean.csv` (24 dòng) | Nguyễn Nhân Sâm |
| Embedding/index | Dataframe sạch | `all-MiniLM-L6-v2`, cosine HNSW | Collection `papers-baseline` (24 docs) | Phan Trọng Hoàn |
| Evaluation | Clean dataframe | 10 câu, 4 loại, cùng file cho 3 trạng thái | `data/eval/test_set.json` | Võ Doanh Nhân |
| Observability | Dataframe | GX 1.x ephemeral, 4 expectations, SLA 180 ngày / 25% | `data/quality/*.json`, `data/reports/*.md` | Đào Đức Hải |
| Corruption/repair | Clean dataframe và raw records | 6 lỗi có seed 42; repair bằng clean lại từ raw | `corruption_log.json`, metrics corrupted/repaired | Võ Doanh Nhân và Nguyễn Xuân Trường Giang |
| Orchestration | Settings | Phase 1 rồi corruption flow | Toàn bộ artifact trong `data/results/` | Nguyễn Xuân Trường Giang |

## 4. Cách tái hiện kết quả

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `openai` (endpoint tương thích OpenAI, không ghi API key) |
| `LLM_MODEL` | `mistralai/mistral-large-2512` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày, stale ratio tối đa 0.25 |
| Random seed corruption | 42 |

```bash
uv sync
python script/run_phase1.py
python script/run_corruption_flow.py
```

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công | 2026-09-25 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow | Thành công | 2026-09-25 | `data/results/corruption_log.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API, fallback `data/raw/crossref_response.json` |
| Query/filter | `agentic retrieval augmented generation large language model`; `has-abstract:true` |
| Số record nhận được | 24 |
| Cơ chế retry/backoff | Fetch có retry khi API trả 429/503; mất mạng thì đọc snapshot local |

| Trường | Kiểu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | string (DOI) | Có | Định danh bài báo | Bỏ record không có DOI |
| `title` | string | Có | Tiêu đề | Chuẩn hóa khoảng trắng |
| `summary` | string | Có | Abstract, đã bỏ tag JATS | Bỏ record không đủ nội dung |
| `published` | date | Có | Ngày xuất bản | Không tính được `age_days` thì không đưa vào clean |
| `age_days` | int | Có | Số ngày từ ngày xuất bản tới ngày chạy | Dùng cho Freshness SLA |
| `text_for_embedding` | string | Có | Ngữ cảnh đưa vào MiniLM | Ghép Title, Authors, Published, Categories, Summary |

`text_for_embedding` là năm dòng cố định: Title, Authors, Published, Categories, Summary. `paper_id` là DOI. `age_days = (run_date - published).days`. Clean sort `published` giảm dần để corruption bỏ đúng 20% bài mới nhất.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 10 |
| Các `question_type` | `summary`, `authors`, `date`, `categories` |
| Ground-truth document ID | DOI trong `ground_truth_doc_ids` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | Chroma persistent, cosine; `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | OpenAI-compatible, `mistralai/mistral-large-2512` cho judge |
| Test set dùng chung | `data/eval/test_set.json` |

Ba trạng thái dùng cùng file test set. Nếu sinh đề mới sau corruption, sự giảm điểm có thể đến từ đề khác chứ không phải từ dữ liệu bẩn.

## 7. Kết quả baseline

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | 2 file JSON |
| Cleaned dataset | `data/clean/papers_clean.csv` | Có | 24 dòng |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/` | Có khi chạy local | Chroma và embedding manifest không commit vì dung lượng |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | 10 mẫu |
| Quality/freshness | `data/quality/` | Có | Baseline success 100% |
| Baseline report | `data/reports/phase1_report.md` | Có | |

| Metric | Giá trị | Diễn giải |
| --- | --- | --- |
| `retrieval_hit_rate` | 1.00 | 10/10 câu tìm đúng DOI |
| `mean_token_f1` | 1.00 | Câu trả lời khớp ground truth |
| `judge_accuracy` | 1.00 | Judge đánh đúng toàn bộ |
| `mean_judge_score` | 5.00 | Thang 1–5 |
| Ragas | Không chạy | `RUN_RAGAS` không bật |

## 8. Data quality và freshness

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| Row count | Completeness | 5–5000 dòng | Pass, 24 dòng | `baseline_quality_report.json` |
| `paper_id`, `title`, `text_for_embedding` not null | Completeness | Không null | Pass | cùng file |
| `paper_id` unique | Uniqueness | Không trùng DOI | Pass | cùng file |
| `summary` length | Validity | Tối thiểu 30 ký tự | Pass | cùng file |

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | `data/quality/freshness_report.json` |
| Timestamp mới nhất | 2026-07-22 |
| Ngưỡng freshness | `age_days > 180` và tỷ lệ tối đa 25% |
| Trạng thái baseline | Fresh (`is_fresh=true`, stale 1/24 = 4.17%) |
| Lý do | Chỉ một bài vượt 180 ngày, dưới ngưỡng 25% |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | --- | --- | --- | --- |
| Drop latest | Bỏ 20% dòng đầu sau khi sort ngày mới nhất | 5 | Mất ngữ cảnh bài mới | Hit Rate giảm | Clean lại từ raw |
| Blank summary | Gán summary rỗng | 3 | Fail độ dài summary | Summary length fail | Clean lại từ raw |
| Inject noise | Nối token rác vào summary | 2 | Nhiễu embedding | Góp phần giảm F1 | Clean lại từ raw |
| Truncate title | Cắt title còn dưới 8 ký tự | 1 | Khó khớp câu hỏi theo title | Góp phần miss retrieval | Clean lại từ raw |
| Stale date | Đưa `published` về 2015-01-01 | 6 | Freshness fail | 7/21 dòng quá hạn, `is_fresh=false` | Clean lại từ raw |
| Duplicate rows | Nhân bản dòng chưa bị sửa | 2 | Unique `paper_id` fail | Uniqueness fail, còn 21 dòng | Clean lại từ raw |

Corruption log `data/results/corruption_log.json` có đủ 6 loại, danh sách DOI và seed 42. `final_rows` = 21.

Repair gọi `load_raw_records` trên snapshot raw rồi `build_clean_dataframe`. Không đọc file corrupted để “vá”. Chạy lại vẫn ra 24 dòng sạch vì nguồn là raw.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.00 | 0.80 | 1.00 | -0.20 | Về 1.00 | 2/10 câu mất đúng DOI |
| `mean_token_f1` | 1.00 | 0.87 | 1.00 | -0.13 | Về 1.00 | Câu trả lời lệch khi summary/title hỏng |
| `judge_accuracy` | 1.00 | 0.80 | 1.00 | -0.20 | Về 1.00 | Cùng mức giảm với Hit Rate |
| `mean_judge_score` | 5.00 | 4.40 | 5.00 | -0.60 | Về 5.00 | Judge vẫn cho điểm cao ở câu còn đúng |
| Quality checks | Pass 6/6 | Fail 2/6 | Pass 6/6 | Unique và summary length fail | Pass lại | Row count vẫn pass vì 21 dòng nằm trong 5–5000 |
| Freshness | Fresh 4.17% | Stale 33.33% | Fresh 4.17% | Vượt ngưỡng 25% | Về 4.17% | Do 6 ngày bị lùi về 2015 |

1. Duplicate và blank summary làm Quality Gate fail, đồng thời drop/truncate làm Hit Rate từ 1.00 xuống 0.80. Agent không ném exception; đó là silent failure nhìn thấy qua metric.
2. Repair từ raw đưa quality về 6/6, freshness về 4.17%, và cả bốn metric RAG về đúng baseline.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Lần corruption đầu, Quality Gate fail nhưng `is_fresh` vẫn true (stale 3/21 = 14.29%).
- **Nguyên nhân:** Tỷ lệ làm cũ ngày chỉ 0.15 trên phần dòng còn lại, không đủ để vượt SLA 25%.
- **Cách xử lý:** Tăng tỷ lệ stale date lên 0.45 để kịch bản lỗi thực sự kích hoạt Freshness SLA, rồi chạy lại `run_corruption_flow.py`.
- **Cách xác minh:** `corrupted_freshness_report.json` có `stale_ratio=0.3333`, `is_fresh=false`. Sau repair, `is_fresh=true`.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Ragas không chạy | Chưa có faithfulness và context precision | Bật `RUN_RAGAS=1` và so với Token F1 |
| Row-count expectation 5–5000 không bắt việc mất 5 bài | Gate không fail chỉ vì drop latest | Siết min/max quanh 24 dòng |
| Chroma local không nằm trong git | Máy chấm phải chạy lại index | Giữ lệnh `run_phase1.py` trong hướng dẫn tái hiện |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong báo cáo.
