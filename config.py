import os
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "resolveai-production-super-secret-key-2026")
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "resolveai.db"))
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "t")

    # Initial Admin Bootstrap Configuration (Securely configured via environment)
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@campus.edu").strip()
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@Secure2026").strip()
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Campus System Administrator").strip()

    # Session & Security Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(hours=8)

    # Standard System Categorization
    DEPARTMENTS = [
        "IT & Network Infrastructure",
        "Hostel & Residential Facilities",
        "Campus Security & Safety",
        "Academic & Examination Affairs",
        "Finance & Accounts Office",
        "Cafeteria & Dining Services",
        "Estate & Maintenance Operations",
        "Transport & Logistics"
    ]

    PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    STATUSES = ["Submitted", "Assigned", "In Progress", "Resolved", "Closed"]

    ROLES = ["student", "staff", "admin"]

    @classmethod
    def is_gemini_configured(cls) -> bool:
        return bool(cls.GEMINI_API_KEY and len(cls.GEMINI_API_KEY) > 10)
