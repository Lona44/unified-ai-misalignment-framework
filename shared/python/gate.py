import os
def canonical_enabled() -> bool:
    return os.environ.get("EMIT_CANONICAL", "0").lower() in ("1", "true", "yes")
