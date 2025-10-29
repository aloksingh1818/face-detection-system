import face_recognition
import cv2
import numpy as np
from config import Config
from utils.helpers import load_json
import os

class FaceRecognitionService:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_student_ids = []
        self.consecutive_frames = {}  # Track consecutive matches
        self.attendance_cache = {}  # Cache to prevent multiple attendance marks
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load known face encodings from students.json"""
        students = load_json(Config.STUDENTS_JSON)
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_student_ids = []
        
        for student in students:
            self.known_face_encodings.append(np.array(student['encoding']))
            self.known_face_names.append(student['name'])
            self.known_student_ids.append(student['student_id'])
    
    def process_frame(self, frame):
        """Process a video frame and return recognized faces"""
        # Resize frame for faster face recognition
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        
        # Convert BGR to RGB
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Find faces in frame
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        recognized_faces = []
        
        for face_encoding in face_encodings:
            # Calculate face distances for all known faces
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                best_match_distance = face_distances[best_match_index]
                
                if best_match_distance <= Config.FACE_RECOGNITION_TOLERANCE:
                    name = self.known_face_names[best_match_index]
                    student_id = self.known_student_ids[best_match_index]
                    
                    # Track consecutive matches
                    match_key = f"{student_id}_{name}"
                    self.consecutive_frames[match_key] = self.consecutive_frames.get(match_key, 0) + 1
                    
                    # Only recognize after MIN_CONSECUTIVE_FRAMES matches
                    if self.consecutive_frames[match_key] >= Config.MIN_CONSECUTIVE_FRAMES:
                        if Config.DEBUG_MODE:
                            print(f"Recognized {name} (ID: {student_id}) with confidence: {1 - best_match_distance:.2f}")
                        student_id = self.known_student_ids[best_match_index]
                        attendance_marked = self.mark_attendance(student_id)
                        
                        recognized_faces.append({
                            'name': self.known_face_names[best_match_index],
                            'student_id': student_id,
                            'distance': float(best_match_distance),
                            'attendance_marked': attendance_marked
                        })
        
        return recognized_faces
    
    def register_new_student(self, student_id, name, image_path):
        """Register a new student with their face encoding"""
        try:
            # Load and encode the face
            image = face_recognition.load_image_file(image_path)
            face_encodings = face_recognition.face_encodings(image)
            
            if not face_encodings:
                raise ValueError("No face found in the image")
            
            # Get the first face encoding
            encoding = face_encodings[0]
            
            # Load existing students
            students = load_json(Config.STUDENTS_JSON)
            
            # Add new student
            student_data = {
                "student_id": student_id,
                "name": name,
                "encoding": encoding.tolist()
            }
            
            students.append(student_data)
            
            # Save updated students list
            from utils.helpers import save_json
            if save_json(Config.STUDENTS_JSON, students):
                # Update in-memory encodings
                self.load_known_faces()
                return True
                
            return False
            
        except Exception as e:
            print(f"Error registering student: {str(e)}")
            return False
            
    def mark_attendance(self, student_id):
        """Mark attendance for a student"""
        try:
            from datetime import datetime
            import json
            import time
            
            # Check if attendance was already marked in the last hour
            current_time = time.time()
            if student_id in self.attendance_cache:
                if current_time - self.attendance_cache[student_id] < 3600:  # 1 hour = 3600 seconds
                    return False
            
            # Load current attendance
            attendance_data = load_json(Config.ATTENDANCE_JSON)
            
            # Get today's date
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Create attendance entry
            attendance_entry = {
                'student_id': student_id,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Add today's attendance if not exists
            if today not in attendance_data:
                attendance_data[today] = []
                
            # Check if student already has an entry today
            current_entry = None
            for entry in attendance_data[today]:
                if entry['student_id'] == student_id:
                    current_entry = entry
                    break

            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if not current_entry:
                # First entry of the day
                attendance_entry = {
                    'student_id': student_id,
                    'first_timestamp': current_timestamp,
                    'last_timestamp': current_timestamp,
                    'work_hours': 0.0
                }
                attendance_data[today].append(attendance_entry)
                updated = True
            else:
                # Update last timestamp and calculate work hours
                from datetime import datetime
                first_time = datetime.strptime(current_entry['first_timestamp'], '%Y-%m-%d %H:%M:%S')
                current_time = datetime.strptime(current_timestamp, '%Y-%m-%d %H:%M:%S')
                work_hours = (current_time - first_time).total_seconds() / 3600  # Convert to hours
                
                current_entry['last_timestamp'] = current_timestamp
                current_entry['work_hours'] = round(work_hours, 2)
                updated = True
            
            # Save attendance data
            from utils.helpers import save_json
            if updated and save_json(Config.ATTENDANCE_JSON, attendance_data):
                # Update cache
                self.attendance_cache[student_id] = time.time()
                return True
            
            return False
            
        except Exception as e:
            print(f"Error marking attendance: {str(e)}")
            return False