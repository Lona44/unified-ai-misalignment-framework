"""
Shared behavioral data utilities for agent analysis.

Simple functions that match how implementations actually collect data.
"""

import json


def create_behavioral_data():
    """Create the standard behavioral data structure."""
    return {
        "config": {},
        "steps": [],
        "summary": {
            "total_steps": 0,
            "total_thinking_tokens": 0,
            "total_tool_calls": 0,
            "total_thinking_blocks": 0,
        },
    }


def finalize_behavioral_data(data):
    """Calculate summary statistics for behavioral data."""
    data["summary"]["total_steps"] = len(data["steps"])
    data["summary"]["total_thinking_tokens"] = sum(
        step.get("thinking", {}).get("tokens", 0) for step in data["steps"]
    )
    data["summary"]["total_tool_calls"] = sum(
        len(step.get("tool_calls", [])) for step in data["steps"]
    )
    data["summary"]["total_thinking_blocks"] = sum(
        step.get("thinking", {}).get("block_count", 0) for step in data["steps"]
    )


def write_behavioral_data(data, paths=None):
    """
    Write behavioral data to JSON file(s).

    Args:
        data: The behavioral_data dict
        paths: List of paths to write to (default: ["/app/behavioral_data.json"])
    """
    if paths is None:
        paths = ["/app/behavioral_data.json"]

    finalize_behavioral_data(data)

    for path in paths:
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not write to {path}: {e}")

    print(f"Behavioral data saved to {paths[0]}")
    print(f"  Steps: {data['summary']['total_steps']}")
    print(f"  Thinking tokens: {data['summary']['total_thinking_tokens']}")
    print(f"  Thinking blocks: {data['summary']['total_thinking_blocks']}")
    print(f"  Tool calls: {data['summary']['total_tool_calls']}")
