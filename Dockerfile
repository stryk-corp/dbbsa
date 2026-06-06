# Use Python 3.14 slim image with system libraries pre-installed
FROM python:3.14-slim

# Install system dependencies required for av (PyAV)
RUN apt-get update && apt-get install -y \
    build-essential \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Copy entrypoint and make it executable
RUN chmod +x /app/entrypoint.sh || true

# Collect static files
RUN python manage.py collectstatic --noinput

# Use entrypoint to handle migrations and startup reliably
ENTRYPOINT ["/app/entrypoint.sh"]
