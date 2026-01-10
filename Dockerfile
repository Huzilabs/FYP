# Dockerfile for deploying the face recognition Flask app on Render (or similar)
# Uses a Debian-based slim Python image and installs system deps needed by dlib/face_recognition

FROM python:3.11-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    libopenblas-dev \
    liblapack-dev \
    libx11-6 \
    libx11-dev \
    libsm6 \
    libxext6 \
    libglib2.0-0 \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files first for better layer caching
COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip "setuptools<81" wheel
RUN pip install -r /app/requirements.txt

# Copy application source
COPY . /app

# Expose port for Render; Render sets $PORT at runtime
EXPOSE ${PORT}

# Use gunicorn to serve the Flask app; webapp_new:app is the Flask app object
CMD ["sh", "-c", "gunicorn -w 4 -b 0.0.0.0:${PORT} webapp_new:app"]
