# Alert và Runbook

Mỗi alert dựa trên **triệu chứng người dùng hoặc SLO**, không dựa trực tiếp vào
tên implementation nội bộ. Nếu hôm sau `rag_slow` được thay bằng
`pinecone_query` hay `vector_db`, điều kiện vẫn đúng vì nó đo latency/SLO chứ
không đo tên component.

Quy ước chung cho cả ba alert:

1. **Định danh request** — mọi log đều có `correlation_id`; trả lại cho client ở
   header `x-request-id`, nên khi có alert ta lấy được request cụ thể ngay.
2. **Nguồn sự thật dashboard** — `data/logs.jsonl`, dựng lại bằng
   `python scripts/build_dashboard.py`.
3. **Truy ngược sâu hơn** — cùng `correlation_id` đó, mở trace trong Langfuse để
   xem span nào chậm/lỗi.

---

## Alert 1

<a id="alert-1"></a>

- **Tên:** `user_visible_latency_burn`
- **Severity:** critical
- **Duration:** 5 phút
- **Kênh thông báo:** Slack `#day13-alerts-critical`
- **SLI/SLO liên quan:** `primary_slo:fast_successful_requests` (99.5% request có
  `latency_ms <= 3000`)
- **Điều kiện và thời gian duy trì:** `p95(latency_ms) > 3000` trong 5 phút liên
  tục, **và** có ít nhất 5 `response_sent` trong cửa sổ đó.
- **Ảnh hưởng tới người dùng:** người dùng chờ > 3 giây mỗi lượt hỏi, trải
  nghiệm như app bị treo. Với bot trợ giảng dạy, đây là lỗi khiến họ bỏ luôn.
- **Ba bước kiểm tra đầu tiên:**
  1. `python scripts/build_dashboard.py` rồi nhìn panel **latency**: nếu cột
     `ttft p95` vẫn ~50 ms mà `p95 latency` vọt lên, thì thời gian nằm ở
     **retrieval**, không phải ở LLM. Cột `retrieval p95` mới thêm cho ra con
     số trực tiếp nên không cần suy đoán.
  2. Nếu `ttft p95` cũng tăng → thời gian nằm ở **model call**: kiểm tra
     `model_parameters.max_tokens` và rate limit phía provider.
  3. Lọc `data/logs.jsonl` theo khoảng thời gian của alert, lấy `correlation_id`
     của một request chậm, mở trace tương ứng ở Langfuse và so sánh span.
- **Giới hạn đã biết:** incident `rag_slow` làm latency lên ~2656 ms. Với cửa
  sổ đủ nhiều request, p95 vọt lên 3405 ms và phá ngưỡng 3000, nhưng nếu chỉ có
  5–10 request trong cửa sổ thì p95 vẫn dưới ngưỡng và alert **không kêu**. Sự cố
  chậm vừa đủ để người dùng khó chịu nhưng chưa phá SLO sẽ lọt qua. Nếu triển
  khai thật, thêm alert riêng theo `retrieval_ms > 2000` trong 5 phút — không
  phụ thuộc tổng latency, nên bắt được cả khi traffic thưa.
- **Mitigation tạm thời:**
  - Nếu nghi do RAG: giảm `top_k` hoặc thêm cache cho truy vấn phổ biến.
  - Nếu nghi do LLM: hạ `max_tokens` (1024 → 512) để cắt thời gian sinh token.
  - Nếu phải chặn triệt đểể dập lửa: tạm trả lời bằng kết quả retrieval mà
    không gọi LLM, ghi log `tool_name=retrieval, tool_success=true` để dashboard
    không báo sai.
- **Owner:** on-call LLMOps (K4-L3A)

---

## Alert 2

<a id="alert-2"></a>

- **Tên:** `error_budget_burn_fast`
- **Severity:** critical
- **Duration:** 10 phút
- **Kênh thông báo:** Slack `#day13-alerts-critical`
- **SLI/SLO liên quan:** `primary_slo:fast_successful_requests`
- **Điều kiện và thời gian duy trì:** `error_rate_pct > 2%` trong 10 phút
  **và** lớn hơn 3 lần ngân sách lỗi (`3 x 0.5% = 1.5%`). Cả hai điều kiện phải
  đúng cùng lúc để loại nhiễu.
- **Ảnh hưởng tới người dùng:** người dùng gõ câu hỏi, chờ, rồi nhận lỗi 500.
- **Ba bước kiểm tra đầu tiên:**
  1. Panel **errors** → đọc breakdown `error_type`. `RuntimeError` từ retrieval
     là đường đi quen thuộc; lỗi lạ là dấu hiệu deploy hỏng.
  2. Nếu toàn `RuntimeError`, lấy một `correlation_id` từ dòng `request_failed`
     và mở trace: span `retrieve-context` sẽ có `level=ERROR` kèm
     `status_message`.
  3. Nếu lỗi không tập trung ở retrieval, kiểm tra `/health` và log
     `app_started` gần nhất — có thể do restart lỗi.
- **Mitigation tạm thời:**
  - Tắt nguồn lỗi: `python scripts/inject_incident.py --scenario tool_fail --disable`
    nếu biết chắc đây là practice incident.
  - Trả lỗi có kiểm soát thay vì 500 trần: thêm fallback "Xin lỗi, hãy thử lại"
    kèm `correlation_id` để người dùng báo lại được chính xác.
  - Rollback prompt về version trước bằng `docs/PROMPT_VERSIONING.md` nếu lỗi
    xuất hiện ngay sau khi đổi prompt.
- **Owner:** on-call LLMOps (K4-L3A)

---

## Alert 3

<a id="alert-3"></a>

- **Tên:** `retrieval_and_cost_regression`
- **Severity:** warning
- **Duration:** 15 phút
- **Kênh thông báo:** Slack `#day13-alerts-warning`
- **SLI/SLO liên quan:** `secondary_slos:retrieval_quality` (retrieval success
  ≥ 90%) và `secondary_slos:cost_per_window` (≤ 2.5 USD/cửa sổ)
- **Điều kiện và thời gian duy trì:** `retrieval_success_rate_pct < 90%` **hoặc**
  `sum(cost_usd) > 2.5` trong 15 phút (với cost, cửa sổ 60 phút).
- **Ảnh hưởng tới người dùng:** hai kiểu khác nhau nhưng đều thấy được —
  (a) retrieval fail thì câu trả lời sai nội dung, người dùng tin nhầm;
  (b) cost tăng thì chủ dự án thấy hoá đơn tăng mà chưa thấy chất lượng tăng.
- **Ba bước kiểm tra đầu tiên:**
  1. Panel **errors** → `retrieval success` có đang dước 90% không. Nếu có,
     mở trace và đọc `retriever` observation metadata `doc_count` và
     `matched_topic`: `matched_topic=fallback` là retrieval trả về tài liệu
     fallback nên câu trả lời sai ngay cả khi `tool_success=true`.
  2. Panel **tokens**: `tokens_out` tăng đột biến mà `tokens_in` đứng yên →
     model sinh thừa nội dung, thường do prompt hỏng hoặc thiếu ràng buộc độ
     dài.
  3. Panel **quality** (`mean quality_score`) giảm theo cùng lúc thì củng cố
     giả thuyết hồi quy chất lượng, không phải sự cố hạ tầng.
- **Mitigation tạm thời:**
  - Retrieval: tăng `top_k` hoặc hạ từ khoá từ corpus; nếu là practice
    incident thì `--scenario ... --disable` để xác nhận giả thuyết.
  - Cost: rollback prompt về version ngắn hơn, hoặc giảm `max_tokens`; xem
    metadata `cost_spike_injected` trên generation để biết có phải do
    workload hay do app.
- **Owner:** owner AI platform (K4-L3A)

---

## Kiểm chứng cả ba alert trong lúc làm bài

Các alert được kiểm chứng bằng practice incident, không mô phỏng tay:

```powershell
# baseline
python scripts/load_test.py
python scripts/build_dashboard.py

# alert 1 và 3: RAG chậm 2.5 s -> p95 lên ~2652 ms (vẫn dưới ngưỡng 3000)
python scripts/inject_incident.py --scenario rag_slow
python scripts/load_test.py
python scripts/build_dashboard.py --out submission/evidence/dashboard-incident-rag-slow.html
python scripts/inject_incident.py --scenario rag_slow --disable

# alert 2 và 3: retrieval lỗi -> error rate vượt 2%, retrieval success về 0%
python scripts/inject_incident.py --scenario tool_fail
python scripts/load_test.py
python scripts/build_dashboard.py --out submission/evidence/dashboard-incident-tool-fail.html
python scripts/inject_incident.py --scenario tool_fail --disable

# alert 3: cost spike -> tokens_out x4
python scripts/inject_incident.py --scenario cost_spike
python scripts/load_test.py
python scripts/build_dashboard.py --out submission/evidence/dashboard-incident-cost-spike.html
python scripts/inject_incident.py --scenario cost_spike --disable
```

Ngưỡng trong `config/alert_rules.yaml` được chọn từ số đo thật của bài, nên
đây là ngưỡng có căn cứ chứ không phải số mặc định.
