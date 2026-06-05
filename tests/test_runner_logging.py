from __future__ import annotations

import json

from obs import setup_logging, get_logger


def test_runner_log_shape(tmp_path):
    # Verifies the runner's logging call-shape produces a correlated json line.
    setup_logging(run_id="exp_42", log_dir=str(tmp_path))
    get_logger("runner").info("routing experiment", extra={"event": "route", "model": "o3"})
    line = json.loads((tmp_path / "log.jsonl").read_text().strip().splitlines()[-1])
    assert line["run_id"] == "exp_42" and line["event"] == "route" and line["component"] == "runner"
