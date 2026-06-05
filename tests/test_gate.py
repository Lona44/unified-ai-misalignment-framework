def test_gate_off_by_default(monkeypatch):
    monkeypatch.delenv("EMIT_CANONICAL", raising=False)
    from gate import canonical_enabled
    assert canonical_enabled() is False

def test_gate_on_when_set(monkeypatch):
    monkeypatch.setenv("EMIT_CANONICAL", "1")
    import importlib, gate
    importlib.reload(gate)
    assert gate.canonical_enabled() is True
