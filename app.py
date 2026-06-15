import os
import io
import time
import math
import random
from datetime import datetime
from functools import wraps
import cv2
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, jsonify, send_file
from werkzeug.utils import secure_filename

import database
from face_helper import FaceRecognizer

app = Flask(__name__)
app.secret_key = "attendai_super_secret_session_key_98765"

# Setup Upload Directory for Student Portraits
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Face Recognition Engine
recognizer = FaceRecognizer()

# Thread Synchronization Flags for Webcam Capturing
CAPTURE_FLAG = None
CAPTURE_RESULT = None

# Global queue to store recent scans (for live client-side polling)
RECENT_SCANS = []

def add_recent_scan(student_id, date_str, time_str, status, confidence):
    """Adds a scan record to the in-memory queue, preventing duplicate notifications."""
    student = database.get_student(student_id)
    if student:
        scan_entry = {
            'student_id': student_id,
            'name': student['name'],
            'class_name': student['class_name'],
            'section': student['section'],
            'date': date_str,
            'time': time_str,
            'status': status,
            'recognition_confidence': confidence
        }
        
        global RECENT_SCANS
        # Filter duplicates: If they scanned in the last 60 seconds, don't trigger a new UI toast/log
        duplicate = False
        for s in RECENT_SCANS:
            # Match date and time up to the minute
            if s['student_id'] == student_id and s['date'] == date_str and s['time'][:5] == time_str[:5]:
                duplicate = True
                break
                
        if not duplicate:
            RECENT_SCANS.append(scan_entry)
            if len(RECENT_SCANS) > 20:
                RECENT_SCANS.pop(0)

# --- Authentication Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'teacher_id' not in session:
            flash("Please sign in to access the system.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def index():
    if 'teacher_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'teacher_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        teacher = database.authenticate_teacher(username, password)
        if teacher:
            session['teacher_id'] = teacher['teacher_id']
            session['username'] = teacher['username']
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password.", "error")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Successfully signed out.", "success")
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    stats = database.get_dashboard_stats()
    native = recognizer.is_engine_native()
    return render_template('dashboard.html', stats=stats, engine_native=native)

# --- Students Management ---

@app.route('/students', methods=['GET'])
@login_required
def students():
    search_query = request.args.get('search', '').strip()
    class_filter = request.args.get('class_filter', '').strip()
    
    student_list = database.get_all_students(search_query, class_filter)
    classes = database.get_all_classes()
    
    return render_template(
        'students.html', 
        students=student_list, 
        classes=classes, 
        search_query=search_query, 
        class_filter=class_filter
    )

@app.route('/students/add', methods=['POST'])
@login_required
def add_student_route():
    student_id = request.form.get('student_id', '').strip()
    name = request.form.get('name', '').strip()
    class_name = request.form.get('class_name', '').strip()
    section = request.form.get('section', '').strip()
    email = request.form.get('email', '').strip() or None
    phone = request.form.get('phone', '').strip() or None

    if not student_id or not name or not class_name or not section:
        flash("All mandatory fields (*) must be filled.", "error")
        return redirect(url_for('students'))

    success = database.add_student(student_id, name, class_name, section, email, phone)
    if success:
        flash("Student profile created successfully! Please enroll face encodings.", "success")
        return redirect(url_for('register_face_page', student_id=student_id))
    else:
        flash(f"Failed to create profile. Student ID '{student_id}' or Email may already exist.", "error")
        return redirect(url_for('students'))

@app.route('/students/edit/<student_id>', methods=['POST'])
@login_required
def edit_student_route(student_id):
    name = request.form.get('name', '').strip()
    class_name = request.form.get('class_name', '').strip()
    section = request.form.get('section', '').strip()
    email = request.form.get('email', '').strip() or None
    phone = request.form.get('phone', '').strip() or None

    if not name or not class_name or not section:
        flash("Name, Class, and Section are mandatory.", "error")
        return redirect(url_for('students'))

    success = database.update_student(student_id, name, class_name, section, email, phone)
    if success:
        # Reload known faces in case metadata changed
        recognizer.reload_known_faces()
        flash("Student profile updated successfully.", "success")
    else:
        flash("Failed to update student profile.", "error")
    return redirect(url_for('students'))

@app.route('/students/delete/<student_id>', methods=['POST'])
@login_required
def delete_student_route(student_id):
    student = database.get_student(student_id)
    if student:
        # Delete image if exists
        if student['image_path']:
            full_img_path = os.path.join(app.static_folder, student['image_path'])
            if os.path.exists(full_img_path):
                try:
                    os.remove(full_img_path)
                except OSError as e:
                    print(f"Error removing photo: {e}")
                    
        success = database.delete_student(student_id)
        if success:
            recognizer.reload_known_faces()
            flash("Student profile and records deleted.", "success")
        else:
            flash("Failed to delete student.", "error")
    else:
        flash("Student not found.", "error")
    return redirect(url_for('students'))

# --- Face Registration Routes ---

@app.route('/register_face')
@login_required
def register_face_page():
    selected_id = request.args.get('student_id', '')
    student_list = database.get_all_students()
    return render_template('register_face.html', students=student_list, selected_student_id=selected_id)

@app.route('/api/student/<student_id>')
@login_required
def api_get_student(student_id):
    student = database.get_student(student_id)
    if student:
        # Don't return raw json binary arrays, strip it
        student_data = {
            'student_id': student['student_id'],
            'name': student['name'],
            'class_name': student['class_name'],
            'section': student['section'],
            'email': student['email'],
            'phone': student['phone'],
            'image_path': student['image_path'],
            'face_encoding': True if student['face_encoding'] else False
        }
        return jsonify(student_data)
    return jsonify(None), 404

@app.route('/api/capture_face', methods=['POST'])
@login_required
def api_capture_face():
    global CAPTURE_FLAG, CAPTURE_RESULT
    data = request.json or {}
    student_id = data.get('student_id')
    
    if not student_id:
        return jsonify({'success': False, 'message': 'Student ID is required'}), 400
        
    student = database.get_student(student_id)
    if not student:
        return jsonify({'success': False, 'message': 'Student profile not found'}), 404
        
    # Trigger Capture flag to be picked up by the webcam streaming thread
    CAPTURE_RESULT = None
    CAPTURE_FLAG = student_id
    
    # Wait for generator thread to process capture (up to 3 seconds)
    timeout = 3.0
    start = time.time()
    while CAPTURE_RESULT is None:
        time.sleep(0.05)
        if time.time() - start > timeout:
            return jsonify({'success': False, 'message': 'Capture timed out. Please ensure the webcam feed is turned on.'}), 500
            
    # If successful, reload our local known faces encodings in the recognizer cache
    if CAPTURE_RESULT.get('success'):
        recognizer.reload_known_faces()
        
    return jsonify(CAPTURE_RESULT)

@app.route('/upload_face', methods=['POST'])
@login_required
def upload_face_route():
    student_id = request.form.get('student_id')
    if not student_id:
        flash("Select a student profile first.", "error")
        return redirect(url_for('register_face_page'))
        
    student = database.get_student(student_id)
    if not student:
        flash("Student profile not found.", "error")
        return redirect(url_for('register_face_page'))
        
    if 'image_file' not in request.files:
        flash("No file part provided.", "error")
        return redirect(url_for('register_face_page', student_id=student_id))
        
    file = request.files['image_file']
    if file.filename == '':
        flash("No file selected.", "error")
        return redirect(url_for('register_face_page', student_id=student_id))
        
    if file:
        filename = secure_filename(f"{student_id}.jpg")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Open saved file in OpenCV to run face check and encoding calculations
        frame = cv2.imread(file_path)
        if frame is None:
            flash("Invalid image format.", "error")
            return redirect(url_for('register_face_page', student_id=student_id))
            
        success, res = recognizer.extract_face_encoding(frame)
        if success:
            db_img_path = f"uploads/{filename}"
            # Save encoding (list) and image relative path to DB
            db_success = database.update_student(
                student_id, 
                name=student['name'],
                class_name=student['class_name'],
                section=student['section'],
                email=student['email'],
                phone=student['phone'],
                face_encoding=res,
                image_path=db_img_path
            )
            if db_success:
                recognizer.reload_known_faces()
                flash("Face photo successfully uploaded and enrolled!", "success")
            else:
                flash("Failed to update face record in database.", "error")
        else:
            # Remove uploaded file if validation failed
            if os.path.exists(file_path):
                os.remove(file_path)
            flash(f"Enrollment Rejected: {res}", "error")
            
    return redirect(url_for('register_face_page', student_id=student_id))

# --- Attendance Scanner & Tracking ---

@app.route('/attendance')
@login_required
def attendance_scanner():
    today_str = datetime.now().strftime('%Y-%m-%d')
    today_records = database.get_attendance_history(start_date=today_str, end_date=today_str)
    students = database.get_all_students()
    native = recognizer.is_engine_native()
    return render_template(
        'attendance.html', 
        today_records=today_records, 
        students=students, 
        today_date=today_str,
        engine_native=native
    )

@app.route('/attendance/manual', methods=['POST'])
@login_required
def manual_attendance_route():
    student_id = request.form.get('student_id')
    status = request.form.get('status', 'Present')
    date_str = request.form.get('date')
    
    if not student_id or not date_str:
        flash("Student ID and Date are mandatory.", "error")
        return redirect(url_for('attendance_scanner'))
        
    time_str = datetime.now().strftime('%H:%M:%S')
    success = database.mark_attendance(student_id, date_str, time_str, status, confidence=100.0)
    
    if success:
        flash("Manual attendance record created.", "success")
    else:
        flash("Duplicate Entry: Attendance has already been logged for this student today.", "error")
        
    return redirect(url_for('attendance_scanner'))

# --- Streaming Video Feed ---

def generate_video_stream(mode):
    """Webcam video capturing and streaming loop with simulation fallback."""
    global CAPTURE_FLAG, CAPTURE_RESULT
    camera = cv2.VideoCapture(0)
    
    # Use local instances inside thread loops to ensure thread-safety
    local_recognizer = FaceRecognizer()

    def mark_attendance_cb(student_id, confidence):
        # Callback triggered by recognizer inside the frame loop
        today_str = datetime.now().strftime('%Y-%m-%d')
        time_str = datetime.now().strftime('%H:%M:%S')
        
        # Simple Late rule: Check-in after 09:15 AM
        status = 'Present'
        now = datetime.now()
        if now.hour > 9 or (now.hour == 9 and now.minute > 15):
            status = 'Late'
            
        db_success = database.mark_attendance(student_id, today_str, time_str, status, confidence)
        if db_success:
            # Sync to in-memory notifications
            add_recent_scan(student_id, today_str, time_str, status, confidence)

    # 1. Simulator Fallback Mode
    if not camera.isOpened():
        print("CRITICAL: Camera device 0 failed to open. Entering Simulation Mode.")
        width, height = 640, 480
        angle = 0.0
        last_scan_time = 0.0
        current_recognized_student = None
        recognized_timer = 0.0
        
        try:
            while True:
                # Create dark blue gradient background
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                for y in range(height):
                    val = int(15 + (y / height) * 20)
                    frame[y, :] = (val + 5, val, 15)
                
                # Draw grid lines
                grid_color = (30, 41, 59)
                for x in range(0, width, 40):
                    cv2.line(frame, (x, 0), (x, height), grid_color, 1)
                for y in range(0, height, 40):
                    cv2.line(frame, (0, y), (width, y), grid_color, 1)
                
                # Draw scanning frame UI
                hud_color = (99, 102, 241)
                cv2.rectangle(frame, (80, 60), (560, 420), hud_color, 1)
                len_corner = 25
                cv2.line(frame, (80, 60), (80 + len_corner, 60), hud_color, 3)
                cv2.line(frame, (80, 60), (80, 60 + len_corner), hud_color, 3)
                cv2.line(frame, (560, 60), (560 - len_corner, 60), hud_color, 3)
                cv2.line(frame, (560, 60), (560, 60 + len_corner), hud_color, 3)
                cv2.line(frame, (80, 420), (80 + len_corner, 420), hud_color, 3)
                cv2.line(frame, (80, 420), (80, 420 - len_corner), hud_color, 3)
                cv2.line(frame, (560, 420), (560 - len_corner, 420), hud_color, 3)
                cv2.line(frame, (560, 420), (560, 420 - len_corner), hud_color, 3)
                
                # Face animation movement
                angle += 0.05
                face_x = int(320 + math.sin(angle) * 45)
                face_y = int(240 + math.cos(angle * 0.7) * 20)
                
                # Draw head outline
                cv2.circle(frame, (face_x, face_y - 20), 75, (148, 163, 184), 2)
                # Neck
                cv2.rectangle(frame, (face_x - 15, face_y + 55), (face_x + 15, face_y + 90), (148, 163, 184), 2)
                # Shoulders
                cv2.ellipse(frame, (face_x, face_y + 140), (95, 50), 0, 180, 360, (148, 163, 184), 2)
                # Eyes
                cv2.circle(frame, (face_x - 25, face_y - 35), 8, (148, 163, 184), 2)
                cv2.circle(frame, (face_x + 25, face_y - 35), 8, (148, 163, 184), 2)
                # Nose
                cv2.line(frame, (face_x, face_y - 25), (face_x, face_y + 5), (148, 163, 184), 2)
                cv2.line(frame, (face_x, face_y + 5), (face_x - 5, face_y + 5), (148, 163, 184), 2)
                # Smile
                cv2.ellipse(frame, (face_x, face_y + 15), (20, 10), 0, 0, 180, (148, 163, 184), 2)
                
                # Draw scanning line overlay
                scan_y = int(240 + math.sin(angle * 1.5) * 160)
                cv2.line(frame, (80, scan_y), (560, scan_y), (20, 184, 166), 1)
                overlay = frame.copy()
                cv2.rectangle(overlay, (80, max(60, scan_y - 10)), (560, min(420, scan_y + 10)), (20, 184, 166), -1)
                cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
                
                cv2.putText(frame, "SIMULATED WEBCAM FEED", (100, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 184, 166), 2)
                cv2.putText(frame, "STATUS: ACTIVE", (420, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (16, 185, 129), 1)
                
                # Sync Capture Request
                if CAPTURE_FLAG is not None:
                    student_id_to_capture = CAPTURE_FLAG
                    CAPTURE_FLAG = None
                    
                    filename = f"{student_id_to_capture}.jpg"
                    img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    cv2.imwrite(img_path, frame)
                    
                    stud = database.get_student(student_id_to_capture)
                    db_success = database.update_student(
                        student_id_to_capture,
                        name=stud['name'],
                        class_name=stud['class_name'],
                        section=stud['section'],
                        email=stud['email'],
                        phone=stud['phone'],
                        face_encoding=list(np.random.normal(0.0, 0.1, 128)),
                        image_path=f"uploads/{filename}"
                    )
                    
                    if db_success:
                        CAPTURE_RESULT = {
                            'success': True,
                            'image_path': f"/static/uploads/{filename}"
                        }
                    else:
                        CAPTURE_RESULT = {'success': False, 'message': 'Failed to save to database.'}
                
                now_time = time.time()
                
                if mode == 'attendance':
                    if current_recognized_student is not None:
                        color = (16, 185, 129)
                        cv2.rectangle(frame, (face_x - 85, face_y - 105), (face_x + 85, face_y + 105), color, 2)
                        
                        label = f"{current_recognized_student['name']} ({current_recognized_student['confidence']}%)"
                        cv2.rectangle(frame, (face_x - 85, face_y + 105), (face_x + 85, face_y + 135), color, cv2.FILLED)
                        cv2.putText(frame, label, (face_x - 80, face_y + 125), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
                        
                        if now_time - recognized_timer > 3.0:
                            current_recognized_student = None
                    else:
                        if last_scan_time == 0.0 or now_time - last_scan_time > 8.0:
                            last_scan_time = now_time
                            all_studs = database.get_all_students()
                            if all_studs:
                                chosen = random.choice(all_studs)
                                conf = round(random.uniform(88.0, 99.5), 1)
                                current_recognized_student = {
                                    'student_id': chosen['student_id'],
                                    'name': chosen['name'],
                                    'confidence': conf
                                }
                                recognized_timer = now_time
                                mark_attendance_cb(chosen['student_id'], conf)
                else:
                    color = (20, 184, 166)
                    cv2.rectangle(frame, (face_x - 85, face_y - 105), (face_x + 85, face_y + 105), color, 2)
                    cv2.rectangle(frame, (face_x - 85, face_y + 105), (face_x + 85, face_y + 135), color, cv2.FILLED)
                    cv2.putText(frame, "Face Detected", (face_x - 45, face_y + 125), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
                
                ret, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')
                time.sleep(0.05)
        except Exception as e:
            print(f"Error in simulated video stream: {e}")
        return

    # 2. Native/Fallback Physical Webcam Mode
    try:
        while True:
            success, frame = camera.read()
            if not success:
                break
            
            # 1. Sync Capture Request (Registration Panel)
            if CAPTURE_FLAG is not None:
                student_id_to_capture = CAPTURE_FLAG
                CAPTURE_FLAG = None # Clear immediately
                
                success_c, res_c = local_recognizer.extract_face_encoding(frame)
                if success_c:
                    filename = f"{student_id_to_capture}.jpg"
                    img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    cv2.imwrite(img_path, frame)
                    
                    stud = database.get_student(student_id_to_capture)
                    db_success = database.update_student(
                        student_id_to_capture,
                        name=stud['name'],
                        class_name=stud['class_name'],
                        section=stud['section'],
                        email=stud['email'],
                        phone=stud['phone'],
                        face_encoding=res_c,
                        image_path=f"uploads/{filename}"
                    )
                    
                    if db_success:
                        CAPTURE_RESULT = {
                            'success': True,
                            'image_path': f"/static/uploads/{filename}"
                        }
                    else:
                        CAPTURE_RESULT = {'success': False, 'message': 'Failed to save to database.'}
                else:
                    CAPTURE_RESULT = {'success': False, 'message': res_c}

            # 2. Recognition Overlays (Attendance vs Registration mode)
            if mode == 'attendance':
                frame = local_recognizer.process_frame(frame, mark_attendance_cb)
            else:
                # In registration mode, just show Haar bounding boxes without saving logs
                frame = local_recognizer.process_frame(frame, None)
                
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')
                   
    finally:
        camera.release()
        print("Camera device shut down and resources freed.")

@app.route('/video_feed')
def video_feed():
    mode = request.args.get('mode', 'attendance')
    return Response(
        generate_video_stream(mode), 
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/recent_scans')
@login_required
def api_recent_scans():
    # Return last 10 scans recorded in memory
    return jsonify(RECENT_SCANS)

# --- Reports Route & Export Features ---

@app.route('/reports', methods=['GET'])
@login_required
def reports():
    start_date = request.args.get('start_date', '').strip() or None
    end_date = request.args.get('end_date', '').strip() or None
    student_id = request.args.get('student_id', '').strip() or None
    class_filter = request.args.get('class_filter', '').strip() or None
    
    logs = database.get_attendance_history(start_date, end_date, student_id, class_filter)
    classes = database.get_all_classes()
    
    return render_template(
        'reports.html',
        logs=logs,
        classes=classes,
        start_date=start_date,
        end_date=end_date,
        student_id=student_id,
        class_filter=class_filter
    )

@app.route('/attendance/edit-status/<int:attendance_id>', methods=['POST'])
@login_required
def edit_attendance_status_route(attendance_id):
    status = request.form.get('status')
    
    # Back parameters to reload reports page with active filters
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    class_filter = request.form.get('class_filter', '')
    student_id = request.form.get('student_id_search', '')

    if status in ['Present', 'Late', 'Absent']:
        database.update_attendance_status(attendance_id, status)
        flash("Record modified successfully.", "success")
    else:
        flash("Invalid status selected.", "error")
        
    return redirect(url_for('reports', start_date=start_date, end_date=end_date, class_filter=class_filter, student_id=student_id))

@app.route('/attendance/delete/<int:attendance_id>', methods=['POST'])
@login_required
def delete_attendance_route(attendance_id):
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    class_filter = request.form.get('class_filter', '')
    student_id = request.form.get('student_id_search', '')

    database.delete_attendance_record(attendance_id)
    flash("Record removed.", "success")
    return redirect(url_for('reports', start_date=start_date, end_date=end_date, class_filter=class_filter, student_id=student_id))

# --- APIs supporting Charts Rendering ---

@app.route('/api/attendance_stats')
@login_required
def api_attendance_stats():
    today_str = datetime.now().strftime('%Y-%m-%d')
    conn = database.get_db_connection()
    
    # Doughnut Chart Data (Ratio today)
    present = conn.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Present'", (today_str,)).fetchone()[0]
    late = conn.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Late'", (today_str,)).fetchone()[0]
    absent = conn.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Absent'", (today_str,)).fetchone()[0]
    
    # Weekly trend
    trend = database.get_weekly_trend()
    
    # Class stats
    dashboard_data = database.get_dashboard_stats()
    
    conn.close()
    
    return jsonify({
        'weekly_trend': trend,
        'class_stats': dashboard_data['class_stats'],
        'today_ratio': {
            'present': present,
            'late': late,
            'absent': absent
        }
    })

# --- Excel & CSV Downloads ---

@app.route('/export/csv')
@login_required
def export_csv():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    student_id = request.args.get('student_id')
    class_filter = request.args.get('class_filter')
    
    logs = database.get_attendance_history(start_date, end_date, student_id, class_filter)
    if not logs:
        flash("No records to export.", "error")
        return redirect(url_for('reports'))
        
    df = pd.DataFrame(logs)
    df = df.rename(columns={
        'date': 'Date',
        'time': 'Time',
        'student_id': 'Student ID',
        'name': 'Student Name',
        'class_name': 'Class',
        'section': 'Section',
        'status': 'Status',
        'recognition_confidence': 'Confidence (%)'
    })
    if 'attendance_id' in df.columns:
        df = df.drop(columns=['attendance_id'])
        
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    
    return Response(
        csv_buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=attendance_report.csv"}
    )

@app.route('/export/excel')
@login_required
def export_excel():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    student_id = request.args.get('student_id')
    class_filter = request.args.get('class_filter')
    
    logs = database.get_attendance_history(start_date, end_date, student_id, class_filter)
    if not logs:
        flash("No records to export.", "error")
        return redirect(url_for('reports'))
        
    df = pd.DataFrame(logs)
    df = df.rename(columns={
        'date': 'Date',
        'time': 'Time',
        'student_id': 'Student ID',
        'name': 'Student Name',
        'class_name': 'Class',
        'section': 'Section',
        'status': 'Status',
        'recognition_confidence': 'Confidence (%)'
    })
    if 'attendance_id' in df.columns:
        df = df.drop(columns=['attendance_id'])
        
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Attendance')
        
    excel_buffer.seek(0)
    
    return send_file(
        excel_buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="attendance_report.xlsx"
    )

# --- Start Server ---
if __name__ == '__main__':
    # Initialize DB tables on startup
    database.init_db()
    
    print("AttendAI flask app running on http://127.0.0.1:5000")
    # Bind to localhost
    app.run(host="127.0.0.1", port=5000, debug=True)
