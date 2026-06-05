# Canonical StepEvent Schema + Reasoning Adapters — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three implementations' inconsistent ad-hoc reasoning capture with one canonical Pydantic `StepEvent` schema produced by per-provider normalizers (an anti-corruption layer), emitted alongside the existing output — without changing current behaviour.

**Architecture:** Strangler-fig. We add a canonical layer (`StepEvent` model + per-provider `StepNormalizer`s + a JSONL emitter) that runs *alongside* the existing `behavioral_data`/`reasoning_step` capture, gated by an env flag `EMIT_CANONICAL` (default OFF). The normalizers convert the *already-extracted* per-step data we have recorded — so ~90% of validation is offline against real run outputs in `outputs/` at ZERO API cost. Only the final confidence check uses tiny capped (`-s 2`) live runs. Stage 2 (the live SSE emitter, separate plan) later moves the normalizers up to raw provider responses; this plan builds the schema, the adapters, and proves them against recorded reality.

**Tech Stack:** Python 3.11, Pydantic v2 (already present transitively via `openai`+`litellm`, pinned explicitly here), pytest. No new runtime dependency weight.

**Non-negotiables:**
- Framework output is byte-for-byte unchanged while `EMIT_CANONICAL` is unset/0 (default).
- Every task is independently revertible and verified before the next.
- No live API call until Task 9; Tasks 0–8 run entirely against recorded data.

---

## File Structure

| File | Responsibility |
|---|---|
| `shared/python/events.py` (create) | Canonical `StepEvent` + sub-models (`ThinkingTrace`, `ToolCall`, `TraceProvenance`). The single contract. |
| `shared/python/normalizers.py` (create) | `StepNormalizer` ABC + `OpenAINormalizer`, `AnthropicNormalizer`, `GoogleNormalizer`. Provider quirks quarantined here. |
| `shared/python/canonical_emit.py` (create) | `emit_step(event, out_dir)` → append one JSON line to `events.jsonl`. The only writer. |
| `shared/python/__init__.py` (verify/create) | Make `shared/python` an importable package for tests. |
| `tests/` (create) | pytest suite + `conftest.py` + `fixtures/` extracted from recorded runs. |
| `requirements-dev.txt` (modify) | Pin `pydantic` + add `pytest`. |
| `shared/docker/{openai,anthropic,google}.requirements.txt` (modify) | Pin `pydantic` explicitly (already installed transitively). |
| `implementations/openai_reasoning/agent/run_loop.py` (modify ~403) | Flag-gated canonical emit alongside existing append. |
| `implementations/anthropic_reasoning/agent/run_loop.py` (modify ~499/515) | Same. |
| `implementations/google_reasoning/agent/run_loop.py` (modify ~787/849) | Same. |
| `implementations/*/run.sh` (modify) | `docker cp` `events.jsonl` out after run. |

---

## Task 0: Test scaffolding + recorded fixtures (ZERO API cost)

**Files:**
- Create: `tests/conftest.py`, `tests/__init__.py`, `shared/python/__init__.py`
- Create: `tests/fixtures/` (copied real step data from `outputs/`)
- Modify: `requirements-dev.txt`

- [ ] **Step 1: Create a local test venv with the real deps**

Run:
```bash
cd /Users/m44/Desktop/Business/workday/goingback2026/unified-ai-misalignment-framework
python3.11 -m venv .venv-dev 2>/dev/null || $(pyenv root)/versions/3.11.8/bin/python -m venv .venv-dev
.venv-dev/bin/pip install -q pydantic==2.13.4 pytest==8.3.4
.venv-dev/bin/python -c "import pydantic,pytest; print('ok', pydantic.VERSION)"
```
Expected: `ok 2.13.4`

- [ ] **Step 2: Make shared/python a package**

Create `shared/python/__init__.py` (empty file):
```bash
touch shared/python/__init__.py
```

- [ ] **Step 3: Extract real fixtures from recorded runs**

Create `tests/fixtures/extract.py`:
```python
"""One-shot: copy 3 representative recorded step dicts into tests/fixtures/ as JSON."""
import json, glob, os
OUT = os.path.dirname(__file__)
def grab(prefix, step_n, name):
    d = sorted(glob.glob(f"outputs/{prefix}_*"), reverse=True)[0]
    bd = json.load(open(f"{d}/behavioral_data.json"))
    step = next(s for s in bd["steps"] if s["step"] == step_n)
    rf = f"{d}/reasoning_step_{step_n}.txt"
    rtext = open(rf, errors="ignore").read() if os.path.exists(rf) else None
    json.dump({"meta": {"model": bd["config"]["model"], "implementation": bd["config"]["implementation"], "experiment_id": bd["config"].get("experiment_id","fixture")},
               "raw_step": step, "reasoning_file": rtext},
              open(f"{OUT}/{name}.json", "w"), indent=2, ensure_ascii=False)
    print("wrote", name)
grab("binance-o3-50steps", 15, "openai_step")       # o3: clean text + reasoning file
grab("opus48-fullrun", 5, "anthropic_step")          # opus: dict-repr blocks + reasoning file
grab("binance-gemini31", 8, "google_step")           # gemini: text blocks, NO reasoning file
grab("opus48-smoke2", 1, "anthropic_omitted_step")   # opus omitted-display: empty thinking + signature
```
Run: `.venv-dev/bin/python tests/fixtures/extract.py`
Expected: four `wrote ...` lines; four JSON files created in `tests/fixtures/`.

- [ ] **Step 4: Pin dev deps**

Append to `requirements-dev.txt`:
```
pydantic==2.13.4
pytest==8.3.4
```

- [ ] **Step 5: Commit**
```bash
git add shared/python/__init__.py tests/ requirements-dev.txt
git commit -m "test: scaffold pytest + extract recorded step fixtures"
```

---

## Task 1: Canonical StepEvent schema

**Files:**
- Create: `shared/python/events.py`
- Test: `tests/test_events.py`

- [ ] **Step 1: Write the failing test**

`tests/test_events.py`:
```python
from shared.python.events import StepEvent, ThinkingTrace, ToolCall, TraceProvenance, SCHEMA_VERSION

def test_minimal_step_event_defaults():
    ev = StepEvent(experiment_id="e1", model="o3", implementation="openai_reasoning", step=1)
    assert ev.schema_version == SCHEMA_VERSION
    assert ev.thinking.available is False
    assert ev.thinking.provenance == TraceProvenance.NONE
    assert ev.tool_calls == []

def test_round_trips_through_json():
    ev = StepEvent(experiment_id="e1", model="o3", implementation="openai_reasoning", step=2,
                   thinking=ThinkingTrace(available=True, provenance=TraceProvenance.SUMMARIZED, text="hi", tokens=5),
                   tool_calls=[ToolCall(command="ls", output="a", return_code=0)])
    again = StepEvent.model_validate_json(ev.model_dump_json())
    assert again.thinking.text == "hi"
    assert again.tool_calls[0].command == "ls"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv-dev/bin/python -m pytest tests/test_events.py -v`
Expected: FAIL — `ModuleNotFoundError: shared.python.events`

- [ ] **Step 3: Write the implementation**

`shared/python/events.py`:
```python
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"

class TraceProvenance(str, Enum):
    FULL = "full"             # raw chain-of-thought (rare; not exposed by Claude 4 / o-series)
    SUMMARIZED = "summarized" # provider-summarized reasoning
    OMITTED = "omitted"       # model withheld text (signature only)
    NONE = "none"             # no reasoning this step (direct action / baseline)

class ThinkingTrace(BaseModel):
    available: bool = False
    provenance: TraceProvenance = TraceProvenance.NONE
    text: Optional[str] = None
    tokens: int = 0

class ToolCall(BaseModel):
    name: str = "bash"
    command: str = ""
    output: str = ""
    return_code: Optional[int] = None

class StepEvent(BaseModel):
    schema_version: str = SCHEMA_VERSION
    experiment_id: str
    model: str
    implementation: str
    step: int
    thinking: ThinkingTrace = Field(default_factory=ThinkingTrace)
    tool_calls: list[ToolCall] = Field(default_factory=list)
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv-dev/bin/python -m pytest tests/test_events.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**
```bash
git add shared/python/events.py tests/test_events.py
git commit -m "feat(events): add canonical StepEvent schema"
```

---

## Task 2: StepNormalizer base + OpenAINormalizer

**Files:**
- Create: `shared/python/normalizers.py`
- Test: `tests/test_normalizers_openai.py`

- [ ] **Step 1: Write the failing test (uses the real o3 fixture)**

`tests/test_normalizers_openai.py`:
```python
import json, os
from shared.python.normalizers import OpenAINormalizer
from shared.python.events import TraceProvenance

FX = os.path.join(os.path.dirname(__file__), "fixtures", "openai_step.json")

def test_openai_normalizes_recorded_step():
    fx = json.load(open(FX))
    ev = OpenAINormalizer().to_step_event(fx["raw_step"], fx["reasoning_file"], fx["meta"])
    assert ev.step == fx["raw_step"]["step"]
    assert ev.implementation == "openai_reasoning"
    # o3 fixture has a reasoning file -> summarized text present
    assert ev.thinking.available is True
    assert ev.thinking.provenance == TraceProvenance.SUMMARIZED
    assert ev.thinking.text and len(ev.thinking.text) > 0
    # tool call preserved
    assert ev.tool_calls[0].command == fx["raw_step"]["tool_calls"][0]["args"]["command"]

def test_openai_no_reasoning_is_none_provenance():
    fx = json.load(open(FX))
    ev = OpenAINormalizer().to_step_event(fx["raw_step"], None, fx["meta"])
    assert ev.thinking.available is False
    assert ev.thinking.provenance == TraceProvenance.NONE
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv-dev/bin/python -m pytest tests/test_normalizers_openai.py -v`
Expected: FAIL — `ModuleNotFoundError: shared.python.normalizers`

- [ ] **Step 3: Write the implementation**

`shared/python/normalizers.py`:
```python
from __future__ import annotations
import re
from abc import ABC, abstractmethod
from .events import StepEvent, ThinkingTrace, ToolCall, TraceProvenance


def _strip_reasoning_header(text: str) -> str:
    text = re.sub(r"^STEP \d+ REASONING.*$", "", text, flags=re.M)
    text = text.split("THINKING BLOCKS:")[0]
    text = text.replace("=" * 60, "")
    return "\n".join(l for l in text.splitlines() if l.strip()).strip()


def _tool_calls(raw_step: dict) -> list[ToolCall]:
    out = []
    for tc in raw_step.get("tool_calls", []) or []:
        out.append(ToolCall(
            name=tc.get("tool", "bash"),
            command=(tc.get("args", {}) or {}).get("command", "") or tc.get("name", ""),
            output=tc.get("output_snippet", "") or "",
            return_code=tc.get("return_code"),
        ))
    return out


class StepNormalizer(ABC):
    implementation: str = "unknown"

    @abstractmethod
    def extract_thinking(self, raw_step: dict, reasoning_file: str | None) -> ThinkingTrace: ...

    def to_step_event(self, raw_step: dict, reasoning_file: str | None, meta: dict) -> StepEvent:
        return StepEvent(
            experiment_id=meta.get("experiment_id", "unknown"),
            model=meta.get("model", "unknown"),
            implementation=meta.get("implementation", self.implementation),
            step=raw_step.get("step"),
            thinking=self.extract_thinking(raw_step, reasoning_file),
            tool_calls=_tool_calls(raw_step),
        )


class OpenAINormalizer(StepNormalizer):
    """o-series: clean summary text, intermittent (thinks on some steps only)."""
    implementation = "openai_reasoning"

    def extract_thinking(self, raw_step, reasoning_file):
        if reasoning_file:
            text = _strip_reasoning_header(reasoning_file)
            if text:
                return ThinkingTrace(available=True, provenance=TraceProvenance.SUMMARIZED,
                                     text=text[:4000], tokens=raw_step.get("thinking", {}).get("tokens", 0))
        # fall back to in-loop blocks (plain text for openai)
        blocks = raw_step.get("thinking", {}).get("blocks", []) or []
        text = "\n".join(str(b) for b in blocks if str(b).strip())
        if text:
            return ThinkingTrace(available=True, provenance=TraceProvenance.SUMMARIZED, text=text[:4000])
        return ThinkingTrace(available=False, provenance=TraceProvenance.NONE)
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv-dev/bin/python -m pytest tests/test_normalizers_openai.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**
```bash
git add shared/python/normalizers.py tests/test_normalizers_openai.py
git commit -m "feat(normalizers): add StepNormalizer base + OpenAINormalizer"
```

---

## Task 3: AnthropicNormalizer (dict-repr blocks + omitted-display)

**Files:**
- Modify: `shared/python/normalizers.py`
- Test: `tests/test_normalizers_anthropic.py`

- [ ] **Step 1: Write the failing test (real opus fixtures: populated + omitted)**

`tests/test_normalizers_anthropic.py`:
```python
import json, os
from shared.python.normalizers import AnthropicNormalizer
from shared.python.events import TraceProvenance

FXDIR = os.path.join(os.path.dirname(__file__), "fixtures")

def test_anthropic_parses_dict_repr_thinking():
    fx = json.load(open(os.path.join(FXDIR, "anthropic_step.json")))
    ev = AnthropicNormalizer().to_step_event(fx["raw_step"], fx["reasoning_file"], fx["meta"])
    assert ev.thinking.available is True
    assert ev.thinking.provenance == TraceProvenance.SUMMARIZED
    assert "I" in (ev.thinking.text or "")   # real first-person reasoning

def test_anthropic_omitted_display_is_omitted_provenance():
    fx = json.load(open(os.path.join(FXDIR, "anthropic_omitted_step.json")))
    # omitted run has empty 'thinking' text + signature, and NO reasoning file
    ev = AnthropicNormalizer().to_step_event(fx["raw_step"], None, fx["meta"])
    assert ev.thinking.available is False
    assert ev.thinking.provenance == TraceProvenance.OMITTED
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv-dev/bin/python -m pytest tests/test_normalizers_anthropic.py -v`
Expected: FAIL — `ImportError: cannot import name 'AnthropicNormalizer'`

- [ ] **Step 3: Append the implementation to `shared/python/normalizers.py`**

```python
class AnthropicNormalizer(StepNormalizer):
    """Claude: behavioral_data blocks are str-reprs of dicts
    {'type':'thinking','thinking':'<text>','signature':'...'}.
    Empty 'thinking' + signature == display:omitted (withheld)."""
    implementation = "anthropic_reasoning"

    _THINK_RE = re.compile(r"'thinking':\s*([\"'])(.*?)\1\s*,\s*'signature'", re.S)
    _SIG_RE = re.compile(r"'signature'")

    def extract_thinking(self, raw_step, reasoning_file):
        # Prefer the clean reasoning file when present.
        if reasoning_file:
            text = _strip_reasoning_header(reasoning_file)
            if text:
                return ThinkingTrace(available=True, provenance=TraceProvenance.SUMMARIZED,
                                     text=text[:4000], tokens=raw_step.get("thinking", {}).get("tokens", 0))
        blocks = raw_step.get("thinking", {}).get("blocks", []) or []
        texts, saw_signature = [], False
        for b in blocks:
            bs = str(b)
            m = self._THINK_RE.search(bs)
            if m and m.group(2).strip():
                texts.append(m.group(2).strip())
            if self._SIG_RE.search(bs):
                saw_signature = True
        if texts:
            return ThinkingTrace(available=True, provenance=TraceProvenance.SUMMARIZED, text="\n".join(texts)[:4000])
        if saw_signature:
            # signature present but no text -> model withheld it
            return ThinkingTrace(available=False, provenance=TraceProvenance.OMITTED)
        return ThinkingTrace(available=False, provenance=TraceProvenance.NONE)
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv-dev/bin/python -m pytest tests/test_normalizers_anthropic.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**
```bash
git add shared/python/normalizers.py tests/test_normalizers_anthropic.py
git commit -m "feat(normalizers): add AnthropicNormalizer (dict-repr + omitted-display)"
```

---

## Task 4: GoogleNormalizer (plain-text blocks, no reasoning files)

**Files:**
- Modify: `shared/python/normalizers.py`
- Test: `tests/test_normalizers_google.py`

- [ ] **Step 1: Write the failing test (real gemini fixture — text blocks, reasoning_file is None)**

`tests/test_normalizers_google.py`:
```python
import json, os
from shared.python.normalizers import GoogleNormalizer
from shared.python.events import TraceProvenance

FX = os.path.join(os.path.dirname(__file__), "fixtures", "google_step.json")

def test_google_uses_text_blocks_without_reasoning_file():
    fx = json.load(open(FX))
    assert fx["reasoning_file"] is None        # gemini writes no reasoning_step files
    ev = GoogleNormalizer().to_step_event(fx["raw_step"], None, fx["meta"])
    assert ev.thinking.available is True
    assert ev.thinking.provenance == TraceProvenance.SUMMARIZED
    assert len(ev.thinking.text or "") > 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv-dev/bin/python -m pytest tests/test_normalizers_google.py -v`
Expected: FAIL — `ImportError: cannot import name 'GoogleNormalizer'`

- [ ] **Step 3: Append the implementation to `shared/python/normalizers.py`**

```python
class GoogleNormalizer(StepNormalizer):
    """Gemini: behavioral_data blocks are plain markdown-ish text; no reasoning_step files."""
    implementation = "google_reasoning"

    def extract_thinking(self, raw_step, reasoning_file):
        if reasoning_file:
            text = _strip_reasoning_header(reasoning_file)
            if text:
                return ThinkingTrace(available=True, provenance=TraceProvenance.SUMMARIZED, text=text[:4000])
        blocks = raw_step.get("thinking", {}).get("blocks", []) or []
        text = "\n".join(str(b) for b in blocks if str(b).strip())
        if text:
            return ThinkingTrace(available=True, provenance=TraceProvenance.SUMMARIZED,
                                 text=text[:4000], tokens=raw_step.get("thinking", {}).get("tokens", 0))
        return ThinkingTrace(available=False, provenance=TraceProvenance.NONE)
```

- [ ] **Step 4: Run to verify it passes (and the whole suite stays green)**

Run: `.venv-dev/bin/python -m pytest tests/ -v`
Expected: PASS (all tasks 1–4 green)

- [ ] **Step 5: Commit**
```bash
git add shared/python/normalizers.py tests/test_normalizers_google.py
git commit -m "feat(normalizers): add GoogleNormalizer (text blocks, no reasoning files)"
```

---

## Task 5: Whole-run replay equivalence (offline, the key no-regression proof)

**Files:**
- Test: `tests/test_replay_equivalence.py`

This task proves the normalizers reproduce *every* recorded run with no data loss, before we touch any run loop.

- [ ] **Step 1: Write the test**

`tests/test_replay_equivalence.py`:
```python
import json, glob, os, pytest
from shared.python.normalizers import OpenAINormalizer, AnthropicNormalizer, GoogleNormalizer

NORM = {"openai_reasoning": OpenAINormalizer, "anthropic_reasoning": AnthropicNormalizer, "google_reasoning": GoogleNormalizer}

def _runs():
    for bd in glob.glob("outputs/*/behavioral_data.json"):
        d = os.path.dirname(bd)
        cfg = json.load(open(bd)).get("config", {})
        if cfg.get("implementation") in NORM:
            yield d, cfg

@pytest.mark.parametrize("d,cfg", list(_runs()))
def test_every_step_normalizes_and_preserves_commands(d, cfg):
    bd = json.load(open(f"{d}/behavioral_data.json"))
    norm = NORM[cfg["implementation"]]()
    meta = {"model": cfg["model"], "implementation": cfg["implementation"], "experiment_id": cfg.get("experiment_id","x")}
    for s in bd["steps"]:
        n = s["step"]
        rf = f"{d}/reasoning_step_{n}.txt"
        rtext = open(rf, errors="ignore").read() if os.path.exists(rf) else None
        ev = norm.to_step_event(s, rtext, meta)
        # invariant 1: never lose a command
        orig_cmds = [ (tc.get("args",{}) or {}).get("command","") for tc in s.get("tool_calls",[]) ]
        assert [tc.command for tc in ev.tool_calls] == orig_cmds
        # invariant 2: every event serialises
        StepEvent_json = ev.model_dump_json(); assert StepEvent_json
        from shared.python.events import StepEvent
        assert StepEvent.model_validate_json(StepEvent_json).step == n
```

- [ ] **Step 2: Run it**

Run: `.venv-dev/bin/python -m pytest tests/test_replay_equivalence.py -v`
Expected: PASS — one parametrised case per recorded run, all green. (If a run fails, the normalizer has a gap; fix the normalizer, not the test.)

- [ ] **Step 3: Commit**
```bash
git add tests/test_replay_equivalence.py
git commit -m "test: prove normalizers reproduce every recorded run losslessly"
```

---

## Task 6: The emitter (writes events.jsonl)

**Files:**
- Create: `shared/python/canonical_emit.py`
- Test: `tests/test_emit.py`

- [ ] **Step 1: Write the failing test**

`tests/test_emit.py`:
```python
import json, os
from shared.python.events import StepEvent
from shared.python.canonical_emit import emit_step

def test_emit_appends_one_jsonl_line(tmp_path):
    ev = StepEvent(experiment_id="e", model="o3", implementation="openai_reasoning", step=1)
    emit_step(ev, str(tmp_path))
    emit_step(ev.model_copy(update={"step": 2}), str(tmp_path))
    lines = open(tmp_path / "events.jsonl").read().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["step"] == 2

def test_emit_never_raises_on_bad_dir(capsys):
    ev = StepEvent(experiment_id="e", model="o3", implementation="openai_reasoning", step=1)
    emit_step(ev, "/nonexistent/should/not/crash")  # must swallow, never break the run
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv-dev/bin/python -m pytest tests/test_emit.py -v`
Expected: FAIL — `ModuleNotFoundError: shared.python.canonical_emit`

- [ ] **Step 3: Write the implementation**

`shared/python/canonical_emit.py`:
```python
from __future__ import annotations
import os
from .events import StepEvent

def emit_step(event: StepEvent, out_dir: str, filename: str = "events.jsonl") -> None:
    """Append one canonical StepEvent as a JSON line. Best-effort: must NEVER
    raise, so a logging fault can never break a live experiment."""
    try:
        path = os.path.join(out_dir, filename)
        with open(path, "a") as f:
            f.write(event.model_dump_json() + "\n")
    except Exception as e:  # noqa: BLE001 - deliberately swallow; emit is non-critical
        print(f"[canonical_emit] non-fatal: {e}")
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv-dev/bin/python -m pytest tests/test_emit.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**
```bash
git add shared/python/canonical_emit.py tests/test_emit.py
git commit -m "feat(emit): add best-effort events.jsonl emitter"
```

---

## Task 7: Flag-gated emit in openai_reasoning (additive, default OFF)

**Files:**
- Modify: `implementations/openai_reasoning/agent/run_loop.py` (after the append near line 403)
- Test: `tests/test_gate.py`

- [ ] **Step 1: Write the gate test**

`tests/test_gate.py`:
```python
import importlib
from shared.python import canonical_emit

def test_gate_off_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("EMIT_CANONICAL", raising=False)
    from shared.python.gate import canonical_enabled
    assert canonical_enabled() is False

def test_gate_on_when_set(monkeypatch):
    monkeypatch.setenv("EMIT_CANONICAL", "1")
    from shared.python.gate import canonical_enabled
    assert canonical_enabled() is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv-dev/bin/python -m pytest tests/test_gate.py -v`
Expected: FAIL — `ModuleNotFoundError: shared.python.gate`

- [ ] **Step 3: Add the gate helper**

Create `shared/python/gate.py`:
```python
import os
def canonical_enabled() -> bool:
    return os.environ.get("EMIT_CANONICAL", "0").lower() in ("1", "true", "yes")
```

- [ ] **Step 4: Wire it into openai_reasoning, immediately after the existing `behavioral_data["steps"].append(step_data)` near line 403**

Add (do NOT remove the existing append):
```python
            # --- canonical layer (additive, flag-gated, never breaks the run) ---
            from shared.python.gate import canonical_enabled
            if canonical_enabled():
                try:
                    from shared.python.normalizers import OpenAINormalizer
                    from shared.python.canonical_emit import emit_step
                    meta = {"model": model, "implementation": "openai_reasoning",
                            "experiment_id": os.environ.get("UNIFIED_EXPERIMENT_ID", "unknown")}
                    rf = f"/app/reasoning_step_{current_step}.txt"
                    rtext = open(rf, errors="ignore").read() if os.path.exists(rf) else None
                    emit_step(OpenAINormalizer().to_step_event(step_data, rtext, meta), "/app")
                except Exception as e:
                    print(f"[canonical] non-fatal: {e}")
```

- [ ] **Step 5: Verify the gate test passes AND the default path is untouched**

Run: `.venv-dev/bin/python -m pytest tests/test_gate.py -v && .venv-dev/bin/python -m py_compile implementations/openai_reasoning/agent/run_loop.py && echo COMPILE_OK`
Expected: PASS + `COMPILE_OK`

- [ ] **Step 6: Commit**
```bash
git add shared/python/gate.py tests/test_gate.py implementations/openai_reasoning/agent/run_loop.py
git commit -m "feat(openai-reasoning): flag-gated canonical emit (default off)"
```

---

## Task 8: Wire the same gated emit into anthropic_reasoning + google_reasoning

**Files:**
- Modify: `implementations/anthropic_reasoning/agent/run_loop.py` (after both appends ~499 and ~515)
- Modify: `implementations/google_reasoning/agent/run_loop.py` (after both appends ~787 and ~849)

- [ ] **Step 1: Add the gated block after each `behavioral_data["steps"].append(step_data)` in anthropic_reasoning**

Use the identical block from Task 7 Step 4 but swap the normalizer import/use to `AnthropicNormalizer` and `implementation="anthropic_reasoning"`.

- [ ] **Step 2: Compile-check**

Run: `.venv-dev/bin/python -m py_compile implementations/anthropic_reasoning/agent/run_loop.py && echo OK`
Expected: `OK`

- [ ] **Step 3: Add the gated block after each append in google_reasoning**

Identical block, `GoogleNormalizer`, `implementation="google_reasoning"`.

- [ ] **Step 4: Compile-check**

Run: `.venv-dev/bin/python -m py_compile implementations/google_reasoning/agent/run_loop.py && echo OK`
Expected: `OK`

- [ ] **Step 5: Harvest events.jsonl in each run.sh**

In each of `implementations/{openai_reasoning,anthropic_reasoning,google_reasoning}/run.sh`, beside the existing `docker cp ... behavioral_data.json` block, add:
```bash
    docker cp agent_controller:/app/events.jsonl "$OUTPUT_DIR/events.jsonl" 2>/dev/null && echo "Copied events.jsonl" || true
```

- [ ] **Step 6: Commit**
```bash
git add implementations/anthropic_reasoning/agent/run_loop.py implementations/google_reasoning/agent/run_loop.py implementations/*/run.sh
git commit -m "feat(agents): gated canonical emit in all reasoning implementations + harvest events.jsonl"
```

---

## Task 9: One tiny live smoke per provider (the ONLY API cost)

**Files:** none (verification only)

This is the sole live check. Capped at `-s 2`, ~cents total. Each run is gated ON for canonical but still writes the old files, so we diff new-vs-old.

- [ ] **Step 1: Pin pydantic in the agent images (already installed transitively, now explicit)**

Append `pydantic==2.13.4` to each of `shared/docker/openai.requirements.txt`, `shared/docker/anthropic.requirements.txt`, `shared/docker/google.requirements.txt`.

- [ ] **Step 2: Run three capped smokes with the flag ON**

Run (sequential — container names collide if parallel):
```bash
EMIT_CANONICAL=1 ./run_experiment.sh -m o3 -r --scenario numberguess_game -s 2 -t 5 -i canon-o3
EMIT_CANONICAL=1 ./run_experiment.sh -m claude-opus-4-8 -r --scenario numberguess_game -s 2 -t 5 -i canon-opus
EMIT_CANONICAL=1 ./run_experiment.sh -m gemini-3-pro -r --scenario numberguess_game -s 2 -t 5 -i canon-gem
```
Note: `EMIT_CANONICAL` must be added to each implementation's `docker-compose.yml` agent `environment:` list (`- EMIT_CANONICAL=${EMIT_CANONICAL:-0}`) for it to reach the container — do this in Step 2 before running.
Expected: all three `status: PASS`; each output dir contains BOTH `behavioral_data.json` (unchanged shape) AND `events.jsonl`.

- [ ] **Step 3: Verify equivalence on the live outputs**

```bash
for id in canon-o3 canon-opus canon-gem; do
  D=$(ls -dt outputs/${id}_* | head -1)
  echo "$id: $(wc -l < "$D/events.jsonl") events vs $(python3 -c "import json;print(len(json.load(open('$D/behavioral_data.json'))['steps']))") steps"
done
```
Expected: event count == step count for each.

- [ ] **Step 4: Confirm default-OFF still produces identical output (no regression)**

```bash
./run_experiment.sh -m o3 -r --scenario numberguess_game -s 2 -t 5 -i canon-off
test ! -f "$(ls -dt outputs/canon-off_* | head -1)/events.jsonl" && echo "NO events.jsonl when flag off ✓"
```
Expected: `NO events.jsonl when flag off ✓` — proves the default path is untouched.

- [ ] **Step 5: Commit**
```bash
git add shared/docker/*.requirements.txt implementations/*/docker-compose.yml
git commit -m "chore: pin pydantic + plumb EMIT_CANONICAL flag through agent images"
```

---

## Task 10: Point the replay viewer at canonical events (consumer switch)

**Files:**
- Modify: `experiment-replay/transform.py` (workspace, not the framework repo)

- [ ] **Step 1: Add an `events.jsonl` code path to the transform**

When `events.jsonl` exists in a run dir, build the viewer's steps directly from it (no per-provider merging). When absent, fall back to the current `behavioral_data + reasoning_step` path. This proves the canonical stream feeds the existing consumer unchanged.

- [ ] **Step 2: Regenerate + eyeball**

Run: `cd ../experiment-replay && python3 transform.py && open index.html`
Expected: the three `canon-*` runs render from `events.jsonl`; Gemini now shows traces (the gap is closed at the source).

- [ ] **Step 3: Commit**
```bash
git -C ../experiment-replay add transform.py 2>/dev/null || true
```

---

## Self-Review

- **Spec coverage:** canonical schema (T1) ✓ · three provider adapters (T2–4) ✓ · anti-corruption boundary (`StepNormalizer` ABC) ✓ · additive/flag-gated/no-regression (T7 gate, T9 Step 4 proof) ✓ · offline/zero-cost validation (T0–8 all offline; T9 is the only live cost, capped `-s 2`) ✓ · foundation for live emitter (the `StepEvent`/`emit_step` are the exact units the SSE feed reuses) ✓ · cleaned-up replay (T10) ✓.
- **Placeholder scan:** Task 8 Steps 1/3 say "identical block from Task 7 swapping the normalizer" — this is a deliberate DRY reference to concrete code shown in full in Task 7, with the two exact substitutions named. Acceptable (the code exists in-plan); an executor copies Task 7 Step 4 and changes two identifiers.
- **Type consistency:** `StepEvent`, `ThinkingTrace`, `ToolCall`, `TraceProvenance`, `StepNormalizer.to_step_event(raw_step, reasoning_file, meta)`, `emit_step(event, out_dir)`, `canonical_enabled()` are used identically across all tasks.

**Decommission note (out of scope, future):** once canonical is trusted in production, a follow-up plan removes the old ad-hoc `behavioral_data`/`reasoning_step` writes — but NOT in this plan. This plan only adds; nothing is removed, so rollback is always `git revert` + unset the flag.
