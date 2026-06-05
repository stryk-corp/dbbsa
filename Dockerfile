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

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations, ensure superuser exists, and start gunicorn
CMD python manage.py migrate --noinput && \
    python manage.py ensure_superuser && \
    gunicorn neural_village.wsgi:application --bind 0.0.0.0:$PORT
