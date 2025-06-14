# Dockerfile for GPL Demo - Quick Demo Version

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Add these two packages for building Python C extensions
    gcc \
    python3-dev \
    # Your existing packages
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglu1-mesa \
    libgl1-mesa-glx \
    libopencv-dev \
    python3-opencv \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Create necessary directories
RUN mkdir -p telemetry/collectors telemetry/sensors web/api web/streaming data/samples data/output

# Create empty __init__.py files
RUN touch telemetry/__init__.py telemetry/collectors/__init__.py telemetry/sensors/__init__.py \
    web/__init__.py web/api/__init__.py web/streaming/__init__.py

# Expose ports (even though demo doesn't use them)
EXPOSE 8000 9090

# Run the demo
CMD ["python", "demo_main.py"]