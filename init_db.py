"""Initialize (or reset) the SQLite database for the Career Guidance System.

Usage:
    python init_db.py
"""
from app import init_db

if __name__ == "__main__":
    init_db()
    print("Database initialized at data/career_guidance.db")
