from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from app import logging_config
from app.main import app


def _post(message: str, user_id: str, session_id: str) -> tuple[httpx.Response, dict]:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": user_id,
                    "session_id": session_id,
                    "feature": "qa",
                    "message": message,
                },
            )

    response = asyncio.run(send())
    return response, response.json()


def _read(log_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_every_request_gets_its_own_correlation_id_in_header_and_log(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    first, first_body = _post("Explain monitoring", "student-01", "session-01")
    second, second_body = _post("Explain traces", "student-02", "session-02")

    assert first_body["correlation_id"].startswith("req-")
    assert second_body["correlation_id"].startswith("req-")
    assert first.headers["x-request-id"] == first_body["correlation_id"]
    assert second.headers["x-request-id"] == second_body["correlation_id"]
    assert first_body["correlation_id"] != second_body["correlation_id"]
    assert int(first.headers["x-response-time-ms"]) > 0


def test_inbound_request_id_is_honoured(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat",
                headers={"x-request-id": "req-deadbeef"},
                json={
                    "user_id": "student-03",
                    "session_id": "session-03",
                    "feature": "qa",
                    "message": "Explain metrics",
                },
            )

    response = asyncio.run(send())
    assert response.headers["x-request-id"] == "req-deadbeef"
    assert response.json()["correlation_id"] == "req-deadbeef"


def test_context_does_not_leak_between_requests(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    _post("First question", "student-a", "session-a")
    _post("Second question", "student-b", "session-b")

    received = [r for r in _read(log_path) if r.get("event") == "request_received"]
    assert len(received) == 2
    first, second = received

    assert first["session_id"] == "session-a"
    assert second["session_id"] == "session-b"
    assert first["user_id_hash"] != second["user_id_hash"]
    assert first["correlation_id"] != second["correlation_id"]


def test_log_records_carry_required_enrichment(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    _post("How does monitoring work?", "student-01", "session-01")

    for record in _read(log_path):
        if record.get("service") != "api":
            continue
        for field in ("ts", "level", "event", "correlation_id", "user_id_hash", "session_id", "feature", "model", "env"):
            assert field in record, f"thiếu {field} trong {record}"


def test_pii_is_scrubbed_in_structured_log(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    _post(
        "SĐT 0912 345 678, email an.nguyen@vinuni.edu.vn, CCCD 001202012345",
        "binh.tran",
        "session-pii",
    )

    raw = log_path.read_text(encoding="utf-8")
    assert "0912 345 678" not in raw
    assert "an.nguyen@vinuni.edu.vn" not in raw
    assert "001202012345" not in raw
    assert "[REDACTED_PHONE_VN]" in raw
    assert "[REDACTED_EMAIL]" in raw
    assert "[REDACTED_CCCD]" in raw
