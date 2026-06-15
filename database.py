import sqlite3
import os
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'attendance.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes the database schema and creates a default administrator."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create Teachers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            class_name VARCHAR(50) NOT NULL,
            section VARCHAR(10) NOT NULL,
            email VARCHAR(100) UNIQUE,
            phone VARCHAR(20),
            face_encoding TEXT, -- Serialized JSON list of float values
            image_path VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create Attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL,
            status VARCHAR(15) DEFAULT 'Present',
            recognition_confidence REAL,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            UNIQUE(student_id, date) -- Prevent duplicate logs for the same student on the same day
        )
    ''')

    # Create default admin if not exists
    cursor.execute("SELECT COUNT(*) FROM teachers")
    if cursor.fetchone()[0] == 0:
        default_pw = generate_password_hash("password123")
        cursor.execute(
            "INSERT INTO teachers (username, password_hash, email) VALUES (?, ?, ?)",
            ("admin", default_pw, "admin@attendance.com")
        )
        print("Default teacher created: admin / password123")

    conn.commit()
    conn.close()

# --- Teacher DB Actions ---

def authenticate_teacher(username, password):
    conn = get_db_connection()
    teacher = conn.execute("SELECT * FROM teachers WHERE username = ?", (username,)).fetchone()
    conn.close()
    if teacher and check_password_hash(teacher['password_hash'], password):
        return dict(teacher)
    return None

def add_teacher(username, password, email):
    conn = get_db_connection()
    try:
        pw_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO teachers (username, password_hash, email) VALUES (?, ?, ?)",
            (username, pw_hash, email)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# --- Student DB Actions ---

def add_student(student_id, name, class_name, section, email, phone, face_encoding=None, image_path=None):
    conn = get_db_connection()
    try:
        encoding_str = json.dumps(face_encoding) if face_encoding is not None else None
        conn.execute(
            """INSERT INTO students (student_id, name, class_name, section, email, phone, face_encoding, image_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (student_id, name, class_name, section, email, phone, encoding_str, image_path)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        print(f"Error adding student: {e}")
        return False
    finally:
        conn.close()

def update_student(student_id, name, class_name, section, email, phone, face_encoding=None, image_path=None):
    conn = get_db_connection()
    try:
        if face_encoding is not None and image_path is not None:
            encoding_str = json.dumps(face_encoding)
            conn.execute(
                """UPDATE students 
                   SET name = ?, class_name = ?, section = ?, email = ?, phone = ?, face_encoding = ?, image_path = ?
                   WHERE student_id = ?""",
                (name, class_name, section, email, phone, encoding_str, image_path, student_id)
            )
        else:
            conn.execute(
                """UPDATE students 
                   SET name = ?, class_name = ?, section = ?, email = ?, phone = ?
                   WHERE student_id = ?""",
                (name, class_name, section, email, phone, student_id)
            )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error updating student: {e}")
        return False
    finally:
        conn.close()

def delete_student(student_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error deleting student: {e}")
        return False
    finally:
        conn.close()

def get_student(student_id):
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    conn.close()
    if student:
        student = dict(student)
        if student['face_encoding']:
            student['face_encoding'] = json.loads(student['face_encoding'])
        return student
    return None

def get_all_students(search_query=None, class_filter=None):
    conn = get_db_connection()
    query = "SELECT * FROM students WHERE 1=1"
    params = []

    if search_query:
        query += " AND (student_id LIKE ? OR name LIKE ? OR email LIKE ?)"
        like_query = f"%{search_query}%"
        params.extend([like_query, like_query, like_query])
    
    if class_filter:
        query += " AND class_name = ?"
        params.append(class_filter)
        
    query += " ORDER BY class_name, name"
    students = conn.execute(query, params).fetchall()
    conn.close()

    result = []
    for s in students:
        s_dict = dict(s)
        if s_dict['face_encoding']:
            s_dict['face_encoding'] = json.loads(s_dict['face_encoding'])
        result.append(s_dict)
    return result

def get_all_classes():
    conn = get_db_connection()
    classes = conn.execute("SELECT DISTINCT class_name FROM students ORDER BY class_name").fetchall()
    conn.close()
    return [c['class_name'] for c in classes]

# --- Attendance DB Actions ---

def mark_attendance(student_id, date_str, time_str, status='Present', confidence=1.0):
    conn = get_db_connection()
    try:
        conn.execute(
            """INSERT INTO attendance (student_id, date, time, status, recognition_confidence)
               VALUES (?, ?, ?, ?, ?)""",
            (student_id, date_str, time_str, status, confidence)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Already marked for today
        return False
    except sqlite3.Error as e:
        print(f"Database error marking attendance: {e}")
        return False
    finally:
        conn.close()

def update_attendance_status(attendance_id, status):
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE attendance SET status = ? WHERE attendance_id = ?",
            (status, attendance_id)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error updating attendance status: {e}")
        return False
    finally:
        conn.close()

def delete_attendance_record(attendance_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM attendance WHERE attendance_id = ?", (attendance_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error deleting attendance: {e}")
        return False
    finally:
        conn.close()

def get_attendance_history(start_date=None, end_date=None, student_id=None, class_name=None):
    conn = get_db_connection()
    query = """
        SELECT a.attendance_id, a.student_id, s.name, s.class_name, s.section, a.date, a.time, a.status, a.recognition_confidence
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE 1=1
    """
    params = []

    if start_date:
        query += " AND a.date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND a.date <= ?"
        params.append(end_date)
    if student_id:
        query += " AND a.student_id = ?"
        params.append(student_id)
    if class_name:
        query += " AND s.class_name = ?"
        params.append(class_name)

    query += " ORDER BY a.date DESC, a.time DESC"
    records = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in records]

# --- Reports & Analytics Actions ---

def get_dashboard_stats():
    conn = get_db_connection()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Total students
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    
    # Active today
    marked_today = conn.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (today_str,)).fetchone()[0]
    
    # Attendance rate today
    present_today = conn.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Present'", (today_str,)).fetchone()[0]
    late_today = conn.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Late'", (today_str,)).fetchone()[0]
    
    rate = 0
    if total_students > 0:
        rate = round(((present_today + late_today) / total_students) * 100, 1)

    # Class stats
    classes = conn.execute("""
        SELECT class_name, COUNT(student_id) as student_count 
        FROM students 
        GROUP BY class_name
    """).fetchall()
    
    class_stats = []
    for c in classes:
        # Today present in this class
        present_in_class = conn.execute("""
            SELECT COUNT(a.student_id) 
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.date = ? AND s.class_name = ? AND a.status IN ('Present', 'Late')
        """, (today_str, c['class_name'])).fetchone()[0]
        
        c_rate = 0
        if c['student_count'] > 0:
            c_rate = round((present_in_class / c['student_count']) * 100, 1)
            
        class_stats.append({
            'class_name': c['class_name'],
            'total': c['student_count'],
            'present': present_in_class,
            'rate': c_rate
        })

    # Recent scans (limit 5)
    recent_scans = conn.execute("""
        SELECT s.name, s.class_name, a.time, a.status, a.recognition_confidence
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.date = ?
        ORDER BY a.time DESC
        LIMIT 5
    """, (today_str,)).fetchall()

    conn.close()
    
    return {
        'total_students': total_students,
        'marked_today': marked_today,
        'attendance_rate': rate,
        'class_stats': class_stats,
        'recent_scans': [dict(r) for r in recent_scans]
    }

def get_weekly_trend():
    """Returns attendance rates for the last 7 active days."""
    conn = get_db_connection()
    # Fetch last 7 days of attendance entries
    dates = conn.execute("""
        SELECT DISTINCT date 
        FROM attendance 
        ORDER BY date DESC 
        LIMIT 7
    """).fetchall()
    
    dates = sorted([d['date'] for d in dates])
    
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    
    trend = []
    if total_students > 0:
        for date_str in dates:
            present = conn.execute("""
                SELECT COUNT(*) 
                FROM attendance 
                WHERE date = ? AND status IN ('Present', 'Late')
            """, (date_str,)).fetchone()[0]
            rate = round((present / total_students) * 100, 1)
            trend.append({'date': date_str, 'rate': rate})
            
    conn.close()
    return trend

def get_student_report_summary(student_id):
    """Returns analytical report for a specific student."""
    conn = get_db_connection()
    total_days = conn.execute("SELECT COUNT(DISTINCT date) FROM attendance").fetchone()[0]
    
    student_logs = conn.execute("""
        SELECT COUNT(*) as count, status 
        FROM attendance 
        WHERE student_id = ? 
        GROUP BY status
    """, (student_id,)).fetchall()
    
    conn.close()
    
    stats = {'Present': 0, 'Late': 0, 'Absent': 0}
    for log in student_logs:
        if log['status'] in stats:
            stats[log['status']] = log['count']
            
    attended = stats['Present'] + stats['Late']
    percentage = 0
    if total_days > 0:
        # Note: If database doesn't record 'Absent' rows, the remainder are absent
        # We can calculate percentage based on total recorded active attendance dates
        percentage = round((attended / total_days) * 100, 1)
        
    return {
        'stats': stats,
        'total_school_days': total_days,
        'attended_days': attended,
        'percentage': percentage
    }
