# Báo cáo cá nhân — Võ Doanh Nhân

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Võ Doanh Nhân |
| MSSV | 2A202602770 |
| Khóa/Lớp | K4-L3 |
| Tên nhóm | 7Goat |
| Vai trò chính | Evaluation set và synthetic corruption |
| Repository | https://github.com/GiangDA881/K4-L3-DAY10-7Goat-DataPipeline |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Test set | `build_test_set` | Dataframe sạch | `data/eval/test_set.json`, 10 câu | Hoàn thành |
| Metrics | `evaluate_pipeline` | Index, test set | Hit Rate, Token F1, judge | Hoàn thành |
| Corruption | `corrupt_clean_dataframe` | Dataframe sạch, seed 42 | Dataframe bẩn và `corruption_log.json` | Hoàn thành |

Mình không viết báo cáo markdown. Đào Đức Hải đọc metrics mình xuất ra.

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/artifact | Kết quả | Cách xác minh |
| --- | --- | --- | --- |
| Sinh đề | `data/eval/test_set.json` | 10 câu, 4 loại | Đếm phần tử và `question_type` |
| Tiêm lỗi | `data/results/corruption_log.json` | 6 loại, `final_rows=21` | Log có DOI từng loại |
| Đo suy giảm | `corrupted_metrics.json` | Hit Rate 0.80, Token F1 0.87 | So với baseline 1.00 |

## 4. Giải thích phần kỹ thuật đã thực hiện

Test set lấy mẫu có `random_state=42` và 10 template. Câu authors chứa “Who authored” hoặc “List the authors”, câu date chứa “When was” hoặc “publication date”, câu categories chứa “What categories”. Những cụm này khớp nhánh trả lời trong `qa.py`, nên baseline có thể đạt F1 cao khi dữ liệu còn sạch.

Corruption copy dataframe, bỏ 20% dòng đầu (bài mới nhất), rồi chia các lát blank, noise, truncate, stale, duplicate không chồng lên nhau nhờ một pool đã xáo. Seed 42 giúp lần chạy sau ra cùng DOI. `text_for_embedding` được ghép lại sau khi sửa ô.

| Thành phần | Mô tả |
| --- | --- |
| Input | Dataframe 24 dòng đã sort ngày mới trước |
| Output | Dataframe 21 dòng và corruption log |
| Module phụ thuộc | Cột `title`, `summary`, `published`, `paper_id`, `age_days` |
| Module sử dụng output | Index corrupted và Quality Gate |
| Lỗi cần xử lý | Dataframe ngắn hơn số lát cần tiêm thì `_pick` lấy tối đa phần còn lại |

```bash
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Log đủ 6 loại và metric corrupted thấp hơn baseline.
- **Kết quả thực tế:** Hit Rate 0.80, Token F1 0.8741, judge accuracy 0.80.
- **Artifact:** `data/results/corruption_log.json`, `corrupted_metrics.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Các lỗi có được phép đè cùng một dòng hay không.
- **Phương án:** Mỗi dòng dính nhiều lỗi, hoặc mỗi lát một nhóm dòng riêng.
- **Đã chọn:** Pool không hoàn lại, trừ bước duplicate chỉ nhân dòng chưa đụng.
- **Lý do:** Nếu một dòng vừa mất summary vừa bị cắt title, không biết lỗi nào làm Gate fail.
- **Bằng chứng:** Log tách `blanked_summary` 3 DOI, `truncated_title` 1 DOI, `duplicated_rows` 2 DOI.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Sau lần chạy đầu, freshness không fail dù đã có stale date.
- **Lệnh:** Đọc `corrupted_freshness_report.json`.
- **Nguyên nhân:** `_STALE_RATIO=0.15` chỉ làm cũ khoảng 14% dòng, SLA cần trên 25%.
- **Cách xử lý:** Đưa tỷ lệ lên 0.45. Log cuối có `stale_date.count=6`. Cộng với bài vốn đã cũ, tổng 7/21.
- **Xác minh:** `is_fresh=false`, `stale_ratio=0.3333`. Repaired không dùng file này nên freshness về 0.0417.
- **Bài học:** “Có tiêm lỗi ngày” khác với “đã vượt ngưỡng SLA”.

## 7. Hiểu biết về luồng end-to-end

1. Mình nhận dataframe sạch, không gọi API. Index là việc của retrieval sau khi orchestration lưu file.
2. Mỗi câu có `ground_truth_doc_ids`. Hit Rate là tỷ lệ câu có DOI đó trong danh sách retrieve.
3. Quality Gate kiểm tra bảng lúc validate. Freshness là một báo cáo riêng trên `age_days`.
4. Mình chỉ sinh test set một lần từ dữ liệu sạch. Corruption flow trỏ lại cùng path.
5. Repair thành công khi corrupted thấp hơn baseline và repaired trùng baseline trên cùng 10 câu.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.00 | 0.80 | 1.00 | Đúng 2 câu mất DOI |
| `mean_token_f1` | 1.00 | 0.87 | 1.00 | Noise và summary rỗng không làm rơi hết token |
| `judge_accuracy` | 1.00 | 0.80 | 1.00 | Judge đồng ý với Hit Rate |
| `mean_judge_score` | 5.00 | 4.40 | 5.00 | Trung bình vẫn cao |
| Quality checks | Pass | Fail | Pass | Duplicate và blank summary là hai fail mình tạo ra |
| Freshness status | Fresh | Stale | Fresh | Sáu DOI trong `stale_date` đẩy tỷ lệ qua 25% |

1. Blank summary và duplicate làm Gate fail. Drop 5 bài mới làm Hit Rate còn 0.80.
2. Repair không đụng `corruption.py`. Nó bỏ dataframe bẩn và clean từ raw, nên metric về 1.00.

Kỳ vọng chưa đúng: mình nghĩ Token F1 sẽ rơi mạnh hơn Hit Rate. Số liệu ngược lại, vì nhiều câu vẫn trích được metadata còn nguyên.

## 9. Điều học được và hướng cải thiện

1. Test set là đề đóng. Đổi đề giữa ba lần đo thì bảng so sánh vô nghĩa.
2. Log corruption phải ghi DOI, không chỉ ghi tên lỗi.
3. Hai câu mất Hit Rate là bằng chứng silent failure: pipeline không crash.

Nếu có thêm thời gian, tách metric theo `question_type` để biết drop latest làm hỏng câu date hay câu summary.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Võ Doanh Nhân
**Ngày xác nhận:** 2026-09-25
