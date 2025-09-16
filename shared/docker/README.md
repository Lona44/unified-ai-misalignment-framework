# Shared Docker Assets

This directory contains consolidated Docker assets to eliminate duplication across implementations.

## Files

### Dockerfiles
- `agent.openai.Dockerfile` - Shared Dockerfile for OpenAI implementations (baseline & reasoning)
- `agent.anthropic.Dockerfile` - Dockerfile for Anthropic implementation (includes build tools for LiteLLM)

### Requirements
- `openai.requirements.txt` - Python dependencies for OpenAI implementations
- `anthropic.requirements.txt` - Python dependencies for Anthropic implementation

## Usage

The `unified_runner.py` automatically selects the appropriate assets based on implementation:

- **OpenAI Baseline & Reasoning**: Uses `openai` assets
- **Anthropic Reasoning**: Uses `anthropic` assets

## Implementation Mapping

```python
def get_docker_asset_type(implementation_name):
    if implementation_name in ['openai_baseline', 'openai_reasoning']:
        return 'openai'
    elif implementation_name == 'anthropic_reasoning':
        return 'anthropic'
```

## Benefits

- ✅ **DRY Principle**: Eliminates duplicate Dockerfiles and requirements
- ✅ **Centralized Maintenance**: Single location for Docker asset updates
- ✅ **Type Safety**: Implementation-specific assets for different needs
- ✅ **Professional Structure**: Clean, maintainable codebase organization