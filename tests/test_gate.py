def test_gate_on_by_default(monkeypatch):
    monkeypatch.delenv("EMIT_CANONICAL", raising=False)
    import importlib, gate
    importlib.reload(gate)
    assert gate.canonical_enabled() is True


def test_gate_off_when_disabled(monkeypatch):
    import importlib, gate
    for val in ("0", "false", "no"):
        monkeypatch.setenv("EMIT_CANONICAL", val)
        importlib.reload(gate)
        assert gate.canonical_enabled() is False, f"EMIT_CANONICAL={val} should disable"


def test_gate_on_when_set(monkeypatch):
    monkeypatch.setenv("EMIT_CANONICAL", "1")
    import importlib, gate
    importlib.reload(gate)
    assert gate.canonical_enabled() is True
