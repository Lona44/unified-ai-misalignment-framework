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

class UnsupportedModelError(Exception):
    pass

class UnifiedRunner:
    def __init__(self, config_path, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.config = self.load_config(config_path)
        self.validate_config()

    def load_config(self, config_path):
        """Load and validate experiment configuration."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"✓ Loaded configuration from {config_path}")
            return config
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {e}")

    def validate_config(self):
        """Validate configuration against schema."""
        required_fields = ['experiment', 'model_config']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required field: {field}")

        model = self.config['model_config']['model']
        valid_models = ['o3', 'gpt-5', 'claude-sonnet-4-20250514', 'claude-opus-4-20250514', 'claude-opus-4-1-20250805']
        if model not in valid_models:
            raise UnsupportedModelError(f"Model {model} not supported. Valid models: {valid_models}")

    def route_experiment(self):
        """Route experiment to appropriate implementation based on model and reasoning."""
        model = self.config['model_config']['model']
        enable_reasoning = self.config['model_config'].get('enable_reasoning', False)

        print(f"🎯 Routing experiment: {model} (reasoning: {enable_reasoning})")

        if model in ['o3', 'gpt-5']:
            if enable_reasoning:
                return self.route_to_openai_reasoning()
            else:
                return self.route_to_openai_baseline()
        elif 'claude' in model:
            return self.route_to_anthropic_reasoning()
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

    def prepare_execution_environment(self, implementation_name):
        """Prepare temporary execution environment with shared and implementation-specific files."""
        temp_dir = tempfile.mkdtemp(prefix=f"unified_experiment_{implementation_name}_")
        temp_path = Path(temp_dir)

        print(f"🏗️  Preparing execution environment: {temp_path}")

        # Copy shared scenario files
        shared_scenario = self.base_dir / "shared" / "scenarios" / "binance_guardrails"
        scenario_dest = temp_path / "submission"
        shutil.copytree(shared_scenario, scenario_dest)

        # Copy shared scripts
        shared_scripts = self.base_dir / "shared" / "scripts"
        scripts_dest = temp_path / "scripts"
        shutil.copytree(shared_scripts, scripts_dest)

        # Copy implementation-specific files
        impl_dir = self.base_dir / "implementations" / implementation_name

        # Copy agent files
        agent_src = impl_dir / "agent"
        agent_dest = temp_path / "agent"
        shutil.copytree(agent_src, agent_dest)

        # Add shared command_client.py to agent directory
        shared_command_client = self.base_dir / "shared" / "common" / "command_client.py"
        shutil.copy2(shared_command_client, agent_dest / "command_client.py")

        # Copy execution files
        for file in ['docker-compose.yml', 'run.sh']:
            src_file = impl_dir / file
            if src_file.exists():
                shutil.copy2(src_file, temp_path / file)

        # Copy environment configuration
        shutil.copy2(self.base_dir / ".env", temp_path / ".env")

        # Create custom PROMPT.json with model configuration
        self.create_custom_prompt(temp_path / "submission" / "PROMPT.json")

        return temp_path

    def create_custom_prompt(self, prompt_path):
        """Create custom PROMPT.json with experiment-specific model configuration."""
        model = self.config['model_config']['model']

        # Load base prompt
        with open(prompt_path, 'r') as f:
            prompt_data = json.load(f)

        # Update model
        prompt_data['model'] = model

        # Write updated prompt
        with open(prompt_path, 'w') as f:
            json.dump(prompt_data, f, indent=2)

        print(f"✓ Updated PROMPT.json with model: {model}")

    def execute_implementation(self, implementation_name):
        """Execute the selected implementation."""
        temp_path = self.prepare_execution_environment(implementation_name)

        try:
            # Generate experiment ID
            experiment_id = self.config['experiment']['id']
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_id = f"{experiment_id}_{timestamp}"

            print(f"🚀 Executing experiment: {run_id}")

            # Set execution parameters
            max_steps = self.config['model_config'].get('max_steps', 30)
            timeout_minutes = self.config.get('execution', {}).get('timeout_minutes', 20)

            # Execute run.sh with metadata environment variables
            env = os.environ.copy()
            env['RUN_ID'] = run_id
            env['NO_TIMESTAMP'] = 'true'  # We handle timestamps ourselves

            # Add metadata for display in step logs
            env['UNIFIED_MODEL'] = self.config['model_config']['model']
            env['UNIFIED_REASONING'] = 'ENABLED' if self.config['model_config'].get('enable_reasoning', False) else 'DISABLED'
            env['UNIFIED_IMPLEMENTATION'] = implementation_name.replace('_', ' ').title()
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