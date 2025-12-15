#!/bin/bash

# Unified AI Misalignment Experiment Runner
# Simple interface for running experiments with different models

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_CONFIG=""

# Load environment variables from .env file if it exists
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    echo "✓ Loading environment variables from .env"
    set -a  # automatically export all variables
    source "$SCRIPT_DIR/.env"
    set +a  # stop automatically exporting
fi

# Default values
MODEL=""
REASONING="false"
EXPERIMENT_ID=""
MAX_STEPS="30"
TIMEOUT="20"
SCENARIO="binance"

show_help() {
    cat << EOF
Unified AI Misalignment Experiment Runner

USAGE:
    ./run_experiment.sh -m MODEL [OPTIONS]

MODELS:
    o3              - OpenAI o3 model
    gpt5            - OpenAI GPT-5 model
    gpt51           - OpenAI GPT-5.1 model
    gpt52           - OpenAI GPT-5.2 model (latest)
    claude-sonnet   - Claude Sonnet-4 model
    claude-sonnet-new - Claude Sonnet-4.5 (latest) model
    claude-opus     - Claude Opus-4 model
    claude-opus-new - Claude Opus-4.1 model
    kimi-k2         - Kimi K2 (via OpenRouter)
    deepseek-r1     - DeepSeek R1 (via OpenRouter)
    gemini-2.5      - Gemini 2.5 Flash (via OpenRouter)
    gemini-2.5-pro  - Gemini 2.5 Pro (via OpenRouter)
    gemini-3-pro    - Gemini 3 Pro (via OpenRouter)
    llama-3.3-70b   - Llama 3.3 70B Instruct (via OpenRouter)

OPTIONS:
    -m, --model MODEL       Model to use (required)
    -r, --reasoning         Enable reasoning (default: false)
    -i, --id ID            Experiment ID (default: auto-generated)
    -s, --steps STEPS      Max steps (default: 30)
    -t, --timeout MINS     Timeout in minutes (default: 20)
    --scenario SCENARIO    Scenario to run (default: binance, options: binance, numberguess_game)
    -h, --help             Show this help

EXAMPLES:
    ./run_experiment.sh -m o3                          # o3 baseline on binance scenario
    ./run_experiment.sh -m gpt5 -r                     # GPT-5 with reasoning on binance scenario
    ./run_experiment.sh -m claude-sonnet -i my_test    # Claude Sonnet with custom ID
    ./run_experiment.sh -m claude-opus -r -s 25        # Claude Opus, reasoning, 25 steps
    ./run_experiment.sh -m claude-opus-new -r          # Claude Opus-4.1 with reasoning
    ./run_experiment.sh -m o3 --scenario numberguess_game    # o3 on number guessing scenario

ROUTING:
    o3/gpt5 + reasoning=true  → Enhanced Palisade (Responses API)
    o3/gpt5 + reasoning=false → Fresh Clone (Chat API)
    claude-*                  → Binance Framework (LiteLLM)

EOF
}

cleanup() {
    if [[ -n "$TEMP_CONFIG" && -f "$TEMP_CONFIG" ]]; then
        rm -f "$TEMP_CONFIG"
    fi
}
trap cleanup EXIT

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -r|--reasoning)
            REASONING="true"
            shift
            ;;
        -i|--id)
            EXPERIMENT_ID="$2"
            shift 2
            ;;
        -s|--steps)
            MAX_STEPS="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --scenario)
            SCENARIO="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$MODEL" ]]; then
    echo "❌ Error: Model is required"
    echo "Use -h or --help for usage information"
    exit 1
fi

# Convert model aliases to full names
case "$MODEL" in
    o3)
        FULL_MODEL="o3"
        ;;
    gpt5)
        FULL_MODEL="gpt-5"
        ;;
    gpt51)
        FULL_MODEL="gpt-5.1"
        ;;
    gpt52)
        FULL_MODEL="gpt-5.2"
        ;;
    claude-sonnet)
        FULL_MODEL="claude-sonnet-4-20250514"
        ;;
    claude-sonnet-new)
        FULL_MODEL="claude-sonnet-4-5-20250929"
        ;;
    claude-opus)
        FULL_MODEL="claude-opus-4-20250514"
        ;;
    claude-opus-new)
        FULL_MODEL="claude-opus-4-1-20250805"
        ;;
    kimi-k2)
        FULL_MODEL="kimi-k2"
        ;;
    deepseek-r1)
        FULL_MODEL="deepseek-r1"
        ;;
    gemini-2.5)
        FULL_MODEL="gemini-2.5"
        ;;
    gemini-2.5-pro)
        FULL_MODEL="gemini-2.5-pro"
        ;;
    gemini-3-pro)
        FULL_MODEL="gemini-3-pro"
        ;;
    llama-3.3-70b)
        FULL_MODEL="llama-3.3-70b"
        ;;
    *)
        echo "❌ Error: Unknown model '$MODEL'"
        echo "Supported models: o3, gpt5, gpt51, gpt52, claude-sonnet, claude-sonnet-new, claude-opus, claude-opus-new, kimi-k2, deepseek-r1, gemini-2.5, gemini-2.5-pro, gemini-3-pro, llama-3.3-70b"
        exit 1
        ;;
esac

# Generate experiment ID if not provided
# Use UNIFIED_EXPERIMENT_ID from environment (set by platform) if available
if [[ -n "$UNIFIED_EXPERIMENT_ID" && -z "$EXPERIMENT_ID" ]]; then
    echo "✓ Using platform experiment ID: $UNIFIED_EXPERIMENT_ID"
    EXPERIMENT_ID="$UNIFIED_EXPERIMENT_ID"
elif [[ -z "$EXPERIMENT_ID" ]]; then
    TIMESTAMP=$(date +"%m%d_%H%M")
    if [[ "$REASONING" == "true" ]]; then
        EXPERIMENT_ID="${MODEL}_reasoning_${TIMESTAMP}"
    else
        EXPERIMENT_ID="${MODEL}_baseline_${TIMESTAMP}"
    fi
fi

# Create temporary config file
TEMP_CONFIG=$(mktemp)
cat > "$TEMP_CONFIG" << EOF
{
  "experiment": {
    "id": "$EXPERIMENT_ID",
    "scenario": "$SCENARIO",
    "description": "Experiment with $FULL_MODEL (reasoning: $REASONING)"
  },
  "model_config": {
    "model": "$FULL_MODEL",
    "enable_reasoning": $REASONING,
    "max_steps": $MAX_STEPS
  },
  "execution": {
    "timeout_minutes": $TIMEOUT
  }
}
EOF

echo "🎯 Running experiment with:"
echo "   Model: $FULL_MODEL"
echo "   Reasoning: $REASONING"
echo "   Experiment ID: $EXPERIMENT_ID"
echo "   Max steps: $MAX_STEPS"
echo "   Timeout: ${TIMEOUT}m"
echo ""

# Run the experiment
cd "$SCRIPT_DIR"
python3 unified_runner.py "$TEMP_CONFIG"