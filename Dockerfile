FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Expose port
ENV PORT=8000
EXPOSE 8000

# Run as HTTP server
CMD ["python", "server.py", "--http"]
