# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# The server will be started by Smithery using the command from smithery.yaml
# No CMD needed as Smithery will execute: python3 server.py
