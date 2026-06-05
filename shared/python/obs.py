from __future__ import annotations
import json, logging, os, sys
from datetime import datetime, timezone

_RESERVED = set(vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()) | {"message", "asctime"}

class JsonFormatter(logging.Formatter):
    """One JSON object per line. Promotes structured `extra=` fields to top level."""
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "run_id": getattr(record, "run_id", None),
            "event": getattr(record, "event", None),
            "step": getattr(record, "step", None),
            "msg": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k not in _RESERVED and k not in payload:
                payload[k] = v
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps({k: v for k, v in payload.items() if v is not None}, ensure_ascii=False, default=str)

class RunIdFilter(logging.Filter):
    def __init__(self, run_id: str | None):
        super().__init__()
        self.run_id = run_id
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "run_id"):
            record.run_id = self.run_id
        return True

_CONFIGURED = False

def setup_logging(run_id: str | None = None, log_dir: str | None = None, level: str | None = None):
    """Configure root logging once: human console + (optional) JSON log.jsonl.
    Idempotent — safe to call from runner and agents."""
    global _CONFIGURED
    run_id = run_id or os.environ.get("UNIFIED_RUN_ID") or os.environ.get("UNIFIED_EXPERIMENT_ID")
    level = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    rid = RunIdFilter(run_id)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("%(levelname)-7s %(name)s | %(message)s"))
    ch.addFilter(rid)
    root.addHandler(ch)
    if log_dir:
        fh = logging.FileHandler(os.path.join(log_dir, "log.jsonl"))
        fh.setFormatter(JsonFormatter())
        fh.addFilter(rid)
        root.addHandler(fh)
    for noisy in ("openai", "httpx", "httpcore", "litellm", "urllib3", "google"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _CONFIGURED = True
    return logging.getLogger("experiment")

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
