import database
import json
from datetime import datetime, timedelta

def inject():
    # Make sure database is initialized
    database.init_db()
    
    print("Injecting mock students...")
    
    dummy_encoding = [0.0] * 128
    
    students = [
        ("STU101", "Abi", "CS-4A", "A", "abi@college.com", "+15550101", dummy_encoding),
        ("STU102", "Marcus Vance", "CS-4A", "A", "marcus@college.edu", "+15550102", dummy_encoding),
        ("STU103", "Chloe Chen", "CS-4B", "B", "chloe@college.edu", "+15550103", None), # Missing face
        ("STU104", "David Miller", "EE-2C", "C", "david@college.edu", "+15550104", dummy_encoding),
        ("STU105", "Sophia Martinez", "EE-2C", "C", "sophia@college.edu", "+15550105", None) # Missing face
    ]
    
    for s in students:
        success = database.add_student(s[0], s[1], s[2], s[3], s[4], s[5], s[6], None)
        if success:
            print(f"Added student: {s[1]}")
        else:
            print(f"Student {s[1]} already exists.")
            
    print("\nInjecting historical attendance logs...")
    
    today = datetime.now()
    
    # Let's seed history for the last 5 days
    # Days offset, and who was what status
    history = [
        # 4 days ago
        (-4, [
            ("STU101", "08:55:00", "Present", 94.2),
            ("STU102", "09:02:10", "Present", 89.5),
            ("STU103", "09:05:44", "Present", 100.0),
            ("STU104", "00:00:00", "Absent", 0.0),
            ("STU105", "09:12:00", "Present", 100.0)
        ]),
        # 3 days ago
        (-3, [
            ("STU101", "08:58:30", "Present", 95.1),
            ("STU102", "09:22:00", "Late", 86.4),
            ("STU103", "09:04:12", "Present", 100.0),
            ("STU104", "09:03:00", "Present", 92.1),
            ("STU105", "00:00:00", "Absent", 0.0)
        ]),
        # 2 days ago
        (-2, [
            ("STU101", "09:01:00", "Present", 93.3),
            ("STU102", "09:04:50", "Present", 87.2),
            ("STU103", "09:08:15", "Present", 100.0),
            ("STU104", "09:10:00", "Present", 90.8),
            ("STU105", "09:02:00", "Present", 100.0)
        ]),
        # 1 day ago (Yesterday)
        (-1, [
            ("STU101", "08:57:15", "Present", 96.0),
            ("STU102", "09:03:40", "Present", 88.9),
            ("STU103", "09:25:00", "Late", 100.0),
            ("STU104", "09:12:55", "Present", 91.5),
            ("STU105", "00:00:00", "Absent", 0.0)
        ]),
        # Today
        (0, [
            ("STU101", "08:59:00", "Present", 94.8),
            ("STU102", "09:05:12", "Present", 87.5),
            ("STU104", "09:14:00", "Present", 93.0)
            # STU103 and STU105 haven't checked in yet today
        ])
    ]
    
    for offset, logs in history:
        log_date = (today + timedelta(days=offset)).strftime('%Y-%m-%d')
        for student_id, log_time, status, conf in logs:
            database.mark_attendance(student_id, log_date, log_time, status, conf)
            
    print("\nInjection completed successfully!")

if __name__ == '__main__':
    inject()
