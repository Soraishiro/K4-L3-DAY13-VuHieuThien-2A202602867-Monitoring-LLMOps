from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .incidents import STATE
from .pii import scrub_text
from .tracing import observation

PRICE_PER_MTOK: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
}
FALLBACK_PRICE_PER_MTOK = {"input": 3.0, "output": 15.0}

MODEL_PARAMETERS = {"temperature": 0.2, "max_tokens": 1024}


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class FakeResponse:
    text: str
    usage: FakeUsage
    model: str
    ttft_ms: int
    first_token_at: datetime | None = None


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    price = PRICE_PER_MTOK.get(model, FALLBACK_PRICE_PER_MTOK)
    input_cost = (tokens_in / 1_000_000) * price["input"]
    output_cost = (tokens_out / 1_000_000) * price["output"]
    return round(input_cost + output_cost, 6)


def cost_breakdown(model: str, tokens_in: int, tokens_out: int) -> dict[str, float]:
    price = PRICE_PER_MTOK.get(model, FALLBACK_PRICE_PER_MTOK)
    return {
        "input": round((tokens_in / 1_000_000) * price["input"], 8),
        "output": round((tokens_out / 1_000_000) * price["output"], 8),
    }


class FakeLLM:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model

    def _complete(self, prompt: str) -> FakeResponse:
        started = time.perf_counter()
        time.sleep(0.05)  # mô phỏng thời điểm token đầu tiên sẵn sàng
        ttft_ms = int((time.perf_counter() - started) * 1000)
        first_token_at = datetime.now(timezone.utc)
        time.sleep(0.10)
        input_tokens = max(20, len(prompt) // 4)
        output_tokens = random.randint(80, 180)
        if STATE["cost_spike"]:
            output_tokens *= 4
        answer = (
            "Starter answer. You should improve this output logic and add better quality checks. "
            "Use retrieved context and keep responses concise."
        )
        return FakeResponse(
            text=answer,
            usage=FakeUsage(input_tokens, output_tokens),
            model=self.model,
            ttft_ms=ttft_ms,
            first_token_at=first_token_at,
        )

    def generate(self, prompt: str, managed_prompt: Any | None = None) -> FakeResponse:
        with observation(
            as_type="generation",
            name="generate-response",
            model=self.model,
            model_parameters=MODEL_PARAMETERS,
            prompt=managed_prompt,
            input=[{"role": "user", "content": scrub_text(prompt)}],
        ) as generation:
            response = self._complete(prompt)
            if generation is not None:
                generation.update(
                    # Scrub cả output: fake LLM hiện trả chuỗi cố định nên chưa
                    # lộ PII, nhưng invariant của lab là không capture raw
                    # input/output. Bảo vệ phải đúng từ thiết kế, không phải do
                    # dữ liệu tình cờ sạch.
                    output=[{"role": "assistant", "content": scrub_text(response.text)}],
                    completion_start_time=response.first_token_at,
                    usage_details={
                        "input": response.usage.input_tokens,
                        "output": response.usage.output_tokens,
                    },
                    cost_details=cost_breakdown(
                        self.model,
                        response.usage.input_tokens,
                        response.usage.output_tokens,
                    ),
                    metadata={
                        "ttft_ms": response.ttft_ms,
                        "prompt_chars": len(prompt),
                        "cost_spike_injected": bool(STATE["cost_spike"]),
                    },
                )
            return response
