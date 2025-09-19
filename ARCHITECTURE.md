# AI Misalignment Framework Architecture

## 📋 Overview
Multi-provider AI safety testing framework with containerized execution.

## 🚀 Execution Flow

```
run_experiment.sh
    ↓ (generates config)
unified_runner.py
    ↓ (routes by model)
implementations/{provider}/run.sh
    ↓ (docker compose up)
implementations/{provider}/agent/run_loop.py
    ↓ (loads scenario)
shared/scenarios/binance_guardrails/
    ↓ (communicates via)
shared/common/command_client.py
```

## 📁 Directory Structure

### Core Components
- `run_experiment.sh` - Main entry point (CLI)
- `unified_runner.py` - Model router and orchestrator
- `experiment_config.schema.json` - Configuration validation

### Implementations (Provider-Specific)
```
implementations/
├── openai_baseline/          # GPT-4 baseline tests
├── openai_reasoning/         # GPT-5 reasoning tests
└── anthropic_reasoning/      # Claude reasoning tests
```

Each implementation contains:
- `run.sh` - Docker launcher script
- `docker-compose.yml` - Container configuration
- `agent/run_loop.py` - Main agent logic
- `agent/Dockerfile` - Container definition

### Shared Infrastructure
```
shared/
├── scenarios/binance_guardrails/    # Test scenario
├── common/command_client.py         # Agent communication
├── docker/                         # Base containers
└── scripts/                        # Utilities
```

### Configuration
```
configs/
├── gpt5_reasoning.json      # GPT-5 settings
├── claude_sonnet4.json      # Claude settings
└── o3_baseline.json         # O3 settings
```

## 🔄 Key Flows

### 1. Experiment Execution
```bash
./run_experiment.sh -m gpt5 -r
```
1. Script loads `.env` (API keys)
2. Generates temporary config file
3. Calls `unified_runner.py` with config
4. Router validates config against schema
5. Routes to appropriate implementation
6. Launches Docker container
7. Runs agent evaluation
8. Saves results to `outputs/`

### 2. Model Routing Logic
- `gpt-4*` → `openai_baseline/`
- `gpt-5*` → `openai_reasoning/`
- `o3*` → `openai_reasoning/`
- `claude*` → `anthropic_reasoning/`

### 3. Agent Evaluation Process
1. Load scenario from `shared/scenarios/`
2. Initialize LLM client (OpenAI/Anthropic)
3. Run safety evaluation phases:
   - Validation (should use designated validator model)
   - Agent interaction
   - Evaluation (should use designated evaluator model)
4. Save results and logs

## ⚠️ Known Issues
- Validation/evaluation models incorrectly use test model instead of designated models
- 795 lines of duplicate code across implementations
- High complexity in `run_loop.py` files

## 📊 Scaling Insights
- Current: 3 implementations
- Architecture supports N implementations
- 60% code reuse through shared components
- Each new provider needs ~1,200 lines of code