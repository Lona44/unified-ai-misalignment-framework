"""
Step logging utilities for agent implementations.

This module provides consistent step header formatting and
metadata display across all agent implementations.
"""

import os
from typing import Optional


# ANSI color codes
YELLOW = "\033[93m"
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"


class StepLogger:
    """
    Logger for agent execution steps.

    Provides consistent formatting for step headers and metadata
    across all agent implementations.

    Usage:
        logger = StepLogger(max_steps=30)
        logger.log_step_header(step=1)
        logger.log_tool_call("bash", {"command": "ls"})
        logger.log_tool_result(result)
    """

    def __init__(self, max_steps: int = 30):
        self.max_steps = max_steps

    def log_step_header(self, step: int):
        """
        Print step header with experiment metadata.

        This format is IDENTICAL across all 5 implementations.

        Args:
            step: Current step number (1-indexed)
        """
        remaining = self.max_steps - step + 1

        print(f"\n{YELLOW}{'='*60}{RESET}")
        print(f"{YELLOW}STEP {step}/{self.max_steps} (Steps remaining: {remaining}){RESET}")

        # Display unified experiment metadata from environment
        unified_model = os.environ.get("UNIFIED_MODEL", "unknown")
        unified_reasoning = os.environ.get("UNIFIED_REASONING", "unknown")
        unified_impl = os.environ.get("UNIFIED_IMPLEMENTATION", "Fresh Clone")
        unified_exp_id = os.environ.get("UNIFIED_EXPERIMENT_ID", "unknown")

        print(f"{YELLOW}Model: {unified_model} | Reasoning: {unified_reasoning} | {unified_impl}{RESET}")
        print(f"{YELLOW}Experiment: {unified_exp_id}{RESET}")
        print(f"{YELLOW}{'='*60}{RESET}")

    def log_tool_call(self, tool_name: str, arguments: dict):
        """
        Log a tool call.

        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments
        """
        print(f"\n{CYAN}[Tool Call: {tool_name}]{RESET}")
        if tool_name == "bash" and "command" in arguments:
            print(f"  Command: {arguments['command']}")
        elif tool_name == "terminate" and "reason" in arguments:
            print(f"  Reason: {arguments['reason']}")
        elif tool_name == "evaluate":
            if "score" in arguments:
                print(f"  Score: {arguments['score']}")
            if "explanation" in arguments:
                # Truncate long explanations
                explanation = arguments["explanation"]
                if len(explanation) > 200:
                    explanation = explanation[:200] + "..."
                print(f"  Explanation: {explanation}")

    def log_tool_result(
        self,
        result: str,
        success: bool = True,
        max_length: int = 1000
    ):
        """
        Log a tool execution result.

        Args:
            result: Tool result string
            success: Whether the tool succeeded
            max_length: Max characters to display (truncates longer)
        """
        color = GREEN if success else RED
        status = "Success" if success else "Error"

        print(f"{color}[Result: {status}]{RESET}")

        if len(result) > max_length:
            print(result[:max_length])
            print(f"... (truncated, {len(result)} total chars)")
        else:
            print(result)

    def log_thinking(
        self,
        tokens: int,
        content: Optional[str] = None,
        max_length: int = 500
    ):
        """
        Log reasoning/thinking output.

        Args:
            tokens: Number of thinking tokens
            content: Thinking content (optional, may be truncated)
            max_length: Max characters to display
        """
        print(f"\n{CYAN}[Thinking: {tokens} tokens]{RESET}")
        if content:
            if len(content) > max_length:
                print(content[:max_length])
                print(f"... (truncated)")
            else:
                print(content)

    def log_message(self, content: str, role: str = "assistant"):
        """
        Log an assistant or user message.

        Args:
            content: Message content
            role: Message role (assistant, user, system)
        """
        if content:
            color = CYAN if role == "assistant" else YELLOW
            print(f"\n{color}[{role.capitalize()}]{RESET}")
            print(content)

    def log_termination(self, reason: str):
        """Log agent termination."""
        print(f"\n{GREEN}[Agent Terminated]{RESET}")
        print(f"Reason: {reason}")

    def log_error(self, error: str):
        """Log an error."""
        print(f"\n{RED}[Error]{RESET}")
        print(error)

    def log_separator(self, char: str = "-", length: int = 40):
        """Print a separator line."""
        print(char * length)


# Module-level convenience functions
_default_logger: Optional[StepLogger] = None


def get_logger(max_steps: int = 30) -> StepLogger:
    """Get or create the default step logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = StepLogger(max_steps)
    return _default_logger


def log_step_header(step: int, max_steps: int = 30):
    """Convenience function for logging step header."""
    logger = StepLogger(max_steps)
    logger.log_step_header(step)
