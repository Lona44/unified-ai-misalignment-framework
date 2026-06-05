from events import StepEvent, ThinkingTrace, ToolCall, TraceProvenance, SCHEMA_VERSION

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
