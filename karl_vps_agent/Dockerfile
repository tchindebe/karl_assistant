FROM python:3.12-slim

WORKDIR /app

# System dependencies: docker CLI to exec into containers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

EXPOSE 8001

# NOTE: runs as root so it can call docker commands on the host socket.
# Mount /var/run/docker.sock from the host.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
