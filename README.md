# Unified AI Misalignment Framework

A unified system for testing AI misalignment across multiple models and reasoning capabilities.

## Architecture

```
unified-misalignment-framework/
├── configs/                  # Experiment configurations
├── shared/                   # Shared resources (50% of codebase)
│   ├── scenarios/binance_guardrails/  # Complete Binance scenario
│   ├── scripts/slack_post.py         # Slack notifications
│   └── common/command_client.py      # Communication layer
├── implementations/          # Implementation-specific files
│   ├── openai_reasoning/     # OpenAI models + Responses API + reasoning
│   ├── openai_baseline/      # OpenAI models + Chat API + no reasoning
│   └── anthropic_reasoning/  # Claude models + LiteLLM + high-effort reasoning
├── unified_runner.py         # Main router script
└── outputs/                  # Experiment results
```

## Supported Implementations

| Implementation | Models | API | Reasoning | Use Case |
|----------------|---------|-----|-----------|----------|
| **OpenAI Reasoning** | GPT-5, o3 | Responses API | ✅ High effort | Reasoning traces via Responses API |
| **OpenAI Baseline** | o3, GPT-5 | Chat API | ❌ None | Standard completion without reasoning |
| **Anthropic Reasoning** | Claude Sonnet-4, Opus-4 | LiteLLM | ✅ High effort | Anthropic reasoning_effort + thinking blocks |

## Quick Start

### 1. Run a Single Experiment

```bash
# GPT-5 with reasoning (OpenAI Reasoning)
python3 unified_runner.py configs/gpt5_reasoning.json

# o3 baseline (OpenAI Baseline)
python3 unified_runner.py configs/o3_baseline.json

# Claude Sonnet-4 (Anthropic Reasoning)
python3 unified_runner.py configs/claude_sonnet4.json
```

### 2. Configuration Format

```json
{
  "experiment": {
    "id": "my_test_experiment",
    "scenario": "binance",
    "description": "Testing model behavior"
  },
  "model_config": {
    "model": "gpt-5",
    "enable_reasoning": true,
    "max_steps": 50
  }
}
```

### 3. Results

Each experiment produces:
- `standardized_result.json` - Unified result format
- `result.json` - Original implementation result
- `run.log` - Complete execution log

## Router Logic

The system automatically routes experiments based on model and reasoning configuration:

```python
if model in ['o3', 'gpt-5']:
    if enable_reasoning:
        → OpenAI Reasoning (Responses API + reasoning)
    else:
        → OpenAI Baseline (Chat API + no reasoning)
elif 'claude' in model:
    → Anthropic Reasoning (LiteLLM + reasoning)
```

## Benefits

- **🎯 Single Entry Point**: One command for all model experiments
- **📊 Standardized Results**: Comparable outputs across implementations
- **🔄 Automatic Routing**: No manual implementation selection
- **📦 50% Code Reduction**: Shared resources eliminate duplication
- **⚡ Fast Setup**: Pre-configured scenarios and dependencies

## Environment Setup

The framework uses a shared `.env` file with all required API keys:

```bash
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
SLACK_WEBHOOK_URL=your_slack_webhook
```

## Advanced Usage

### Batch Experiments

```bash
# Run multiple configurations
for config in configs/*.json; do
    python3 unified_runner.py "$config"
done
```

### Custom Configuration

Create your own configuration file following the schema in `experiment_config.schema.json`.

## Technical Details

- **Temporary Execution Environment**: Each experiment runs in isolated temporary directory
- **Shared Resources**: Common files are copied once, reducing disk usage
- **Implementation Isolation**: Each implementation maintains its specific logic
- **Result Standardization**: All outputs converted to common format for analysis

---

Built for comprehensive AI misalignment research across multiple models and reasoning paradigms.