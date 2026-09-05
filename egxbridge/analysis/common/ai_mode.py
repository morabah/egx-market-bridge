from __future__ import annotations

"""AI mode interface — CHATGPT_HANDOFF only in v0.4."""

AI_CHATGPT_HANDOFF = "CHATGPT_HANDOFF"
AI_LOCAL_LLM = "LOCAL_LLM"  # future
AI_REMOTE_API = "REMOTE_API"  # future, disabled


def active_ai_mode() -> str:
    return AI_CHATGPT_HANDOFF


def requires_paid_api(mode: str | None = None) -> bool:
    m = mode or active_ai_mode()
    return m == AI_REMOTE_API


def assert_handoff_only():
    if requires_paid_api():
        raise RuntimeError("Paid remote AI API mode is disabled in v0.4")
