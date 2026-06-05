import os
import sys

# Mirror the agent container: inside Docker, /app/shared_python is on PYTHONPATH,
# so shared modules import flat (e.g. `from events import StepEvent`, matching the
# existing `from bash_executor import ...` convention). Put shared/python on the
# path here so tests import the same way the container does.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "shared", "python"))
