#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/app"
MODEL_DIR="$ROOT_DIR/models"

echo "Starting app: ensuring dlib model files exist..."

# Simple helper to download model files if missing. We recommend pre-populating models
# in the repository or hosting them in a private bucket for production. These URLs
# are placeholders; replace them with your own storage URLs if desired.
download_if_missing() {
  local fname="$1"
  local url="$2"
  if [ ! -f "$MODEL_DIR/$fname" ]; then
    echo "Model $fname missing, attempting to download from $url"
    wget -O "$MODEL_DIR/$fname" "$url" || {
      echo "Warning: failed to download $fname from $url" >&2
    }
  else
    echo "$fname already exists"
  fi
}

mkdir -p "$MODEL_DIR"

# Replace the URLs below with real hosted model URLs (S3/GCS) or keep the files in repo.
download_if_missing "shape_predictor_68_face_landmarks.dat" "https://github.com/davisking/dlib-models/raw/master/shape_predictor_68_face_landmarks.dat.bz2"
download_if_missing "dlib_face_recognition_resnet_model_v1.dat" "https://github.com/davisking/dlib-models/raw/master/dlib_face_recognition_resnet_model_v1.dat.bz2"

# If the downloaded files are bz2 compressed, try to decompress them
for f in "$MODEL_DIR"/*.bz2; do
  if [ -f "$f" ]; then
    echo "Decompressing $f"
    bunzip2 -k "$f" || true
  fi
done

echo "Starting Gunicorn..."
exec gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 2
