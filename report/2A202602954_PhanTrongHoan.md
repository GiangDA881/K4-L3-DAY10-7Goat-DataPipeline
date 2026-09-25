# Báo cáo cá nhân — Phan Trọng Hoàn

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Phan Trọng Hoàn |
| MSSV | 2A202602954 |
| Khóa/Lớp | K4-L3 |
| Tên nhóm | 7Goat |
| Vai trò chính | RAG, embedding và ChromaDB |
| Repository | https://github.com/GiangDA881/K4-L3-DAY10-7Goat-DataPipeline |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Embedding | `MiniLMEmbeddings` | `text_for_embedding` | Vector MiniLM | Hoàn thành |
| Index | `LocalEmbeddingIndex.build` | Dataframe | 3 collection tách biệt | Hoàn thành |
| QA | `answer_question`, `build_agent` | Câu hỏi và index | Câu trả lời cùng danh sách DOI | Hoàn thành |

Ba collection không dùng chung một tên. Baseline, corrupted và repaired mỗi bên một không gian vector.

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/artifact | Kết quả | Cách xác minh |
| --- | --- | --- | --- |
| Index baseline | Collection `papers-baseline` | 24 documents | Log phase 1: `Index: collection papers-baseline (24 docs)` |
| Index hai trạng thái kia | `papers-corrupted`, `papers-repaired` | Đo được chênh lệch Hit Rate | `corrupted_metrics.json` và `repaired_metrics.json` |

## 4. Giải thích phần kỹ thuật đã thực hiện

`LocalEmbeddingIndex.build` xóa collection cũ cùng tên rồi tạo mới với HNSW cosine. Document id là `paper_id` cộng chỉ số dòng, nên dòng duplicate vẫn được thêm nhưng metadata DOI bị trùng. Câu hỏi có title trong dấu nháy được lookup đúng bài trước khi search. `top_k` là 4.

| Thành phần | Mô tả |
| --- | --- |
| Input | Dataframe có `paper_id`, `title`, `text_for_embedding`, metadata |
| Output | Collection Chroma và manifest embedding |
| Module phụ thuộc | Dataframe sạch hoặc dataframe đã corrupt |
| Module sử dụng output | `evaluate_pipeline`, agent demo |
| Lỗi cần xử lý | Collection đã tồn tại thì xóa rồi tạo lại để lần chạy sau không nhân đôi vector |

```bash
python script/run_phase1.py
```

- **Kết quả mong đợi:** 24 vector trong `papers-baseline`.
- **Kết quả thực tế:** Đúng 24 documents, Hit Rate baseline 1.00.
- **Artifact:** `data/results/baseline_metrics.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** So sánh ba trạng thái dữ liệu.
- **Phương án:** Ghi đè một collection, hoặc ba collection riêng.
- **Đã chọn:** `papers-baseline`, `papers-corrupted`, `papers-repaired`.
- **Lý do:** Ghi đè làm mất index sạch trước khi kịp so sánh. Tách collection giữ cùng model, khác dữ liệu.
- **Bằng chứng:** Hit Rate đổi từ 1.00 sang 0.80 rồi về 1.00 trên cùng test set.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Agent cần tool-calling, mock LLM ban đầu không `bind_tools`.
- **Nguyên nhân:** `FakeListChatModel` không có `bind_tools`, `create_agent` không dựng được.
- **Cách xử lý:** Subclass mock có `bind_tools` trả về chính nó.
- **Xác minh:** Phase 1 chạy đến dòng `Agent demo: 3 cau`.
- **Bài học:** Index đúng chưa đủ nếu lớp LLM không nhận tool.

## 7. Hiểu biết về luồng end-to-end

1. Text sạch được embed rồi add vào Chroma cùng metadata DOI.
2. Hit Rate đúng khi DOI ground truth xuất hiện trong kết quả search.
3. Quality Gate quyết định dữ liệu có được tin trước khi index. Freshness không nhìn vector.
4. Cùng test set và cùng `top_k` thì khác biệt điểm nằm ở nội dung collection.
5. Repair thành công khi collection `papers-repaired` đưa Hit Rate về 1.00.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.00 | 0.80 | 1.00 | Index bẩn làm mất 2 DOI đúng |
| `mean_token_f1` | 1.00 | 0.87 | 1.00 | Metadata summary hỏng nên câu trả lời lệch |
| `judge_accuracy` | 1.00 | 0.80 | 1.00 | Cùng 2 câu fail với retrieval |
| `mean_judge_score` | 5.00 | 4.40 | 5.00 | Không sụp hết vì 8 câu vẫn đúng |
| Quality checks | Pass | Fail | Pass | Mình không chặn index khi Gate fail; orchestration vẫn index để đo mức giảm |
| Freshness status | Fresh | Stale | Fresh | Ngày cũ đổi metadata `published`, không đổi model |

1. Title cụt và bài mới bị xóa làm search không còn đúng DOI, Hit Rate 0.80.
2. Index lại từ dataframe repair đưa Hit Rate về 1.00.

Ảnh hưởng rõ nhất là truncate title, vì lookup và câu hỏi đều bám chuỗi title. Drop latest cũng làm mất tài liệu mà đề đang hỏi.

## 9. Điều học được và hướng cải thiện

1. Vector store là bản sao của dữ liệu tại một thời điểm, không phải nguồn sự thật.
2. Gate fail mà vẫn index là cố ý để đo silent failure, không phải để phục vụ production.
3. Cùng một model, dữ liệu bẩn vẫn làm Hit Rate giảm 0.20.

Nếu có thêm thời gian, từ chối build collection khi Gate fail trong một chế độ production riêng, rồi so Hit Rate của chế độ đó với chế độ đo corruption.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phan Trọng Hoàn
**Ngày xác nhận:** 2026-09-25
