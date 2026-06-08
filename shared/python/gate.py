import os


def canonical_enabled() -> bool:
    """Whether to emit the canonical events.jsonl thinking-trace stream.

    Defaults to ON so every run persists full-fidelity thinking traces with no
    flag required. Set EMIT_CANONICAL=0 (or false/no) to opt out — e.g. to keep
    legacy output byte-for-byte unchanged.
    """
    return os.environ.get("EMIT_CANONICAL", "1").lower() not in ("0", "false", "no")
