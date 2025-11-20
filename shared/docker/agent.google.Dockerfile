# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    bash \
    coreutils \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create the shared directory for named pipes
RUN mkdir -p /shared

# Copy requirements file and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the Python scripts
COPY command_client.py /app/agent/command_client.py
COPY run_loop.py /app/run_loop.py

# Copy scenario files (PROMPT.json and DESCRIPTION.md)
COPY PROMPT.json /app/PROMPT.json
COPY DESCRIPTION.md /app/DESCRIPTION.md

# Make scripts executable
RUN chmod +x /app/agent/command_client.py /app/run_loop.py

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command runs the test loop
CMD ["python3", "/app/run_loop.py"]

# Alternative: you can also run the command client directly by overriding the command
# docker run <image> python3 /app/agent/command_client.py "ls -la"