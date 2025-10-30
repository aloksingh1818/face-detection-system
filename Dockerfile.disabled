FROM python:3.12-slim

# Install system deps for OpenCV and building optional dlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libgtk2.0-dev \
    libavcodec-dev libavformat-dev libswscale-dev \
    libsm6 libxext6 libxrender-dev \
    wget git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Use a virtualenv-like isolation via pip install to system site-packages
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt || true

# Note: dlib installation may require additional system libs; the Dockerfile
# installs cmake and build-essential to enable building dlib when required.

EXPOSE 5000
CMD ["python", "app.py"]
