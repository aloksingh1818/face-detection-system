from datetime import datetime
from utils.helpers import (
    load_json, save_json, get_current_time,
    is_session_expired, calculate_duration
)
from config import Config

class AttendanceService:
    def __init__(self):
        self.active_sessions = {}  # Keep track of active sessions in memory
        # Migrate attendance file to canonical fields if needed
        self._migrate_attendance()

    def _migrate_attendance(self):
        """Ensure attendance records contain canonical keys: first_timestamp, last_timestamp, work_hours (float).
        Keep legacy keys for backward compatibility but populate canonical ones.
        """
        try:
            records = load_json(Config.ATTENDANCE_JSON)
            changed = False
            for rec in records:
                # Add first_timestamp / last_timestamp from login_time/logout_time if missing
                if 'first_timestamp' not in rec and 'login_time' in rec:
                    rec['first_timestamp'] = rec.get('login_time')
                    changed = True
                if 'last_timestamp' not in rec and 'logout_time' in rec:
                    rec['last_timestamp'] = rec.get('logout_time')
                    changed = True
                # Add numeric work_hours from duration string if missing
                if 'work_hours' not in rec and 'duration' in rec:
                    try:
                        rec['work_hours'] = float(str(rec.get('duration')).split()[0])
                        changed = True
                    except Exception:
                        rec['work_hours'] = 0.0
                        changed = True
            if changed:
                save_json(Config.ATTENDANCE_JSON, records)
        except Exception as e:
            print(f"Error migrating attendance records: {e}")
        
    def get_today_attendance(self, student_id):
        """Get today's attendance record for a student"""
        try:
            today = datetime.now().date().isoformat()
            attendance_records = load_json(Config.ATTENDANCE_JSON)

            for entry in attendance_records:
                if entry.get('student_id') == student_id and entry.get('date') == today:
                    return entry

            return None
        except Exception as e:
            print(f"Error getting today's attendance: {str(e)}")
            return None
    
    def mark_login(self, student_id, name):
        """Mark a student's login"""
        current_time = get_current_time()
        attendance_records = load_json(Config.ATTENDANCE_JSON)
        
        # Legacy method: create a login record if none exists for today.
        # For the new first/last appearance logic prefer using record_appearance().
        today = current_time.date().isoformat()
        # Check if today's record exists
        for record in attendance_records:
            if record.get('student_id') == student_id and record.get('date') == today:
                # Already has today's record; do not create another
                return False

        new_record = {
            "student_id": student_id,
            "name": name,
            "login_time": current_time.isoformat(),
            "logout_time": current_time.isoformat(),
            "duration": "0.00 hours",
            "date": today
        }

        attendance_records.append(new_record)
        self.active_sessions[student_id] = current_time

        return save_json(Config.ATTENDANCE_JSON, attendance_records)

    def record_appearance(self, student_id, name):
        """Record a user's appearance: first appearance of the day is login_time, last appearance updates logout_time.

        This method ensures only the first login_time is kept and logout_time is updated to the most recent appearance during the day.
        Returns True on success.
        """
        try:
            current_time = get_current_time()
            today = current_time.date().isoformat()
            attendance_records = load_json(Config.ATTENDANCE_JSON)

            # Find existing today's record
            existing = None
            for rec in attendance_records:
                if rec.get('student_id') == student_id and rec.get('date') == today:
                    existing = rec
                    break

            if existing is None:
                # First appearance of the day: set both login and logout to now
                new_record = {
                    "student_id": student_id,
                    "name": name,
                    "login_time": current_time.isoformat(),
                    "logout_time": current_time.isoformat(),
                    "duration": "0.00 hours",
                    "date": today
                }
                attendance_records.append(new_record)
            else:
                # Update logout_time to the latest appearance
                existing['logout_time'] = current_time.isoformat()
                # Recompute duration
                existing['duration'] = calculate_duration(existing['login_time'], existing['logout_time'])

            # Update active sessions/last seen
            self.active_sessions[student_id] = current_time

            return save_json(Config.ATTENDANCE_JSON, attendance_records)
        except Exception as e:
            print(f"Error recording appearance: {e}")
            return False
    
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