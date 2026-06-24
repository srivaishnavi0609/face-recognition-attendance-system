<<<<<<< HEAD
Student Attendance Management System

Student Attendance Management System powered by a secure Python (Flask) backend, a high-fidelity SQLite database, and an OpenCV/Deep Learning Face Recognition engine. It features a modern, responsive Glassmorphic dashboard with dark mode and voice assistance.

---

## 🌟 Key Features

1. **Teacher / Admin Portal**: Secure session-based authentication using PBKDF2/SHA256 password hashing.
2. **Live Webcam Scanner**: Detects and recognizes student faces in real-time, automatically logs attendance (Present/Late/Absent), and speaks voice greetings ("Welcome, John!").
3. **Fallback Engine**: Seamlessly boots into an OpenCV Haar Cascade mode if the native C++ `face_recognition` models are missing, ensuring the app never crashes on startup.
4. **Interactive Dashboard**: Dynamically renders weekly trends, today's status ratios, class performances, and scan logs using Chart.js.
5. **Student Directory**: Complete CRUD operations for student profiles, tracking contact information, profile photos, and face engram registrations.
6. **Double-Scan Prevention**: Smart buffer prevents duplicate scans for the same student on the same day.
7. **Detailed Reports**: Comprehensive date, student, and class query filters, with inline status corrections for instructors.
8. **Export Utilities**: Quick download buttons to output sheets to Microsoft Excel (`.xlsx`) and CSV tables.

---

## 📁 Project Structure

```
attendance/
├── app.py                  # Controller: Flask web server and endpoints
├── database.py             # Model: SQLite schema and query functions
├── face_helper.py          # Service: OpenCV frame processing & face recognition
├── requirements.txt        # Dependencies configuration
├── README.md               # Documentation and setup instructions
├── inject_sample_data.py   # Seeding script for mock data
├── static/
│   ├── css/
│   │   └── style.css       # View: Glassmorphic theme styles
│   ├── js/
│   │   ├── main.js         # View: Dark/Light toggle, responsive sidebar, toast alerts
│   │   ├── dashboard.js    # View: Chart.js visualization
│   │   └── face_recognize.js # View: Live polling & camera registration handlers
│   └── uploads/            # Dynamic storage for student face captures
└── templates/
    ├── base.html           # View: Core sidebar layout template
    ├── login.html          # View: Teacher login panel
    ├── dashboard.html      # View: Analytics and counters
    ├── students.html       # View: Student list and editor
    ├── register_face.html  # View: Camera capture & manual upload page
    ├── attendance.html     # View: Live face recognition attendance view
    └── reports.html        # View: Records manager and exports
```

---

## 🚀 Installation & Quick Start

The project is pre-seeded with mock student accounts and past attendance records. Follow these steps to launch the app:

### 1. Install Dependencies
Open a terminal (Powershell/Cmd) inside the project directory and install the required packages:

```bash
pip install -r requirements.txt
```

### 2. Run the Application
Start the Flask development server:

```bash
python app.py
```

Open your web browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

### 3. Log In
Use the default administrator credentials:
* **Username**: `admin`
* **Password**: `password123`

---

## 🧠 Enabling the Production-Grade Face Recognition Model

By default, the application runs in **Fallback Mode** using OpenCV Haar Cascades for face detection. To activate the high-fidelity deep learning face identification model, you must install the native C++ compiler compiler toolset (`dlib`) on Windows.

### Windows Setup Instructions:

1. **Install CMake**:
   Download and install CMake from the [official website](https://cmake.org/download/) (ensure you select the option to "Add CMake to the system PATH").
   
2. **Install Visual Studio Build Tools**:
   Download the [Visual Studio Community Installer](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and select:
   * **Desktop Development with C++** (check the C++ CMake Tools option).

3. **Install the Libraries**:
   Restart your terminal and run:
   ```bash
   pip install face_recognition
   ```
   *Note: This command will automatically compile `dlib` which can take 5-10 minutes.*

4. **Restart App**:
   Relaunch `python app.py`. The system will automatically detect the new library, change its dashboard status to **Active**, and begin running real deep learning face mappings.

---

## 🛠️ Security & Design Features
* **SQL Injection Shield**: Every database interaction uses SQL parameter bindings.
* **XSS & CSRF Safe**: Templates use Jinja2 escaping; sessions are signed with encrypted cookies.
* **Glassmorphic Cyber-Dark Palette**: Colors include deep slate base gradients, indigo focus highlights, teal secondary alerts, and custom backdrop blur containers that adapt dynamically.
=======
# face-recognition-attendance-system
AI-powered attendance management system using Flask, OpenCV, face recognition, and SQLite for automated student attendance tracking and reporting.
>>>>>>> 7646b5fe4dd667c6f4922b1a5e847f273c0bc114
