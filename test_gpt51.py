#!/usr/bin/env python3
"""
Quick test script to understand GPT-5.1 API behavior
"""

import os
from openai import OpenAI

# Load .env file
from pathlib import Path
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

client = OpenAI()

question = "What is the meaning of life, in one short sentence?"

print("="*60)
print("Testing GPT-5.1 API Models")
print("="*60)

# Test 1: gpt-5.1 with Responses API (like we use for GPT-5)
print("\n1. Testing gpt-5.1 with Responses API (reasoning enabled)")
print("-"*60)
try:
    response = client.responses.create(
        model="gpt-5.1",
        input=[{"role": "user", "content": question}],
        reasoning={"summary": "auto", "effort": "high"},
        store=False
    )

    print("SUCCESS with Responses API!")
    print(f"Response type: {type(response)}")

    if hasattr(response, 'output') and response.output:
        for i, item in enumerate(response.output):
            item_type = type(item).__name__
            print(f"\nOutput item {i}: {item_type}")

            if item_type == 'ResponseTextItem':
                print(f"Text: {item.text}")
            elif item_type == 'ResponseReasoningItem':
                if hasattr(item, 'summary'):
                    print(f"Reasoning summary:")
                    for summary_item in item.summary:
                        if hasattr(summary_item, 'text'):
                            print(f"  {summary_item.text}")
            elif item_type == 'ResponseOutputMessage':
                if hasattr(item, 'content'):
                    for content_item in item.content:
                        if hasattr(content_item, 'text'):
                            print(f"Content: {content_item.text}")

except Exception as e:
    print(f"FAILED: {e}")

# Test 2: gpt-5.1 with Chat Completions API
print("\n\n2. Testing gpt-5.1 with Chat Completions API")
print("-"*60)
try:
    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[{"role": "user", "content": question}]
    )

    print("SUCCESS with Chat Completions API!")
    print(f"Response: {response.choices[0].message.content}")

except Exception as e:
    print(f"FAILED: {e}")

# Test 3: gpt-5.1 with Responses API and reasoning_effort: 'none'
print("\n\n3. Testing gpt-5.1 with Responses API (reasoning_effort: 'none')")
print("-"*60)
try:
    response = client.responses.create(
        model="gpt-5.1",
        input=[{"role": "user", "content": question}],
        reasoning={"summary": "auto", "effort": "none"},
        store=False
    )

    print("SUCCESS with Responses API (no reasoning)!")

    if hasattr(response, 'output') and response.output:
        for i, item in enumerate(response.output):
            item_type = type(item).__name__
            print(f"\nOutput item {i}: {item_type}")

            if item_type == 'ResponseTextItem':
                print(f"Text: {item.text}")
            elif item_type == 'ResponseReasoningItem':
                print(f"Reasoning found (unexpected!)")
            elif item_type == 'ResponseOutputMessage':
                if hasattr(item, 'content'):
                    for content_item in item.content:
                        if hasattr(content_item, 'text'):
                            print(f"Content: {content_item.text}")

except Exception as e:
    print(f"FAILED: {e}")

# Test 4: gpt-5.1-chat-latest with Chat Completions API
print("\n\n4. Testing gpt-5.1-chat-latest with Chat Completions API")
print("-"*60)
try:
    response = client.chat.completions.create(
        model="gpt-5.1-chat-latest",
        messages=[{"role": "user", "content": question}]
    )

    print("SUCCESS with Chat Completions API!")
    print(f"Response: {response.choices[0].message.content}")

except Exception as e:
    print(f"FAILED: {e}")

# Test 5: gpt-5.1-chat-latest with Responses API
print("\n\n5. Testing gpt-5.1-chat-latest with Responses API")
print("-"*60)
try:
    response = client.responses.create(
        model="gpt-5.1-chat-latest",
        input=[{"role": "user", "content": question}],
        reasoning={"summary": "auto", "effort": "none"},
        store=False
    )

    print("SUCCESS with Responses API!")

    if hasattr(response, 'output') and response.output:
        for i, item in enumerate(response.output):
            item_type = type(item).__name__
            print(f"\nOutput item {i}: {item_type}")

            if item_type == 'ResponseTextItem':
                print(f"Text: {item.text}")

except Exception as e:
    print(f"FAILED: {e}")

print("\n" + "="*60)
print("Test complete!")
print("="*60)
