from flask import Blueprint, jsonify, request, render_template, send_file
from services.attendance_service import AttendanceService
from services.dlib_face_service import DlibFaceService
from utils.helpers import load_json
import pandas as pd
import os
from datetime import datetime
import tempfile
from config import Config
import base64
import io
from PIL import Image
import numpy as np
import cv2

admin_bp = Blueprint('admin', __name__)
attendance_service = AttendanceService()
face_service = DlibFaceService()

@admin_bp.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard showing all attendance records"""
    attendance_records = attendance_service.get_all_attendance()
    # Load registered students to display on dashboard
    students = load_json(Config.STUDENTS_JSON)
    return render_template('admin_dashboard.html', attendance_records=attendance_records, students=students)

@admin_bp.route('/admin/register', methods=['GET', 'POST'])
def register_student():
    """Register a new student with face recognition"""
    if request.method == 'POST':
        try:
            # Check if data is JSON (from webcam) or form data (from file upload)
            if request.is_json:
                data = request.get_json()
                student_id = data['student_id']
                name = data['name']
                
                # Convert base64 image to file
                photo_data = data['photo'].split(',')[1] if ',' in data['photo'] else data['photo']
                photo_bytes = base64.b64decode(photo_data)
                
                # Convert to PIL Image
                image = Image.open(io.BytesIO(photo_bytes))
                
                # Convert PIL Image to OpenCV format
                cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Attempt to get face encoding first
                face_encoding = face_service.get_face_encoding(cv_image)
                
                if face_encoding is None:
                    return jsonify({
                        'success': False, 
                        'message': 'No face detected in the image. Please ensure your face is clearly visible and well-lit.'
                    })
                
                # Save photo only if face is detected
                photo_path = os.path.join(
                    Config.STUDENT_PHOTOS_DIR,
                    f"{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                )
                image.save(photo_path, 'JPEG')
                
            else:
                student_id = request.form['student_id']
                name = request.form['name']
                photo = request.files['photo']
                
                # Save photo
                photo_path = os.path.join(
                    Config.STUDENT_PHOTOS_DIR,
                    f"{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                )
                photo.save(photo_path)
            
            # Register student
            if face_service.register_new_student(student_id, name, photo_path):
                return jsonify({'success': True, 'message': 'Student registered successfully'})
            else:
                if os.path.exists(photo_path):
                    os.remove(photo_path)
                return jsonify({'success': False, 'message': 'Failed to register student. Please try again with a clearer photo showing your face.'})
                
        except Exception as e:
            if 'photo_path' in locals() and os.path.exists(photo_path):
                os.remove(photo_path)
            return jsonify({'success': False, 'message': str(e)}), 400
            
    return render_template('register_student.html')

@admin_bp.route('/admin/export-attendance')
def export_attendance():
    """Export attendance records as CSV"""
    try:
        attendance_records = attendance_service.get_all_attendance()
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(attendance_records)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            df.to_csv(temp_file.name, index=False)
            
        return send_file(
            temp_file.name,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'attendance_export_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@admin_bp.route('/api/admin/attendance')
def get_attendance():
    """API endpoint to get filtered attendance records"""
    date = request.args.get('date')
    student_id = request.args.get('student_id')
    
    records = attendance_service.get_all_attendance(date)
    
    if student_id:
        records = [r for r in records if r['student_id'] == student_id]
        
    return jsonify(records)