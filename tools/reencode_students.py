#!/usr/bin/env python3
"""Utility: re-generate face encodings for students using the FaceRecognitionService

This script loads students from data/students.json and attempts to compute a new
face encoding for each student using their stored `photo_path` or by finding a
matching photo file in the student photos directory. It overwrites the encoding
in-place and saves the JSON if any updates succeed.

Run inside the conda env where face_recognition is available:

    conda run -n faceenv python tools/reencode_students.py

"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.face_recognition_service import FaceRecognitionService
from utils.helpers import load_json, save_json
from config import Config
from pathlib import Path
import os

service = FaceRecognitionService()
students = load_json(Config.STUDENTS_JSON) or []
updated = False

for i, s in enumerate(students):
    sid = s.get('student_id')
    print(f"Processing student {sid} - {s.get('name')}")
    photo_path = s.get('photo_path')
    if photo_path and os.path.exists(photo_path):
        path = photo_path
    else:
        # try to find a file in STUDENT_PHOTOS_DIR that starts with this id
        files = list(Path(Config.STUDENT_PHOTOS_DIR).glob(f"{sid}_*.jpg"))
        if files:
            path = str(files[0])
        else:
            print(f"  No photo found for {sid}; skipping")
            continue

    # load with OpenCV
    import cv2
    img = cv2.imread(path)
    if img is None:
        print(f"  Failed to load image {path}")
        continue

    enc = service.get_face_encoding(img)
    if enc is None:
        print(f"  Could not detect face for {sid} in {path}")
        continue

    students[i]['encoding'] = enc.tolist()
    # also update photo_path to a normalized static path (store absolute path currently)
    students[i]['photo_path'] = os.path.abspath(path)
    updated = True
    print(f"  Updated encoding for {sid}")

if updated:
    if save_json(Config.STUDENTS_JSON, students):
        print("Students JSON updated with new encodings.")
    else:
        print("Failed to save updated students.json")
else:
    print("No updates made.")
