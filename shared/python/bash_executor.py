"""
Bash command executor for agent tool calls.

This module provides a unified interface for executing bash commands
across all agent implementations. It delegates to command_client.py
which handles the actual execution via named pipes.
"""

import subprocess
import sys
from typing import Optional, Dict, Any


def run_bash_command(
    command: str,
    working_dir: Optional[str] = None,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run a bash command using the command client.

    This function is IDENTICAL across all 5 implementations:
    - openai_baseline
    - openai_reasoning
    - anthropic_baseline
    - anthropic_reasoning
    - google_reasoning

    Args:
        command: The bash command to execute
        working_dir: Optional working directory for command execution
        timeout: Optional timeout in seconds (default handled by command_client)

    Returns:
        Dict with keys:
            - stdout: Standard output from the command
            - stderr: Standard error from the command
            - returncode: Exit code (0 for success, non-zero for failure, -1 for errors)
    """
    try:
        cmd_args = [sys.executable, "agent/command_client.py"]

        if working_dir:
            cmd_args.extend(["-d", working_dir])

        if timeout is not None:
            cmd_args.extend(["-t", str(timeout)])

        cmd_args.append(command)

        result = subprocess.run(cmd_args, capture_output=True, text=True)

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Error running command: {e}",
            "returncode": -1
        }


def format_tool_result(result: Dict[str, Any]) -> str:
    """
    Format a bash command result for display in agent conversation.

    Args:
        result: Dict from run_bash_command

    Returns:
        Formatted string with stdout, stderr, and return code
    """
    parts = []

    if result.get("stdout"):
        parts.append(f"stdout:\n{result['stdout']}")

    if result.get("stderr"):
        parts.append(f"stderr:\n{result['stderr']}")

    parts.append(f"return code: {result.get('returncode', -1)}")

    return "\n".join(parts)
