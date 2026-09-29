"""Regression: traffic phải đếm cả request lỗi, error rate phải phản ánh đúng.

Bug gốc: TRAFFIC chỉ tăng trong record_request() (chỉ chạy khi response thành
công). Một đợt toàn lỗi cho TRAFFIC == 0 và error_rate_pct() == 0%, tức báo
động im lặng đúng lúc cần nhất.
"""

from __future__ import annotations

import pytest

from app import metrics


@pytest.fixture(autouse=True)
def clean_metrics() -> None:
    metrics.TRAFFIC = 0
    metrics.SUCCESSES = 0
    metrics.REQUEST_LATENCIES.clear()
    metrics.REQUEST_TTFT.clear()
    metrics.REQUEST_COSTS.clear()
    metrics.REQUEST_TOKENS_IN.clear()
    metrics.REQUEST_TOKENS_OUT.clear()
    metrics.QUALITY_SCORES.clear()
    metrics.ERRORS.clear()
    metrics.TOOL_RESULTS.clear()


def test_all_failures_report_100_percent_error_rate() -> None:
    for _ in range(3):
        metrics.record_request_started()
        metrics.record_error("RuntimeError")

    assert metrics.snapshot()["traffic"] == 3
    assert metrics.error_rate_pct() == 100.0


def test_failed_request_still_counts_as_traffic() -> None:
    metrics.record_request_started()
    metrics.record_request(
        latency_ms=120,
        ttft_ms=40,
        cost_usd=0.0001,
        tokens_in=10,
        tokens_out=20,
        quality_score=0.8,
    )
    metrics.record_request_started()
    metrics.record_error("RuntimeError")

    snapshot = metrics.snapshot()
    assert snapshot["traffic"] == 2
    assert snapshot["successes"] == 1
    assert snapshot["failures"] == 1
    assert metrics.error_rate_pct() == 50.0


def test_record_request_alone_does_not_inflate_traffic() -> None:
    metrics.record_request(
        latency_ms=100,
        ttft_ms=30,
        cost_usd=0.0002,
        tokens_in=5,
        tokens_out=6,
        quality_score=0.9,
    )

    assert metrics.snapshot()["traffic"] == 0
    assert metrics.snapshot()["successes"] == 1


def test_error_rate_is_zero_when_no_traffic_yet() -> None:
    assert metrics.error_rate_pct() == 0.0
