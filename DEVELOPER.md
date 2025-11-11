# Developer guide — face-detection-system

This guide explains how a developer can set up, run, and test the FaceAttendAI project locally.

It covers two main workflows:
- Quick/demo (no dlib) — fast install using a virtualenv and `requirements-no-dlib.txt`. Uses OpenCV fallback for face detection.
- Full/accurate (dlib & face_recognition) — recommended if you want production-like face encodings. Use conda to install prebuilt `dlib` and `face_recognition` from conda-forge.

Contents
- Prerequisites
- Quick/demo (venv) — commands
- Full (conda) — commands
- Running the server
- Running tests
- Re-encoding student photos (tool)
- VS Code tips
- Troubleshooting
- Notes about models & data

---

## Prerequisites

- Git and a recent Python (3.10 recommended). On Ubuntu/Debian: `sudo apt update && sudo apt install -y git python3 python3-venv python3-pip`.
- For full dlib install via pip you'll need system build tools (cmake, build-essential, libopenblas-dev, liblapack-dev, libgtk-3-dev, libjpeg-dev, etc.). See Troubleshooting below — for most developers we recommend using conda to avoid native build problems.
- Conda (Miniconda / Anaconda) is strongly recommended for the full pipeline (dlib/face_recognition) because conda-forge provides prebuilt binaries.

---

## Quick / demo setup (no dlib)

Use this when you want to run the app quickly and don't need the highest-quality face encodings. This is what we use for CI and fast demos.

Linux / macOS

```bash
git clone https://github.com/aloksingh1818/face-detection-system.git
cd face-detection-system
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements-no-dlib.txt
```

Windows (PowerShell)

```powershell
> git clone https://github.com/aloksingh1818/face-detection-system.git
> cd face-detection-system
> python -m venv venv
> .\venv\Scripts\Activate.ps1
> python -m pip install --upgrade pip setuptools wheel
> pip install -r requirements-no-dlib.txt
```

Notes:
- `requirements-no-dlib.txt` excludes `dlib` and `face_recognition` and uses the OpenCV fallback. This is fast to install and suitable for demos.

---

## Full setup (recommended) — use conda (Linux/macOS/Windows)

This creates an environment with `dlib`, `face_recognition`, `opencv`, and `numpy` from conda-forge (no native builds required).

Linux / macOS / Windows (conda)

```bash
# Create environment (Python 3.10 recommended)
conda create -n faceenv -c conda-forge python=3.10 -y
conda activate faceenv

# Install the key packages from conda-forge
conda install -n faceenv -c conda-forge dlib face_recognition opencv numpy pillow -y

# Install the remaining Python deps from our requirements (if desired)
pip install -r requirements-dev.txt
```

Notes:
- `dlib` and `face_recognition` are CPU-heavy native packages. Using conda avoids many compilation issues because conda-forge distributes prebuilt wheels for common platforms.
- If you prefer a single pip-based install (not recommended for dlib), see the Troubleshooting section for required system packages.

---

## Run the server

Start the Flask dev server from the project root.

With conda (recommended when using `face_recognition`):

```bash
conda activate faceenv
python app.py
```

With venv (quick/demo):

```bash
source venv/bin/activate   # or activate on Windows
python app.py
```

The app runs on port 5000 by default. Open http://127.0.0.1:5000/ in your browser.

Useful endpoints:
- GET /api/health — returns {"status":"ok"}
- POST /api/process-frame — used by the front-end camera UI
- Admin UI: /admin/dashboard and /admin/register

If you get "Address already in use" when starting the server, find and stop the process using port 5000 (e.g. `ss -ltnp | grep 5000` then `kill <pid>`).

---

## Run tests

The repository includes a small test suite (pytest).

```bash
# Use the environment you installed dependencies into (venv or conda)
pytest -q
```

---

## Re-encode students (useful after changing detection pipeline)

We included a helper script `tools/reencode_students.py` that will read existing student photos and regenerate encodings using the current `FaceRecognitionService` pipeline. Run this from the project root (inside the conda env if you need face_recognition):

```bash
conda activate faceenv
python tools/reencode_students.py
```

This will update `data/students.json` with new encodings where possible.

---

## VS Code / Dev container tips

- Open the project in VS Code. If you use the Remote - Containers extension or Dev Containers, you can base your dev container on an image that includes conda (or install conda inside the container). Keep the `python` version to 3.10 in the devcontainer for best compatibility.
- Use the integrated terminal to activate `faceenv` and run the server.
- Add a simple task to `.vscode/tasks.json` to run `python app.py` (I can help add this if you'd like).

---

## Troubleshooting

1) dlib build failures with pip

- When installing `dlib` from pip, builds often fail due to missing system dependencies (cmake, Boost, BLAS/LAPACK, etc.). If you must install `dlib` from pip, ensure the following packages are installed on Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y build-essential cmake libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev libboost-all-dev libjpeg-dev libpng-dev
```

Then try:

```bash
python -m pip install dlib
```

But note: the conda approach avoids all this and is the least-frustrating route.

2) Camera not initializing / front-end errors

- Make sure your browser has camera permission.
- On pages that don't include the camera UI (e.g. admin dashboard), the client script will skip initialization.
- If your camera UI shows "No face detected" even with a clear face, try re-registering a student using a frontal, well-lit photo, or run `tools/reencode_students.py` after updating the detection pipeline.

3) Face detection returns 0 faces for some photos

- Some stored photos may be small, sideways, low contrast, or non-frontal. Use the Admin → Register Student page to upload a clear frontal photo and the server will generate an encoding using the same pipeline used at runtime.
- We added multiple fallbacks (CLAHE, upscaling, CNN, Haar) in `FaceRecognitionService.get_face_encoding()` to improve detection. If detection still fails, try a different image.

4) Port conflicts

- If port 5000 is taken, either stop the process holding it or set the `PORT` environment variable and change the `app.run(host, port)` call. Example to run on port 8000:

```bash
python app.py --port 8000
# or set environment variable FRONTEND_URL etc. (app supports redirecting to frontend)
```

---

## Models & Large files

- dlib model weights (if you plan to use dlib's shape predictor / resnet model locally) are not checked into this repo. If you want to use dlib for highest fidelity, download the official weights and place them in the `models/` directory:

- shape predictor (68 landmarks): shape_predictor_68_face_landmarks.dat
- dlib face recognition model: dlib_face_recognition_resnet_model_v1.dat

Download links (official):
- http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
- http://dlib.net/files/dlib_face_recognition_resnet_model_v1.dat.bz2

After downloading, decompress and move into `models/`.

---

If you'd like, I can:
- add a ready-made `.vscode/tasks.json`/`launch.json` for running and debugging the app in VS Code,
- add a small diagnostic page to the Admin UI to upload an image and preview detection/encoding, or
- create a GitHub Actions workflow that runs `pytest` on PRs.

Pick one and I'll implement it next.
