from datetime import datetime
from utils.helpers import (
    load_json, save_json, get_current_time,
    is_session_expired, calculate_duration
)
from config import Config

class AttendanceService:
    def __init__(self):
        self.active_sessions = {}  # Keep track of active sessions in memory
        
    def get_today_attendance(self, student_id):
        """Get today's attendance record for a student"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            attendance_data = load_json(Config.ATTENDANCE_JSON)
            
            if today in attendance_data:
                for entry in attendance_data[today]:
                    if entry['student_id'] == student_id:
                        return entry
            
            return None
        except Exception as e:
            print(f"Error getting today's attendance: {str(e)}")
            return None
    
    def mark_login(self, student_id, name):
        """Mark a student's login"""
        current_time = get_current_time()
        attendance_records = load_json(Config.ATTENDANCE_JSON)
        
        # Check for existing active session
        existing_session = None
        for record in attendance_records:
            if (record['student_id'] == student_id and 
                not record['logout_time']):
                existing_session = record
                break
        
        if existing_session:
            # If existing session has expired, close it and create new one
            if is_session_expired(existing_session['login_time']):
                existing_session['logout_time'] = (
                    current_time - Config.AUTO_LOGOUT_TIME
                ).isoformat()
                existing_session['duration'] = calculate_duration(
                    existing_session['login_time'],
                    existing_session['logout_time']
                )
            else:
                # Session still active, don't create new one
                return False
        
        # Create new attendance record
        new_record = {
            "student_id": student_id,
            "name": name,
            "login_time": current_time.isoformat(),
            "logout_time": "",
            "duration": "0.00 hours",
            "date": current_time.date().isoformat()
        }
        
        attendance_records.append(new_record)
        
        # Update active sessions
        self.active_sessions[student_id] = current_time
        
        return save_json(Config.ATTENDANCE_JSON, attendance_records)
    
    def mark_logout(self, student_id):
        """Mark a student's logout"""
        current_time = get_current_time()
        attendance_records = load_json(Config.ATTENDANCE_JSON)
        
        # Find the student's active session
        for record in attendance_records:
            if (record['student_id'] == student_id and 
                not record['logout_time']):
                record['logout_time'] = current_time.isoformat()
                record['duration'] = calculate_duration(
                    record['login_time'],
                    record['logout_time']
                )
                
                # Remove from active sessions
                self.active_sessions.pop(student_id, None)
                
                return save_json(Config.ATTENDANCE_JSON, attendance_records)
        
        return False
    
    def get_student_attendance(self, student_id):
        """Get attendance history for a specific student"""
        attendance_records = load_json(Config.ATTENDANCE_JSON)
        return [
            record for record in attendance_records 
            if record['student_id'] == student_id
        ]
    
    def get_all_attendance(self, date=None):
        """Get all attendance records, optionally filtered by date"""
        attendance_records = load_json(Config.ATTENDANCE_JSON)
        if date:
            return [
                record for record in attendance_records 
                if record['date'] == date
            ]
        return attendance_records
    
    def check_and_update_timeouts(self):
        """Check for timed out sessions and mark logouts"""
        current_time = get_current_time()
        
        for student_id, last_seen in list(self.active_sessions.items()):
            if (current_time - last_seen) > Config.FACE_TIMEOUT:
                self.mark_logout(student_id)
    
    def update_last_seen(self, student_id):
        """Update the last seen time for an active session"""
        self.active_sessions[student_id] = get_current_time()