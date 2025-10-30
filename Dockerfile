FROM python:3.12-slim

# reduce interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system-level build dependencies commonly required for:
# - building/using dlib, OpenCV
# - building Pillow (libjpeg, zlib, freetype, lcms)
# - compiling scientific packages (numpy/pandas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake pkg-config git wget curl ca-certificates \
    libjpeg-dev zlib1g-dev libpng-dev libtiff-dev libwebp-dev libopenjp2-7-dev \
    libfreetype6-dev liblcms2-dev libffi-dev libexpat1-dev tk-dev tcl-dev \
    libavcodec-dev libavformat-dev libswscale-dev libgstreamer1.0-dev \
    libglib2.0-0 libsm6 libxrender1 libxext6 libgtk-3-dev \
    libopenblas-dev liblapack-dev gfortran \
    ninja-build libboost-all-dev pkg-config python3-dev \
    # dlib build / GUI and X11 related deps
    libx11-dev libxrandr-dev libxinerama-dev libxcursor-dev libxss-dev libxi-dev \
    libxcomposite-dev libxdamage-dev libglu1-mesa-dev libgl1-mesa-dev mesa-common-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt /app/requirements.txt

# Ensure latest pip/setuptools/wheel so build isolation and metadata work reliably

# Limit parallel jobs during native builds to reduce peak memory usage inside the builder
ENV MAKEFLAGS="-j2"

RUN python -m pip install --upgrade pip setuptools wheel

# Install requirements (will build wheels where needed)
RUN python -m pip install -r /app/requirements.txt

# Copy the rest of the source
COPY . /app

EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
