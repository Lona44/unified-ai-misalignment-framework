import json, os
from events import StepEvent
from canonical_emit import emit_step

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
