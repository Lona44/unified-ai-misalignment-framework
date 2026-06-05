from __future__ import annotations
import re
from abc import ABC, abstractmethod
from events import StepEvent, ThinkingTrace, ToolCall, TraceProvenance


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
        blocks = raw_step.get("thinking", {}).get("blocks", []) or []
        text = "\n".join(str(b) for b in blocks if str(b).strip())
        if text:
            return ThinkingTrace(available=True, provenance=TraceProvenance.SUMMARIZED, text=text[:4000])
        return ThinkingTrace(available=False, provenance=TraceProvenance.NONE)


class AnthropicNormalizer(StepNormalizer):
    """Claude: behavioral_data blocks are str-reprs of dicts
    {'type':'thinking','thinking':'<text>','signature':'...'}.
    Empty 'thinking' + signature == display:omitted (withheld)."""
    implementation = "anthropic_reasoning"

    _THINK_RE = re.compile(r"'thinking':\s*([\"'])(.*?)\1", re.S)
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
            return ThinkingTrace(available=False, provenance=TraceProvenance.OMITTED)
        return ThinkingTrace(available=False, provenance=TraceProvenance.NONE)


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
