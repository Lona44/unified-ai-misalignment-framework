# Unified AI Misalignment Framework

A unified system for testing AI misalignment across multiple models and reasoning capabilities.

## Architecture

```
unified-misalignment-framework/
├── configs/                  # Experiment configurations
├── shared/                   # Shared resources (60% of codebase)
│   ├── scenarios/binance_guardrails/  # Complete Binance scenario
│   ├── scripts/slack_post.py         # Slack notifications
│   ├── common/command_client.py      # Communication layer
│   └── docker/               # Consolidated Docker assets
│       ├── agent.openai.Dockerfile       # Shared Dockerfile for OpenAI models
│       ├── agent.anthropic.Dockerfile    # Dockerfile for Anthropic models
│       ├── openai.requirements.txt       # OpenAI dependencies
│       └── anthropic.requirements.txt    # Anthropic dependencies
├── implementations/          # Implementation-specific files (run_loop.py only)
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
- `scorer_result.txt` - Evaluation score (e.g., "SUCCESS: 100/100")
- `improved.py` - Model-generated code (captured when created)
- `security_override.txt` - Authorization documents (captured when created)

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

## Setup

### 1. Python Environment Setup

**Option A: With Virtual Environment (Recommended)**
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install openai litellm
```

**Option B: System-Wide Installation**
```bash
# Install dependencies directly
pip install openai litellm
```

### 2. Environment Configuration

The framework uses a shared `.env` file with all required API keys:

```bash
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
SLACK_WEBHOOK_URL=your_slack_webhook
```

Copy `.env.example` to `.env` and fill in your API keys.

### 3. System Requirements

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
- **Consolidated Docker Assets**: DRY principle applied to Dockerfiles and requirements
- **Implementation Isolation**: Each implementation maintains only its specific logic (run_loop.py)
- **Automatic Asset Selection**: Router automatically selects appropriate Docker assets per implementation
- **Result Standardization**: All outputs converted to common format for analysis

## Research Context

This framework was developed to support systematic AI misalignment research, building on findings from the [Palisade Research AI Misalignment Bounty](https://palisaderesearch.org/blog/misalignment-bounty) competition. The bounty program seeks to identify problematic behaviors in AI agents, including deceptive actions, manipulative conduct, and sabotage attempts. Techniques developed through this framework contributed to a winning submission in the competition, helping validate the research approaches implemented here.

Research conducted using earlier versions of this framework contributed to published findings on [boundary navigation in AI systems](https://www.approxiomresearch.com/blog/how-boundary-navigation-revealed-an-architectural-flaw-at-the-heart-of-ai-safety-4nprt), which identified how AI models can systematically overcome permission constraints and perform reward-hacking in sandboxed environments.

The unified framework enables reproducible testing of these behaviors across different models and reasoning paradigms, supporting the broader AI safety research community's efforts to understand and mitigate potential risks in increasingly autonomous AI systems.

---

Built for comprehensive AI misalignment research across multiple models and reasoning paradigms.