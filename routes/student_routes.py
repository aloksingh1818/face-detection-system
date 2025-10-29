from flask import Blueprint, jsonify, request, render_template
from services.attendance_service import AttendanceService
from utils.helpers import load_json
from config import Config

student_bp = Blueprint('student', __name__)
attendance_service = AttendanceService()

@student_bp.route('/student/dashboard/<student_id>')
def student_dashboard(student_id):
    """Student dashboard showing attendance history"""
    # Get student details
    students = load_json(Config.STUDENTS_JSON)
    student = next((s for s in students if s['student_id'] == student_id), None)
    
    if not student:
        return render_template('error.html', message='Student not found'), 404
    
    # Get attendance history
    attendance_history = attendance_service.get_student_attendance(student_id)
    
    # Calculate statistics
    total_hours = sum(
        float(record['duration'].split()[0]) 
        for record in attendance_history 
        if record['duration']
    )
    avg_hours = total_hours / len(attendance_history) if attendance_history else 0
    
    return render_template(
        'student_dashboard.html',
        student=student,
        attendance_history=attendance_history,
        total_hours=round(total_hours, 2),
        avg_hours=round(avg_hours, 2)
    )

@student_bp.route('/api/student/attendance/<student_id>')
def get_student_attendance(student_id):
    """API endpoint to get student's attendance history"""
    attendance_history = attendance_service.get_student_attendance(student_id)
    return jsonify(attendance_history)

@student_bp.route('/api/student/current-status/<student_id>')
def get_current_status(student_id):
    """API endpoint to check if student is currently logged in"""
    attendance_records = attendance_service.get_student_attendance(student_id)
    current_session = next(
        (r for r in attendance_records if not r['logout_time']),
        None
    )
    
    return jsonify({
        'logged_in': bool(current_session),
        'current_session': current_session
    })