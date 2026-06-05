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


def test_no_reserved_logrecord_keys_in_extra():
    """Guard: passing a reserved LogRecord attribute (args, name, module, msg, ...)
    in `extra=` makes stdlib logging RAISE at call time — it crashed a live agent run.
    Scan every migrated source file so this whole class of bug can't recur (here or
    in the remaining loop migrations)."""
    import re, glob
    reserved = {"args", "name", "module", "msg", "message", "levelname", "levelno",
                "pathname", "filename", "lineno", "funcName", "created", "msecs",
                "relativeCreated", "thread", "threadName", "processName", "process",
                "exc_info", "exc_text", "stack_info", "taskName"}
    bad = []
    files = ["unified_runner.py"] + glob.glob("implementations/*/agent/run_loop.py")
    for f in files:
        src = open(f).read()
        for m in re.finditer(r"extra=\{([^}]*)\}", src, re.S):
            for key in re.findall(r"[\"'](\w+)[\"']\s*:", m.group(1)):
                if key in reserved:
                    bad.append(f"{f}: reserved key '{key}' in extra=")
    assert not bad, "Reserved LogRecord keys in extra= (logging will raise): " + "; ".join(bad)


def test_tool_call_log_pattern_does_not_raise(tmp_path):
    """Regression for the live crash: the exact tool_call log shape must not raise."""
    setup_logging(run_id="r", log_dir=str(tmp_path))
    get_logger("agent.openai").info("tool call",
        extra={"event": "tool_call", "step": 1, "function": "bash", "tool_args": "ls -la"})
    line = json.loads((tmp_path / "log.jsonl").read_text().strip().splitlines()[-1])
    assert line["event"] == "tool_call" and line["tool_args"] == "ls -la"
