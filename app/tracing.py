from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

try:
    from langfuse import get_client, observe, propagate_attributes

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _NoopObservation:
        def update(self, **kwargs: Any) -> None:
            return None

        def end(self, **kwargs: Any) -> None:
            return None

    class _DummyClient:
        def update_current_span(self, **kwargs: Any) -> None:
            return None

        def update_current_generation(self, **kwargs: Any) -> None:
            return None

        def flush(self) -> None:
            return None

        def shutdown(self) -> None:
            return None

        @contextmanager
        def start_as_current_observation(self, **kwargs: Any) -> Iterator[Any]:
            yield _NoopObservation()

    def get_client():
        return _DummyClient()

    @contextmanager
    def propagate_attributes(**kwargs: Any):
        yield


def get_langfuse_client():
    return get_client()


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )


@contextmanager
def observation(**attributes: Any) -> Iterator[Any | None]:
    """Mở một observation con và yield handle của nó (None nếu tracing tắt).

    Dùng `with observation(...) as obs:` để mọi observation tạo bên trong trở thành
    con của observation đang active, và không cần nhánh lệnh khi thiếu Langfuse.
    """
    if not tracing_enabled():
        yield None
        return
    with get_client().start_as_current_observation(**attributes) as obs:
        yield obs


def flush_tracing() -> None:
    """Đẩy nốt buffer trước khi tiến trình kết thúc, tránh mất trace."""
    if not tracing_enabled():
        return
    try:
        get_client().flush()
    except Exception:  # pragma: no cover - flush không được làm sập app
        pass
