import os
from datetime import timedelta

# Application Configuration
class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # File Paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    STUDENT_PHOTOS_DIR = os.path.join(BASE_DIR, 'static', 'images', 'student_photos')
    STUDENTS_JSON = os.path.join(DATA_DIR, 'students.json')
    ATTENDANCE_JSON = os.path.join(DATA_DIR, 'attendance.json')
    
    # Attendance Settings
    AUTO_LOGOUT_TIME = timedelta(hours=8)  # Auto logout after 8 hours
    FACE_TIMEOUT = timedelta(minutes=5)    # Assume logout if face not detected for 5 minutes
    SESSION_EXPIRY = timedelta(days=2)     # Close old session if new login after 2 days
    
    # Face Recognition Settings
    FACE_RECOGNITION_TOLERANCE = 0.5       # Lower is more strict (reduce false positives)
    MIN_FACE_SIZE = 20                     # Minimum face size in pixels
    # Debugging toggle to enable verbose server logs
    DEBUG_MODE = True
    # Tunable thresholds (exposed to client via template)
    RECOGNITION_COOLDOWN_MS = 800         # client: short cooldown after a recognition (ms) - reduced for snappier UX
    SOUND_COOLDOWN_MS = 30 * 1000         # client: per-student sound cooldown (ms)
    # Immediate acceptance thresholds: if match is very confident, accept immediately without waiting for consecutive frames
    FACE_RECOGNITION_IMMEDIATE_DISTANCE = 0.35
    FACE_RECOGNITION_IMMEDIATE_COSINE = 0.92
    DISTANCE_MARGIN = 0.25                # server: require margin between best and second distance
    COSINE_MARGIN = 0.12                  # server: require margin between best and second cosine
    COSINE_THRESHOLD = 0.70               # server: minimal cosine to accept fallback
    TEMPLATE_THRESHOLD = 0.65             # server: minimal template match score
    COSINE_DISTANCE_GUARD = 0.90          # server: guard to avoid accepting cosine if distance too large
    MIN_CONSECUTIVE_FRAMES = 4            # Number of consecutive frames required to confirm recognition
    
    # Time Zone Settings
    TIMEZONE = 'Asia/Kolkata'             # Default timezone for timestamps

    @staticmethod
    def init_app(app):
        # Create required directories if they don't exist
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        os.makedirs(Config.STUDENT_PHOTOS_DIR, exist_ok=True)
        # Models directory for dlib / cascades
        Config.MODEL_DIR = os.path.join(Config.BASE_DIR, 'models')
        os.makedirs(Config.MODEL_DIR, exist_ok=True)
        
        # Initialize empty JSON files if they don't exist
        if not os.path.exists(Config.STUDENTS_JSON):
            with open(Config.STUDENTS_JSON, 'w') as f:
                f.write('[]')
                
        if not os.path.exists(Config.ATTENDANCE_JSON):
            with open(Config.ATTENDANCE_JSON, 'w') as f:
                f.write('[]')
