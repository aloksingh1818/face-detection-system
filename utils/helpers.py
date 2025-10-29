import json
import os
from datetime import datetime
import pytz
from threading import Lock
from config import Config

# Thread-safe file locks
students_lock = Lock()
attendance_lock = Lock()

def save_json(file_path, data):
    """Thread-safe JSON file writing with error handling"""
    lock = students_lock if file_path == Config.STUDENTS_JSON else attendance_lock
    
    with lock:
        try:
            temp_file = file_path + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(temp_file, file_path)  # Atomic operation
            return True
        except Exception as e:
            print(f"Error saving JSON file {file_path}: {str(e)}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False

def load_json(file_path):
    """Thread-safe JSON file reading with error handling"""
    lock = students_lock if file_path == Config.STUDENTS_JSON else attendance_lock
    
    with lock:
        try:
            if not os.path.exists(file_path):
                return []
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading JSON file {file_path}: {str(e)}")
            return []

def get_current_time():
    """Get current time in configured timezone"""
    return datetime.now(pytz.timezone(Config.TIMEZONE))

def format_duration(duration):
    """Format timedelta into hours with 2 decimal places"""
    hours = duration.total_seconds() / 3600
    return f"{hours:.2f} hours"

def is_session_expired(login_time):
    """Check if a session has expired based on configuration"""
    if not login_time:
        return False
    
    login_dt = datetime.fromisoformat(login_time)
    current_time = get_current_time()
    
    # Check if session exceeds auto logout time
    if (current_time - login_dt) > Config.AUTO_LOGOUT_TIME:
        return True
    
    return False

def calculate_duration(login_time, logout_time):
    """Calculate duration between login and logout times"""
    try:
        login_dt = datetime.fromisoformat(login_time)
        logout_dt = datetime.fromisoformat(logout_time)
        duration = logout_dt - login_dt
        return format_duration(duration)
    except Exception as e:
        print(f"Error calculating duration: {str(e)}")
        return "0.00 hours"