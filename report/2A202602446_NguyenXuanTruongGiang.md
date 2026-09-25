# Báo cáo cá nhân — Nguyễn Xuân Trường Giang

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Xuân Trường Giang |
| MSSV | 2A202602446 |
| Khóa/Lớp | K4-L3 |
| Tên nhóm | 7Goat |
| Vai trò chính | Trưởng nhóm, tích hợp pipeline và kiểm thử cuối |
| Repository | https://github.com/GiangDA881/K4-L3-DAY10-7Goat-DataPipeline |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Baseline orchestration | `src/pipelines/phase1.py` | Raw records, hàm clean/index/eval/quality của cả nhóm | `baseline_metrics.json`, `phase1_report.md` | Hoàn thành |
| Corruption orchestration | `src/pipelines/corruption_flow.py` | Clean dataframe, raw records, test set | `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` | Hoàn thành |

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Ghép nhánh observability và evaluation | Đào Đức Hải, Võ Doanh Nhân | Giữ test set 10 câu / 4 loại vì đúng contract `build_test_set(df, path)` |
| Chạy kiểm thử cuối | Cả nhóm | Hai script exit code 0 ngày 2026-09-25 |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/artifact | Kết quả | Cách xác minh |
| --- | --- | --- | --- |
| Nối phase 1 | `script/run_phase1.py` | 24 dòng sạch, Hit Rate 1.00 | `data/results/baseline_metrics.json` |
| Nối corruption và repair | `script/run_corruption_flow.py` | Hit Rate 0.80 rồi về 1.00 | Bảng in ra console và `corruption_report.md` |

Output cụ thể: repair không đọc file bẩn. Hàm `main` của corruption flow gọi `load_raw_records` rồi `build_clean_dataframe`, ghi `papers_clean_repaired.json` với 24 dòng.

## 4. Giải thích phần kỹ thuật đã thực hiện

Pipeline phase 1 đi theo thứ tự cố định: load hoặc fetch raw, clean, lưu CSV/JSON, build collection `papers-baseline`, sinh test set nếu chưa có, evaluate, quality, freshness, rồi viết markdown. Corruption flow chỉ chạy khi baseline artifact đã có; nếu thiếu thì gọi lại phase 1. Sau khi đo dữ liệu bẩn, repair luôn bắt đầu từ raw.

| Thành phần | Mô tả |
| --- | --- |
| Input | `Settings`, `data/raw/crossref_records.json`, dataframe sạch |
| Output | Metrics JSON và hai báo cáo markdown |
| Module phụ thuộc | ingestion, retrieval, evaluation, observability |
| Module sử dụng output | `generate_phase1_report`, `generate_corruption_report` |
| Lỗi cần xử lý | Thiếu baseline thì chạy phase 1 trước; demo agent bỏ qua nếu không có credential |

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả hai lệnh thoát 0, repaired khớp baseline.
- **Kết quả thực tế:** Hit Rate 1.00 / 0.80 / 1.00.
- **Artifact:** `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Hai nhánh cùng sửa `testset.py`.
- **Phương án:** Giữ bản 5 câu kèm `multi_hop`, hoặc giữ bản 10 câu đúng 4 nhóm lab.
- **Đã chọn:** Bản 10 câu `summary`, `authors`, `date`, `categories`.
- **Lý do:** Checkpoint yêu cầu 10 câu và 4 nhóm. Câu hỏi cũng khớp từ khóa mà `qa.py` dùng để chấm.
- **Bằng chứng:** `test_set.json` có 10 phần tử; baseline Hit Rate 1.00.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Corruption đã làm Quality Gate fail nhưng freshness vẫn `is_fresh=true`.
- **Lệnh:** `python script/run_corruption_flow.py`.
- **Nguyên nhân:** Chỉ khoảng 14% dòng quá hạn, dưới SLA 25%.
- **Cách xử lý:** Tăng tỷ lệ stale date để có 6 bài bị lùi về 2015-01-01, chạy lại flow.
- **Xác minh:** `corrupted_freshness_report.json` có `stale_ratio=0.3333`, `is_fresh=false`.
- **Bài học:** Một kịch bản lỗi chưa đủ mạnh thì observability không kêu, dù code SLA đã đúng.

## 7. Hiểu biết về luồng end-to-end

1. Crossref thành `PaperRecord`, clean thành dataframe, MiniLM ghi vào Chroma.
2. Test set giữ DOI ground truth. Hit Rate đúng khi DOI đó nằm trong top-k.
3. Quality Gate chặn schema và nội dung. Freshness chỉ nhìn tuổi dữ liệu so với 180 ngày.
4. Cùng một đề thì chênh lệch điểm đến từ dữ liệu, không đến từ việc đổi câu hỏi.
5. Repair thành công khi 24 dòng sạch trở lại, quality pass, freshness fresh, và bốn metric bằng baseline.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.00 | 0.80 | 1.00 | Mất 2 câu sau khi bỏ bài mới và cắt title |
| `mean_token_f1` | 1.00 | 0.87 | 1.00 | Giảm ít hơn Hit Rate vì vài câu vẫn trùng token |
| `judge_accuracy` | 1.00 | 0.80 | 1.00 | Đi cùng Hit Rate |
| `mean_judge_score` | 5.00 | 4.40 | 5.00 | Câu còn đúng vẫn được 5 |
| Quality checks | Pass | Fail | Pass | Fail uniqueness và độ dài summary |
| Freshness status | Fresh | Stale | Fresh | 4.17% rồi 33.33% rồi về 4.17% |

1. Blank summary và duplicate làm Gate fail; drop latest làm Hit Rate xuống 0.80.
2. Clean lại từ raw phục hồi Gate, freshness và cả bốn metric.

Ảnh hưởng rõ nhất lên agent là mất bài mới và title bị cắt, vì câu hỏi bám title. Kỳ vọng ban đầu là freshness fail ngay lần đầu; số liệu 14% cho thấy tỷ lệ inject chưa đủ.

## 9. Điều học được và hướng cải thiện

1. Pipeline nhiều người chỉ chạy được khi chữ ký hàm và đường dẫn artifact cố định.
2. Observability phải được chứng minh bằng một lần fail thật, không chỉ bằng code có expectation.
3. RAG có thể trả lời trôi chảy khi dữ liệu hỏng; Hit Rate là chỗ nhìn thấy silent failure.

Nếu có thêm thời gian, siết expectation số dòng quanh 24 để việc drop 5 bài cũng làm Gate fail, rồi đo lại `success` trên corrupted.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Xuân Trường Giang
**Ngày xác nhận:** 2026-09-25
