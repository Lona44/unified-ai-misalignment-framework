import json, glob, os, pytest
from normalizers import OpenAINormalizer, AnthropicNormalizer, GoogleNormalizer
from events import StepEvent

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
    meta = {"model": cfg["model"], "implementation": cfg["implementation"], "experiment_id": cfg.get("experiment_id", "x")}
    for s in bd["steps"]:
        n = s["step"]
        rf = f"{d}/reasoning_step_{n}.txt"
        rtext = open(rf, errors="ignore").read() if os.path.exists(rf) else None
        ev = norm.to_step_event(s, rtext, meta)
        # invariant 1: never lose a command
        orig_cmds = [(tc.get("args", {}) or {}).get("command", "") for tc in s.get("tool_calls", [])]
        assert [tc.command for tc in ev.tool_calls] == orig_cmds
        # invariant 2: every event serialises and round-trips its step number
        js = ev.model_dump_json()
        assert StepEvent.model_validate_json(js).step == n
