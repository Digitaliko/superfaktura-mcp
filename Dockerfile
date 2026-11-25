FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# stdio MCP server (0.1.0 has no HTTP mode)
CMD ["python", "server.py"]
