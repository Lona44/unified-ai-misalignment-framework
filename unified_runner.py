#!/usr/bin/env python3
"""
Unified AI Misalignment Experiment Runner

Routes experiments to appropriate implementations based on model and reasoning configuration.
Supports: Enhanced Palisade (GPT-5 + reasoning), Fresh Clone (o3 baseline), Binance Framework (Claude)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Union

class UnsupportedModelError(Exception):
    pass

class UnifiedRunner:
    """Unified AI Misalignment Experiment Runner.

    Routes experiments to appropriate implementations based on model and reasoning configuration.
    Supports OpenAI models (GPT-5, o3) and Anthropic models (Claude Sonnet, Claude Opus).
    """

    def __init__(self, config_path: Union[str, Path], base_dir: Optional[Union[str, Path]] = None) -> None:
        """Initialize the unified experiment runner.

        Args:
            config_path: Path to the experiment configuration JSON file
            base_dir: Base directory for the framework (defaults to script directory)

        Raises:
            ValueError: If configuration is invalid
            UnsupportedModelError: If model is not supported
        """
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.config = self.load_config(config_path)
        self.validate_config()

    def load_config(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """Load and validate experiment configuration from JSON file.

        Args:
            config_path: Path to the configuration JSON file

        Returns:
            Dictionary containing the parsed configuration

        Raises:
            ValueError: If configuration file cannot be loaded or parsed
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"✓ Loaded configuration from {config_path}")
            return config
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {e}")

    def validate_config(self) -> None:
        """Validate configuration against schema and check requirements.

        Validates required fields, model support, API key availability,
        and configuration value constraints.

        Raises:
            ValueError: If configuration is invalid or missing required values
            UnsupportedModelError: If specified model is not supported
        """
        # Validate required fields
        required_fields = ['experiment', 'model_config']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required field: {field}")

        # Validate model
        model = self.config['model_config']['model']
        valid_models = [
            'o3', 'gpt-5', 'gpt-5.1',
            'claude-sonnet-4-20250514', 'claude-sonnet-4-5-20250929',
            'claude-opus-4-20250514', 'claude-opus-4-1-20250805',
            'kimi-k2', 'deepseek-r1', 'deepseek-v3.1'
        ]
        if model not in valid_models:
            raise UnsupportedModelError(f"Model {model} not supported. Valid models: {valid_models}")

        # Validate API keys based on model
        if model in ['o3', 'gpt-5', 'gpt-5.1']:
            if not os.getenv('OPENAI_API_KEY'):
                raise ValueError(f"OPENAI_API_KEY environment variable required for model {model}")
        elif 'claude' in model:
            if not os.getenv('ANTHROPIC_API_KEY'):
                raise ValueError(f"ANTHROPIC_API_KEY environment variable required for model {model}")
        elif model in ['kimi-k2', 'deepseek-r1', 'deepseek-v3.1']:
            if not os.getenv('OPENROUTER_API_KEY'):
                raise ValueError(f"OPENROUTER_API_KEY environment variable required for model {model}")
            # Also need OpenAI key for GPT-5 evaluator
            if not os.getenv('OPENAI_API_KEY'):
                raise ValueError(f"OPENAI_API_KEY environment variable required for GPT-5 evaluator")

        # Validate numeric fields
        max_steps = self.config.get('model_config', {}).get('max_steps', 30)
        if not isinstance(max_steps, int) or max_steps <= 0:
            raise ValueError(f"max_steps must be a positive integer, got: {max_steps}")

        # Validate scenario
        scenario = self.config.get('experiment', {}).get('scenario', 'binance')
        valid_scenarios = ['binance', 'numberguess_game']
        if scenario not in valid_scenarios:
            raise ValueError(f"Supported scenarios: {valid_scenarios}, got: {scenario}")

        print("✓ Configuration validation passed")

    def route_experiment(self) -> Dict[str, Any]:
        """Route experiment to appropriate implementation based on model and reasoning.

        Analyzes the model configuration and reasoning requirements to automatically
        select the most appropriate implementation framework.

        Returns:
            Dictionary containing experiment results and metadata

        Raises:
            UnsupportedModelError: If model routing logic fails
        """
        model = self.config['model_config']['model']
        enable_reasoning = self.config['model_config'].get('enable_reasoning', False)

        print(f"🎯 Routing experiment: {model} (reasoning: {enable_reasoning})")

        if model in ['o3', 'gpt-5', 'gpt-5.1']:
            if enable_reasoning:
                return self.route_to_openai_reasoning()
            else:
                return self.route_to_openai_baseline()
        elif 'claude' in model:
            if enable_reasoning:
                return self.route_to_anthropic_reasoning()
            else:
                return self.route_to_anthropic_baseline()
        elif model in ['kimi-k2', 'deepseek-r1']:
            # OpenRouter models - route to openai_reasoning (supports OpenRouter)
            # Note: These implementations now detect OpenRouter models and use appropriate API
            if enable_reasoning:
                return self.route_to_openai_reasoning()
            else:
                return self.route_to_openai_baseline()
        else:
            raise UnsupportedModelError(f"Model {model} not supported")

    def route_to_openai_reasoning(self):
        """Route to OpenAI Reasoning (Responses API + High effort reasoning)."""
        print("📡 Routing to OpenAI Reasoning (Responses API + reasoning)")
        return self.execute_implementation('openai_reasoning')

    def route_to_openai_baseline(self):
        """Route to OpenAI Baseline (Chat API + No reasoning)."""
        print("📡 Routing to OpenAI Baseline (Chat API + no reasoning)")
        return self.execute_implementation('openai_baseline')

    def route_to_anthropic_reasoning(self):
        """Route to Anthropic Reasoning (LiteLLM + High effort reasoning)."""
        print("📡 Routing to Anthropic Reasoning (LiteLLM + reasoning)")
        return self.execute_implementation('anthropic_reasoning')

    def route_to_anthropic_baseline(self):
        """Route to Anthropic Baseline (LiteLLM + No reasoning)."""
        print("📡 Routing to Anthropic Baseline (LiteLLM + no reasoning)")
        return self.execute_implementation('anthropic_baseline')

    def sanitize_for_docker(self, name: str) -> str:
        """Sanitize name for Docker compatibility by replacing underscores with hyphens.

        Args:
            name: The name to sanitize for Docker compatibility

        Returns:
            Docker-compatible name with hyphens instead of underscores
        """
        return name.replace('_', '-')

    def get_docker_asset_type(self, implementation_name: str) -> str:
        """Determine which shared Docker assets to use based on implementation.

        Maps implementation names to their corresponding Docker asset types,
        allowing for shared Docker configuration while maintaining implementation-specific needs.

        Args:
            implementation_name: Name of the implementation (e.g., 'openai_baseline', 'anthropic_reasoning')

        Returns:
            Asset type string ('openai' or 'anthropic')

        Raises:
            ValueError: If implementation name is not recognized
        """
        if implementation_name in ['openai_baseline', 'openai_reasoning']:
            return 'openai'
        elif implementation_name in ['anthropic_reasoning', 'anthropic_baseline']:
            return 'anthropic'
        else:
            raise ValueError(f"Unknown implementation: {implementation_name}")

    def prepare_execution_environment(self, implementation_name: str) -> Path:
        """Prepare temporary execution environment with shared and implementation-specific files.

        Creates an isolated temporary directory containing all necessary files for
        experiment execution, including shared resources, Docker assets, and
        implementation-specific configurations.

        Args:
            implementation_name: Name of the implementation to prepare environment for

        Returns:
            Path object pointing to the prepared temporary directory

        Raises:
            ValueError: If implementation name is not recognized
            FileNotFoundError: If required shared assets are missing
        """
        # Sanitize implementation name for Docker compatibility
        docker_safe_name = self.sanitize_for_docker(implementation_name)
        temp_dir = tempfile.mkdtemp(prefix=f"unified-experiment-{docker_safe_name}")
        temp_path = Path(temp_dir)

        print(f"🏗️  Preparing execution environment: {temp_path}")

        # Get scenario name from config
        scenario_name = self.config.get('experiment', {}).get('scenario', 'binance')

        # Map scenario names to folder names
        scenario_folder_map = {
            'binance': 'binance_guardrails',
            'numberguess_game': 'numberguess_game'
        }
        scenario_folder = scenario_folder_map[scenario_name]

        # Copy shared scenario files
        shared_scenario = self.base_dir / "shared" / "scenarios" / scenario_folder

        # Create both paths that different implementations expect
        scenario_dest_submission = temp_path / "submission"
        scenario_dest_scenarios = temp_path / "scenarios" / scenario_folder

        # Copy to submission/ (for some implementations)
        shutil.copytree(shared_scenario, scenario_dest_submission)

        # Copy to scenarios/<scenario_folder>/ (for anthropic_reasoning)
        scenario_dest_scenarios.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(shared_scenario, scenario_dest_scenarios)

        # Copy shared scripts
        shared_scripts = self.base_dir / "shared" / "scripts"
        scripts_dest = temp_path / "scripts"
        shutil.copytree(shared_scripts, scripts_dest)

        # Copy implementation-specific files
        impl_dir = self.base_dir / "implementations" / implementation_name

        # Copy agent files using shared Docker assets
        agent_src = impl_dir / "agent"
        agent_dest = temp_path / "agent"

        # Get the appropriate shared Docker assets
        asset_type = self.get_docker_asset_type(implementation_name)
        shared_docker = self.base_dir / "shared" / "docker"

        # Create agent directory
        agent_dest.mkdir(parents=True, exist_ok=True)

        # Copy run_loop.py from implementation
        shutil.copy2(agent_src / "run_loop.py", agent_dest / "run_loop.py")

        # Copy shared command_client.py
        shared_command_client = self.base_dir / "shared" / "common" / "command_client.py"
        shutil.copy2(shared_command_client, agent_dest / "command_client.py")

        # Copy DESCRIPTION.md into agent build context for Docker COPY
        shutil.copy2(scenario_dest_submission / "DESCRIPTION.md", agent_dest / "DESCRIPTION.md")

        # Copy appropriate shared Dockerfile and requirements
        shared_dockerfile = shared_docker / f"agent.{asset_type}.Dockerfile"
        shared_requirements = shared_docker / f"{asset_type}.requirements.txt"

        shutil.copy2(shared_dockerfile, agent_dest / "Dockerfile")
        shutil.copy2(shared_requirements, agent_dest / "requirements.txt")

        print(f"📦 Using shared {asset_type} Docker assets")

        # Copy execution files
        for file in ['docker-compose.yml', 'run.sh']:
            src_file = impl_dir / file
            if src_file.exists():
                shutil.copy2(src_file, temp_path / file)

        # Copy environment configuration
        shutil.copy2(self.base_dir / ".env", temp_path / ".env")

        # Create custom PROMPT.json with model configuration
        self.create_custom_prompt(temp_path / "submission" / "PROMPT.json")

        # Copy updated PROMPT.json to agent build context AFTER customization
        shutil.copy2(temp_path / "submission" / "PROMPT.json", agent_dest / "PROMPT.json")

        return temp_path

    def create_custom_prompt(self, prompt_path: Path) -> None:
        """Create custom PROMPT.json with experiment-specific model configuration.

        Modifies the base prompt configuration to include the specific model
        being tested in this experiment.

        Args:
            prompt_path: Path where the custom PROMPT.json should be written

        Raises:
            FileNotFoundError: If base prompt file doesn't exist
            ValueError: If prompt configuration is malformed
        """
        model = self.config['model_config']['model']
        enable_reasoning = self.config['model_config'].get('enable_reasoning', False)

        # Map simplified model names to actual OpenRouter model IDs
        model_mapping = {
            'kimi-k2': 'moonshotai/kimi-k2-thinking' if enable_reasoning else 'moonshotai/kimi-k2',
            'deepseek-r1': 'deepseek/deepseek-r1' if enable_reasoning else 'deepseek/deepseek-chat-v3',
            'deepseek-v3.1': 'deepseek/deepseek-chat' if enable_reasoning else 'deepseek/deepseek-chat'
        }

        # Use mapped model if available, otherwise use original
        actual_model = model_mapping.get(model, model)

        # Load base prompt
        with open(prompt_path, 'r') as f:
            prompt_data = json.load(f)

        # Update model
        prompt_data['model'] = actual_model

        # Write updated prompt
        with open(prompt_path, 'w') as f:
            json.dump(prompt_data, f, indent=2)

        if actual_model != model:
            print(f"✓ Updated PROMPT.json with model: {model} → {actual_model}")
        else:
            print(f"✓ Updated PROMPT.json with model: {model}")

    def execute_implementation(self, implementation_name: str) -> Dict[str, Any]:
        """Execute the selected implementation and return results.

        Prepares the execution environment, runs the implementation, and
        collects the results in a standardized format.

        Args:
            implementation_name: Name of the implementation to execute

        Returns:
            Dictionary containing experiment results, metadata, and status

        Raises:
            subprocess.CalledProcessError: If implementation execution fails
            FileNotFoundError: If implementation files are missing
        """
        temp_path = self.prepare_execution_environment(implementation_name)

        try:
            # Generate experiment ID
            experiment_id = self.config['experiment']['id']
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_id = f"{experiment_id}_{timestamp}"

            print(f"🚀 Executing experiment: {run_id}")

            # Set execution parameters
            max_steps = self.config['model_config'].get('max_steps', 30)
            timeout_minutes = self.config.get('execution', {}).get('timeout_minutes', 30)

            # Execute run.sh with metadata environment variables
            env = os.environ.copy()
            env['RUN_ID'] = run_id
            env['NO_TIMESTAMP'] = 'true'  # We handle timestamps ourselves

            # Add metadata for display in step logs
            model = self.config['model_config']['model']
            env['UNIFIED_MODEL'] = model
            env['UNIFIED_REASONING'] = 'ENABLED' if self.config['model_config'].get('enable_reasoning', False) else 'DISABLED'

            # Create descriptive implementation label based on actual model/provider
            if model in ['kimi-k2', 'deepseek-r1', 'deepseek-v3.1']:
                impl_label = 'OpenRouter API'
            elif model.startswith('claude-'):
                impl_label = 'Anthropic API'
            elif model in ['gpt-5', 'o3', 'gpt-5.1']:
                impl_label = 'OpenAI API'
            else:
                impl_label = implementation_name.replace('_', ' ').title()

            env['UNIFIED_IMPLEMENTATION'] = impl_label
            env['UNIFIED_EXPERIMENT_ID'] = self.config['experiment']['id']
            env['UNIFIED_MAX_STEPS'] = str(self.config['model_config'].get('max_steps', 30))

            cmd = ['bash', './run.sh']
            print(f"💻 Running: {' '.join(cmd)} (timeout: {timeout_minutes}m)")

            # Stream output live to terminal while capturing for logs
            process = subprocess.Popen(
                cmd,
                cwd=temp_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            output_lines = []
            try:
                # Stream output live while capturing
                for line in process.stdout:
                    print(line, end='')  # Stream to terminal
                    output_lines.append(line)  # Capture for logs

                # Wait for process to complete with timeout
                process.wait(timeout=timeout_minutes * 60)
                result_returncode = process.returncode

            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                print(f"\n⏰ Process timed out after {timeout_minutes} minutes")
                result_returncode = -1

            # Create result object for compatibility
            class ProcessResult:
                def __init__(self, returncode, stdout="", stderr=""):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            result = ProcessResult(result_returncode, ''.join(output_lines))

            # Copy results to permanent location
            output_dir = self.base_dir / "outputs" / run_id
            output_dir.mkdir(parents=True, exist_ok=True)

            # Find the actual output directory created by run.sh
            outputs_pattern = list(temp_path.glob("outputs/*"))
            if outputs_pattern:
                actual_output = outputs_pattern[0]
                for item in actual_output.iterdir():
                    if item.is_file():
                        shutil.copy2(item, output_dir / item.name)

            # Create standardized result
            self.create_standardized_result(output_dir, implementation_name, result)

            print(f"✅ Experiment completed: {output_dir}")
            return output_dir

        finally:
            # Cleanup temporary directory
            shutil.rmtree(temp_path, ignore_errors=True)

    def create_standardized_result(self, output_dir, implementation_name, process_result):
        """Create standardized result format."""
        experiment_id = self.config['experiment']['id']
        timestamp = datetime.now().isoformat()

        # Try to load result.json if it exists
        result_json_path = output_dir / "result.json"
        experiment_result = {}
        if result_json_path.exists():
            try:
                with open(result_json_path, 'r') as f:
                    experiment_result = json.load(f)
            except:
                pass

        standardized_result = {
            "metadata": {
                "experiment_id": experiment_id,
                "timestamp": timestamp,
                "model": self.config['model_config']['model'],
                "implementation": implementation_name,
                "reasoning_enabled": self.config['model_config'].get('enable_reasoning', False),
                "scenario": self.config['experiment']['scenario']
            },
            "execution": {
                "status": experiment_result.get('status', 'unknown'),
                "max_steps": self.config['model_config'].get('max_steps', 30),
                "process_return_code": process_result.returncode
            },
            "behavior_analysis": {
                "evaluation_score": experiment_result.get('evaluation', None),
                "reasoning_summary": experiment_result.get('reasoning', None)
            },
            "configuration": self.config
        }

        # Write standardized result
        with open(output_dir / "standardized_result.json", 'w') as f:
            json.dump(standardized_result, f, indent=2)

        print(f"📊 Created standardized result: {output_dir}/standardized_result.json")

def main():
    parser = argparse.ArgumentParser(description='Unified AI Misalignment Experiment Runner')
    parser.add_argument('config', help='Path to experiment configuration JSON file')
    parser.add_argument('--base-dir', help='Base directory for unified framework')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    if args.verbose:
        print("🔧 Verbose mode enabled")

    try:
        runner = UnifiedRunner(args.config, args.base_dir)
        output_dir = runner.route_experiment()

        print("\n" + "="*60)
        print("🎉 EXPERIMENT COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"📁 Results: {output_dir}")
        print(f"📊 Standardized result: {output_dir}/standardized_result.json")
        print(f"📝 Logs: {output_dir}/run.log")

    except Exception as e:
        print(f"\n❌ Experiment failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()