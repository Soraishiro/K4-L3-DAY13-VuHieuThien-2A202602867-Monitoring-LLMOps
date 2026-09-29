"""Regression: official mode phải khóa đúng challenge của bài Day 13.

Bug gốc: load_challenge() chấp nhận mọi challenge_id khác rỗng và cả K3/K4,
nên chạy "official" vẫn có thể dùng nhầm file. Loader generic phải giữ nguyên vì
starter test dùng fixture K3; chỉ entrypoint official mới bắt buộc khớp identity.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from app.challenge import (
    OFFICIAL_CHALLENGE_ID,
    load_challenge,
    load_official_challenge,
    resolve_incident,
)

OFFICIAL_PAYLOAD = {
    "cohort": "K4",
    "challenge_id": OFFICIAL_CHALLENGE_ID,
    "incident": "rag_slow",
    "seed": 1304,
    "affected_feature": "monitoring",
    "latency_threshold_ms": 2000,
    "queries": [
        {
            "user_id": "k4-01",
            "session_id": "official",
            "feature": "monitoring",
            "message": "Find the affected span.",
        }
    ],
}


def _write(payload: dict) -> Path:
    path = Path(tempfile.mkdtemp()) / "challenge.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_generic_loader_still_accepts_k3_fixture() -> None:
    payload = {**OFFICIAL_PAYLOAD, "cohort": "K3", "challenge_id": "day13-k3"}
    challenge = load_challenge(_write(payload))
    assert challenge.cohort == "K3"
    assert challenge.challenge_id == "day13-k3"


def test_official_loader_accepts_the_released_challenge() -> None:
    challenge = load_official_challenge(_write(OFFICIAL_PAYLOAD))
    assert challenge.challenge_id == OFFICIAL_CHALLENGE_ID


def test_official_loader_rejects_other_challenge_id() -> None:
    payload = {**OFFICIAL_PAYLOAD, "challenge_id": "day13-k4-l3a-monitoring-llmops-v0"}
    with pytest.raises(ValueError, match="Sai challenge chính thức"):
        load_official_challenge(_write(payload))


def test_official_loader_rejects_wrong_cohort() -> None:
    payload = {**OFFICIAL_PAYLOAD, "cohort": "K3"}
    with pytest.raises(ValueError, match="Sai challenge chính thức"):
        load_official_challenge(_write(payload))


def test_practice_incident_bypass_does_not_need_release_file() -> None:
    assert resolve_incident("tool_fail") == "tool_fail"
