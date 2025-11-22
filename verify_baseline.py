#!/usr/bin/env python3
"""
Verification script to compare reasoning vs baseline implementations
"""


def compare_implementations():
    """Compare key differences between reasoning and baseline versions"""

    print("🔍 COMPARING ANTHROPIC IMPLEMENTATIONS")
    print("=" * 60)

    reasoning_file = "implementations/anthropic_reasoning/agent/run_loop.py"
    baseline_file = "implementations/anthropic_baseline/agent/run_loop.py"

    # Check key differences
    differences = []

    print("📊 CHECKING KEY REASONING PARAMETERS...")

    # Check reasoning_effort parameter
    with open(reasoning_file) as f:
        reasoning_content = f.read()

    with open(baseline_file) as f:
        baseline_content = f.read()

    # Test 1: reasoning_effort parameter
    if '"reasoning_effort": "high"' in reasoning_content:
        print("✅ Reasoning version: Has reasoning_effort parameter")
    else:
        print("❌ Reasoning version: Missing reasoning_effort parameter")

    if '"reasoning_effort": "high"' in baseline_content:
        print("❌ Baseline version: Still has reasoning_effort parameter")
        differences.append("reasoning_effort parameter still present")
    else:
        print("✅ Baseline version: reasoning_effort parameter removed")

    # Test 2: Display message
    if "DISABLED (BASELINE)" in baseline_content:
        print("✅ Baseline version: Shows correct display message")
    else:
        print("❌ Baseline version: Missing baseline display message")
        differences.append("Missing baseline display message")

    # Test 3: Thinking blocks handling
    reasoning_thinking = reasoning_content.count("thinking_blocks")
    baseline_thinking = baseline_content.count("thinking_blocks")

    print("📋 Thinking blocks references:")
    print(f"   Reasoning version: {reasoning_thinking}")
    print(f"   Baseline version: {baseline_thinking}")

    if baseline_thinking < reasoning_thinking:
        print("✅ Baseline version: Reduced thinking blocks handling")
    else:
        print("⚠️  Baseline version: Same thinking blocks handling as reasoning")

    # Test 4: File size comparison
    reasoning_size = len(reasoning_content.split("\n"))
    baseline_size = len(baseline_content.split("\n"))

    print("📏 File size comparison:")
    print(f"   Reasoning version: {reasoning_size} lines")
    print(f"   Baseline version: {baseline_size} lines")
    print(f"   Difference: {reasoning_size - baseline_size} lines")

    # Summary
    print("\n🎯 VERIFICATION SUMMARY")
    print("=" * 40)

    if not differences:
        print("✅ All baseline modifications appear correct!")
        print("🚀 Ready for testing (when you approve API calls)")
    else:
        print("⚠️  Issues found:")
        for diff in differences:
            print(f"   - {diff}")

    print("\n📋 NEXT STEPS:")
    print("1. Review the changes above")
    print("2. When ready: Test with actual API calls")
    print("3. Compare reasoning vs baseline behavior")


if __name__ == "__main__":
    compare_implementations()
