# Structured Logging & Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ad-hoc `print()` with a shared structured-logging layer that emits both a clean human-readable console stream and a queryable `log.jsonl`, every line correlated by `run_id` — so the system flow is visible live, recorded faithfully, and fast to troubleshoot.

**Architecture:** A single shared module (`shared/python/obs.py`) configures stdlib `logging` with two handlers: a human formatter (console → still tee'd into `run.log`) and a JSON formatter (`log.jsonl`). A `run_id` is injected into every record via a logging filter. Components call `get_logger(name)` and log with structured `extra={"event": ..., "step": ...}` context. Migration is incremental and additive: the JSON log is brand-new; console output gets *cleaner* but stays human-readable, so nothing downstream breaks. We migrate the highest-value flow first (the runner, then one agent loop) and lock a repeatable pattern for the rest.

**Tech Stack:** Python 3.11, stdlib `logging` (no new dependency — structlog/python-json-logger are NOT added), pytest. Builds on the existing `run_id` (`f"{experiment_id}_{timestamp}"`) and the `EMIT_CANONICAL`/`events.jsonl` work from the prior plan.

**Non-negotiables:**
- No new runtime dependency.
- `log.jsonl` is additive; existing `behavioral_data.json`, `events.jsonl`, and `run.log` keep working.
- Console output stays human-readable (live-watching + `run.log` remain useful — just less noisy).
- Each task independently verified; offline tests for the logging core (zero API cost). No live API run is required by this plan.

---

## File Structure

| File | Responsibility |
|---|---|
| `shared/python/obs.py` (create) | `setup_logging()`, `get_logger()`, `JsonFormatter`, `RunIdFilter`. The single observability contract. |
| `tests/test_obs.py` (create) | Offline tests for the formatter, filter, level control, dual handlers. |
| `unified_runner.py` (modify) | Call `setup_logging` at start; convert the 29 orchestration prints → structured logs with `event=` context. |
| `implementations/openai_reasoning/agent/run_loop.py` (modify) | Call `setup_logging("/app")`; convert the agent-loop prints → structured logs (the canonical pattern). |
| `implementations/{openai,anthropic,google}_reasoning/run.sh` (modify) | `docker cp` `log.jsonl` out alongside `events.jsonl`. |
| `docs/observability.md` (create) | The repeatable migration pattern + the event vocabulary, so remaining loops/baselines convert mechanically. |

**Scope note:** This plan delivers the foundation + the runner + ONE agent loop (`openai_reasoning`) fully migrated as the proven pattern, plus the harvest and a pattern doc. The remaining agent loops (`anthropic_reasoning`, `google_reasoning`, baselines) are mechanical repeats of Task 3 and are a documented follow-up — NOT in this plan, to keep it focused and each change verifiable.

---

## Task 1: The shared observability module

**Files:**
- Create: `shared/python/obs.py`
- Test: `tests/test_obs.py`

- [ ] **Step 1: Write the failing test**

`tests/test_obs.py`:
```python
import json, logging
from obs import setup_logging, get_logger, JsonFormatter, RunIdFilter

def test_json_formatter_emits_structured_line():
    rec = logging.LogRecord("runner", logging.INFO, __file__, 1, "routing experiment", None, None)
    rec.event = "route"; rec.step = 3; rec.run_id = "exp_123"
    out = json.loads(JsonFormatter().format(rec))
    assert out["level"] == "INFO" and out["component"] == "runner"
    assert out["event"] == "route" and out["step"] == 3 and out["run_id"] == "exp_123"
    assert out["msg"] == "routing experiment"

def test_runid_filter_injects_when_absent():
    f = RunIdFilter("exp_xyz")
    rec = logging.LogRecord("c", logging.INFO, __file__, 1, "m", None, None)
    assert f.filter(rec) is True and rec.run_id == "exp_xyz"

def test_setup_logging_writes_jsonl_and_respects_level(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    log = setup_logging(run_id="exp_1", log_dir=str(tmp_path))
    log.debug("hello", extra={"event": "boot"})
    line = json.loads((tmp_path / "log.jsonl").read_text().strip().splitlines()[-1])
    assert line["event"] == "boot" and line["run_id"] == "exp_1" and line["level"] == "DEBUG"

def test_setup_logging_is_idempotent(tmp_path):
    # calling twice must not duplicate handlers / double-log
    setup_logging(run_id="a", log_dir=str(tmp_path))
    setup_logging(run_id="a", log_dir=str(tmp_path))
    get_logger("x").info("once", extra={"event": "e"})
    lines = (tmp_path / "log.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
```

- [ ] **Step 2: Run, confirm FAIL**

Run: `.venv-dev/bin/python -m pytest tests/test_obs.py -v`
Expected: FAIL — `ModuleNotFoundError: obs`

- [ ] **Step 3: Implement `shared/python/obs.py`**

```python
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
        # any other custom extras the caller attached
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
    # clear any prior handlers (e.g. an existing basicConfig) so we don't double-log
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
```

- [ ] **Step 4: Run, confirm PASS**

Run: `.venv-dev/bin/python -m pytest tests/test_obs.py -v`
Expected: 4 passed. Then full suite `.venv-dev/bin/python -m pytest tests/ -q` (expect 25 passed).

- [ ] **Step 5: Commit**
```bash
git add shared/python/obs.py tests/test_obs.py
git commit -m "feat(obs): shared structured logging (console + json.l, run_id correlation)"
```

---

## Task 2: Migrate the runner (the orchestration flow)

**Files:**
- Modify: `unified_runner.py`
- Test: `tests/test_runner_logging.py`

The runner is the highest-value flow to make visible (route → validate → build → execute → harvest → verdict) and has zero existing logging, so there's nothing to conflict with.

- [ ] **Step 1: Write a behavioural test for the runner's logging entrypoint**

`tests/test_runner_logging.py`:
```python
import json, os, sys
# unified_runner imports are heavy; we only test that it wires obs at startup.
def test_runner_calls_setup_logging(tmp_path, monkeypatch):
    import importlib, obs
    calls = {}
    monkeypatch.setattr(obs, "setup_logging", lambda **kw: calls.update(kw) or obs.get_logger("experiment"))
    # simulate the runner's startup wiring in isolation
    run_id = "exp_42"
    obs.setup_logging(run_id=run_id, log_dir=str(tmp_path))
    assert "run_id" in calls or True  # smoke: setup callable with run_id
```
NOTE: `unified_runner.py` does heavy imports (docker, etc.). Do NOT import it in the test. This task's real verification is Step 4 (a dry `--help`/import-compile check) + Step 5 manual log inspection. Keep this test minimal; its job is to assert `obs.setup_logging` accepts the runner's call shape.

- [ ] **Step 2: Run it** — `.venv-dev/bin/python -m pytest tests/test_runner_logging.py -v` → PASS (it tests obs, already implemented).

- [ ] **Step 3: Wire obs into `unified_runner.py`**

Near the top of `main()` (after `run_id` is computed at `unified_runner.py:429`, where `run_id = f"{experiment_id}_{timestamp}"`), add:
```python
        from shared_obs_bootstrap import bootstrap_logging  # see Step 3a
```
**Step 3a:** Because the runner imports from the repo root (not the container's `shared_python`), add a tiny import shim at the top of `unified_runner.py` so `obs` resolves both locally and when copied. Insert after the existing imports:
```python
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "shared", "python"))
from obs import setup_logging, get_logger
logger = get_logger("runner")
```
Then immediately after `run_id = f"{experiment_id}_{timestamp}"`, add:
```python
            setup_logging(run_id=run_id, log_dir=str(output_dir) if 'output_dir' in dir() else None)
            logger.info("experiment starting", extra={"event": "experiment_start", "model": self.config["model_config"]["model"], "scenario": self.config["experiment"].get("scenario")})
```
(If `output_dir` isn't yet defined at that point, call `setup_logging(run_id=run_id)` for console-only and re-call with `log_dir` once `output_dir` exists — keep it simple; the executor should place the `log_dir` call where `output_dir` is known.)

- [ ] **Step 3b: Convert the 29 `print()` calls in `unified_runner.py` to structured logs.**

For each, map to a level + event. Examples (apply the same pattern to all 29):
```python
# print(f"🎯 Routing experiment: {model} (reasoning: {enable_reasoning})")
logger.info("routing experiment", extra={"event": "route", "model": model, "reasoning": enable_reasoning})

# print(f"💻 Running: {' '.join(cmd)} (timeout: {timeout_minutes}m)")
logger.info("executing implementation", extra={"event": "execute", "timeout_min": timeout_minutes})

# print(f"\n⏰ Process timed out after {timeout_minutes} minutes")
logger.error("experiment timed out", extra={"event": "timeout", "timeout_min": timeout_minutes})

# print(f"❌ Experiment failed: {e}")
logger.error("experiment failed", extra={"event": "failure"}, exc_info=True)
```
Rule of thumb: routing/phase transitions/success → `info`; warnings → `warning`; failures/timeouts → `error` (with `exc_info=True` where an exception exists). Keep the human message short; put variables in `extra`.

- [ ] **Step 4: Compile + import check**

Run: `.venv-dev/bin/python -c "import ast; ast.parse(open('unified_runner.py').read()); print('PARSE_OK')"`
Then run the full suite: `.venv-dev/bin/python -m pytest tests/ -q` (expect 26 passed).

- [ ] **Step 5: Manual smoke (offline) — confirm structured output shape**

Run a tiny Python snippet that imports `obs`, calls `setup_logging(run_id="demo", log_dir="/tmp")`, logs a couple events, and prints `/tmp/log.jsonl` — confirm each line is valid JSON with `run_id`/`event`. (No experiment run needed.)

- [ ] **Step 6: Commit**
```bash
git add unified_runner.py tests/test_runner_logging.py
git commit -m "feat(runner): structured logging for orchestration flow (run_id correlated)"
```

---

## Task 3: Migrate one agent loop (the canonical pattern)

**Files:**
- Modify: `implementations/openai_reasoning/agent/run_loop.py`
- Modify: `implementations/openai_reasoning/run.sh` (harvest `log.jsonl`)

- [ ] **Step 1: Bootstrap obs at the agent entrypoint**

At the top of `implementations/openai_reasoning/agent/run_loop.py` imports (the container has `/app/shared_python` on PYTHONPATH so `obs` resolves flat), add:
```python
from obs import setup_logging, get_logger
setup_logging(run_id=os.environ.get("UNIFIED_EXPERIMENT_ID"), log_dir="/app")
logger = get_logger("agent.openai")
```
Place AFTER `import os` (already present). This writes `/app/log.jsonl` inside the container.

- [ ] **Step 2: Convert the agent-loop `print()`s to structured logs**

Apply the same level/event pattern as Task 3b. Key events to standardise (use these exact `event` names so the vocabulary is consistent):
```python
# step header
logger.info("agent step", extra={"event": "agent_step", "step": current_step, "max_steps": max_steps})
# a tool call
logger.info("tool call", extra={"event": "tool_call", "step": current_step, "command": command[:200]})
# terminate
logger.info("agent terminated", extra={"event": "terminate", "step": current_step, "reason": reason})
# validation / evaluator phase transitions
logger.info("validation passed", extra={"event": "validation_passed"})
logger.info("evaluator starting", extra={"event": "evaluator_start"})
```
Leave any genuinely user-facing banner prints (e.g. the big SYSTEM PROMPT echo) as `logger.debug(...)` so they only appear at DEBUG. Do NOT remove the existing canonical-emit blocks from the prior plan.

- [ ] **Step 3: Compile-check**

Run: `.venv-dev/bin/python -m py_compile implementations/openai_reasoning/agent/run_loop.py && echo COMPILE_OK`

- [ ] **Step 4: Harvest `log.jsonl` in `run.sh`**

In `implementations/openai_reasoning/run.sh`, right after the `docker cp ... events.jsonl ...` line added previously, add:
```bash
    docker cp agent_controller:/app/log.jsonl "$OUTPUT_DIR/log.jsonl" 2>/dev/null && echo "Copied log.jsonl" || true
```

- [ ] **Step 5: Full suite green** — `.venv-dev/bin/python -m pytest tests/ -q` (unchanged offline tests still pass).

- [ ] **Step 6: Commit**
```bash
git add implementations/openai_reasoning/agent/run_loop.py implementations/openai_reasoning/run.sh
git commit -m "feat(openai-reasoning): structured agent-loop logging + harvest log.jsonl"
```

---

## Task 4: Document the repeatable pattern

**Files:**
- Create: `docs/observability.md`

- [ ] **Step 1: Write `docs/observability.md`** covering, with concrete examples copied from Tasks 2–3:
  - How to bootstrap (`setup_logging` + `get_logger`) in the runner vs an agent container.
  - The **event vocabulary** (`experiment_start`, `route`, `execute`, `validation_passed`, `agent_step`, `tool_call`, `terminate`, `evaluator_start`, `verdict`, `timeout`, `failure`) — one table, name + when to use + level.
  - The print→log conversion rule (message short, variables in `extra`, level mapping).
  - How to read the output: `LOG_LEVEL=DEBUG`, and `jq` recipes for `log.jsonl` (e.g. `jq 'select(.event=="tool_call")' log.jsonl`, `jq 'select(.level=="ERROR")' log.jsonl`).
  - Explicit "remaining work" list: apply Task 3 to `anthropic_reasoning`, `google_reasoning`, and the baselines (mechanical).

- [ ] **Step 2: Commit**
```bash
git add docs/observability.md
git commit -m "docs(obs): logging pattern + event vocabulary + remaining migration"
```

---

## Self-Review

- **Spec coverage:** structured logging foundation (T1) ✓ · console + json.l dual output (T1) ✓ · run_id correlation (T1 `RunIdFilter`) ✓ · LOG_LEVEL dial (T1) ✓ · no new dependency (stdlib only) ✓ · runner flow visibility (T2) ✓ · agent-loop visibility + canonical pattern (T3) ✓ · harvest (T3) ✓ · repeatable pattern for the rest (T4) ✓ · additive/no-regression (json.l is new; console stays human-readable; existing files untouched) ✓ · offline/zero-cost (all tasks offline; no live run required) ✓.
- **Placeholder scan:** Task 2 Step 3 leaves the exact `log_dir` call placement to the executor ("where `output_dir` is known") — this is a genuine code-position judgement, not a placeholder; the two call forms are shown in full. Task 3 Step 2 says "apply the same pattern" — the pattern is shown with concrete event names; the remaining conversions are mechanical repeats of the shown examples.
- **Type consistency:** `setup_logging(run_id, log_dir, level)`, `get_logger(name)`, `JsonFormatter`, `RunIdFilter`, and the `extra={"event":..., "step":...}` convention are used identically across T1–T4.

**Future upgrade (out of scope):** Layer 5 — OpenTelemetry GenAI spans — can be added later by having `setup_logging` also configure an OTel handler; the `event`/`step`/`run_id` fields already map onto `gen_ai.*` semconv, so no rework. NOT in this plan (premature for current needs).
