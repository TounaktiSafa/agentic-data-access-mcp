"""Optional Langfuse tracing. Everything is a no-op unless LANGFUSE_* env vars are set,
so tests, CI and the evaluation can run without Docker."""
import os

ENABLED = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))

if ENABLED:
    from langfuse import get_client, observe
else:

    def observe(*args, **kwargs):
        # works both as @observe and @observe(name=..., ...)
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return lambda fn: fn

    def get_client():
        return None


def _safe(method: str, **kwargs) -> None:
    """Tracing must never break the agent: swallow any Langfuse error."""
    if not ENABLED:
        return
    try:
        getattr(get_client(), method)(**kwargs)
    except Exception:
        pass


def update_generation(**kw) -> None:
    _safe("update_current_generation", **kw)


def update_span(**kw) -> None:
    _safe("update_current_span", **kw)


def update_trace(**kw) -> None:
    _safe("update_current_trace", **kw)


def flush() -> None:
    if ENABLED:
        try:
            get_client().flush()
        except Exception:
            pass
