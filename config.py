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
    FACE_RECOGNITION_TOLERANCE = 0.4  # Lower value = more strict matching (0.6 is default)
    MIN_CONSECUTIVE_FRAMES = 3  # Number of consecutive frames needed for recognition
    DEBUG_MODE = True  # Enable debug logging
    # Face Recognition Settings
    FACE_RECOGNITION_TOLERANCE = 0.6       # Lower is more strict (0.6 is default)
    DEBUG_MODE = True                      # Enable debug logging
    
    # Face Recognition Settings
    FACE_RECOGNITION_TOLERANCE = 0.6       # Lower is more strict
    MIN_FACE_SIZE = 20                     # Minimum face size in pixels
    
    # Time Zone Settings
    TIMEZONE = 'Asia/Kolkata'             # Default timezone for timestamps

    @staticmethod
    def init_app(app):
        # Create required directories if they don't exist
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        os.makedirs(Config.STUDENT_PHOTOS_DIR, exist_ok=True)
        
        # Initialize empty JSON files if they don't exist
        if not os.path.exists(Config.STUDENTS_JSON):
            with open(Config.STUDENTS_JSON, 'w') as f:
                f.write('[]')
                
        if not os.path.exists(Config.ATTENDANCE_JSON):
            with open(Config.ATTENDANCE_JSON, 'w') as f:
                f.write('[]')