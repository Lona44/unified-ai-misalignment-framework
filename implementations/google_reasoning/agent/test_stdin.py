#!/usr/bin/env python3
"""Quick stdin test - no API calls"""
import sys
import select

print("=== STDIN TEST ===")
print(f"stdin.isatty(): {sys.stdin.isatty()}")
print(f"stdin.fileno(): {sys.stdin.fileno()}")

# Test 1: select with timeout
print("\n--- Test 1: select() with 10s timeout ---")
print("Type something and press Enter:")
print("> ", end="", flush=True)

ready, _, _ = select.select([sys.stdin], [], [], 10)
if ready:
    line = sys.stdin.readline().strip()
    print(f"select() Got: '{line}'")

    # Test 2: basic input() if select worked
    print("\n--- Test 2: input() ---")
    print("Type something else:")
    try:
        line2 = input("> ")
        print(f"input() Got: '{line2}'")
    except EOFError:
        print("input() EOFError - stdin exhausted")
else:
    print("TIMEOUT - no input received in 10 seconds")

print("\n=== TEST COMPLETE ===")
