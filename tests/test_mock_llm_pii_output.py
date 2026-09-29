"""Regression: generation span không được capture raw output.

Bug gốc: input đã scrub_text() nhưng output đẩy thẳng response.text vào
Langfuse. Fake LLM hiện trả chuỗi cố định nên chưa lộ PII, nhưng invariant của
lab là không capture raw input/output, nên phải kiểm tra theo thiết kế chứ không
theo dữ liệu tình cờ.
"""

from __future__ import annotations

import pytest

from app.mock_llm import FakeLLM
from app.tracing import observation


class _SpyObservation:
    def __init__(self) -> None:
        self.attributes: dict = {}
        self.updates: list[dict] = []

    def update(self, **kwargs) -> None:
        self.updates.append(kwargs)

    def end(self, **kwargs) -> None:
        return None


@pytest.fixture
def spy(monkeypatch) -> _SpyObservation:
    obs = _SpyObservation()

    import app.mock_llm as mock_llm

    def fake_observation(**attributes):
        obs.attributes.update(attributes)

        class _Ctx:
            def __enter__(self_inner):
                return obs

            def __exit__(self_inner, *exc):
                return False

        return _Ctx()

    monkeypatch.setattr(mock_llm, "observation", fake_observation)
    return obs


def test_generation_output_is_scrubbed(spy: _SpyObservation) -> None:
    llm = FakeLLM()

    original = llm._complete

    def leaky_complete(prompt: str):
        response = original(prompt)
        response.text = "Liên hệ 0901234567 hoặc student@vinuni.edu.vn"
        return response

    llm._complete = leaky_complete  # type: ignore[method-assign]
    response = llm.generate("xin chào")

    assert spy.updates, "generation span chưa được update"
    output = spy.updates[0]["output"]
    content = output[0]["content"]
    assert "0901234567" not in content
    assert "student@vinuni.edu.vn" not in content
    assert "[REDACTED" in content
    # Response trả về cho client vẫn giữ nguyên, chỉ trace bị scrub.
    assert "0901234567" in response.text


def test_generation_input_is_scrubbed(spy: _SpyObservation) -> None:
    llm = FakeLLM()
    llm.generate("Số CCCD của tôi là 001202012345")

    assert spy.updates
    content = spy.attributes["input"][0]["content"]
    assert "001202012345" not in content
    assert "[REDACTED_CCCD]" in content


def test_observation_is_noop_without_langfuse() -> None:
    with observation(as_type="generation", name="x") as handle:
        assert handle is None
