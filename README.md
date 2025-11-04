# FaceAttendAI - Automated Face Recognition Attendance System

FaceAttendAI is a production-ready Python web application that automatically performs face recognition attendance tracking using real-time camera feed. The system detects student faces automatically without requiring any manual clicks and records attendance in local JSON files.

## Features

- 🎥 Real-time face detection and recognition
- 📊 Automatic attendance tracking with login/logout times
- 💾 Local JSON storage (no database required)
- 🔄 Automatic session management
- 📱 Responsive web interface
- 📈 Admin dashboard with attendance analytics
- 👤 Student dashboard with personal attendance history
- 📄 Export attendance records to CSV

## Prerequisites

- Python 3.8 or higher
- Webcam
- Modern web browser

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/face-detection-system.git
cd face-detection-system
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick start — copy / paste

These commands will get a fresh clone running on a typical Ubuntu/macOS machine. Copy-paste each block for your platform.

Linux (Ubuntu / Debian)
```bash
# clone
git clone https://github.com/aloksingh1818/face-detection-system.git
cd face-detection-system

# (optional) install system packages required to build dlib and OpenCV native dependencies
sudo apt update
sudo apt install -y build-essential cmake python3-dev \
   libopenblas-dev liblapack-dev libatlas-base-dev libboost-all-dev \
   libx11-dev libgtk-3-dev libjpeg-dev zlib1g-dev pkg-config
sudo apt install -y libglib2.0-0 libsm6 libxrender1 libxext6 || true

# create and activate a virtual environment
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel

# install Python dependencies
python -m pip install -r requirements.txt

# Download dlib models if you want full dlib-based recognition (optional)
# Place them in the `models/` directory (create the folder if missing):
# - shape_predictor_68_face_landmarks.dat
# - dlib_face_recognition_resnet_model_v1.dat
# If you don't want to build dlib, remove `dlib` and `face_recognition`
# from requirements.txt and re-run pip install; the app will fall back to OpenCV.

# run the app
python app.py
```

macOS (with Homebrew)
```bash
git clone https://github.com/aloksingh1818/face-detection-system.git
cd face-detection-system

# install build tools
brew install cmake boost pkg-config
xcode-select --install || true

python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

# (optional) download dlib models into `models/`
python app.py
```

Windows (developer tooling required)
```powershell
# Install Visual Studio Build Tools (C++), CMake, and add them to PATH.
# Then from PowerShell:
git clone https://github.com/aloksingh1818/face-detection-system.git
cd face-detection-system
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python app.py
```

Notes about dlib and face_recognition
- `dlib` and `face_recognition` require native build tools and can fail to install if CMake, compilers, or BLAS/LAPACK libraries are missing. If you hit build errors for `dlib`, either install the system packages above or remove `dlib` and `face_recognition` from `requirements.txt` to use the OpenCV fallback.

Open the app

After the server is running (the dev server listens on port 5000 by default), open:

```
http://localhost:5000
```

Health check

To confirm the backend is running:

```bash
curl http://127.0.0.1:5000/api/health
# expect: {"status":"ok"}
```

## Registering a New Student

1. Navigate to Admin Dashboard and click "Register Student"
2. Fill in the student details:
   - Student ID
   - Full Name
   - Upload a clear face photo
3. Submit the form
4. The system will automatically extract and store face encodings

## How Automatic Login/Logout Works

1. **Login Process:**
   - When a registered face is detected in the camera feed
   - System automatically records login time
   - Visual and audio confirmation is provided
   
2. **Active Session:**
   - System continuously monitors presence
   - Updates "last seen" timestamp
   
3. **Automatic Logout:**
   - If face not detected for 5+ minutes
   - If session exceeds 8 hours
   - When browser/tab is closed

## Exporting Attendance Records

1. Go to Admin Dashboard
2. Use filters to select desired records:
   - Date range
   - Specific student
3. Click "Export to CSV"
4. Save the downloaded file

## Project Structure

```
FaceAttendAI/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── config.py             # Configuration settings
│
├── /data/                # JSON storage
│   ├── students.json     # Student records
│   └── attendance.json   # Attendance logs
│
├── /services/            # Business logic
├── /routes/             # URL routing
├── /templates/          # HTML templates
├── /static/             # Assets (CSS, JS, images)
└── /utils/              # Helper functions
```

## Configuration

Key settings in `config.py`:

- `AUTO_LOGOUT_TIME`: Maximum session duration (default: 8 hours)
- `FACE_TIMEOUT`: Time until auto-logout when face missing (default: 5 minutes)
- `FACE_RECOGNITION_TOLERANCE`: Recognition strictness (default: 0.6)
- `TIMEZONE`: Local timezone for timestamps (default: 'Asia/Kolkata')

## Security Notes

1. Keep `students.json` and `attendance.json` backed up
2. Use HTTPS in production
3. Implement user authentication for admin access
4. Regular backups of attendance data recommended

## License

MIT License - feel free to use for any purpose

## Support

For issues and feature requests, please create an issue on GitHub.


export FLASK_APP=app.py && export FLASK_ENV=development && flask run --host=0.0.0.0 --port=5001


to run the application -- python app.py


## Models

This repository was imported without large model binaries and the virtual environment to keep the repository small.

Please download and place the following files in the project root before running the app:

- shape_predictor_68_face_landmarks.dat
- dlib_face_recognition_resnet_model_v1.dat


Model downloads and Git LFS
---------------------------------
If you want to keep the model binaries in the repository, it's recommended to use Git LFS (Large File Storage).

- To enable LFS locally:
   - Install Git LFS: https://git-lfs.github.com/
   - Run: `git lfs install`
   - Track the model files: `git lfs track "*.dat"` (or the specific filenames)
   - Commit the resulting `.gitattributes` and push the files (or upload the binaries via releases)

- If you prefer not to store the models in Git, download the following files and place them in the repository root before running the app:
   - shape_predictor_68_face_landmarks.dat — (download from the dlib model releases or your backup)
   - dlib_face_recognition_resnet_model_v1.dat — (download from the dlib model releases or your backup)

Replace the parenthetical notes above with the exact download URLs if you have them.
You can obtain them from their original sources or move them from a local backup.
