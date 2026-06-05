import json, os
from normalizers import GoogleNormalizer
from events import TraceProvenance

FX = os.path.join(os.path.dirname(__file__), "fixtures", "google_step.json")

def test_google_uses_text_blocks_without_reasoning_file():
    fx = json.load(open(FX))
    assert fx["reasoning_file"] is None        # gemini writes no reasoning_step files
    ev = GoogleNormalizer().to_step_event(fx["raw_step"], None, fx["meta"])
    assert ev.thinking.available is True
    assert ev.thinking.provenance == TraceProvenance.SUMMARIZED
    assert len(ev.thinking.text or "") > 0
