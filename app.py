from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import traceback
from config import Config
import json
from routes.student_routes import student_bp
from routes.admin_routes import admin_bp
from services.dlib_face_service import DlibFaceService
from services.attendance_service import AttendanceService
import cv2
import threading
import time
import numpy as np
import base64
import os

app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)
# Enable CORS for API endpoints so a separately-hosted frontend (e.g. GitHub Pages)
# can call the backend on Render. Tighten origins in production if desired.
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize services
face_service = DlibFaceService()
attendance_service = AttendanceService()

@app.route('/api/check-face', methods=['POST'])
def check_face():
    try:
        data = request.get_json()
        photo_data = data['photo'].split(',')[1] if ',' in data['photo'] else data['photo']
        photo_bytes = base64.b64decode(photo_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(photo_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({'face_detected': False, 'error': 'Invalid image data'})
        
        # Use dlib to check for faces
        encoding = face_service.get_face_encoding(image)
        face_detected = encoding is not None
        
        return jsonify({
            'face_detected': face_detected,
            'quality': 'good' if face_detected else 'poor'
        })
        
    except Exception as e:
        print(f"Error checking face: {str(e)}")
        return jsonify({'face_detected': False, 'error': str(e)})

# Register blueprints
app.register_blueprint(student_bp)
app.register_blueprint(admin_bp)

@app.route('/')
def index():
    """Main page with live camera feed"""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health endpoint to verify the service is up."""
    return jsonify({'status': 'ok'}), 200


@app.context_processor
def inject_app_config():
    # Expose a small subset of tunable client/server thresholds to templates
    cfg = {
        'RECOGNITION_COOLDOWN_MS': Config.RECOGNITION_COOLDOWN_MS,
        'SOUND_COOLDOWN_MS': Config.SOUND_COOLDOWN_MS,
        'DISTANCE_MARGIN': Config.DISTANCE_MARGIN,
        'COSINE_MARGIN': Config.COSINE_MARGIN,
        'COSINE_THRESHOLD': Config.COSINE_THRESHOLD,
        'TEMPLATE_THRESHOLD': Config.TEMPLATE_THRESHOLD,
        'COSINE_DISTANCE_GUARD': Config.COSINE_DISTANCE_GUARD,
        'MIN_CONSECUTIVE_FRAMES': Config.MIN_CONSECUTIVE_FRAMES
    }
    return dict(app_config=cfg)

@app.route('/api/process-frame', methods=['POST'])
def process_frame():
    """Process video frame for face recognition"""
    try:
        # Get frame data from request
        # Use silent parsing so we don't raise on bad/missing Content-Type
        frame_data = request.get_json(silent=True)
        # Defensive logging for debugging intermittent 400s
        try:
            print("/api/process-frame received request. Keys:", list(frame_data.keys()) if frame_data else None)
        except Exception:
            print("/api/process-frame received request. Keys: Unable to list keys")

        if not frame_data or 'frame' not in frame_data:
            # Return a graceful non-HTTP-error response so the client won't see repeated 400s
            print("/api/process-frame: no frame data provided or missing 'frame' key")
            return jsonify({'success': False, 'error': 'No frame data provided', 'recognized_faces': []}), 200

        raw_frame = frame_data['frame']
        # Accept data URLs or raw base64
        if isinstance(raw_frame, str) and ',' in raw_frame:
            raw_frame = raw_frame.split(',')[1]

        print(f"Received frame length: {len(raw_frame) if isinstance(raw_frame, str) else 'N/A'}")

        # Decode base64 frame
        try:
            frame_bytes = base64.b64decode(raw_frame)
        except Exception as be:
            print(f"/api/process-frame: invalid base64 frame data: {str(be)}")
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Invalid base64 frame data: {str(be)}', 'recognized_faces': []}), 200
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            print("/api/process-frame: could not decode frame")
            return jsonify({'success': False, 'error': 'Could not decode frame', 'recognized_faces': []}), 200
        
        # Process frame
        recognized_faces = face_service.process_frame(frame)

        # Update attendance for recognized faces
        attendance_info = []
        for face in recognized_faces:
            student_id = face['student_id']
            name = face['name']
            
            # Update last seen time
            # Record appearance: first appearance of the day is login_time; update logout_time to last appearance
            attendance_service.record_appearance(student_id, name)

            # Get attendance details from today's records
            today_attendance = attendance_service.get_today_attendance(student_id)
            if today_attendance:
                # Normalize legacy/new keys: attendance service stores 'login_time'/'logout_time'/'duration'
                face['attendance_marked'] = True
                face['first_timestamp'] = today_attendance.get('first_timestamp') or today_attendance.get('login_time')
                face['last_timestamp'] = today_attendance.get('last_timestamp') or today_attendance.get('logout_time')

                # Normalize work hours: some records store a string like '1.23 hours'
                duration_val = today_attendance.get('duration') or today_attendance.get('work_hours')
                work_hours = 0.0
                if isinstance(duration_val, str):
                    try:
                        work_hours = float(duration_val.split()[0])
                    except Exception:
                        work_hours = 0.0
                elif isinstance(duration_val, (int, float)):
                    work_hours = float(duration_val)

                face['work_hours'] = work_hours
            # include photo_url if provided by face service
            try:
                photo_path = face.get('photo_path')
                if photo_path:
                    from flask import url_for
                    fname = os.path.basename(photo_path)
                    face['photo_url'] = url_for('static', filename=f'images/student_photos/{fname}')
            except Exception:
                pass
            
            attendance_info.append(face)
        
        return jsonify({
            'success': True,
            'recognized_faces': attendance_info
        })
    except Exception as e:
        # Log full traceback for debugging but return 200 to avoid flooding client with 400s
        print(f"Unexpected error in /api/process-frame: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e), 'recognized_faces': []}), 200

def check_timeouts():
    """Background task to check for session timeouts"""
    while True:
        attendance_service.check_and_update_timeouts()
        time.sleep(60)  # Check every minute

if __name__ == '__main__':
    # Start timeout checker in background thread
    timeout_thread = threading.Thread(target=check_timeouts, daemon=True)
    timeout_thread.start()
    
    # Run the Flask application
    app.run(host='0.0.0.0', port=5000, debug=True)