from __future__ import annotations

from collections import Counter
from statistics import mean

REQUEST_LATENCIES: list[int] = []
REQUEST_TTFT: list[int] = []
REQUEST_COSTS: list[float] = []
REQUEST_TOKENS_IN: list[int] = []
REQUEST_TOKENS_OUT: list[int] = []
ERRORS: Counter[str] = Counter()
TOOL_RESULTS: Counter[tuple[str, bool]] = Counter()
TRAFFIC: int = 0
SUCCESSES: int = 0
QUALITY_SCORES: list[float] = []


def record_request_started() -> None:
    """Ghi nhận 1 request đã đi vào hệ thống, bất kể sau đó thành công hay lỗi.

    Traffic phải đếm ở đầu request vì `error_rate_pct()` lấy mẫu số là
    tổng số request. Nếu chỉ tăng trong `record_request()` thì một đợt toàn
    lỗi sẽ cho TRAFFIC == 0 và error rate 0%, tức báo động im lặng đúng lúc
    cần nhất.
    """
    global TRAFFIC
    TRAFFIC += 1


def record_request(
    latency_ms: int,
    ttft_ms: int,
    cost_usd: float,
    tokens_in: int,
    tokens_out: int,
    quality_score: float,
) -> None:
    """Ghi latency/token/cost của một response thành công.

    Không tăng TRAFFIC ở đây nữa; việc đó thuộc `record_request_started()`.
    """
    global SUCCESSES
    SUCCESSES += 1
    REQUEST_LATENCIES.append(latency_ms)
    REQUEST_TTFT.append(ttft_ms)
    REQUEST_COSTS.append(cost_usd)
    REQUEST_TOKENS_IN.append(tokens_in)
    REQUEST_TOKENS_OUT.append(tokens_out)
    QUALITY_SCORES.append(quality_score)



def record_error(error_type: str) -> None:
    ERRORS[error_type] += 1



def record_tool_result(tool_name: str, success: bool) -> None:
    """Panel 'errors' cần biết retrieval có thành công không, không chỉ có 500."""
    TOOL_RESULTS[(tool_name, success)] += 1



def tool_success_rate_pct(tool_name: str = "retrieval") -> float:
    succeeded = TOOL_RESULTS[(tool_name, True)]
    total = succeeded + TOOL_RESULTS[(tool_name, False)]
    if not total:
        return 100.0
    return round(succeeded / total * 100, 2)



def error_rate_pct() -> float:
    """Tỷ lệ lỗi theo tổng số request đã nhận, kể cả request không có response."""
    if not TRAFFIC:
        return 0.0
    return round(sum(ERRORS.values()) / TRAFFIC * 100, 2)



def percentile(values: list[int], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])



def snapshot() -> dict:
    return {
        "traffic": TRAFFIC,
        "successes": SUCCESSES,
        "failures": sum(ERRORS.values()),
        "latency_p50": percentile(REQUEST_LATENCIES, 50),
        "latency_p95": percentile(REQUEST_LATENCIES, 95),
        "latency_p99": percentile(REQUEST_LATENCIES, 99),
        "ttft_p95": percentile(REQUEST_TTFT, 95),
        "avg_cost_usd": round(mean(REQUEST_COSTS), 4) if REQUEST_COSTS else 0.0,
        "total_cost_usd": round(sum(REQUEST_COSTS), 4),
        "tokens_in_total": sum(REQUEST_TOKENS_IN),
        "tokens_out_total": sum(REQUEST_TOKENS_OUT),
        "error_breakdown": dict(ERRORS),
        "error_rate_pct": error_rate_pct(),
        "retrieval_success_rate_pct": tool_success_rate_pct("retrieval"),
        "quality_avg": round(mean(QUALITY_SCORES), 4) if QUALITY_SCORES else 0.0,
    }
