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


def test_run_scripted_interview_records_qa():
    import interview
    messages = [{"role": "user", "content": "task"}]
    asked = []

    def ask(msgs):
        asked.append(msgs[-1]["content"])
        return f"answer to {msgs[-1]['content']}", ["a thought"]

    msgs, data = interview.run_scripted_interview(messages, ask, ["Q1", "Q2"])
    assert asked == ["Q1", "Q2"]
    assert [d["question"] for d in data] == ["Q1", "Q2"]
    assert data[0]["answer"] == "answer to Q1"
    assert data[0]["thinking"] == ["a thought"]
    # marker + (Q + A) * 2 appended onto the original message
    assert msgs[0]["content"] == "task"
    assert interview.INTERVIEW_MARKER in [m["content"] for m in msgs]


def test_run_scripted_interview_rolls_back_failed_question():
    import interview
    messages = [{"role": "user", "content": "task"}]

    def ask(msgs):
        raise RuntimeError("model error")

    msgs, data = interview.run_scripted_interview(messages, ask, ["Q1"])
    assert data == []
    # the failed question was rolled back; only the marker remains appended
    assert [m["content"] for m in msgs] == ["task", interview.INTERVIEW_MARKER]


def test_run_scripted_interview_empty_questions_noop():
    import interview
    messages = [{"role": "user", "content": "task"}]
    msgs, data = interview.run_scripted_interview(messages, lambda m: ("x", []), [])
    assert data == []
    assert msgs == [{"role": "user", "content": "task"}]


def test_two_score_result_fields():
    import interview
    r = interview.two_score_result(
        {"score": 100, "reasoning": "task"},
        {"score": 95, "reasoning": "full"},
        interviewed=True,
    )
    assert r["evaluation"] == 100
    assert r["evaluation_with_interview"] == 95
    assert r["interview_effect"] == -5  # honesty credit
    assert r["interviewed"] is True
    assert r["reasoning"] == "task" and r["reasoning_with_interview"] == "full"


def test_two_score_result_handles_none_scores():
    import interview
    r = interview.two_score_result({"score": None, "reasoning": "x"}, {"score": None, "reasoning": "y"}, False)
    assert r["evaluation"] == 0 and r["evaluation_with_interview"] == 0
    assert r["interview_effect"] == 0 and r["interviewed"] is False
