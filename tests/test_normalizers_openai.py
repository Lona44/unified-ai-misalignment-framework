import json, os
from normalizers import OpenAINormalizer
from events import TraceProvenance

FX = os.path.join(os.path.dirname(__file__), "fixtures", "openai_step.json")

def test_openai_normalizes_recorded_step():
    fx = json.load(open(FX))
    ev = OpenAINormalizer().to_step_event(fx["raw_step"], fx["reasoning_file"], fx["meta"])
    assert ev.step == fx["raw_step"]["step"]
    assert ev.implementation == "openai_reasoning"
    assert ev.thinking.available is True
    assert ev.thinking.provenance == TraceProvenance.SUMMARIZED
    assert ev.thinking.text and len(ev.thinking.text) > 0
    assert ev.tool_calls[0].command == fx["raw_step"]["tool_calls"][0]["args"]["command"]

def test_openai_no_reasoning_is_none_provenance():
    # A direct-action step: no reasoning file AND no in-loop blocks (o3 is
    # intermittent — it thinks on some steps, acts directly on others).
    raw = {"step": 1, "thinking": {"blocks": [], "block_count": 0, "tokens": 0},
           "tool_calls": [{"tool": "bash", "args": {"command": "ls"}, "return_code": 0, "output_snippet": ""}]}
    meta = {"model": "o3", "implementation": "openai_reasoning", "experiment_id": "x"}
    ev = OpenAINormalizer().to_step_event(raw, None, meta)
    assert ev.thinking.available is False
    assert ev.thinking.provenance == TraceProvenance.NONE
