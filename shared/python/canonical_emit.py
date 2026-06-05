from __future__ import annotations
import os
from events import StepEvent

def emit_step(event: StepEvent, out_dir: str, filename: str = "events.jsonl") -> None:
    """Append one canonical StepEvent as a JSON line. Best-effort: must NEVER
    raise, so a logging fault can never break a live experiment."""
    try:
        path = os.path.join(out_dir, filename)
        with open(path, "a") as f:
            f.write(event.model_dump_json() + "\n")
    except Exception as e:  # noqa: BLE001 - deliberately swallow; emit is non-critical
        print(f"[canonical_emit] non-fatal: {e}")
