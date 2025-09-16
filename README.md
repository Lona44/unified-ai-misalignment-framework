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
| **Anthropic Reasoning** | Claude Sonnet-4-20250514, Opus-4-20250514, Opus-4.1-20250805 | LiteLLM | ✅ High effort | Anthropic reasoning_effort + thinking blocks |

## Quick Start

### 1. Quick Run with Bash Script (Recommended)

```bash
# GPT-5 with reasoning
./run_experiment.sh -m gpt5 -r

# o3 baseline (no reasoning)
./run_experiment.sh -m o3

# Claude Sonnet-4 with reasoning
./run_experiment.sh -m claude-sonnet

# See all options
./run_experiment.sh --help
```

**Available Models:**
- `o3` - OpenAI o3 model
- `gpt5` - OpenAI GPT-5 model
- `claude-sonnet` - Claude Sonnet-4-20250514 model
- `claude-opus` - Claude Opus-4-20250514 model
- `claude-opus-new` - Claude Opus-4.1-20250805 model

**Options:**
- `-r, --reasoning` - Enable reasoning capture
- `-s, --steps N` - Set max steps (default: 30)
- `-t, --timeout N` - Set timeout in minutes (default: 20)
- `-i, --id STRING` - Custom experiment ID

### 2. Direct Python Execution

```bash
# GPT-5 with reasoning (OpenAI Reasoning)
python3 unified_runner.py configs/gpt5_reasoning.json

# o3 baseline (OpenAI Baseline)
python3 unified_runner.py configs/o3_baseline.json

# Claude Sonnet-4 (Anthropic Reasoning)
python3 unified_runner.py configs/claude_sonnet4.json
```

### 3. Configuration Format

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
    "max_steps": 30
  }
}
```

### 4. Results

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

## Platform Compatibility

**Supported Platforms:**
- ✅ **macOS** - Full support (tested)
- ✅ **Linux** - Full support (Docker-based execution)
- ✅ **Windows** - Supported via WSL2 or Git Bash

**Requirements:**
- Docker & Docker Compose
- Python 3.8+
- Bash shell (for convenience script)

**Platform-Specific Notes:**
- **macOS/Linux**: Native bash script support
- **Windows**: Use WSL2, Git Bash, or run Python commands directly
- **All platforms**: Docker ensures consistent execution environments

## Environment Setup

The framework uses a shared `.env` file with all required API keys:

```bash
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
SLACK_WEBHOOK_URL=your_slack_webhook
```

Copy `.env.example` to `.env` and fill in your API keys.

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