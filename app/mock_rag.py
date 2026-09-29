from __future__ import annotations

import time

from .incidents import STATE
from .pii import scrub_text
from .tracing import observation

CORPUS = {
    "refund": ["Refunds are available within 7 days with proof of purchase."],
    "monitoring": ["Metrics detect incidents, logs identify affected requests, traces localize the root cause."],
    "policy": ["Do not expose PII in logs. Use sanitized summaries only."],
}

DATA_SOURCE = "day13-kb-corpus"


def _match_topic(message: str) -> str | None:
    lowered = message.lower()
    for key in CORPUS:
        if key in lowered:
            return key
    return None


def _lookup(message: str) -> list[str]:
    if STATE["tool_fail"]:
        raise RuntimeError("Vector store timeout")
    if STATE["rag_slow"]:
        time.sleep(2.5)
    topic = _match_topic(message)
    if topic is None:
        return ["No domain document matched. Use general fallback answer."]
    return CORPUS[topic]


def retrieve(message: str) -> list[str]:
    with observation(
        as_type="retriever",
        name="retrieve-context",
        input={"query": scrub_text(message), "top_k": len(CORPUS)},
    ) as span:
        try:
            docs = _lookup(message)
        except Exception as exc:
            if span is not None:
                span.update(
                    level="ERROR",
                    status_message=f"{type(exc).__name__}: {exc}",
                    metadata={
                        "data_source": DATA_SOURCE,
                        "retrieval_method": "keyword_lookup",
                        "query_chars": len(message),
                        "error_type": type(exc).__name__,
                    },
                )
            raise
        if span is not None:
            span.update(
                output=docs,
                metadata={
                    "data_source": DATA_SOURCE,
                    "retrieval_method": "keyword_lookup",
                    "query_chars": len(message),
                    "matched_topic": _match_topic(message) or "fallback",
                    "doc_count": len(docs),
                },
            )
        return docs
