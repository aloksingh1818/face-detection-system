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

    def get_face_encoding(self, cv_image):
        """Return a single face encoding for a given OpenCV BGR image or None.

        This helper mirrors the DlibFaceService.get_face_encoding contract used by
        the admin registration endpoint and the /api/check-face endpoint.
        The input is expected to be an OpenCV BGR image (as produced by cv2).
        """
        try:
            # Convert BGR to RGB for face_recognition
            rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)

            # Optionally resize a large image to speed up detection while keeping
            # enough resolution for reliable face detection.
            h, w = rgb.shape[:2]
            if max(h, w) > 1600:
                scale = 1600.0 / max(h, w)
                rgb = cv2.resize(rgb, (int(w * scale), int(h * scale)))

            # Try several strategies to improve detection on difficult images.
            # 1) Default HOG detector on the original image
            locations = face_recognition.face_locations(rgb)
            encodings = face_recognition.face_encodings(rgb, locations)
            if encodings:
                return encodings[0]

            # 2) Try simple contrast-limited adaptive histogram equalization (CLAHE)
            try:
                ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
                y, cr, cb = cv2.split(ycrcb)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                y2 = clahe.apply(y)
                ycrcb2 = cv2.merge((y2, cr, cb))
                rgb_clahe = cv2.cvtColor(ycrcb2, cv2.COLOR_YCrCb2RGB)
                locations = face_recognition.face_locations(rgb_clahe)
                encodings = face_recognition.face_encodings(rgb_clahe, locations)
                if encodings:
                    return encodings[0]
            except Exception:
                # Non-fatal; continue to other fallbacks
                pass

            # 3) Try upscaling the image progressively (helps small or low-res faces)
            try:
                h, w = rgb.shape[:2]
                for scale in (1.25, 1.5, 2.0):
                    nh = int(h * scale)
                    nw = int(w * scale)
                    rgb_up = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
                    locations = face_recognition.face_locations(rgb_up)
                    encodings = face_recognition.face_encodings(rgb_up, locations)
                    if encodings:
                        # Convert coordinates back to original scale if needed by caller
                        return encodings[0]
            except Exception:
                pass

            # 4) Try CNN model if dlib/face_recognition was built with it. This is
            # slower but can detect faces missed by HOG. Wrapped in try/except
            # because some installations may not include the CNN model files.
            try:
                locations = face_recognition.face_locations(rgb, model='cnn')
                encodings = face_recognition.face_encodings(rgb, locations)
                if encodings:
                    return encodings[0]
            except Exception:
                pass

            # 5) As a final fallback, try OpenCV's Haar cascade to get a bbox and
            # compute an encoding from that region.
            try:
                cascade_path = os.path.join(Config.MODEL_DIR, 'haarcascade_frontalface_default.xml')
                if os.path.exists(cascade_path):
                    cascade = cv2.CascadeClassifier(cascade_path)
                else:
                    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
                faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                if len(faces) > 0:
                    # Take first detected face region and compute encoding on the crop
                    (x, y, w, h) = faces[0]
                    crop = rgb[y:y+h, x:x+w]
                    encs = face_recognition.face_encodings(crop)
                    if encs:
                        return encs[0]
            except Exception:
                pass

            # Nothing found
            return None
        except Exception as e:
            print('Error in get_face_encoding:', e)
            return None
    
    def register_new_student(self, student_id, name, image_path):
        """Register a new student with their face encoding"""
        try:
            # Load image with OpenCV so we can reuse get_face_encoding fallback
            cv_image = cv2.imread(image_path)
            if cv_image is None:
                raise ValueError('Could not load image')

            encoding = self.get_face_encoding(cv_image)
            if encoding is None:
                raise ValueError("No face found in the image")
            
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