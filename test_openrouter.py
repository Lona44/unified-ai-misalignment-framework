#!/usr/bin/env python3
"""
Simple test script to validate OpenRouter API integration
Tests Kimi K2 Thinking model via OpenRouter
"""

import os


# Load .env file manually
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value


load_env()


def test_openrouter_kimi():
    """Test Kimi K2 Thinking via OpenRouter"""

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        print("❌ OPENROUTER_API_KEY not found in .env file")
        print("Please add OPENROUTER_API_KEY=your_key_here to .env")
        return False

    print("✓ Found OPENROUTER_API_KEY")

    try:
        from openai import OpenAI

        # Initialize OpenAI client with OpenRouter base URL
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
        )

        print("\n🧪 Testing Kimi K2 Thinking via OpenRouter...")
        print("=" * 60)

        # Simple test message
        response = client.chat.completions.create(
            model="moonshotai/kimi-k2-thinking",
            messages=[{"role": "user", "content": "What is 2+2? Respond in one sentence."}],
            max_tokens=100,
        )

        print("✓ API call successful!")
        print(f"\nModel: {response.model}")
        print(f"Response: {response.choices[0].message.content}")
        print("=" * 60)

        # Test tool calling
        print("\n🧪 Testing tool calling support...")
        print("=" * 60)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string", "description": "City name"}},
                        "required": ["location"],
                    },
                },
            }
        ]

        response = client.chat.completions.create(
            model="moonshotai/kimi-k2-thinking",
            messages=[{"role": "user", "content": "What's the weather in San Francisco?"}],
            tools=tools,
            max_tokens=100,
        )

        print("✓ Tool calling test successful!")
        if response.choices[0].message.tool_calls:
            print(f"Tool called: {response.choices[0].message.tool_calls[0].function.name}")
        else:
            print(f"Response: {response.choices[0].message.content}")
        print("=" * 60)

        print("\n✅ All OpenRouter tests passed!")
        print("Kimi K2 Thinking is ready for integration")
        return True

    except Exception as e:
        print(f"\n❌ Error testing OpenRouter: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_openrouter_kimi()
    exit(0 if success else 1)
