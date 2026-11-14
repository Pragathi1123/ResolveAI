# ResolveAI &mdash; AI-Based Complaint Management and Resolution Assistant

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask 3.x](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![SQLite 3](https://img.shields.io/badge/Database-SQLite-003B57.svg)](https://www.sqlite.org/)
[![Werkzeug Security](https://img.shields.io/badge/Security-Werkzeug%20RBAC-red.svg)](https://werkzeug.palletsprojects.com/)
[![Google Gemini API](https://img.shields.io/badge/AI-Google%20Gemini-4285F4.svg)](https://ai.google.dev/)
[![Chart.js](https://img.shields.io/badge/Charts-Chart.js-FF6384.svg)](https://www.chartjs.org/)

**ResolveAI** is an advanced Agentic AI system that automates the lifecycle of student and campus grievances: understanding natural language complaints, assessing urgency and impact, intelligently routing to appropriate campus departments, providing real-time tracking with full agent audit trails, and generating verified resolution closure summaries.

---

## 🔐 Secure Role-Based Authentication (RBAC)

ResolveAI features a multi-tiered role-based authentication and authorization system using Werkzeug password hashing, secure Flask session management, and CSRF protection.

### Three User Roles

| Role | Access & Permissions | Public Registration? |
| :--- | :--- | :--- |
| **Student** | Submit grievances (auto-linked to student profile), view personal submission history, track status of their own tickets. Cannot view other students' tickets. | **Yes** via `/register` (Name, College Email, USN/ID, Password). |
| **Staff** | View tickets assigned to their department, update permitted statuses (`In Progress`, `Resolved`), record verified resolution notes. Cannot access admin functionality or other departments. | **No**. Provisioned exclusively by authenticated administrators via `/admin/staff`. |
| **Admin** | Full system oversight: view and filter all campus complaints, inspect agent traces, access analytics, create and deactivate staff accounts. | **No**. Bootstrapped securely via environment variables (`ADMIN_EMAIL`, `ADMIN_PASSWORD`). |

### Pre-Configured Seed Demo Credentials

For quick evaluation and testing across all three roles:

| Role | Email | Password | Details |
| :--- | :--- | :--- | :--- |
| **Student** | `aarav.sharma@campus.edu` | `Student@Secure2026` | USN: `1MS21CS001` |
| **Student** | `priya.nair@campus.edu` | `Student@Secure2026` | USN: `1MS21IS045` |
| **Staff** | `vikram.staff@campus.edu` | `Staff@Secure2026` | Senior Network Engineer (IT & Network) |
| **Staff** | `meera.staff@campus.edu` | `Staff@Secure2026` | Accounts Reconciliation Desk (Finance) |
| **Admin** | `admin@campus.edu` | `Admin@Secure2026` | System Administrator |

---

## 🏛️ System Architecture

ResolveAI uses a modular multi-agent pipeline coordinated by a Central Orchestrator:

```
[ Student / User Intake ]
           │
           ▼
[ Central Orchestrator ]
           │
           ├─► 1. Complaint Understanding Agent (Intent, Category, Location, Scope, Urgency Cues)
           │
           ├─► 2. Priority Assessment Agent (Urgency, Severity, Impact -> CRITICAL / HIGH / MEDIUM / LOW)
           │
           ├─► 3. Department Assignment Agent (Department Routing, Staff Designation, SLA Assignment)
           │
           ├─► 4. SQLite Persistence & Unique Ticket ID Generation (RES-YYYYMMDD-XXXXX)
           │
           └─► 5. Resolution Tracking Agent (Status Lifecycle, Audit Logs & Verified Closure Summaries)
```

---

## 🤖 The 5 Core Agents

| Agent Name | Primary Responsibility | Output Artifact |
| :--- | :--- | :--- |
| **1. Complaint Understanding Agent** | Analyzes natural language descriptions, extracts key issues, specific location, affected cohort scope, and urgency indicators. | Structured Semantic JSON (`category`, `issue_summary`, `extracted_location`, `urgency_cues`) |
| **2. Priority Assessment Agent** | Evaluates risk across 3 dimensions: Urgency (1-5), Severity (1-5), and Impact (1-5). | `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW` priority + target SLA hours |
| **3. Department Assignment Agent** | Maps grievance to one of 8 university departments, designates field staff roles, and outlines initial action plans. | Target Department (`IT`, `Estate`, `Hostel`, `Security`, `Food`, `Finance`, `Academic`, `Transport`) |
| **4. Resolution Tracking Agent** | Manages status updates (`Submitted` &rarr; `Assigned` &rarr; `In Progress` &rarr; `Resolved` &rarr; `Closed`) and generates formal AI closure summaries once authorized resolution notes are provided. | Lifecycle Milestones & Verified AI Closure Summaries |
| **5. Central Orchestrator** | Coordinates sequential agent execution, validates schema inputs/outputs, logs step-by-step activity traces, and handles fallbacks. | End-to-end ticket lifecycle dispatch & audit logs |

---

## 💻 Tech Stack

- **Backend:** Python 3.10+, Flask 3.x
- **Frontend:** HTML5, Modern CSS3 (Dark Navy & Electric Blue Theme), Vanilla JavaScript (Fetch API)
- **Database:** SQLite3 with relational indices (`users`, `complaints`, `agent_logs`, `status_history`)
- **Security:** Werkzeug password hashing (scrypt), HTTP-only SameSite cookies, CSRF protection, Role-Based Access Control decorators
- **AI Engine:** Google Gemini API (`google-genai` SDK) with **intelligent rule-based local fallbacks**
- **Visualization:** Chart.js 4.x for real-time dashboard analytics

---

## 📁 Project Structure

```
d:\ResolveAI\
├── app.py                     # Flask application entry point, auth & API routes
├── auth.py                    # Session helpers, CSRF validation, and @login_required / @role_required
├── config.py                  # Configuration, admin bootstrap, & environment variables
├── requirements.txt           # Python dependencies
├── .env                       # Local environment file (API keys & admin credentials)
├── .env.example               # Example environment template
├── test_auth_e2e.py           # Comprehensive Role-Based Auth & Security test suite
├── test_e2e.py                # Main end-to-end integration test suite
├── database/
│   ├── __init__.py
│   ├── db.py                  # SQLite schema, migrations, user & complaint functions
│   └── seed_data.py           # Seed users (Student, Staff, Admin) and sample complaints
├── agents/
│   ├── __init__.py
│   ├── base_agent.py          # Gemini API wrapper, JSON parsing & fallback handler
│   ├── understanding_agent.py # Complaint Understanding Agent
│   ├── priority_agent.py      # Priority Assessment Agent
│   ├── assignment_agent.py    # Department Assignment Agent
│   ├── tracking_agent.py      # Resolution Tracking Agent
│   └── orchestrator.py        # Central Orchestrator
├── templates/
│   ├── base.html              # Dark navy navigation header, dynamic user chip & footer
│   ├── login.html             # Secure login form with 1-click demo role selector
│   ├── register.html          # Public student registration form
│   ├── student_dashboard.html # Student portal: personal submissions & live tracking
│   ├── staff_dashboard.html   # Staff portal: department queue & resolution modal
│   ├── admin_staff.html       # Admin staff directory: create & deactivate staff
│   ├── submit.html            # Grievance intake with 1-click sample demo buttons
│   ├── track.html             # Ticket tracking timeline & agent reasoning trace
│   ├── admin.html             # Admin command center, filters, and resolution modal
│   ├── analytics.html         # Chart.js metrics and global agent activity feed
│   └── error.html             # 403 / 404 modern error dialog
└── static/
    ├── css/
    │   └── style.css          # Theme stylesheet, badges, responsive layout
    └── js/
        ├── submit.js          # Form handling & animated agent pipeline visualizer
        ├── track.js           # Live timeline tracking & agent log renderer
        ├── admin.js           # Table filtering & status resolution updater
        └── analytics.js       # Chart.js initialization & data loaders
```

---

## 🚀 Quickstart Guide

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
The system automatically initializes an admin user based on `.env`:
```ini
ADMIN_EMAIL=admin@campus.edu
ADMIN_PASSWORD=Admin@Secure2026
ADMIN_NAME=Campus System Administrator
```
To enable Google Gemini AI, add your API key in `.env`:
```ini
GEMINI_API_KEY=your_google_gemini_api_key_here
```

### 3. Run the Automated Test Suites
Run the RBAC security tests:
```powershell
python test_auth_e2e.py
```
Run the unified application tests:
```powershell
python test_e2e.py
```

### 4. Start the Application Server
```powershell
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```
You will be directed to the Sign In page where you can log in as a Student, Staff, or Administrator, or register a new student account.
