FROM python:3.12-slim

# Install system-level build dependencies commonly required for:
# - building/using dlib, OpenCV
# - building Pillow (libjpeg, zlib)
# - compiling scientific packages (numpy/pandas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake pkg-config git wget curl ca-certificates \
    libjpeg-dev zlib1g-dev libpng-dev libtiff-dev libwebp-dev libopenjp2-7-dev \
    libavcodec-dev libavformat-dev libswscale-dev libgstreamer1.0-dev \
    libglib2.0-0 libsm6 libxrender1 libxext6 libgtk-3-dev libgl1-mesa-glx \
    libatlas-base-dev libopenblas-dev liblapack-dev gfortran \
    ninja-build libboost-all-dev \
    build-essential pkg-config python3-dev python3-setuptools python3-wheel \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip setuptools wheel
RUN pip install -r /app/requirements.txt

# Copy the rest of the source
COPY . /app

EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
