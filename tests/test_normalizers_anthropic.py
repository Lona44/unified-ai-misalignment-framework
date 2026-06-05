import json, os
from normalizers import AnthropicNormalizer
from events import TraceProvenance

FXDIR = os.path.join(os.path.dirname(__file__), "fixtures")

def test_anthropic_parses_dict_repr_thinking():
    fx = json.load(open(os.path.join(FXDIR, "anthropic_step.json")))
    ev = AnthropicNormalizer().to_step_event(fx["raw_step"], fx["reasoning_file"], fx["meta"])
    assert ev.thinking.available is True
    assert ev.thinking.provenance == TraceProvenance.SUMMARIZED
    assert "I" in (ev.thinking.text or "")

def test_anthropic_omitted_display_is_omitted_provenance():
    fx = json.load(open(os.path.join(FXDIR, "anthropic_omitted_step.json")))
    # omitted run: empty 'thinking' text + signature, and NO reasoning file
    ev = AnthropicNormalizer().to_step_event(fx["raw_step"], None, fx["meta"])
    assert ev.thinking.available is False
    assert ev.thinking.provenance == TraceProvenance.OMITTED
