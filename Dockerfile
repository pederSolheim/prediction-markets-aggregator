FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY aggregator.py .
COPY config.yaml .

# Create log directory
RUN mkdir -p /app/logs

# Run the aggregator
CMD ["python", "aggregator.py"]
