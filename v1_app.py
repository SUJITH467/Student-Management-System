from flask import Flask, jsonify, request, render_template, abort, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import re
import os

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None
    Credentials = None

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "dev-secret-key-2026"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "database.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Models
class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "full_name": self.full_name, "email": self.email}


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50))
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    department = db.relationship("Department", backref="students")
    year = db.Column(db.Integer)
    dob = db.Column(db.Date)
    address = db.Column(db.String(500))
    student_type = db.Column(db.String(50), nullable=False, default="College")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "department": self.department.name if self.department else None,
            "department_id": self.department_id,
            "year": self.year,
            "dob": self.dob.strftime("%Y-%m-%d") if self.dob else None,
            "address": self.address,
            "student_type": self.student_type,
        }


class Attendance(db.Model):
    __tablename__ = "attendance"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    student = db.relationship("Student", backref=db.backref("attendances", cascade="all, delete-orphan"))
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    remarks = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.full_name if self.student else None,
            "date": self.date.strftime("%Y-%m-%d") if self.date else None,
            "status": self.status,
            "remarks": self.remarks,
        }


def apply_db_migrations():
    if db.engine.dialect.name == "sqlite":
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        if "students" in table_names:
            columns = [col["name"] for col in inspector.get_columns("students")]
            if "student_type" not in columns:
                with db.engine.connect() as connection:
                    connection.execute(text("ALTER TABLE students ADD COLUMN student_type VARCHAR(50) DEFAULT 'College';"))
                    connection.commit()


GSHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_gsheet_client():
    if not gspread or not Credentials:
        return None, "gspread or google-auth not installed"

    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        return None, "Google Sheet ID is not configured. Set GOOGLE_SHEET_ID."

    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    service_account_info = os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO")
    if not service_account_file and not service_account_info:
        return None, "Google Sheets credentials not configured. Set GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_INFO."

    try:
        if service_account_info:
            account_info = json.loads(service_account_info)
            credentials = Credentials.from_service_account_info(account_info, scopes=GSHEET_SCOPES)
        else:
            credentials = Credentials.from_service_account_file(service_account_file, scopes=GSHEET_SCOPES)
        client = gspread.authorize(credentials)
        return client, None
    except Exception as exc:
        return None, str(exc)


def get_attendance_worksheet():
    client, err = get_gsheet_client()
    if not client:
        return None, err

    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    try:
        sheet = client.open_by_key(sheet_id)
        try:
            worksheet = sheet.worksheet("Attendance")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title="Attendance", rows="1000", cols="10")
            worksheet.append_row(["ID", "Student ID", "Student Name", "Date", "Status", "Remarks"], value_input_option="USER_ENTERED")
        return worksheet, None
    except Exception as exc:
        return None, str(exc)


def append_attendance_to_sheet(attendance):
    worksheet, err = get_attendance_worksheet()
    if not worksheet:
        return False, err

    try:
        worksheet.append_row([
            attendance.id,
            attendance.student_id,
            attendance.student.full_name if attendance.student else None,
            attendance.date.strftime("%Y-%m-%d") if attendance.date else None,
            attendance.status,
            attendance.remarks or "",
        ], value_input_option="USER_ENTERED")
        return True, None
    except Exception as exc:
        return False, str(exc)


def export_all_attendance_to_sheet():
    worksheet, err = get_attendance_worksheet()
    if not worksheet:
        return False, err, 0

    records = Attendance.query.order_by(Attendance.date.asc()).all()
    if not records:
        return False, "No attendance records available to export.", 0

    rows = [
        [
            attendance.id,
            attendance.student_id,
            attendance.student.full_name if attendance.student else None,
            attendance.date.strftime("%Y-%m-%d") if attendance.date else None,
            attendance.status,
            attendance.remarks or "",
        ]
        for attendance in records
    ]
    try:
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")
        return True, None, len(rows)
    except Exception as exc:
        return False, str(exc), 0


# Initialize DB and seed
def init_db():
    db.create_all()
    apply_db_migrations()

    # Seed departments if none
    if Department.query.count() == 0:
        departments = ["Computer Science", "Mathematics", "Physics", "Biology", "Chemistry", "English"]
        for name in departments:
            db.session.add(Department(name=name))
        db.session.commit()

    # Seed courses if none
    if Course.query.count() == 0:
        courses = ["Intro to Programming", "Calculus I", "Physics I", "Biology I", "Chemistry I", "English Literature"]
        for name in courses:
            db.session.add(Course(name=name))
        db.session.commit()

    # Seed default user
    if User.query.count() == 0:
        default_user = User(full_name="Admin User", email="admin@example.com")
        default_user.set_password("Password123")
        db.session.add(default_user)
        db.session.commit()


@app.before_request
def before_request():
    init_db()


# Utility validation
EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def validate_student_data(data, for_update=False):
    errors = {}

    def check_required(key, label):
        if not for_update and not data.get(key):
            errors[key] = f"{label} is required."

    check_required("student_id", "Student ID")
    check_required("full_name", "Full Name")
    check_required("email", "Email")
    check_required("department_id", "Department")
    check_required("year", "Year")
    check_required("dob", "Date of birth")
    check_required("student_type", "Student Type")

    email = data.get("email")
    if email and not EMAIL_RE.match(email):
        errors["email"] = "Invalid email format."

    year = data.get("year")
    if year:
        try:
            year_int = int(year)
            if year_int < 1 or year_int > 10:
                errors["year"] = "Year must be between 1 and 10."
        except ValueError:
            errors["year"] = "Year must be an integer."

    phone = data.get("phone")
    if phone and not re.match(r"^[\d\-\+\s\(\)]{6,20}$", phone):
        errors["phone"] = "Invalid phone number."

    dob = data.get("dob")
    if dob:
        try:
            datetime.strptime(dob, "%Y-%m-%d")
        except ValueError:
            errors["dob"] = "Date of birth must be YYYY-MM-DD."

    # Department existence
    dep_id = data.get("department_id")
    if dep_id:
        try:
            dep_id_int = int(dep_id)
            if not Department.query.get(dep_id_int):
                errors["department_id"] = "Department not found."
        except ValueError:
            errors["department_id"] = "Invalid department id."

    return errors


def validate_attendance_data(data):
    errors = {}
    if not data.get("student_id"):
        errors["student_id"] = "Student is required."
    if not data.get("date"):
        errors["date"] = "Date is required."
    if not data.get("status"):
        errors["status"] = "Attendance status is required."
    elif data.get("status") not in ["Present", "Absent"]:
        errors["status"] = "Status must be Present or Absent."

    if data.get("student_id"):
        try:
            student_id_int = int(data.get("student_id"))
            if not Student.query.get(student_id_int):
                errors["student_id"] = "Student not found."
        except ValueError:
            errors["student_id"] = "Invalid student id."

    if data.get("date"):
        try:
            datetime.strptime(data.get("date"), "%Y-%m-%d")
        except ValueError:
            errors["date"] = "Date must be YYYY-MM-DD."

    return errors


# Frontend routes - all served by single index.html
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/students")
def students_page():
    return render_template("index.html")


@app.route("/attendance")
def attendance_page():
    return render_template("index.html")


@app.route("/login")
def login_page():
    return render_template("index.html")


@app.route("/signup")
def signup_page():
    return render_template("index.html")


@app.route("/logout", methods=["POST"])
def logout_page():
    session.clear()
    return jsonify({"status": "logged out"})


# API routes
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials."}), 401

    session["user_id"] = user.id
    session["user_name"] = user.full_name
    return jsonify({"user": user.to_dict()})


@app.route("/api/signup", methods=["POST"])
def api_signup():
    data = request.get_json() or {}
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    if not full_name or not email or not password or not confirm_password:
        return jsonify({"error": "All fields are required."}), 400
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email format."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 409

    user = User(full_name=full_name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    session["user_id"] = user.id
    session["user_name"] = user.full_name
    return jsonify({"user": user.to_dict()}), 201


@app.route("/api/dashboard")
def api_dashboard():
    total_students = Student.query.count()
    total_courses = Course.query.count()
    total_departments = Department.query.count()
    today = datetime.utcnow().date()
    today_present = Attendance.query.filter_by(date=today, status="Present").count()
    today_absent = Attendance.query.filter_by(date=today, status="Absent").count()
    return jsonify(
        {
            "total_students": total_students,
            "total_courses": total_courses,
            "total_departments": total_departments,
            "today_present": today_present,
            "today_absent": today_absent,
        }
    )


@app.route("/api/attendance", methods=["GET", "POST"])
def api_attendance():
    if request.method == "GET":
        student_id = request.args.get("student_id")
        date = request.args.get("date")
        query = Attendance.query.order_by(Attendance.date.desc())
        if student_id:
            try:
                query = query.filter_by(student_id=int(student_id))
            except ValueError:
                return jsonify({"error": "Invalid student id."}), 400
        if date:
            try:
                parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
                query = query.filter_by(date=parsed_date)
            except ValueError:
                return jsonify({"error": "Invalid date format."}), 400
        return jsonify([a.to_dict() for a in query.all()])

    data = request.get_json() or {}
    errors = validate_attendance_data(data)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        attendance = Attendance(
            student_id=int(data.get("student_id")),
            date=datetime.strptime(data.get("date"), "%Y-%m-%d").date(),
            status=data.get("status"),
            remarks=data.get("remarks", "").strip() if data.get("remarks") else None,
        )
        db.session.add(attendance)
        db.session.commit()

        sheet_saved, sheet_err = append_attendance_to_sheet(attendance)
        attendance_data = attendance.to_dict()
        if sheet_saved:
            attendance_data["sheet_status"] = "Saved to Google Sheets."
        else:
            attendance_data["sheet_status"] = sheet_err

        return jsonify(attendance_data), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"errors": {"attendance": "Attendance record conflict."}}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"errors": {"server": str(e)}}), 500


@app.route("/api/attendance/export", methods=["POST"])
def api_export_attendance():
    success, err, count = export_all_attendance_to_sheet()
    if not success:
        return jsonify({"error": err or "Failed to export attendance to Google Sheets."}), 500
    return jsonify({"message": f"Exported {count} attendance records to Google Sheets."}), 200


@app.route("/api/attendance/<int:attendance_id>", methods=["DELETE"])
def api_attendance_detail(attendance_id):
    attendance = Attendance.query.get(attendance_id)
    if not attendance:
        return jsonify({"error": "Attendance record not found."}), 404
    try:
        db.session.delete(attendance)
        db.session.commit()
        return jsonify({"message": "Attendance deleted."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"errors": {"server": str(e)}}), 500


@app.route("/api/departments")
def api_departments():
    deps = Department.query.order_by(Department.name).all()
    return jsonify([d.to_dict() for d in deps])


@app.route("/api/students", methods=["GET", "POST"])
def api_students():
    if request.method == "GET":
        search = request.args.get("search", "").strip()
        query = Student.query
        if search:
            like = f"%{search}%"
            query = query.filter(
                db.or_(
                    Student.student_id.ilike(like),
                    Student.full_name.ilike(like),
                    Student.email.ilike(like),
                    Student.phone.ilike(like),
                    Student.address.ilike(like),
                )
            )
        students = query.order_by(Student.full_name).all()
        return jsonify([s.to_dict() for s in students])

    # POST - create
    data = request.get_json() or {}
    errors = validate_student_data(data, for_update=False)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        dob_parsed = datetime.strptime(data.get("dob"), "%Y-%m-%d").date() if data.get("dob") else None
        student = Student(
            student_id=data.get("student_id").strip(),
            full_name=data.get("full_name").strip(),
            email=data.get("email").strip(),
            phone=data.get("phone").strip() if data.get("phone") else None,
            department_id=int(data.get("department_id")) if data.get("department_id") else None,
            year=int(data.get("year")) if data.get("year") else None,
            dob=dob_parsed,
            address=data.get("address").strip() if data.get("address") else None,
            student_type=data.get("student_type", "College"),
        )
        db.session.add(student)
        db.session.commit()
        return jsonify(student.to_dict()), 201
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"errors": {"student_id": "Student ID or email may already exist."}}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"errors": {"server": str(e)}}), 500


@app.route("/api/students/<int:student_id>", methods=["GET", "PUT", "DELETE"])
def api_student_detail(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found."}), 404

    if request.method == "GET":
        return jsonify(student.to_dict())

    if request.method == "PUT":
        data = request.get_json() or {}
        errors = validate_student_data(data, for_update=True)
        if errors:
            return jsonify({"errors": errors}), 400
        try:
            if data.get("student_id"):
                student.student_id = data.get("student_id").strip()
            if data.get("full_name"):
                student.full_name = data.get("full_name").strip()
            if data.get("email"):
                student.email = data.get("email").strip()
            if "phone" in data:
                student.phone = data.get("phone").strip() if data.get("phone") else None
            if "department_id" in data and data.get("department_id"):
                student.department_id = int(data.get("department_id"))
            if "year" in data and data.get("year"):
                student.year = int(data.get("year"))
            if "dob" in data and data.get("dob"):
                student.dob = datetime.strptime(data.get("dob"), "%Y-%m-%d").date()
            if "address" in data:
                student.address = data.get("address").strip() if data.get("address") else None
            if "student_type" in data and data.get("student_type"):
                student.student_type = data.get("student_type")

            db.session.commit()
            return jsonify(student.to_dict())
        except IntegrityError:
            db.session.rollback()
            return jsonify({"errors": {"student_id": "Student ID or email conflict."}}), 409
        except Exception as e:
            db.session.rollback()
            return jsonify({"errors": {"server": str(e)}}), 500

    if request.method == "DELETE":
        try:
            db.session.delete(student)
            db.session.commit()
            return jsonify({"message": "Deleted"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"errors": {"server": str(e)}}), 500


# Error handlers
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad request"}), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error"}), 500


if __name__ == "__main__":
    app.run(debug=True)