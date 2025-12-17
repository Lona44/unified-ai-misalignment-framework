"""
Behavioral data collection for agent analysis.

This module provides a unified class for collecting and storing
behavioral data from agent execution across all implementations.
"""

import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ThinkingData:
    """Data about reasoning/thinking in a step."""
    tokens: int = 0
    block_count: int = 0
    content: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class ToolCallData:
    """Data about a tool call in a step."""
    name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    success: bool = True


@dataclass
class StepData:
    """Data collected for a single agent step."""
    step: int
    thinking: Optional[ThinkingData] = None
    tool_calls: List[ToolCallData] = field(default_factory=list)
    response_content: Optional[str] = None
    timestamp: Optional[str] = None


class BehavioralDataCollector:
    """
    Collector for agent behavioral data.

    This class provides a unified interface for collecting behavioral
    data across all agent implementations. Data structure is identical
    across openai_baseline, openai_reasoning, anthropic_baseline,
    anthropic_reasoning, and google_reasoning.

    Usage:
        collector = BehavioralDataCollector()
        collector.set_config(model="gpt-5", implementation="openai_baseline")

        # For each step:
        collector.start_step(step_number)
        collector.add_thinking(tokens=150, content="...")
        collector.add_tool_call("bash", {"command": "ls"}, result="...")
        collector.end_step()

        # When done:
        collector.save()
    """

    def __init__(self, output_path: str = "/app/behavioral_data.json"):
        self.output_path = output_path
        self._data: Dict[str, Any] = {
            "config": {},
            "steps": [],
            "summary": {
                "total_steps": 0,
                "total_thinking_tokens": 0,
                "total_tool_calls": 0,
                "total_thinking_blocks": 0,
            },
        }
        self._current_step: Optional[Dict[str, Any]] = None

    @property
    def data(self) -> Dict[str, Any]:
        """Access the raw behavioral data dict."""
        return self._data

    def set_config(
        self,
        model: str,
        implementation: str,
        reasoning_enabled: bool = False,
        experiment_id: Optional[str] = None,
        **kwargs
    ):
        """
        Set configuration for this run.

        Args:
            model: Model being tested (e.g., "gpt-5", "claude-opus-4")
            implementation: Implementation name (e.g., "openai_baseline")
            reasoning_enabled: Whether reasoning/thinking is enabled
            experiment_id: Optional experiment ID from platform
            **kwargs: Additional config fields
        """
        self._data["config"] = {
            "model": model,
            "implementation": implementation,
            "reasoning_enabled": reasoning_enabled,
            "experiment_id": experiment_id or os.environ.get("UNIFIED_EXPERIMENT_ID", "unknown"),
            **kwargs
        }

    def start_step(self, step_number: int):
        """Start recording a new step."""
        self._current_step = {
            "step": step_number,
            "thinking": {},
            "tool_calls": [],
        }

    def add_thinking(
        self,
        tokens: int = 0,
        content: Optional[str] = None,
        summary: Optional[str] = None,
        block_count: int = 1
    ):
        """
        Record thinking/reasoning data for current step.

        Args:
            tokens: Number of thinking tokens used
            content: Raw thinking content (may be truncated)
            summary: Optional summary of thinking
            block_count: Number of thinking blocks
        """
        if self._current_step is None:
            return

        self._current_step["thinking"] = {
            "tokens": tokens,
            "block_count": block_count,
        }
        if content:
            self._current_step["thinking"]["content"] = content
        if summary:
            self._current_step["thinking"]["summary"] = summary

    def add_tool_call(
        self,
        name: str,
        arguments: Dict[str, Any],
        result: Optional[str] = None,
        success: bool = True
    ):
        """
        Record a tool call for current step.

        Args:
            name: Tool name (bash, terminate, evaluate)
            arguments: Tool arguments
            result: Tool execution result
            success: Whether tool executed successfully
        """
        if self._current_step is None:
            return

        tool_data = {
            "name": name,
            "arguments": arguments,
        }
        if result is not None:
            tool_data["result"] = result
        if not success:
            tool_data["success"] = success

        self._current_step["tool_calls"].append(tool_data)

    def end_step(self, response_content: Optional[str] = None):
        """
        Finalize current step and add to steps list.

        Args:
            response_content: Optional assistant response content
        """
        if self._current_step is None:
            return

        if response_content:
            self._current_step["response_content"] = response_content

        self._data["steps"].append(self._current_step)
        self._current_step = None

    def add_interview_data(self, interview_data: List[Dict[str, str]]):
        """
        Add post-hoc interview data.

        Args:
            interview_data: List of {"question": ..., "answer": ...} dicts
        """
        self._data["interview"] = interview_data

    def _finalize(self):
        """Calculate summary statistics."""
        steps = self._data["steps"]
        self._data["summary"] = {
            "total_steps": len(steps),
            "total_thinking_tokens": sum(
                step.get("thinking", {}).get("tokens", 0) for step in steps
            ),
            "total_tool_calls": sum(
                len(step.get("tool_calls", [])) for step in steps
            ),
            "total_thinking_blocks": sum(
                step.get("thinking", {}).get("block_count", 0) for step in steps
            ),
        }

    def save(self, path: Optional[str] = None):
        """
        Save behavioral data to JSON file.

        Args:
            path: Optional override for output path
        """
        self._finalize()

        output = path or self.output_path
        with open(output, "w") as f:
            json.dump(self._data, f, indent=2)
        print(f"Behavioral data saved to {output}")

    def to_dict(self) -> Dict[str, Any]:
        """Get finalized data as dictionary."""
        self._finalize()
        return self._data


# Global instance for backward compatibility with existing code
_global_collector: Optional[BehavioralDataCollector] = None


def get_collector() -> BehavioralDataCollector:
    """Get or create the global behavioral data collector."""
    global _global_collector
    if _global_collector is None:
        _global_collector = BehavioralDataCollector()
    return _global_collector


def write_behavioral_data():
    """Write behavioral data to JSON file (backward compatible function)."""
    get_collector().save()


def write_result(result_data: Dict[str, Any], path: str = "result.json"):
    """
    Write result data to JSON file.

    Args:
        result_data: Result dictionary to write
        path: Output file path
    """
    with open(path, "w") as f:
        json.dump(result_data, f, indent=2)
    print(f"Results written to {path}")
