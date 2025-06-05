# Dockerfile
FROM python:3.8-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-wheel \
    swig \
    python3-dev \
    build-essential \
    libpq-dev \
    osmosis \
    osm2pgsql \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /code

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output directory
RUN mkdir -p /code/output

# Default command
CMD ["python3", "-c", "print('OpenLUR container is ready. Use kubectl exec to run commands.')"]