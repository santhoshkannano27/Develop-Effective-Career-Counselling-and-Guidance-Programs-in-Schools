"""
Career Counselling and Guidance Program for Schools
=====================================================
A web-based system that helps students discover suitable career paths
through a Holland Code (RIASEC) interest assessment, and gives school
counsellors a dashboard to track, filter and support every student.

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, g, jsonify
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "career_guidance.db")
COUNSELOR_PASSCODE = os.environ.get("COUNSELOR_PASSCODE", "counsellor123")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

# ----------------------------------------------------------------------
# RIASEC Model: Realistic, Investigative, Artistic, Social,
# Enterprising, Conventional  (Holland Occupational Themes)
# ----------------------------------------------------------------------
RIASEC_LABELS = {
    "R": "Realistic (Doers)",
    "I": "Investigative (Thinkers)",
    "A": "Artistic (Creators)",
    "S": "Social (Helpers)",
    "E": "Enterprising (Persuaders)",
    "C": "Conventional (Organizers)",
}

RIASEC_DESCRIPTIONS = {
    "R": "You enjoy hands-on, practical work — building, fixing, operating tools/machines, and working outdoors or with your hands.",
    "I": "You enjoy analysing, researching and solving complex problems using logic, data and scientific thinking.",
    "A": "You enjoy self-expression, original thinking, design and creativity in unstructured settings.",
    "S": "You enjoy helping, teaching, training and caring for others, and working closely with people.",
    "E": "You enjoy leading, persuading, selling, managing and starting new ventures.",
    "C": "You enjoy order, structure, data accuracy, and organizing information or processes.",
}

# 30 assessment statements, 5 per RIASEC dimension. Students rate 1-5.
QUIZ_QUESTIONS = [
    {"id": 1, "text": "I like repairing or assembling mechanical or electronic things.", "type": "R"},
    {"id": 2, "text": "I enjoy working with tools, machines, or equipment.", "type": "R"},
    {"id": 3, "text": "I prefer physical, outdoor, or hands-on activities over sitting at a desk.", "type": "R"},
    {"id": 4, "text": "I like building or constructing things (models, furniture, structures).", "type": "R"},
    {"id": 5, "text": "I enjoy activities like sports, gardening, or mechanics.", "type": "R"},

    {"id": 6, "text": "I enjoy solving puzzles, riddles, or logical problems.", "type": "I"},
    {"id": 7, "text": "I like conducting experiments or researching how things work.", "type": "I"},
    {"id": 8, "text": "I am curious about science, mathematics, or technology topics.", "type": "I"},
    {"id": 9, "text": "I enjoy analysing data to find patterns or draw conclusions.", "type": "I"},
    {"id": 10, "text": "I like reading about new scientific or technical discoveries.", "type": "I"},

    {"id": 11, "text": "I enjoy drawing, painting, writing, or other creative expression.", "type": "A"},
    {"id": 12, "text": "I like coming up with original ideas or unconventional solutions.", "type": "A"},
    {"id": 13, "text": "I enjoy music, drama, design, or other artistic activities.", "type": "A"},
    {"id": 14, "text": "I prefer flexible, unstructured tasks over strict routines.", "type": "A"},
    {"id": 15, "text": "I like expressing my feelings and ideas through creative work.", "type": "A"},

    {"id": 16, "text": "I enjoy helping classmates or friends understand difficult topics.", "type": "S"},
    {"id": 17, "text": "I like volunteering, tutoring, or caring for others.", "type": "S"},
    {"id": 18, "text": "I am good at listening to and comforting people.", "type": "S"},
    {"id": 19, "text": "I enjoy working in teams and building relationships.", "type": "S"},
    {"id": 20, "text": "I care deeply about community service and social causes.", "type": "S"},

    {"id": 21, "text": "I enjoy persuading others or presenting ideas to a group.", "type": "E"},
    {"id": 22, "text": "I like taking charge and leading projects or teams.", "type": "E"},
    {"id": 23, "text": "I am interested in starting my own business someday.", "type": "E"},
    {"id": 24, "text": "I enjoy competition and setting ambitious goals.", "type": "E"},
    {"id": 25, "text": "I like negotiating, selling, or convincing people of my viewpoint.", "type": "E"},

    {"id": 26, "text": "I like organizing files, schedules, or data accurately.", "type": "C"},
    {"id": 27, "text": "I enjoy following clear procedures and structured routines.", "type": "C"},
    {"id": 28, "text": "I am good at working with numbers, spreadsheets, or records.", "type": "C"},
    {"id": 29, "text": "I prefer clearly defined tasks with specific instructions.", "type": "C"},
    {"id": 30, "text": "I enjoy proofreading, checking accuracy, or managing details.", "type": "C"},
]

# Career map keyed by 2-letter dominant RIASEC code (order-independent)
CAREER_MAP = {
    "RI": ["Mechanical Engineer", "Civil Engineer", "Aerospace Technician", "Robotics Engineer"],
    "RA": ["Industrial Designer", "Architect", "Automotive Designer", "Set/Production Designer"],
    "RS": ["Paramedic", "Physical Education Teacher", "Firefighter", "Athletic Trainer"],
    "RE": ["Construction Manager", "Military Officer", "Agricultural Manager", "Pilot"],
    "RC": ["Surveyor", "Quality Control Technician", "Electrician", "Drafting Technician"],
    "IR": ["Biomedical Engineer", "Environmental Scientist", "Aerospace Engineer", "Geologist"],
    "IA": ["Research Scientist", "Data Scientist", "Astronomer", "UX Researcher"],
    "IS": ["Physician", "Psychologist", "Epidemiologist", "Genetic Counselor"],
    "IE": ["Actuary", "Management Consultant", "Biotech Entrepreneur", "Financial Analyst"],
    "IC": ["Statistician", "Lab Technician", "Pharmacist", "Systems Analyst"],
    "AR": ["Industrial/Product Designer", "Landscape Architect", "Game Designer", "Animator"],
    "AI": ["UX/UI Designer", "Film Director", "Architect", "Fashion Technologist"],
    "AS": ["Art Therapist", "Music Teacher", "Museum Educator", "Drama Therapist"],
    "AE": ["Advertising Creative Director", "Fashion Designer", "Content Strategist", "Brand Manager"],
    "AC": ["Graphic Designer", "Editor/Publisher", "Interior Designer", "Photographer"],
    "SR": ["Occupational Therapist", "Recreation Therapist", "Coach", "Park Ranger Educator"],
    "SI": ["Psychologist", "Speech Therapist", "School Counselor", "Nurse"],
    "SA": ["Teacher", "Social Worker", "Child Development Specialist", "Drama/Music Therapist"],
    "SE": ["HR Manager", "Nonprofit Director", "Public Relations Specialist", "Corporate Trainer"],
    "SC": ["School Administrator", "Healthcare Administrator", "Case Manager", "Career Counselor"],
    "ER": ["Real Estate Developer", "Sales Engineer", "Entrepreneur (trades)", "Operations Manager"],
    "EI": ["Management Consultant", "Investment Banker", "Product Manager", "Business Analyst"],
    "EA": ["Marketing Director", "Public Relations Executive", "Event Planner", "Media Producer"],
    "ES": ["Sales Manager", "Politician/Public Servant", "Recruiter", "Fundraising Director"],
    "EC": ["Business Manager", "Entrepreneur", "Insurance Agent", "Retail Manager"],
    "CR": ["Logistics Coordinator", "Bank Teller/Officer", "Inventory Manager", "Quality Assurance"],
    "CI": ["Accountant", "Auditor", "Actuarial Analyst", "Financial Planner"],
    "CA": ["Technical Writer", "Librarian", "Copy Editor", "Archivist"],
    "CS": ["Human Resources Coordinator", "Medical Records Manager", "Administrative Officer", "Paralegal"],
    "CE": ["Accountant/Finance Manager", "Office Manager", "Bank Manager", "Compliance Officer"],
}


# ----------------------------------------------------------------------
# Database helpers
# ----------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            grade TEXT,
            email TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            score_r INTEGER, score_i INTEGER, score_a INTEGER,
            score_s INTEGER, score_e INTEGER, score_c INTEGER,
            top_code TEXT,
            recommended_careers TEXT,
            taken_at TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id)
        );

        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            author TEXT,
            note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id)
        );

        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            purpose TEXT,
            requested_slot TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id)
        );
        """
    )
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# Auth helper (simple passcode-gated counselor area)
# ----------------------------------------------------------------------
def counselor_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_counselor"):
            flash("Please sign in as a counselor to view this page.", "warning")
            return redirect(url_for("counselor_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


# ----------------------------------------------------------------------
# Public / student routes
# ----------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/quiz/start", methods=["GET", "POST"])
def quiz_start():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        grade = request.form.get("grade", "").strip()
        email = request.form.get("email", "").strip()
        if not name:
            flash("Please enter your name to begin.", "danger")
            return redirect(url_for("quiz_start"))

        db = get_db()
        cur = db.execute(
            "INSERT INTO students (name, grade, email, created_at) VALUES (?, ?, ?, ?)",
            (name, grade, email, datetime.utcnow().isoformat()),
        )
        db.commit()
        session["student_id"] = cur.lastrowid
        session["student_name"] = name
        return redirect(url_for("quiz_take"))

    return render_template("quiz_start.html")


@app.route("/quiz/take")
def quiz_take():
    if "student_id" not in session:
        return redirect(url_for("quiz_start"))
    return render_template("quiz_take.html", questions=QUIZ_QUESTIONS)


@app.route("/quiz/submit", methods=["POST"])
def quiz_submit():
    if "student_id" not in session:
        return redirect(url_for("quiz_start"))

    scores = {k: 0 for k in "RIASEC"}
    for q in QUIZ_QUESTIONS:
        val = request.form.get(f"q{q['id']}")
        try:
            val = int(val)
        except (TypeError, ValueError):
            val = 3  # neutral default if unanswered
        scores[q["type"]] += val

    # Determine top two dimensions -> Holland code
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_code = "".join([ranked[0][0], ranked[1][0]])
    careers = CAREER_MAP.get(top_code) or CAREER_MAP.get(top_code[::-1]) or []

    db = get_db()
    db.execute(
        """INSERT INTO assessments
           (student_id, score_r, score_i, score_a, score_s, score_e, score_c,
            top_code, recommended_careers, taken_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session["student_id"], scores["R"], scores["I"], scores["A"],
            scores["S"], scores["E"], scores["C"], top_code,
            ", ".join(careers), datetime.utcnow().isoformat(),
        ),
    )
    db.commit()

    session["last_scores"] = scores
    session["last_top_code"] = top_code
    session["last_careers"] = careers
    return redirect(url_for("quiz_results"))


@app.route("/quiz/results")
def quiz_results():
    if "last_top_code" not in session:
        return redirect(url_for("quiz_start"))

    scores = session["last_scores"]
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return render_template(
        "results.html",
        scores=scores,
        ranked=ranked,
        labels=RIASEC_LABELS,
        descriptions=RIASEC_DESCRIPTIONS,
        top_code=session["last_top_code"],
        careers=session["last_careers"],
        student_name=session.get("student_name", "Student"),
    )


@app.route("/appointment/request", methods=["GET", "POST"])
def appointment_request():
    if "student_id" not in session:
        flash("Please take the assessment first so a counselor has context.", "info")
        return redirect(url_for("quiz_start"))

    if request.method == "POST":
        purpose = request.form.get("purpose", "").strip()
        slot = request.form.get("requested_slot", "").strip()
        db = get_db()
        db.execute(
            """INSERT INTO appointments (student_id, purpose, requested_slot, status, created_at)
               VALUES (?, ?, ?, 'Pending', ?)""",
            (session["student_id"], purpose, slot, datetime.utcnow().isoformat()),
        )
        db.commit()
        flash("Your appointment request has been sent to the counseling office.", "success")
        return redirect(url_for("index"))

    return render_template("appointment_request.html")


# ----------------------------------------------------------------------
# Counselor routes
# ----------------------------------------------------------------------
@app.route("/counselor/login", methods=["GET", "POST"])
def counselor_login():
    if request.method == "POST":
        code = request.form.get("passcode", "")
        if code == COUNSELOR_PASSCODE:
            session["is_counselor"] = True
            flash("Signed in successfully.", "success")
            nxt = request.args.get("next") or url_for("counselor_dashboard")
            return redirect(nxt)
        flash("Incorrect passcode.", "danger")
    return render_template("counselor_login.html")


@app.route("/counselor/logout")
def counselor_logout():
    session.pop("is_counselor", None)
    return redirect(url_for("index"))


@app.route("/counselor/dashboard")
@counselor_required
def counselor_dashboard():
    db = get_db()
    students = db.execute(
        """
        SELECT s.id, s.name, s.grade, s.email, s.created_at,
               a.top_code, a.recommended_careers, a.taken_at
        FROM students s
        LEFT JOIN (
            SELECT student_id, top_code, recommended_careers, taken_at,
                   ROW_NUMBER() OVER (PARTITION BY student_id ORDER BY taken_at DESC) rn
            FROM assessments
        ) a ON a.student_id = s.id AND a.rn = 1
        ORDER BY s.created_at DESC
        """
    ).fetchall()

    total_students = len(students)
    assessed = len([s for s in students if s["top_code"]])

    pending_appts = db.execute(
        """SELECT ap.id, ap.purpose, ap.requested_slot, ap.status, ap.created_at,
                  s.name AS student_name
           FROM appointments ap JOIN students s ON s.id = ap.student_id
           WHERE ap.status = 'Pending'
           ORDER BY ap.created_at DESC"""
    ).fetchall()

    code_counts = {}
    for s in students:
        if s["top_code"]:
            code_counts[s["top_code"]] = code_counts.get(s["top_code"], 0) + 1

    return render_template(
        "dashboard.html",
        students=students,
        total_students=total_students,
        assessed=assessed,
        pending_appts=pending_appts,
        code_counts=code_counts,
    )


@app.route("/counselor/student/<int:student_id>")
@counselor_required
def counselor_student_detail(student_id):
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("counselor_dashboard"))

    assessments = db.execute(
        "SELECT * FROM assessments WHERE student_id = ? ORDER BY taken_at DESC",
        (student_id,),
    ).fetchall()
    notes = db.execute(
        "SELECT * FROM notes WHERE student_id = ? ORDER BY created_at DESC",
        (student_id,),
    ).fetchall()
    appts = db.execute(
        "SELECT * FROM appointments WHERE student_id = ? ORDER BY created_at DESC",
        (student_id,),
    ).fetchall()

    return render_template(
        "student_detail.html",
        student=student,
        assessments=assessments,
        notes=notes,
        appts=appts,
        labels=RIASEC_LABELS,
    )


@app.route("/counselor/student/<int:student_id>/note", methods=["POST"])
@counselor_required
def add_note(student_id):
    author = request.form.get("author", "Counselor").strip() or "Counselor"
    note_text = request.form.get("note", "").strip()
    if note_text:
        db = get_db()
        db.execute(
            "INSERT INTO notes (student_id, author, note, created_at) VALUES (?, ?, ?, ?)",
            (student_id, author, note_text, datetime.utcnow().isoformat()),
        )
        db.commit()
        flash("Note added.", "success")
    return redirect(url_for("counselor_student_detail", student_id=student_id))


@app.route("/counselor/appointment/<int:appt_id>/status", methods=["POST"])
@counselor_required
def update_appointment_status(appt_id):
    new_status = request.form.get("status", "Pending")
    db = get_db()
    db.execute("UPDATE appointments SET status = ? WHERE id = ?", (new_status, appt_id))
    db.commit()
    return redirect(url_for("counselor_dashboard"))


# ----------------------------------------------------------------------
# JSON API (optional, for integration with other school systems)
# ----------------------------------------------------------------------
@app.route("/api/careers/<code>")
def api_career_lookup(code):
    code = code.upper()
    careers = CAREER_MAP.get(code) or CAREER_MAP.get(code[::-1]) or []
    return jsonify({"code": code, "careers": careers})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
