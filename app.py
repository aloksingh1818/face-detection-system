from flask import Flask, render_template, jsonify, request
from config import Config
from routes.student_routes import student_bp
from routes.admin_routes import admin_bp
from services.dlib_face_service import DlibFaceService
from services.attendance_service import AttendanceService
import cv2
import threading
import time
import numpy as np
import base64

app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

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

@app.route('/api/process-frame', methods=['POST'])
def process_frame():
    """Process video frame for face recognition"""
    try:
        # Get frame data from request
        frame_data = request.get_json()
        if not frame_data or 'frame' not in frame_data:
            raise ValueError("No frame data provided")

        # Decode base64 frame
        frame_bytes = base64.b64decode(frame_data['frame'])
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise ValueError("Could not decode frame")
        
        # Process frame
        recognized_faces = face_service.process_frame(frame)
        
            # Update attendance for recognized faces
        attendance_info = []
        for face in recognized_faces:
            student_id = face['student_id']
            name = face['name']
            
            # Update last seen time
            attendance_service.update_last_seen(student_id)
            
            # Mark login if not already logged in
            attendance_marked = attendance_service.mark_login(student_id, name)
            
            # Get attendance details from today's records
            today_attendance = attendance_service.get_today_attendance(student_id)
            if today_attendance:
                face['attendance_marked'] = True
                face['first_timestamp'] = today_attendance['first_timestamp']
                face['last_timestamp'] = today_attendance['last_timestamp']
                face['work_hours'] = today_attendance['work_hours']
            
            attendance_info.append(face)
        
        return jsonify({
            'success': True,
            'recognized_faces': attendance_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

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