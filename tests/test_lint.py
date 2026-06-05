"""Lint gate: catch the class of runtime bug that offline unit tests miss —
undefined names and 'referenced before assignment' (which crashed a live agent
run when a log call referenced eval_model before it was assigned). Runs pyflakes
over the runner, every agent loop, and the shared modules. Only fails on the
two fatal categories; ignores style noise (unused vars/imports)."""
import glob
import subprocess
import sys


def test_no_undefined_or_unbound_names():
    files = (
        ["unified_runner.py"]
        + glob.glob("implementations/*/agent/run_loop.py")
        + glob.glob("shared/python/*.py")
    )
    res = subprocess.run([sys.executable, "-m", "pyflakes", *files], capture_output=True, text=True)
    fatal = [
        line for line in (res.stdout + res.stderr).splitlines()
        if "undefined name" in line or "referenced before assignment" in line
    ]
    assert not fatal, "pyflakes found fatal name errors:\n" + "\n".join(fatal)
