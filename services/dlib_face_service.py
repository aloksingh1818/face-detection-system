try:
    import dlib
    DLIB_AVAILABLE = True
except Exception:
    dlib = None
    DLIB_AVAILABLE = False

import cv2
import numpy as np
from config import Config
from utils.helpers import load_json
import os

class DlibFaceService:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_student_ids = []
        self.consecutive_frames = {}  # Track consecutive detections

        # Instance-level flag for dlib availability
        self.dlib_available = DLIB_AVAILABLE

        if self.dlib_available:
            try:
                # Prefer model files from Config.MODEL_DIR if available
                model_dir = getattr(Config, 'MODEL_DIR', os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'models'))
                shape_path = os.path.join(model_dir, 'shape_predictor_68_face_landmarks.dat')
                face_rec_path = os.path.join(model_dir, 'dlib_face_recognition_resnet_model_v1.dat')

                if not os.path.exists(shape_path) or not os.path.exists(face_rec_path):
                    raise FileNotFoundError(f"dlib model files missing in {model_dir}: shape_exists={os.path.exists(shape_path)} rec_exists={os.path.exists(face_rec_path)}")

                if Config.DEBUG_MODE:
                    print(f"Loading dlib models from: {model_dir}")

                self.detector = dlib.get_frontal_face_detector()
                self.shape_predictor = dlib.shape_predictor(shape_path)
                self.face_rec_model = dlib.face_recognition_model_v1(face_rec_path)
            except Exception as e:
                # If model files are missing or there's an error, fall back to OpenCV cascade
                if Config.DEBUG_MODE:
                    print(f"dlib models not available or failed to load: {e}")
                self.dlib_available = False
                # Use local cascade file (from models dir) as primary fallback
                model_dir = getattr(Config, 'MODEL_DIR', os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'models'))
                cascade_path = os.path.join(model_dir, 'haarcascade_frontalface_default.xml')
                if not os.path.exists(cascade_path):
                    # fallback to OpenCV package data if present
                    cv2_data = getattr(cv2, 'data', None)
                    if cv2_data:
                        cascade_path = os.path.join(cv2_data, 'haarcascade_frontalface_default.xml')
                    else:
                        cascade_path = ''
                if Config.DEBUG_MODE:
                    print(f"Using cascade at: {cascade_path}")
                self.detector = cv2.CascadeClassifier(cascade_path)
        else:
            # dlib not installed; use OpenCV cascade as a lightweight fallback
            if Config.DEBUG_MODE:
                print("dlib not available — using OpenCV Haar cascade fallback for face detection")
            model_dir = getattr(Config, 'MODEL_DIR', os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'models'))
            cascade_path = os.path.join(model_dir, 'haarcascade_frontalface_default.xml')
            if not os.path.exists(cascade_path):
                cv2_data = getattr(cv2, 'data', None)
                if cv2_data:
                    cascade_path = os.path.join(cv2_data, 'haarcascade_frontalface_default.xml')
                else:
                    cascade_path = ''
            if Config.DEBUG_MODE:
                print(f"Using cascade at: {cascade_path}")
            self.detector = cv2.CascadeClassifier(cascade_path)

        self.load_known_faces()
    
    def load_known_faces(self):
        """Load known face encodings from students.json"""
        students = load_json(Config.STUDENTS_JSON)
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_student_ids = []
        self.known_face_photos = []
        
        for student in students:
            self.known_face_encodings.append(np.array(student['encoding']))
            self.known_face_names.append(student['name'])
            self.known_student_ids.append(student['student_id'])
            # Optional photo path for fallback matching. If not present, try to find a photo file
            photo = student.get('photo_path')
            if not photo:
                # look up in the student photos directory for files starting with student_id_
                try:
                    files = os.listdir(Config.STUDENT_PHOTOS_DIR)
                    matched = [f for f in files if f.startswith(f"{student.get('student_id')}_")]
                    if matched:
                        photo = os.path.join(Config.STUDENT_PHOTOS_DIR, matched[-1])
                except Exception:
                    photo = None
            self.known_face_photos.append(photo)
    
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
            
            # If dlib is available use the original pipeline
            if self.dlib_available:
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

            # Fallback (no dlib): use OpenCV Haar cascade to detect a face and return a dummy encoding
            gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
            rects = self.detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            if len(rects) == 0:
                if Config.DEBUG_MODE:
                    print("No face detected by OpenCV fallback")
                return None

            # Create a deterministic placeholder encoding (not suitable for real recognition)
            # Use a normalized histogram of the face region and pad/truncate to 128 dims
            x, y, w, h = rects[0]
            face_region = gray[y:y+h, x:x+w]
            hist = cv2.calcHist([face_region], [0], None, [64], [0, 256]).flatten()
            hist = hist / (np.linalg.norm(hist) + 1e-6)
            # Pad to 128
            if hist.size < 128:
                pad = np.zeros(128 - hist.size, dtype=float)
                encoding = np.concatenate([hist, pad])
            else:
                encoding = hist[:128]

            if Config.DEBUG_MODE:
                print("Returning fallback (non-dlib) face encoding")

            return list(encoding)
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
        if self.dlib_available:
            faces = self.detector(rgb_frame)
            num_faces = len(faces)
        else:
            gray = cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2GRAY)
            rects = self.detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            num_faces = len(rects)

        if Config.DEBUG_MODE:
            print(f"Number of faces detected: {num_faces}")

        if num_faces == 0:
            return []

        # Get face encoding for the first face (may be a fallback)
        face_encoding = self.get_face_encoding(rgb_frame)
        
        recognized_faces = []
        
        if face_encoding is not None:
            # Compare with known faces
            if Config.DEBUG_MODE:
                print(f"Comparing face encoding (len={len(face_encoding)}) against {len(self.known_face_encodings)} known encodings")

            # Collect scores for all known encodings first, then pick the best candidate with a margin
            candidates = []  # list of dicts: {i, distance, cosine}
            fe = np.array(face_encoding)
            for i, known_encoding in enumerate(self.known_face_encodings):
                try:
                    ke = np.array(known_encoding)
                except Exception as ex:
                    if Config.DEBUG_MODE:
                        print(f"Skipping known encoding #{i} due to exception: {ex}")
                    continue

                # compute distance and cosine
                try:
                    distance = float(np.linalg.norm(fe - ke))
                except Exception:
                    distance = float('inf')

                try:
                    denom = (np.linalg.norm(fe) * np.linalg.norm(ke)) + 1e-9
                    cosine_sim = float(np.dot(fe, ke) / denom)
                except Exception:
                    cosine_sim = 0.0

                candidates.append({
                    'i': i,
                    'distance': distance,
                    'cosine': cosine_sim
                })

                if Config.DEBUG_MODE:
                    print(f"Candidate known[{i}] name={self.known_face_names[i]} id={self.known_student_ids[i]} distance={distance:.4f} cosine={cosine_sim:.4f}")

            if not candidates:
                return recognized_faces

            # Sort by distance (ascending) and by cosine (descending) for tie-breaks
            candidates_by_distance = sorted(candidates, key=lambda c: c['distance'])
            candidates_by_cosine = sorted(candidates, key=lambda c: c['cosine'], reverse=True)

            # Decide using distance first if best distance below tolerance
            best = candidates_by_distance[0]
            second = candidates_by_distance[1] if len(candidates_by_distance) > 1 else None

            matched_index = None
            match_reason = None

            # margin thresholds (read from Config to allow tuning)
            DISTANCE_MARGIN = getattr(Config, 'DISTANCE_MARGIN', 0.20)
            COSINE_MARGIN = getattr(Config, 'COSINE_MARGIN', 0.08)
            COSINE_THRESHOLD = getattr(Config, 'COSINE_THRESHOLD', 0.65)
            TEMPLATE_THRESHOLD = getattr(Config, 'TEMPLATE_THRESHOLD', 0.60)
            COSINE_DISTANCE_GUARD = getattr(Config, 'COSINE_DISTANCE_GUARD', 0.90)

            if best['distance'] < Config.FACE_RECOGNITION_TOLERANCE:
                # require margin between best and second best to avoid ambiguous picks
                if second is None or (second['distance'] - best['distance']) > DISTANCE_MARGIN:
                    matched_index = best['i']
                    match_reason = f"distance ({best['distance']:.4f})"
                else:
                    if Config.DEBUG_MODE:
                        print(f"Best distance {best['distance']:.4f} not sufficiently better than second {second['distance']:.4f}")

            # If not matched by distance, try cosine on top cosine candidate
            if matched_index is None:
                best_cos = candidates_by_cosine[0]
                second_cos = candidates_by_cosine[1] if len(candidates_by_cosine) > 1 else None
                if best_cos['cosine'] >= COSINE_THRESHOLD:
                    # additional guard: ensure that candidate's distance is not extremely large
                    cand_dist = best_cos.get('distance', 1e9)
                    if cand_dist <= COSINE_DISTANCE_GUARD and (second_cos is None or (best_cos['cosine'] - second_cos['cosine']) > COSINE_MARGIN):
                        matched_index = best_cos['i']
                        match_reason = f"cosine ({best_cos['cosine']:.4f})"
                    else:
                        if Config.DEBUG_MODE:
                            sc = second_cos['cosine'] if second_cos else 0.0
                            print(f"Best cosine {best_cos['cosine']:.4f} not sufficiently better than second {sc:.4f} or distance {cand_dist:.4f} too large")

            # If still no confident match, use template matching on top N candidates (by cosine)
            if matched_index is None and self.known_face_photos:
                # try top 3 by cosine
                for cand in candidates_by_cosine[:3]:
                    i = cand['i']
                    stored_photo = self.known_face_photos[i]
                    try:
                        if stored_photo and os.path.exists(stored_photo):
                            sp = cv2.imread(stored_photo)
                            if sp is not None:
                                gray_sp = cv2.cvtColor(sp, cv2.COLOR_BGR2GRAY)
                                r = self.detector.detectMultiScale(gray_sp, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))
                                if len(r) > 0:
                                    x,y,w,h = r[0]
                                    sp_face = gray_sp[y:y+h, x:x+w]
                                    gray_live = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2GRAY)
                                    r2 = self.detector.detectMultiScale(gray_live, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))
                                    if len(r2) > 0:
                                        x2,y2,w2,h2 = r2[0]
                                        live_face = gray_live[y2:y2+h2, x2:x2+w2]
                                        try:
                                            sp_r = cv2.resize(sp_face, (100,100))
                                            live_r = cv2.resize(live_face, (100,100))
                                            res = cv2.matchTemplate(live_r, sp_r, cv2.TM_CCOEFF_NORMED)
                                            _, max_val, _, _ = cv2.minMaxLoc(res)
                                            if Config.DEBUG_MODE:
                                                print(f"Template max_val for known[{i}]: {max_val:.4f}")
                                            if max_val > TEMPLATE_THRESHOLD:
                                                matched_index = i
                                                match_reason = f"template ({max_val:.4f})"
                                                break
                                        except Exception:
                                            pass
                    except Exception:
                        pass

            # If we have a confident match, require consecutive-frame confirmation before returning
            if matched_index is not None:
                name = self.known_face_names[matched_index]
                student_id = self.known_student_ids[matched_index]
                face_entry = {'student_id': student_id, 'name': name}
                # attach photo path if available
                try:
                    photo = self.known_face_photos[matched_index]
                except Exception:
                    photo = None
                if photo:
                    face_entry['photo_path'] = photo

                # Decide if we can accept immediately (high-confidence) or require consecutive frames
                immediate_dist = getattr(Config, 'FACE_RECOGNITION_IMMEDIATE_DISTANCE', 0.35)
                immediate_cos = getattr(Config, 'FACE_RECOGNITION_IMMEDIATE_COSINE', 0.92)

                # Heuristic: accept immediately if very low distance OR very high cosine similarity
                is_high_conf = False
                try:
                    if best and best.get('distance', 1e9) <= immediate_dist:
                        is_high_conf = True
                    # also accept if any candidate has extremely high cosine and reasonable distance
                    top_cos = candidates_by_cosine[0]
                    if top_cos.get('cosine', 0.0) >= immediate_cos and top_cos.get('distance', 1e9) <= COSINE_DISTANCE_GUARD:
                        is_high_conf = True
                except Exception:
                    is_high_conf = False

                match_key = f"{student_id}_{name}"
                # reset other counters
                for k in list(self.consecutive_frames.keys()):
                    if k != match_key:
                        self.consecutive_frames[k] = 0

                if is_high_conf:
                    # Immediately accept high-confidence matches
                    recognized_faces.append(face_entry)
                    # also set counter so subsequent logic knows this was recently seen
                    self.consecutive_frames[match_key] = getattr(self.consecutive_frames, match_key, 0) + 1
                    if Config.DEBUG_MODE:
                        print(f"Selected (IMMEDIATE) match: {name} (id={student_id}) by {match_reason} (high-confidence)")
                else:
                    # Normal consecutive-frame logic
                    self.consecutive_frames[match_key] = self.consecutive_frames.get(match_key, 0) + 1
                    if Config.DEBUG_MODE:
                        print(f"Consecutive frames for {match_key}: {self.consecutive_frames[match_key]}")

                    if self.consecutive_frames.get(match_key, 0) >= getattr(Config, 'MIN_CONSECUTIVE_FRAMES', 1):
                        recognized_faces.append(face_entry)
                        if Config.DEBUG_MODE:
                            print(f"Selected match: {name} (id={student_id}) by {match_reason} after {self.consecutive_frames[match_key]} frames")
        
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
                "encoding": encoding,  # encoding is already a list from get_face_encoding
                "photo_path": image_path
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