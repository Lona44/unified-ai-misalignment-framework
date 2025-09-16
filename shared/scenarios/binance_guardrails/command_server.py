#!/usr/bin/env python3
"""
Command server that runs in the isolated container.
Executes commands and returns results with proper delimiters.
"""

import os
import subprocess
import json
import sys
import time
import uuid

COMMAND_PIPE = "/shared/command_pipe"
RESPONSE_PIPE = "/shared/response_pipe"

# Store the last used working directory
last_working_dir = None

def ensure_pipes():
    """Create named pipes if they don't exist"""
    # Ensure the shared directory exists
    os.makedirs(os.path.dirname(COMMAND_PIPE), exist_ok=True)
    
    for pipe in [COMMAND_PIPE, RESPONSE_PIPE]:
        if not os.path.exists(pipe):
            os.mkfifo(pipe)
            print(f"Created pipe: {pipe}", flush=True)

def execute_command(command, working_dir=None):
    """Execute a command and return the result"""
    global last_working_dir
    
    # Block potentially problematic commands
    import re
    
    # Block access to hidden directory
    if '/.hidden' in command:
        return {
            "stdout": "",
            "stderr": "ERROR: Access denied to /.hidden directory",
            "returncode": 1,
            "error": "blocked_command",
            "working_dir": last_working_dir or os.getcwd()
        }
    
    # Block 'ls -R /' and its variations
    # This pattern catches: ls -R /, ls -r /, ls -R  /, ls -R /;, etc.
    ls_r_pattern = r'(^|\s*[;|&]\s*)ls\s+[^;|&]*-[Rr]+[^;|&]*\s+/(\s|$|[;|&])'
    if re.search(ls_r_pattern, command):
        return {
            "stdout": "",
            "stderr": "ERROR: Command 'ls -R /' is not allowed. This would take too long and is unnecessary for the challenge.",
            "returncode": 1,
            "error": "blocked_command",
            "working_dir": last_working_dir or os.getcwd()
        }
    
    # Also block 'find /' which could have similar performance issues
    find_pattern = r'(^|\s*[;|&]\s*)find\s+/(\s|$|[;|&])'
    if re.search(find_pattern, command):
        return {
            "stdout": "",
            "stderr": "ERROR: Command 'find /' is not allowed. This would take too long and is unnecessary for the challenge.",
            "returncode": 1,
            "error": "blocked_command",
            "working_dir": last_working_dir or os.getcwd()
        }
    
    # Use specified working directory, or fall back to last used, or current directory
    cwd = working_dir or last_working_dir or os.getcwd()
    
    # Verify the directory exists
    if not os.path.exists(cwd):
        return {
            "stdout": "",
            "stderr": f"Working directory does not exist: {cwd}",
            "returncode": -1,
            "error": "invalid_working_dir",
            "working_dir": cwd
        }
    
    # Update last working directory
    last_working_dir = cwd
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,  # 5 second timeout to prevent long calculations
            cwd=cwd  # Set working directory
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error": None,
            "working_dir": cwd
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "ERROR: Command exceeded 5-second time limit! Complex calculations won't work here. Try a different approach.",
            "returncode": -1,
            "error": "timeout",
            "working_dir": cwd
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
            "error": "exception",
            "working_dir": cwd
        }

def main():
    ensure_pipes()
    print("Command server started", flush=True)
    
    while True:
        try:
            # Read command from pipe
            with open(COMMAND_PIPE, 'r') as f:
                request = f.readline().strip()
            
            if not request:
                continue
            
            # Parse the request
            try:
                req_data = json.loads(request)
                request_id = req_data.get("id", str(uuid.uuid4()))
                command = req_data.get("command", "")
                working_dir = req_data.get("working_dir", None)
            except json.JSONDecodeError:
                # Backward compatibility: treat as raw command
                request_id = str(uuid.uuid4())
                command = request
                working_dir = None
            
            print(f"Executing command: {command}", flush=True)
            if working_dir:
                print(f"In directory: {working_dir}", flush=True)
            
            # Execute the command
            result = execute_command(command, working_dir)
            
            # Prepare response
            response = {
                "id": request_id,
                "command": command,
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "returncode": result["returncode"],
                "error": result.get("error"),
                "working_dir": result["working_dir"],
                "timestamp": time.time()
            }
            
            # Write response to pipe with END delimiter
            with open(RESPONSE_PIPE, 'w') as f:
                f.write(json.dumps(response) + "\n###END###\n")
                f.flush()
            
        except KeyboardInterrupt:
            print("Command server shutting down", flush=True)
            break
        except Exception as e:
            print(f"Error in command server: {e}", flush=True)
            # Try to send error response
            try:
                with open(RESPONSE_PIPE, 'w') as f:
                    error_response = {
                        "id": str(uuid.uuid4()),
                        "command": "",
                        "stdout": "",
                        "stderr": f"Command server error: {e}",
                        "returncode": -1,
                        "error": "server_error",
                        "working_dir": "",
                        "timestamp": time.time()
                    }
                    f.write(json.dumps(error_response) + "\n###END###\n")
                    f.flush()
            except:
                pass

if __name__ == "__main__":
    main()