# AGENTS.md

Ghi chú lâu dài cho agent làm việc trên repo này. Nội dung ở đây được coi là
sự thật đã xác nhận, không cần suy đoán lại.

## Người dùng

- **Họ tên:** Vũ Hiếu Thiên
- **MSSV:** 2A202602867
- **Lớp:** K4-L3A
- **GitHub:** https://github.com/Soraishiro
- **Project Langfuse cá nhân:** `day13-k4-l3a-2A202602867`
- **Base URL Langfuse:** `https://jp.cloud.langfuse.com` (không phải
  `cloud.langfuse.com` — dùng region Nhật)

Cảnh báo: tên thư mục repo là `VuHieuThien` nhưng dấu là **Hiếu**, không phải
Hiệu. Lần trước đã tự ý sửa tên trong `submission/REPORT.md` theo tên thư mục
và sai. Tên đúng chỉ lấy từ chính người dùng xác nhận, không đoán từ path.

## Bối cảnh

Bài lab VinUni AI20k, module K4-L3A, ngày 13 — Monitoring & LLMOps cho ứng dụng
chat dựa trên LLM. Bốn checkpoint: CP1 logging/PII, CP2 metrics/traces/prompt/
dashboard/SLO, CP3 điều tra challenge, CP4 nộp bài.

Challenge CP3 là `day13-k4-l3a-monitoring-llmops-v1` (cohort K4, incident
`rag_slow`). File `config/challenge.json` do Lab Coach gửi, nằm trong
`.gitignore` — không bao giờ commit, push hay force-add.

## Cách làm việc đã được chấp nhận

Người dùng mới làm quen hệ thống, nên khi giải thích phải đi từ bản chất vấn đề
chứ không chỉ liệt kê cách làm. Họ yêu cầu rõ: sau mỗi checkpoint phải giải
thích được *tại sao* cấu hình đó đúng, để tự làm được trên hệ thống khác khi
không có lab.

**Đừng làm thay phần học.** Khi phát hiện lab bắt buộc xây gì (ví dụ sáu panel
dashboard), hãy nói rõ phần đó là nhiệm vụ của họ và để trống, kể cả khi có
thể viết nhanh. Lần trước viết sẵn cả `build_dashboard.py` lẫn script dựng ảnh
PNG giả bằng Pillow, rồi phải xoá lại — mất công và làm sai ý lab.

**Evidence phải thật.** Chỉ chụp màn hình từ terminal hoặc từ giao diện web thật.
Không dựng ảnh giả bằng thư viện render. Cũng không đoán URL hay đường dẫn
điều hướng rồi đưa cho người dùng — hãy kiểm chứng trước.

**Không đoán số liệu.** Mọi con số trong `submission/REPORT.md` phải lấy từ
lần chạy thật gần nhất, và các mục trong report phải nhất quán với nhau. Đã có
lần bảng kỹ thuật ghi p95 2654 còn mục điều tra ghi 3366.

**Trước khi push:** chạy `pytest -q`, `validate_logs.py`, `validate_dashboard.py`,
rà secret trong `submission/evidence/`, kiểm `config/challenge.json` không lọt
vào staging, và xác minh mọi đường dẫn tương đối trong report đều tồn tại.

## Vấn đề từng gặp, đừng vấp lại

- `validate_dashboard.py` chỉ đọc `config/dashboard.yaml`, không bao giờ kiểm tra
  biểu đồ. Xóa hết notebook nó vẫn trả 6/6. Đừng coi 6/6 là bằng chứng đã dựng
  đúng.
- Langfuse API `GET /api/public/traces` trả 410 với tổ chức tạo sau 16/09/2026.
  Dùng `client.api.observations.get_many()` và phải truyền `fields` đúng kiểu
  (`"core"`, `"time"`, `"metadata"`) thì mới nhận được `prompt_version`; không
  truyền `fields` thì mọi trường là `None`.
- Metadata span do Langfuse tự gắn kèm `scope.attributes.public_key`. Luôn lọc
  bỏ `scope.*` và `resourceAttributes.*` trước khi đưa vào evidence.
- `get_prompt` cache 60 giây. Đổi label trên Langfuse rồi chạy workload ngay sẽ
  vẫn ra version cũ. Khởi động lại server thì cache trống.
- `uvicorn --env-file .env` không ghi đè biến môi trường đã có sẵn (dotenv
  `override=False`), nên set `$env:...` trước khi start là thắng `.env`.
- `json.dumps` mặc định `ensure_ascii=True`, nên tiếng Việt trong
  `data/logs.jsonl` bị ghi thành `\uXXXX`. Không phải lỗi encoding, nhưng ảnh
  chứng minh PII trông như hỏng — giải thích trước khi người chấm hỏi.
- `threadpool` của FastAPI tái sử dụng thread, thiếu `clear_contextvars()` thì
  request sau dính `correlation_id` của request trước.
- `import matplotlib.pyplot as plt` không tạo tên `matplotlib` trong namespace.
  Muốn dùng `matplotlib.dates` phải import tường minh.
