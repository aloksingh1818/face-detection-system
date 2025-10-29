import dlib
import cv2
import numpy as np
from config import Config
from utils.helpers import load_json
import os

class DlibFaceService:
    def __init__(self):
        self.detector = dlib.get_frontal_face_detector()
        self.shape_predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')
        self.face_rec_model = dlib.face_recognition_model_v1('dlib_face_recognition_resnet_model_v1.dat')
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_student_ids = []
        self.consecutive_frames = {}  # Track consecutive detections
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
    
    def get_face_encoding(self, image):
        """Get face encoding for a single image"""
        try:
            # Convert to RGB (dlib expects RGB images)
            if isinstance(image, str):
                # If image is a file path
                image = cv2.imread(image)
                if image is None:
                    raise ValueError("Could not read image file")
                
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Ensure minimum size and quality
            min_size = 300
            height, width = rgb_image.shape[:2]
            if width < min_size or height < min_size:
                scale = min_size / min(width, height)
                rgb_image = cv2.resize(rgb_image, (0, 0), fx=scale, fy=scale)
            
            # Detect faces with multiple scale factors for better detection
            faces = []
            best_quality = 0
            best_face = None
            
            for scale in [1.0, 0.75, 1.5]:  # Try different scales
                test_img = cv2.resize(rgb_image, (0, 0), fx=scale, fy=scale)
                detected = self.detector(test_img, 1)  # Second argument is number of upsampling
                
                for det in detected:
                    # Convert coordinates back to original scale
                    scaled_rect = dlib.rectangle(
                        int(det.left()/scale), 
                        int(det.top()/scale),
                        int(det.right()/scale),
                        int(det.bottom()/scale)
                    )
                    
                    # Calculate face quality (size and position)
                    face_width = det.right() - det.left()
                    face_height = det.bottom() - det.top()
                    quality = face_width * face_height
                    
                    if quality > best_quality:
                        best_quality = quality
                        best_face = scaled_rect
                        faces = [scaled_rect]  # Keep only the best face
            
            if not faces:
                if Config.DEBUG_MODE:
                    print("No face detected in the image")
                return None
                
            # Get face shape and compute encoding
            shape = self.shape_predictor(rgb_image, faces[0])
            face_encoding = self.face_rec_model.compute_face_descriptor(rgb_image, shape)
            
            if Config.DEBUG_MODE:
                print("Face encoding computed successfully")
            
            return list(face_encoding)
        except Exception as e:
            if Config.DEBUG_MODE:
                print(f"Error in get_face_encoding: {str(e)}")
            return None
    
    def process_frame(self, frame):
        """Process a video frame and return recognized faces"""
        # Resize frame for faster face recognition
        height, width = frame.shape[:2]
        small_frame = cv2.resize(frame, (width//2, height//2))  # Less aggressive resize
        
        # Convert frame to RGB (dlib expects RGB)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        if Config.DEBUG_MODE:
            print("Processing frame:", rgb_frame.shape)
        
        # Detect faces first
        faces = self.detector(rgb_frame)
        if Config.DEBUG_MODE:
            print(f"Number of faces detected: {len(faces)}")
        
        if not faces:
            return []
            
        # Get face encoding for the first face
        face_encoding = self.get_face_encoding(rgb_frame)
        
        recognized_faces = []
        
        if face_encoding is not None:
            # Compare with known faces
            for i, known_encoding in enumerate(self.known_face_encodings):
                # Calculate Euclidean distance
                distance = np.linalg.norm(face_encoding - known_encoding)
                
                # If distance is below threshold (similar faces)
                if distance < Config.FACE_RECOGNITION_TOLERANCE:
                    name = self.known_face_names[i]
                    student_id = self.known_student_ids[i]
                    recognized_faces.append({
                        'student_id': student_id,
                        'name': name
                    })
                    break  # Stop after first match
        
        return recognized_faces
    
    def register_new_student(self, student_id, name, image_path):
        """Register a new student with their face encoding"""
        try:
            # Load the image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not load image")
                
            # Get face encoding
            encoding = self.get_face_encoding(image)
            if encoding is None:
                raise ValueError("No face found in the image")
            
            # Load existing students
            students = load_json(Config.STUDENTS_JSON)
            
            # Add new student
            student_data = {
                "student_id": student_id,
                "name": name,
                "encoding": encoding  # encoding is already a list from get_face_encoding
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