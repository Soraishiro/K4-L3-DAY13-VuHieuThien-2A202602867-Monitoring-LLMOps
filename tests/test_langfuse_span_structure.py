from __future__ import annotations

from contextlib import contextmanager

from app import mock_llm, mock_rag, tracing


class RecordingObservation:
    def __init__(self, name: str, as_type: str, attributes: dict) -> None:
        self.name = name
        self.as_type = as_type
        self.created_with = dict(attributes)
        self.updates: list[dict] = []

    def update(self, **kwargs) -> None:
        self.updates.append(kwargs)

    def end(self, **kwargs) -> None:
        return None

    @property
    def merged(self) -> dict:
        merged = dict(self.created_with)
        for update in self.updates:
            merged.update(update)
        return merged


class RecordingClient:
    def __init__(self) -> None:
        self.observations: list[RecordingObservation] = []

    @contextmanager
    def start_as_current_observation(self, **attributes):
        obs = RecordingObservation(attributes.get("name"), attributes.get("as_type"), attributes)
        self.observations.append(obs)
        yield obs

    def update_current_span(self, **kwargs) -> None:
        return None


def _instrument(monkeypatch) -> RecordingClient:
    client = RecordingClient()
    monkeypatch.setattr(tracing, "tracing_enabled", lambda: True)
    monkeypatch.setattr(tracing, "get_client", lambda: client)
    return client


def test_retrieval_is_typed_as_retriever_and_scrubs_pii(monkeypatch) -> None:
    client = _instrument(monkeypatch)

    docs = mock_rag.retrieve("Explain monitoring, email me at a@b.com")

    assert docs
    (obs,) = client.observations
    assert obs.as_type == "retriever"
    assert obs.name == "retrieve-context"
    assert "a@b.com" not in obs.created_with["input"]["query"]
    assert obs.merged["metadata"]["data_source"] == mock_rag.DATA_SOURCE
    assert obs.merged["metadata"]["doc_count"] == len(docs)


def test_failed_retrieval_is_recorded_as_an_error_observation(monkeypatch) -> None:
    from app import incidents

    client = _instrument(monkeypatch)
    incidents.enable("tool_fail")
    try:
        mock_rag.retrieve("refund")
    except RuntimeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("tool_fail phải ném RuntimeError")
    finally:
        incidents.disable("tool_fail")

    (obs,) = client.observations
    assert obs.merged["level"] == "ERROR"
    assert obs.merged["metadata"]["error_type"] == "RuntimeError"


def test_llm_call_is_typed_as_generation_with_model_usage_and_cost(monkeypatch) -> None:
    client = _instrument(monkeypatch)
    managed_prompt = object()
    llm = mock_llm.FakeLLM(model="claude-sonnet-4-5")
    result = llm.generate("Question=refund", managed_prompt=managed_prompt)

    (obs,) = client.observations
    assert obs.as_type == "generation"
    assert obs.name == "generate-response"
    assert obs.merged["model"] == "claude-sonnet-4-5"
    assert obs.merged["prompt"] is managed_prompt
    assert obs.merged["usage_details"] == {
        "input": result.usage.input_tokens,
        "output": result.usage.output_tokens,
    }
    assert obs.merged["cost_details"]["output"] > 0
    assert obs.merged["completion_start_time"] is not None
    assert obs.merged["output"] == [{"role": "assistant", "content": result.text}]


def test_observation_helper_is_inert_when_tracing_is_disabled(monkeypatch) -> None:
    monkeypatch.setattr(tracing, "tracing_enabled", lambda: False)

    with tracing.observation(as_type="span", name="noop") as obs:
        assert obs is None
