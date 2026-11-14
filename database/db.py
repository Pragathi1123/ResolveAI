import sqlite3
import json
import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional, Tuple
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

logger = logging.getLogger("ResolveAI.Database")

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(Config.DATABASE_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db_connection()
    with conn:
        # 1. Users Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student', 'staff', 'admin')),
                student_id TEXT,
                department TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Complaints Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                student_name TEXT NOT NULL,
                student_email TEXT NOT NULL,
                student_user_id INTEGER,
                assigned_staff_id INTEGER,
                subject TEXT NOT NULL,
                raw_description TEXT NOT NULL,
                location TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                severity_score INTEGER DEFAULT 1,
                department TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Submitted',
                assigned_staff_role TEXT,
                estimated_sla_hours INTEGER DEFAULT 24,
                resolution_notes TEXT,
                closure_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (student_user_id) REFERENCES users(id),
                FOREIGN KEY (assigned_staff_id) REFERENCES users(id)
            )
        """)

        # 3. Agent Logs Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                action TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                reasoning TEXT,
                execution_status TEXT DEFAULT 'SUCCESS',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Status History Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                updated_by TEXT NOT NULL,
                notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Safe Migration for existing databases: check for student_user_id and assigned_staff_id
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(complaints)")
        columns = [row["name"] for row in cursor.fetchall()]

        if "student_user_id" not in columns:
            cursor.execute("ALTER TABLE complaints ADD COLUMN student_user_id INTEGER REFERENCES users(id)")
            logger.info("Migrated complaints table: added student_user_id column.")

        if "assigned_staff_id" not in columns:
            cursor.execute("ALTER TABLE complaints ADD COLUMN assigned_staff_id INTEGER REFERENCES users(id)")
            logger.info("Migrated complaints table: added assigned_staff_id column.")

        # Indexes for fast querying
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_ticket_id ON complaints(ticket_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_department ON complaints(department)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_priority ON complaints(priority)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_student_user ON complaints(student_user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_assigned_staff ON complaints(assigned_staff_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_ticket ON agent_logs(ticket_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status_history_ticket ON status_history(ticket_id)")

    conn.close()

    # Bootstrap administrator securely if configured
    bootstrap_admin()

def bootstrap_admin():
    """
    Bootstraps the initial system administrator from environment variables if not already existing.
    Ensures no hardcoded default passwords are used.
    """
    admin_email = Config.ADMIN_EMAIL
    admin_password = Config.ADMIN_PASSWORD
    admin_name = Config.ADMIN_NAME

    if not admin_email or not admin_password:
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    admin_exists = cursor.fetchone()

    if not admin_exists:
        try:
            pwd_hash = generate_password_hash(admin_password)
            with conn:
                conn.execute("""
                    INSERT INTO users (name, email, password_hash, role, is_active)
                    VALUES (?, ?, ?, 'admin', 1)
                """, (admin_name, admin_email.lower(), pwd_hash))
            logger.info(f"Initialized secure bootstrap admin account: {admin_email}")
        except Exception as e:
            logger.error(f"Error bootstrapping admin user: {e}")

    conn.close()

def generate_ticket_id() -> str:
    now_str = datetime.datetime.now().strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:5].upper()
    return f"RES-{now_str}-{short_uuid}"

def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    if row is None:
        return {}
    return dict(row)

# ---------------------------------------------------------
# User Management & Authentication Functions
# ---------------------------------------------------------
def create_user(
    name: str,
    email: str,
    password: str,
    role: str,
    student_id: Optional[str] = None,
    department: Optional[str] = None,
    is_active: int = 1
) -> int:
    """
    Creates a new user with hashed password.
    Raises ValueError on invalid role or duplicate email.
    """
    role = role.strip().lower()
    if role not in Config.ROLES:
        raise ValueError(f"Invalid user role '{role}'. Allowed roles: {Config.ROLES}")

    email_clean = email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise ValueError("A valid email address is required.")

    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE", (email_clean,))
    if cursor.fetchone():
        conn.close()
        raise ValueError(f"An account with email '{email_clean}' already exists.")

    password_hash = generate_password_hash(password)
    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with conn:
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, student_id, department, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name.strip(),
            email_clean,
            password_hash,
            role,
            student_id.strip() if student_id else None,
            department.strip() if department else None,
            1 if is_active else 0,
            now_iso
        ))
        user_id = cursor.lastrowid

    conn.close()
    return user_id

def get_user_by_id(user_id: int, include_password: bool = False) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = row_to_dict(row)
    if not include_password and "password_hash" in d:
        del d["password_hash"]
    return d

def get_user_by_email(email: str, include_password: bool = False) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = row_to_dict(row)
    if not include_password and "password_hash" in d:
        del d["password_hash"]
    return d

def authenticate_user(email: str, password: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Authenticates user credentials.
    Returns (user_dict, None) on success.
    Returns (None, error_message) on failure.
    """
    if not email or not password:
        return None, "Email and password are required."

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip().lower(),))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None, "Invalid email or password."

    user = row_to_dict(row)

    if not user.get("is_active"):
        return None, "Account is deactivated. Please contact an administrator."

    if not check_password_hash(user["password_hash"], password):
        return None, "Invalid email or password."

    # Return safe user dictionary without password hash
    del user["password_hash"]
    return user, None

def update_user(user_id: int, **kwargs) -> bool:
    """
    Updates user fields (e.g. name, department, student_id, is_active, password).
    """
    conn = get_db_connection()
    allowed_fields = {"name", "student_id", "department", "is_active", "password"}
    updates = []
    params = []

    for k, v in kwargs.items():
        if k in allowed_fields:
            if k == "password":
                updates.append("password_hash = ?")
                params.append(generate_password_hash(v))
            else:
                updates.append(f"{k} = ?")
                params.append(v)

    if not updates:
        conn.close()
        return False

    params.append(user_id)
    with conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        success = cursor.rowcount > 0

    conn.close()
    return success

def set_user_active_status(user_id: int, is_active: bool) -> bool:
    """
    Activates or deactivates a user account.
    """
    return update_user(user_id, is_active=1 if is_active else 0)


def get_staff_by_department(department: str, active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Retrieves all staff members belonging to a given department.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT id, name, email, department, role, is_active FROM users WHERE role = 'staff' AND department = ?"
    if active_only:
        query += " AND is_active = 1"
    query += " ORDER BY name ASC"
    cursor.execute(query, (department.strip(),))
    rows = cursor.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

def assign_complaint(
    ticket_id: str,
    department: str,
    staff_id: int,
    assigned_by: str,
    notes: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Assigns or reassigns a complaint to a department and specific active staff officer.
    Validates staff department membership and updates lifecycle status to 'Assigned'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Fetch complaint
    cursor.execute("SELECT * FROM complaints WHERE ticket_id = ? COLLATE NOCASE", (ticket_id.strip(),))
    comp_row = cursor.fetchone()
    if not comp_row:
        conn.close()
        return False, f"Ticket '{ticket_id}' not found."

    old_status = comp_row["status"]
    old_dept = comp_row["department"]
    old_staff_id = comp_row["assigned_staff_id"]

    # 2. Fetch and validate staff member
    cursor.execute("SELECT * FROM users WHERE id = ?", (staff_id,))
    staff_row = cursor.fetchone()
    if not staff_row:
        conn.close()
        return False, f"Staff member ID {staff_id} not found."

    staff = row_to_dict(staff_row)
    if staff["role"] != "staff":
        conn.close()
        return False, f"User '{staff['name']}' is not a staff member."

    if not staff["is_active"]:
        conn.close()
        return False, f"Staff member '{staff['name']}' is currently deactivated."

    if staff.get("department") != department.strip():
        conn.close()
        return False, f"Department mismatch: Staff '{staff['name']}' belongs to '{staff.get('department')}', not '{department}'."

    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # If the complaint was 'Submitted' or if reassigning, set status to 'Assigned'
    new_status = "Assigned" if old_status in ("Submitted", "Assigned") else old_status

    with conn:
        conn.execute("""
            UPDATE complaints
            SET department = ?, assigned_staff_id = ?, assigned_staff_role = ?,
                status = ?, updated_at = ?
            WHERE ticket_id = ? COLLATE NOCASE
        """, (department.strip(), staff["id"], staff["name"], new_status, now_iso, ticket_id.strip()))

        # Add to status_history
        action_detail = f"Assigned to {staff['name']} ({department.strip()}) by {assigned_by}."
        if notes and notes.strip():
            action_detail += f" Notes: {notes.strip()}"

        conn.execute("""
            INSERT INTO status_history (ticket_id, old_status, new_status, updated_by, notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticket_id.strip(), old_status, new_status, assigned_by, action_detail, now_iso))

        # Add to agent_logs
        str_input = json.dumps({
            "target_department": department.strip(),
            "target_staff_id": staff["id"],
            "target_staff_name": staff["name"],
            "assigned_by": assigned_by,
            "admin_notes": notes or ""
        }, indent=2)

        str_output = json.dumps({
            "status": new_status,
            "department": department.strip(),
            "assigned_staff_id": staff["id"],
            "assigned_staff_name": staff["name"]
        }, indent=2)

        reasoning = (
            f"Admin {assigned_by} assigned complaint to {staff['name']} in department '{department.strip()}'. "
            f"Staff department membership verified."
        )

        conn.execute("""
            INSERT INTO agent_logs (ticket_id, agent_name, action, input_data, output_data, reasoning, execution_status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticket_id.strip(), "Central Orchestrator", "Admin Staff Assignment", str_input, str_output, reasoning, "SUCCESS", now_iso))

    conn.close()
    return True, None

def get_all_users(role: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if role:
        cursor.execute("""
            SELECT id, name, email, role, student_id, department, is_active, created_at
            FROM users WHERE role = ? ORDER BY id DESC
        """, (role,))
    else:
        cursor.execute("""
            SELECT id, name, email, role, student_id, department, is_active, created_at
            FROM users ORDER BY id DESC
        """)
    rows = cursor.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

# ---------------------------------------------------------
# Complaints Database Operations
# ---------------------------------------------------------
def create_complaint(complaint_data: Dict[str, Any]) -> str:
    ticket_id = complaint_data.get("ticket_id") or generate_ticket_id()
    conn = get_db_connection()
    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # If student_user_id is not explicitly provided, attempt lookup by email
    student_user_id = complaint_data.get("student_user_id")
    if not student_user_id and complaint_data.get("student_email"):
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE", (complaint_data["student_email"].strip().lower(),))
        u_row = cursor.fetchone()
        if u_row:
            student_user_id = u_row["id"]

    assigned_staff_id = complaint_data.get("assigned_staff_id")

    with conn:
        conn.execute("""
            INSERT INTO complaints (
                ticket_id, student_name, student_email, student_user_id, assigned_staff_id,
                subject, raw_description, location, category, priority,
                severity_score, department, status, assigned_staff_role,
                estimated_sla_hours, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket_id,
            complaint_data.get("student_name", "Anonymous Student"),
            complaint_data.get("student_email", "student@campus.edu"),
            student_user_id,
            assigned_staff_id,
            complaint_data.get("subject", "General Complaint"),
            complaint_data.get("raw_description", ""),
            complaint_data.get("location", "Campus Grounds"),
            complaint_data.get("category", "General"),
            complaint_data.get("priority", "MEDIUM"),
            int(complaint_data.get("severity_score", 2)),
            complaint_data.get("department", "Estate & Maintenance Operations"),
            complaint_data.get("status", "Assigned"),
            complaint_data.get("assigned_staff_role", "Department Duty Officer"),
            int(complaint_data.get("estimated_sla_hours", 24)),
            now_iso,
            now_iso
        ))

        # Initial status history record
        conn.execute("""
            INSERT INTO status_history (ticket_id, old_status, new_status, updated_by, notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            ticket_id,
            None,
            complaint_data.get("status", "Assigned"),
            "System Orchestrator",
            "Complaint received and initially processed by ResolveAI multi-agent pipeline.",
            now_iso
        ))

    conn.close()
    return ticket_id

def get_complaint_by_ticket_id(ticket_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints WHERE ticket_id = ? COLLATE NOCASE", (ticket_id.strip(),))
    row = cursor.fetchone()
    conn.close()
    return row_to_dict(row) if row else None

def get_all_complaints(
    status: Optional[str] = None,
    department: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    student_user_id: Optional[int] = None,
    student_email: Optional[str] = None,
    assigned_staff_id: Optional[int] = None,
    limit: int = 150
) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM complaints WHERE 1=1"
    params = []

    if status == "PENDING_UNASSIGNED":
        query += " AND (status = 'Submitted' OR assigned_staff_id IS NULL) AND status NOT IN ('Resolved', 'Closed')"
    elif status and status != "ALL":
        query += " AND status = ?"
        params.append(status)

    if department and department != "ALL":
        query += " AND department = ?"
        params.append(department)

    if priority and priority != "ALL":
        query += " AND priority = ?"
        params.append(priority)

    if student_user_id is not None:
        if student_email:
            query += " AND (student_user_id = ? OR student_email = ? COLLATE NOCASE)"
            params.extend([student_user_id, student_email.strip().lower()])
        else:
            query += " AND student_user_id = ?"
            params.append(student_user_id)
    elif student_email:
        query += " AND student_email = ? COLLATE NOCASE"
        params.append(student_email.strip().lower())

    if assigned_staff_id is not None:
        query += " AND assigned_staff_id = ?"
        params.append(assigned_staff_id)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query += " AND (ticket_id LIKE ? OR subject LIKE ? OR raw_description LIKE ? OR location LIKE ? OR student_name LIKE ?)"
        params.extend([term, term, term, term, term])

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

def update_complaint_status(
    ticket_id: str,
    new_status: str,
    updated_by: str,
    notes: str,
    closure_summary: Optional[str] = None,
    assigned_staff_id: Optional[int] = None
) -> bool:
    conn = get_db_connection()
    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor = conn.cursor()
    cursor.execute("SELECT status FROM complaints WHERE ticket_id = ? COLLATE NOCASE", (ticket_id.strip(),))
    curr_row = cursor.fetchone()
    if not curr_row:
        conn.close()
        return False

    old_status = curr_row["status"]

    with conn:
        resolved_at = now_iso if new_status in ("Resolved", "Closed") else None
        
        if assigned_staff_id is not None:
            if closure_summary:
                conn.execute("""
                    UPDATE complaints
                    SET status = ?, resolution_notes = ?, closure_summary = ?, updated_at = ?, resolved_at = COALESCE(resolved_at, ?), assigned_staff_id = ?
                    WHERE ticket_id = ? COLLATE NOCASE
                """, (new_status, notes, closure_summary, now_iso, resolved_at, assigned_staff_id, ticket_id.strip()))
            else:
                conn.execute("""
                    UPDATE complaints
                    SET status = ?, resolution_notes = ?, updated_at = ?, resolved_at = COALESCE(resolved_at, ?), assigned_staff_id = ?
                    WHERE ticket_id = ? COLLATE NOCASE
                """, (new_status, notes, now_iso, resolved_at, assigned_staff_id, ticket_id.strip()))
        else:
            if closure_summary:
                conn.execute("""
                    UPDATE complaints
                    SET status = ?, resolution_notes = ?, closure_summary = ?, updated_at = ?, resolved_at = COALESCE(resolved_at, ?)
                    WHERE ticket_id = ? COLLATE NOCASE
                """, (new_status, notes, closure_summary, now_iso, resolved_at, ticket_id.strip()))
            else:
                conn.execute("""
                    UPDATE complaints
                    SET status = ?, resolution_notes = ?, updated_at = ?, resolved_at = COALESCE(resolved_at, ?)
                    WHERE ticket_id = ? COLLATE NOCASE
                """, (new_status, notes, now_iso, resolved_at, ticket_id.strip()))

        conn.execute("""
            INSERT INTO status_history (ticket_id, old_status, new_status, updated_by, notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticket_id.strip(), old_status, new_status, updated_by, notes, now_iso))

    conn.close()
    return True

def add_agent_log(
    ticket_id: str,
    agent_name: str,
    action: str,
    input_data: Any,
    output_data: Any,
    reasoning: str,
    execution_status: str = "SUCCESS"
) -> int:
    conn = get_db_connection()
    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Serialize input/output if they are dicts or lists
    str_input = json.dumps(input_data, indent=2) if isinstance(input_data, (dict, list)) else str(input_data)
    str_output = json.dumps(output_data, indent=2) if isinstance(output_data, (dict, list)) else str(output_data)

    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agent_logs (
                ticket_id, agent_name, action, input_data, output_data, reasoning, execution_status, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticket_id, agent_name, action, str_input, str_output, reasoning, execution_status, now_iso))
        log_id = cursor.lastrowid

    conn.close()
    return log_id

def get_agent_logs_by_ticket_id(ticket_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM agent_logs
        WHERE ticket_id = ? COLLATE NOCASE
        ORDER BY id ASC
    """, (ticket_id.strip(),))
    rows = cursor.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

def get_all_agent_logs(limit: int = 60) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM agent_logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

def get_status_history(ticket_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM status_history
        WHERE ticket_id = ? COLLATE NOCASE
        ORDER BY id ASC
    """, (ticket_id.strip(),))
    rows = cursor.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

def get_dashboard_stats(department: Optional[str] = None) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()

    dept_filter = " WHERE department = ?" if department else ""
    dept_params = [department] if department else []

    cursor.execute(f"SELECT COUNT(*) as total FROM complaints{dept_filter}", dept_params)
    total = cursor.fetchone()["total"]

    sub_where = f" WHERE status = 'Submitted' {'AND department = ?' if department else ''}"
    cursor.execute(f"SELECT COUNT(*) as count FROM complaints{sub_where}", dept_params)
    submitted_count = cursor.fetchone()["count"]

    ass_where = f" WHERE status = 'Assigned' {'AND department = ?' if department else ''}"
    cursor.execute(f"SELECT COUNT(*) as count FROM complaints{ass_where}", dept_params)
    assigned_count = cursor.fetchone()["count"]

    prog_where = f" WHERE status = 'In Progress' {'AND department = ?' if department else ''}"
    cursor.execute(f"SELECT COUNT(*) as count FROM complaints{prog_where}", dept_params)
    in_progress_count = cursor.fetchone()["count"]

    res_where = f" WHERE status IN ('Resolved', 'Closed') {'AND department = ?' if department else ''}"
    cursor.execute(f"SELECT COUNT(*) as count FROM complaints{res_where}", dept_params)
    resolved_count = cursor.fetchone()["count"]

    # Pending / Unassigned complaints
    unassigned_where = f" WHERE (status = 'Submitted' OR assigned_staff_id IS NULL) AND status NOT IN ('Resolved', 'Closed') {'AND department = ?' if department else ''}"
    cursor.execute(f"SELECT COUNT(*) as count FROM complaints{unassigned_where}", dept_params)
    pending_unassigned_count = cursor.fetchone()["count"]

    # All Critical and High Priority complaints
    crit_all_where = f" WHERE priority IN ('HIGH', 'CRITICAL') {'AND department = ?' if department else ''}"
    cursor.execute(f"SELECT COUNT(*) as count FROM complaints{crit_all_where}", dept_params)
    critical_high_count = cursor.fetchone()["count"]

    crit_where = f" WHERE priority IN ('HIGH', 'CRITICAL') AND status NOT IN ('Resolved', 'Closed') {'AND department = ?' if department else ''}"
    cursor.execute(f"SELECT COUNT(*) as count FROM complaints{crit_where}", dept_params)
    critical_high_open = cursor.fetchone()["count"]

    # By Priority
    p_where = f"{'WHERE department = ?' if department else ''}"
    cursor.execute(f"SELECT priority, COUNT(*) as count FROM complaints {p_where} GROUP BY priority", dept_params)
    priority_rows = cursor.fetchall()
    priority_distribution = {row["priority"]: row["count"] for row in priority_rows}

    # By Department
    cursor.execute("SELECT department, COUNT(*) as count FROM complaints GROUP BY department ORDER BY count DESC")
    dept_rows = cursor.fetchall()
    dept_distribution = {row["department"]: row["count"] for row in dept_rows}

    # By Status
    s_where = f"{'WHERE department = ?' if department else ''}"
    cursor.execute(f"SELECT status, COUNT(*) as count FROM complaints {s_where} GROUP BY status", dept_params)
    status_rows = cursor.fetchall()
    status_distribution = {row["status"]: row["count"] for row in status_rows}

    # Resolution rate
    resolution_rate = round((resolved_count / total * 100), 1) if total > 0 else 0.0

    conn.close()
    return {
        "total": total,
        "submitted": submitted_count,
        "pending_unassigned": pending_unassigned_count,
        "assigned": assigned_count,
        "in_progress": in_progress_count,
        "resolved": resolved_count,
        "critical_high": critical_high_count,
        "open_tickets": total - resolved_count,
        "critical_high_open": critical_high_open,
        "resolution_rate": resolution_rate,
        "priority_distribution": priority_distribution,
        "department_distribution": dept_distribution,
        "status_distribution": status_distribution
    }
