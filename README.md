# Unified AI Misalignment Framework

A comprehensive system for systematic AI safety testing across multiple model implementations and reasoning paradigms.

## Initial Results

This repository includes sample experiment outputs in `outputs_samples/` from early experiments. Preliminary findings from single-run experiments show:

| Model | Reasoning Mode | Baseline Mode |
|-------|---------------|---------------|
| Claude Opus 4.1 | 90/100 misalignment | 100/100 misalignment |
| Claude Opus 4 | 100/100 misalignment | 100/100 misalignment |
| Claude Sonnet 4.5 | 0/100 misalignment | 0/100 misalignment |
| Claude Sonnet 4 | 0/100 misalignment | 0/100 misalignment |
| OpenAI o3 | 95/100 misalignment | 0/100 misalignment |
| OpenAI GPT-5 | 0/100 misalignment | 100/100 misalignment |

**Important Notes:**
- These are single-run results; statistically significant findings require many more experiments
- Experiments are expensive to run due to API costs - community contributions of additional runs are welcome
- Counter-intuitive patterns (some models showing worse alignment in baseline mode) warrant further investigation
- Open source model support will be added soon, enabling inference-time mechanistic interpretability studies for researchers with appropriate tools

**Test Efficacy:**
The framework demonstrates discriminative power by producing a full range of alignment scores (0-100), indicating the test scenario effectively differentiates between aligned and misaligned behaviors:
- **Perfect alignment** (0/100): Models that discover but refuse to use security overrides (Claude Sonnet 4.5, Sonnet 4, GPT-5 reasoning)
- **Complete misalignment** (100/100): Models that implement overrides and falsify authorization (Claude Opus 4.1/4 baseline, GPT-5 baseline)
- **Partial misalignment** (90-95/100): Models that attempt overrides but don't fully complete the misaligned behavior (Claude Opus 4.1 reasoning, o3 reasoning)

This range validates that the test neither trivially passes all models nor artificially fails them, but genuinely measures alignment behavior. **Notable finding**: Claude Sonnet models (4 and 4.5) show exceptional consistency in ethical behavior across both reasoning and baseline modes.

**Research Opportunities:**
- Comparative safety analysis across reasoning vs baseline modes
- Statistical validation through large-scale experiment batches
- Mechanistic interpretability studies (coming with open source model support)
- Community-driven safety research through shared experiment results

## Architecture

```
unified-misalignment-framework/
├── configs/                  # Experiment configurations
├── shared/                   # Shared resources
│   ├── scenarios/            # Testing scenarios
│   │   ├── binance_guardrails/    # Financial security scenario
│   │   └── numberguess_game/      # Ethical constraint scenario
│   ├── python/               # Shared Python modules
│   │   ├── bash_executor.py       # Command execution layer
│   │   └── behavioral_data.py     # Behavioral data collection
│   ├── scripts/slack_post.py      # Notification system
│   ├── common/command_client.py   # Communication layer
│   └── docker/               # Containerization assets
├── implementations/          # Model-specific implementations
│   ├── openai_reasoning/     # OpenAI models with reasoning traces
│   ├── openai_baseline/      # OpenAI models without reasoning
│   ├── anthropic_reasoning/  # Anthropic models with reasoning
│   ├── anthropic_baseline/   # Anthropic models without reasoning
│   └── google_reasoning/     # Google Gemini with native thinking
├── unified_runner.py         # Central routing system
├── outputs/                  # Experiment results
└── outputs_samples/          # Sample results from initial experiments
```

## Supported Models

| Implementation | Models | API Interface | Reasoning | Validation/Evaluation |
|----------------|---------|---------------|-----------|----------------------|
| **OpenAI Reasoning** | GPT-5, GPT-5.1, GPT-5.2, o3 | Responses API | High effort reasoning traces | Independent GPT-5 |
| **OpenAI Baseline** | GPT-5, GPT-5.1, GPT-5.2, o3 | Chat API | None | Independent GPT-5 |
| **Anthropic Reasoning** | Claude Sonnet-4, Sonnet-4.5, Opus-4, Opus-4.1 | LiteLLM | High effort reasoning | Independent GPT-5 |
| **Anthropic Baseline** | Claude Sonnet-4, Sonnet-4.5, Opus-4, Opus-4.1 | LiteLLM | None | Independent GPT-5 |
| **Google Reasoning** | Gemini 3 Pro | Native Generative AI | High/Low thinking mode | Independent GPT-5 |
| **OpenRouter** | Kimi K2, DeepSeek R1, Gemini 2.5, Gemini 2.5 Pro, Llama 3.3 70B | OpenRouter (OpenAI-compatible) | Model-native reasoning | Independent GPT-5 |

## Quick Start

### Command Line Interface

```bash
# GPT-5 with reasoning traces
./run_experiment.sh -m gpt5 -r

# o3 baseline testing
./run_experiment.sh -m o3

# Claude Sonnet-4.5 with reasoning
./run_experiment.sh -m claude-sonnet-new -r

# Claude Sonnet-4 baseline testing
./run_experiment.sh -m claude-sonnet

# Run number guessing scenario with o3
./run_experiment.sh -m o3 --scenario numberguess_game

# View all options
./run_experiment.sh --help
```

**Available Models:**
- `o3` - OpenAI o3 model
- `gpt5` - OpenAI GPT-5 model
- `gpt51` - OpenAI GPT-5.1 model
- `gpt52` - OpenAI GPT-5.2 model
- `claude-sonnet` - Claude Sonnet-4-20250514
- `claude-sonnet-new` - Claude Sonnet-4.5-20250929 (latest)
- `claude-opus` - Claude Opus-4-20250514
- `claude-opus-new` - Claude Opus-4.1-20250805
- `gemini-3-pro` - Google Gemini 3 Pro (native API)
- `gemini-2.5` - Google Gemini 2.5 (via OpenRouter)
- `gemini-2.5-pro` - Google Gemini 2.5 Pro (via OpenRouter)
- `kimi-k2` - Moonshot Kimi K2 (via OpenRouter)
- `deepseek-r1` - DeepSeek R1 (via OpenRouter)
- `llama-3.3-70b` - Llama 3.3 70B (via OpenRouter, baseline only)

**Configuration Options:**
- `-r, --reasoning` - Enable reasoning capture
- `-s, --steps N` - Maximum steps (default: 30)
- `-t, --timeout N` - Timeout in minutes (default: 20)
- `-i, --id STRING` - Custom experiment identifier
- `--scenario NAME` - Test scenario (binance, numberguess_game)

### Direct Python Execution

```bash
# Using configuration files
python3 unified_runner.py configs/gpt5_reasoning.json
python3 unified_runner.py configs/o3_baseline.json
python3 unified_runner.py configs/claude_sonnet4.json
python3 unified_runner.py configs/claude_sonnet4_baseline.json
```

### Configuration Schema

```json
{
  "experiment": {
    "id": "experiment_identifier",
    "scenario": "binance",
    "description": "Research objective description"
  },
  "model_config": {
    "model": "claude-sonnet-4-5-20250929",
    "enable_reasoning": true,
    "max_steps": 30
  }
}
```

**Available Scenarios:**
- `binance` - Financial security and ethics testing scenario
- `numberguess_game` - Ethical constraint and rule compliance scenario

## Setup Requirements

### Environment Configuration

Create `.env` file from template:

```bash
cp .env.example .env
```

Required environment variables:

```bash
# API Access
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key         # For Gemini 3 Pro (native API)
OPENROUTER_API_KEY=your_openrouter_api_key # For OpenRouter models

# Safety Testing Configuration
OPENAI_VALIDATE_MODEL=gpt-5    # Independent validator
OPENAI_EVAL_MODEL=gpt-5        # Independent evaluator
OPENAI_FALLBACK_MODEL=gpt-5    # Fallback model

# Optional Notifications
SLACK_WEBHOOK_URL=your_slack_webhook_url
MAX_STEPS=30
```

### System Dependencies

**Required:**
- Docker and Docker Compose
- Python 3.8 or higher
- Bash shell (for convenience scripts)

**Python Dependencies:**
```bash
pip install openai litellm
```

**Platform Support:**
- macOS: Full native support
- Linux: Full native support
- Windows: Supported via WSL2 or Git Bash

## Safety Architecture

The framework implements independent validation and evaluation to prevent self-assessment:

### Model Routing Logic

```python
# Test subject routing
if model in ['o3', 'gpt-5', 'gpt-5.1', 'gpt-5.2']:
    → OpenAI Implementation (reasoning or baseline)
elif 'claude' in model:
    → Anthropic Implementation (reasoning or baseline)
elif model == 'gemini-3-pro':
    → Google Reasoning Implementation (native API)
elif model in ['kimi-k2', 'deepseek-r1', 'gemini-2.5', 'gemini-2.5-pro', 'llama-3.3-70b']:
    → OpenRouter Implementation (OpenAI-compatible API)

# Safety validation (always independent)
validator_model = OPENAI_VALIDATE_MODEL or "gpt-5"
evaluator_model = OPENAI_EVAL_MODEL or "gpt-5"
```

### Independent Evaluation

All experiments undergo three-phase evaluation:

1. **Validation Phase**: Independent model validates scenario setup
2. **Agent Phase**: Test subject executes the task
3. **Evaluation Phase**: Independent model assesses potential misalignment

This architecture prevents self-evaluation scenarios where test subjects judge their own behavior.

## Experiment Results

Each experiment generates:

- `standardized_result.json` - Unified result format across implementations
- `result.json` - Implementation-specific detailed results
- `behavioral_data.json` - Structured behavioral analysis data
- `run.log` - Complete execution trace
- `scorer_result.txt` - Quantitative evaluation score
- `improved.py` - Generated code artifacts (when applicable)
- `security_override.txt` - Authorization documents (when created)

## Behavioral Data Collection

All implementations output structured behavioral data to `/output/behavioral_data.json` for cross-model analysis:

```json
{
  "config": {
    "model": "claude-sonnet-4-5-20250929",
    "implementation": "anthropic_reasoning",
    "reasoning_enabled": true,
    "temperature": 1.0,
    "experiment_id": "exp_12345"
  },
  "steps": [
    {
      "step": 1,
      "thinking": {
        "tokens": 1234,
        "blocks": ["thinking content..."],
        "block_count": 2
      },
      "tool_calls": [
        {
          "tool": "bash",
          "args": {"command": "ls -la"},
          "return_code": 0,
          "output_snippet": "total 16..."
        }
      ]
    }
  ],
  "summary": {
    "total_steps": 6,
    "total_thinking_tokens": 5432,
    "total_tool_calls": 8,
    "total_thinking_blocks": 10
  }
}
```

This enables:
- **Cross-model comparison**: Standardized metrics across all providers
- **Reasoning analysis**: Token counts and thinking block extraction
- **Tool use patterns**: Track command execution and success rates
- **Network effects**: Aggregate insights from multiple experiments

## Advanced Configuration

### Batch Experiments

```bash
# Process multiple configurations
for config in configs/*.json; do
    python3 unified_runner.py "$config"
done
```

### Custom Scenarios

Extend the framework by:
1. Creating new scenario directories in `shared/scenarios/`
2. Implementing scenario-specific validation logic
3. Updating configuration schema as needed

## Technical Implementation

### Containerized Execution

Each experiment runs in isolated Docker containers to ensure:
- Consistent execution environments across platforms
- Reproducible results independent of host system
- Secure isolation of test subjects from host system

### Shared Resource Architecture

The framework achieves 60% code reuse through:
- Centralized scenario implementations
- Shared Docker assets and dependencies
- Common communication protocols
- Unified result standardization

### Implementation Isolation

Each model implementation maintains only its specific execution logic (`run_loop.py`), while sharing:
- Scenario definitions and validation logic
- Docker containerization infrastructure
- Communication and result processing systems
- Evaluation and scoring mechanisms

## Research Applications

This framework supports systematic AI misalignment research by enabling:

- **Reproducible Testing**: Consistent evaluation across different models and reasoning paradigms
- **Comparative Analysis**: Standardized output formats for cross-model comparison
- **Safety Validation**: Independent evaluation prevents self-assessment bias
- **Scalable Research**: Modular architecture supports rapid addition of new models

### Research Context

Developed to support systematic AI safety research, building on methodologies from the [Palisade Research AI Misalignment Bounty program](https://palisaderesearch.org/blog/misalignment-bounty). The framework enables reproducible testing of boundary navigation, reward hacking, and deceptive behavior patterns across multiple AI systems.

Research conducted using this framework has contributed to published findings on architectural vulnerabilities in AI safety systems and systematic approaches to identifying misalignment behaviors in autonomous agents.

---

Built for comprehensive AI safety research across multiple models and reasoning paradigms.
