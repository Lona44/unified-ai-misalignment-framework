# Observability: Structured Logging

## 1. Overview

The logging layer emits a human-readable console stream and a machine-queryable
`log.jsonl` side-by-side, both stamped with the same `run_id` so every line
across the runner and the agent container is correlated. `log.jsonl` lands in
the run's output directory inside the container (`/app/log.jsonl`) and is
harvested by `run.sh` via `docker cp` into `outputs/<run_id>/log.jsonl` at the
end of each run.

---

## 2. Bootstrap

### Runner (host process)

```python
# top of unified_runner.py — sys.path shim so obs.py is importable
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "shared", "python"))
from obs import setup_logging, get_logger

# Console-only at startup; file handler added once output_dir is known
setup_logging(level="DEBUG" if args.verbose else None)
logger = get_logger("runner")

# ... later, once output_dir exists:
setup_logging(run_id=run_id, log_dir=str(output_dir))
```

### Agent (container)

```python
# top of run_loop.py — PYTHONPATH already includes /app/shared_python
from obs import setup_logging, get_logger

setup_logging(run_id=os.environ.get("UNIFIED_EXPERIMENT_ID"), log_dir="/app")
logger = get_logger("agent.openai")   # use agent.<provider> convention
```

`setup_logging` is idempotent — calling it twice (container bootstrap then
runner re-call after `output_dir` is created) replaces handlers safely without
duplicating output.

---

## 3. Event Vocabulary

| `event` | When to emit | Level |
|---------|-------------|-------|
| `experiment_start` | Runner: experiment ID assigned, subprocess about to be launched | INFO |
| `config_loaded` | Runner: config JSON parsed successfully | INFO |
| `validation_passed` | Runner + Agent: a validation check passed (use `check=` field for which one) | INFO |
| `route` | Runner: model + reasoning flags resolved, before routing decision | INFO |
| `route_selected` | Runner: implementation chosen (use `implementation=` field) | INFO |
| `env_prepare` | Runner: temp directory created and populated | INFO |
| `docker_assets` | Runner: shared Dockerfile/requirements selected (use `asset_type=`) | INFO |
| `prompt_updated` | Runner: PROMPT.json model field written/remapped | INFO |
| `execute` | Runner: `docker compose up` subprocess started | INFO |
| `subprocess_output` | Runner: live line from docker compose stdout | INFO |
| `verbose_mode` | Runner: `--verbose` flag active | DEBUG |
| `run_start` | Agent: main() entry, model identified from PROMPT.json | INFO |
| `prompts_loaded` | Agent: PROMPT.json read | INFO |
| `validation_start` | Agent: Phase 1 validation beginning | INFO |
| `agent_start` | Agent: Phase 2 agent loop beginning | INFO |
| `agent_step` | Agent + Evaluator: start of each step iteration (use `step=`, `phase=` fields) | INFO |
| `tool_call` | Agent + Evaluator: a tool is being dispatched (use `function=`, `args=` fields) | INFO |
| `tool_result` | Agent + Evaluator: result of a bash tool call (use `returncode=`, `stdout=`, `stderr=`) | DEBUG |
| `terminate` | Agent: model called the `terminate` tool | INFO |
| `evaluator_start` | Agent: Phase 3 evaluator loop beginning | INFO |
| `evaluator_complete` | Agent: evaluator called `evaluate` tool and returned score | INFO |
| `run_complete` | Agent: final score and reasoning captured | INFO |
| `reasoning_summary` | Agent: reasoning block from Responses API (DEBUG only) | DEBUG |
| `model_response` | Agent + Evaluator: raw content preview after each API call | DEBUG |
| `model_reasoning` | Agent: model `.reasoning` field (DeepSeek V3.1) | DEBUG |
| `api_retry` | Agent: transient OpenAI error, backing off | WARNING |
| `config_warning` | Agent: bad env-var value, falling back to default | WARNING |
| `openrouter_init` | Agent: OpenRouter base URL selected | INFO |
| `behavioral_data_saved` | Agent: behavioral_data.json written | INFO |
| `history_saved` | Agent: full_history.json written | INFO |
| `description_loaded` | Agent: DESCRIPTION.md read for evaluator | INFO |
| `results_written` | Agent: result.json written | INFO |
| `max_steps_reached` | Agent + Evaluator: loop exited via step limit | INFO / WARNING |
| `behavioral_data_loaded` | Runner: behavioral_data.json loaded into standardized result | INFO |
| `standardized_result` | Runner: standardized_result.json written | INFO |
| `experiment_complete` | Runner: output_dir populated, subprocess returned 0 | INFO |
| `timeout` | Runner: subprocess hit the timeout ceiling | ERROR |
| `verdict` | Runner: final PASS / non-PASS status logged | INFO / WARNING |
| `failure` | Runner: unhandled exception in main() | ERROR |
| `error` | Agent + Runner: any local failure (parse error, bad response, etc.) | ERROR / WARNING |

---

## 4. Conversion Rule: `print()` → `logger`

**Level mapping**

| Situation | Level |
|-----------|-------|
| Normal flow, phase transitions, success | `INFO` |
| Recoverable issues, unexpected-but-non-fatal state | `WARNING` |
| Exceptions, failed operations | `ERROR` with `exc_info=True` inside `except` |
| Banners, full prompt echoes, verbose dumps | `DEBUG` |

**Rule**: the log message is a short human sentence; every variable goes in
`extra={}` as a named field — never interpolated into the string.

**Before:**

```python
print(f"Starting agent with model={model}, step={current_step}/{max_steps}")
```

**After:**

```python
logger.info(
    "agent step",
    extra={
        "event": "agent_step",
        "step": current_step,
        "max_steps": max_steps,
        "model": model,
    },
)
```

**Exception pattern:**

```python
except Exception as e:
    logger.error("tool argument parse failed", extra={"event": "error", "step": current_step}, exc_info=True)
```

> **Exception to the rule**: the three `print(f"[canonical] non-fatal: {e}")` lines
> inside the canonical-emit `except` blocks in `run_loop.py` are intentionally left
> as plain prints — the canonical layer is designed to never touch the logger to
> avoid interfering with the run.

---

## 5. Reading the Logs

### Full detail

```bash
LOG_LEVEL=DEBUG ./run_experiment.sh configs/my_experiment.json
```

### Query `log.jsonl` with `jq`

Filter all tool calls from a run:
```bash
jq 'select(.event=="tool_call")' outputs/<run_id>/log.jsonl
```

Show only errors:
```bash
jq 'select(.level=="ERROR")' outputs/<run_id>/log.jsonl
```

Compact timeline (timestamp, event, message) for a specific run:
```bash
jq -r 'select(.run_id=="<id>") | "\(.ts) \(.event) \(.msg)"' outputs/<run_id>/log.jsonl
```

Show every agent step with step number and remaining steps:
```bash
jq 'select(.event=="agent_step") | {step, remaining_steps, phase}' outputs/<run_id>/log.jsonl
```

Extract final evaluation score:
```bash
jq 'select(.event=="evaluator_complete") | {score, reasoning}' outputs/<run_id>/log.jsonl
```

---

## 6. Remaining Migration Checklist

The following implementations still use `print()` for flow logging and have not
yet received the `setup_logging` bootstrap. Apply the same pattern as
`openai_reasoning`:

- [ ] `implementations/anthropic_reasoning/agent/run_loop.py` — add
  `setup_logging(run_id=os.environ.get("UNIFIED_EXPERIMENT_ID"), log_dir="/app")`
  at module top; replace `print()` calls with `logger.*` using the event vocabulary above.
- [ ] `implementations/google_reasoning/agent/run_loop.py` — same as above.
- [ ] `implementations/openai_baseline/agent/run_loop.py` — same as above.
- [ ] `implementations/anthropic_baseline/agent/run_loop.py` — same as above.
- [ ] Each of the above `run.sh` files — add the harvest line after the
  `behavioral_data.json` copy block:
  ```bash
  docker cp agent_controller:/app/log.jsonl "$OUTPUT_DIR/log.jsonl" 2>/dev/null && echo "Copied log.jsonl" || true
  ```
  (The `openai_reasoning/run.sh` already has this line at line 189.)

---

## 7. Future: OpenTelemetry

The `event`, `step`, and `run_id` fields already map cleanly onto the
`gen_ai.*` semantic conventions, so `setup_logging` can later be extended to
attach an OTel `LoggingHandler` or span exporter — no caller changes required.
