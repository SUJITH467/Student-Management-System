# Student Management System

A full-stack student management web app built with Flask, SQLAlchemy, SQLite, HTML, CSS, and JavaScript.

## Features
- Dashboard with totals for students, courses, and departments
- Student management with add, edit, delete, search, and view actions
- User authentication with signup and login
- Attendance tracking for students
- Optional Google Sheets export for attendance records
- Responsive UI with a modern sidebar and card-based layout
- SQLite database that is created and seeded automatically

## Project structure
student-management-system/
│
├── v1_app.py
├── v1_requirements.txt
├── database.db  (created automatically on first run)
│
├── templates/
│   ├── index.html
│   ├── students.html
│   ├── attendance.html
│   ├── login.html
│   └── signup.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
│
└── v1_README.md

## Installation

1. Clone or download the project files into a directory.

2. Create and activate a virtual environment:

On macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

3. Install dependencies:
```bash
pip install -r v1_requirements.txt
```

4. Run the application:
```bash
python v1_app.py
```

The Flask server will start in debug mode by default and listen on http://127.0.0.1:5000.

## Usage
Open the app in your browser:
- Dashboard: http://127.0.0.1:5000/
- Students: http://127.0.0.1:5000/students
- Attendance: http://127.0.0.1:5000/attendance
- Login: http://127.0.0.1:5000/login
- Signup: http://127.0.0.1:5000/signup

## Notes
- The database file database.db will be created automatically the first time you run the app.
- Sample departments, courses, and a default admin account are seeded automatically when the app starts.
- Google Sheets export is optional. To enable it, set the following environment variables:
  - GOOGLE_SHEET_ID
  - GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_INFO

## License
This project is provided as-is for learning and prototyping purposes.