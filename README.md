# Career Compass — Career Counselling & Guidance Program for Schools

A lightweight, self-contained web application that helps schools run an
effective career counselling program:

- **Students** take a 30-item Holland Code (RIASEC) interest assessment and
  instantly get a personalized breakdown plus suggested career paths.
- **Counselors** get a live dashboard listing every student, their latest
  results, notes, and appointment requests — no spreadsheets required.

Built with Python (Flask) + SQLite, so it runs anywhere with zero external
services or paid APIs.

## Features

- 30-question RIASEC (Realistic / Investigative / Artistic / Social /
  Enterprising / Conventional) interest assessment with a live progress bar
- Automatic scoring engine that maps each student's top two interest areas
  to a Holland Code (e.g. "IA") and a curated list of matching careers
  (30 two-letter code combinations covered, 120+ careers)
- Visual results page with per-dimension score bars and explanations
- Student appointment request form
- Passcode-protected counselor dashboard with:
  - Roster of all students and their latest results
  - Pending appointment queue with confirm/decline actions
  - Per-student detail page: full assessment history, notes log, appointments
  - Ability for counselors to add follow-up notes per student
- Small JSON API endpoint (`/api/careers/<code>`) for integrating the
  career map into other school tools

## Project Structure

```
career-guidance-system/
├── app.py                     # Flask app: routes, scoring engine, career map, DB
├── init_db.py                 # Standalone script to (re)create the database
├── requirements.txt
├── data/                      # SQLite database lives here (created on first run)
├── static/
│   └── css/style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── quiz_start.html
    ├── quiz_take.html
    ├── results.html
    ├── appointment_request.html
    ├── counselor_login.html
    ├── dashboard.html
    └── student_detail.html
```

## Setup

1. **Install dependencies** (Python 3.9+ recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run the app** (this also creates the database automatically on first run):

   ```bash
   python app.py
   ```

3. Open **http://127.0.0.1:5000** in your browser.

4. **Counselor sign-in passcode** defaults to `counsellor123`. Change it
   before deploying by setting an environment variable:

   ```bash
   export COUNSELOR_PASSCODE="your-secure-passcode"
   export SECRET_KEY="a-long-random-string"
   ```

## How the Scoring Works

The assessment is based on **John Holland's RIASEC theory**, one of the
most widely used frameworks in career guidance. Each of the 30 statements
belongs to one of six interest types; students rate each 1–5. The two
types with the highest totals form the student's two-letter Holland Code
(e.g. a student strong in Investigative and Artistic gets **"IA"**), which
is then matched against a built-in career map covering all 30 possible
code pairings.

You can freely edit `CAREER_MAP` and `QUIZ_QUESTIONS` in `app.py` to match
your school's local curriculum, subject offerings, or regional job market.

## Customization Ideas

- Add subject/elective recommendations alongside each career suggestion
- Export a student's results and notes to PDF for their file
- Add parent/guardian view with a shareable results link
- Connect `COUNSELOR_PASSCODE` to your school's existing staff login (SSO)
- Add multi-language support for the assessment text

## Deployment Notes

This app uses Flask's built-in dev server, which is fine for a classroom
demo or small pilot. For a real school rollout, deploy behind a production
WSGI server (e.g. `gunicorn app:app`) and a reverse proxy (e.g. Nginx), and
switch `data/career_guidance.db` to a persistent volume or migrate to
PostgreSQL/MySQL for multi-user concurrency at scale.

## License

Free to use and adapt for educational purposes.
