FROM condaforge/mambaforge:latest

# Use conda/mamba to install heavy native packages (dlib, opencv, numpy, pillow)
# This avoids compiling dlib from source inside the Docker build and uses prebuilt conda-forge packages.
SHELL ["/bin/bash", "-lc"]

WORKDIR /app

# Copy requirements so we can install pure-Python deps via pip later
COPY requirements.txt /app/requirements.txt

# Create a pip-only requirements file excluding heavy native packages that we will install via mamba
RUN python - <<'PY'
from pathlib import Path
excludes = {b'dlib', b'opencv-python', b'numpy', b'Pillow', b'pandas'}
orig = Path('requirements.txt').read_bytes().splitlines()
filtered = [line.decode() for line in orig if line.strip() and not any(line.split(b'==')[0].strip() == ex for ex in excludes)]
Path('pip-requirements.txt').write_text('\n'.join(filtered) + '\n')
print('pip requirements written: pip-requirements.txt')
PY

# Install heavy native packages from conda-forge using mamba for speed
RUN mamba install -y -c conda-forge python=3.12 dlib=19.24.2 opencv numpy pillow libboost && \
    mamba clean -afy

# Ensure pip tooling is up-to-date and install the remaining pure-Python requirements
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install -r /app/pip-requirements.txt

# Copy the rest of the source
COPY . /app

EXPOSE 5000

# Start with gunicorn; mamba image uses conda Python on PATH
## Use sh -lc so environment variable expansion works (JSON array form doesn't expand $PORT)
CMD ["sh", "-lc", "gunicorn app:app --bind 0.0.0.0:${PORT:-5000}"]
