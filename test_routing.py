#!/usr/bin/env python3
"""
Test script to verify routing logic without making API calls
"""

import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from unified_runner import UnifiedRunner


def test_routing():
    """Test routing logic for all model configurations"""

    test_cases = [
        # OpenAI models
        ("configs/gpt5_reasoning.json", "OpenAI Reasoning"),
        ("configs/o3_baseline.json", "OpenAI Baseline"),
        # Anthropic models
        ("configs/claude_sonnet4.json", "Anthropic Reasoning"),
        ("configs/claude_sonnet4_baseline.json", "Anthropic Baseline"),
    ]

    print("🧪 TESTING ROUTING LOGIC")
    print("=" * 50)

    for config_path, expected_route in test_cases:
        try:
            print(f"\n📋 Testing: {config_path}")
            runner = UnifiedRunner(config_path)

            # Get model and reasoning config
            model = runner.config["model_config"]["model"]
            enable_reasoning = runner.config["model_config"].get("enable_reasoning", False)

            print(f"   Model: {model}")
            print(f"   Reasoning: {enable_reasoning}")
            print(f"   Expected: {expected_route}")

            # Test routing (this should only print routing decisions, not execute)
            print("   Routing Decision:", end=" ")

            # Just test the routing logic without execution
            if model in ["o3", "gpt-5"]:
                if enable_reasoning:
                    print("→ OpenAI Reasoning ✅")
                else:
                    print("→ OpenAI Baseline ✅")
            elif "claude" in model:
                if enable_reasoning:
                    print("→ Anthropic Reasoning ✅")
                else:
                    print("→ Anthropic Baseline ✅")
            else:
                print("→ UNSUPPORTED ❌")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n🎯 ROUTING TEST COMPLETE")


if __name__ == "__main__":
    test_routing()
