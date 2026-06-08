import importlib


def _fresh(monkeypatch, **env):
    for k in ("UNIFIED_INTERVIEW", "UNIFIED_INTERVIEW_QUESTIONS"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import interview
    return importlib.reload(interview)


def test_default_questions_loaded_from_bundled_json(monkeypatch):
    iv = _fresh(monkeypatch)
    qs = iv.load_interview_questions()
    assert len(qs) >= 3
    assert all(isinstance(q, str) and q.strip() for q in qs)


def test_disabled_returns_empty(monkeypatch):
    iv = _fresh(monkeypatch, UNIFIED_INTERVIEW="off")
    assert iv.load_interview_questions() == []
    assert iv.interview_enabled() is False


def test_override_file_json_array(monkeypatch, tmp_path):
    f = tmp_path / "q.json"
    f.write_text('["Q one?", "Q two?"]')
    iv = _fresh(monkeypatch, UNIFIED_INTERVIEW_QUESTIONS=str(f))
    assert iv.load_interview_questions() == ["Q one?", "Q two?"]


def test_override_file_one_per_line(monkeypatch, tmp_path):
    f = tmp_path / "q.txt"
    f.write_text("First?\n\nSecond?\n")
    iv = _fresh(monkeypatch, UNIFIED_INTERVIEW_QUESTIONS=str(f))
    assert iv.load_interview_questions() == ["First?", "Second?"]


def test_missing_override_falls_back_to_bundled(monkeypatch):
    iv = _fresh(monkeypatch, UNIFIED_INTERVIEW_QUESTIONS="/nonexistent/path.json")
    assert len(iv.load_interview_questions()) >= 3
