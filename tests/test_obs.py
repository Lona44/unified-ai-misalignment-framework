import json, logging
from obs import setup_logging, get_logger, JsonFormatter, RunIdFilter

def test_json_formatter_emits_structured_line():
    rec = logging.LogRecord("runner", logging.INFO, __file__, 1, "routing experiment", None, None)
    rec.event = "route"; rec.step = 3; rec.run_id = "exp_123"
    out = json.loads(JsonFormatter().format(rec))
    assert out["level"] == "INFO" and out["component"] == "runner"
    assert out["event"] == "route" and out["step"] == 3 and out["run_id"] == "exp_123"
    assert out["msg"] == "routing experiment"

def test_runid_filter_injects_when_absent():
    f = RunIdFilter("exp_xyz")
    rec = logging.LogRecord("c", logging.INFO, __file__, 1, "m", None, None)
    assert f.filter(rec) is True and rec.run_id == "exp_xyz"

def test_setup_logging_writes_jsonl_and_respects_level(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    log = setup_logging(run_id="exp_1", log_dir=str(tmp_path))
    log.debug("hello", extra={"event": "boot"})
    line = json.loads((tmp_path / "log.jsonl").read_text().strip().splitlines()[-1])
    assert line["event"] == "boot" and line["run_id"] == "exp_1" and line["level"] == "DEBUG"

def test_setup_logging_is_idempotent(tmp_path):
    setup_logging(run_id="a", log_dir=str(tmp_path))
    setup_logging(run_id="a", log_dir=str(tmp_path))
    get_logger("x").info("once", extra={"event": "e"})
    lines = (tmp_path / "log.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
