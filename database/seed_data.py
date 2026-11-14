import datetime
from config import Config
from database.db import (
    init_db,
    get_db_connection,
    create_user,
    get_user_by_email,
    create_complaint,
    add_agent_log,
    update_complaint_status
)

SEED_USERS = [
    # Admin is handled by bootstrap_admin or seeded here as well
    {
        "name": Config.ADMIN_NAME,
        "email": Config.ADMIN_EMAIL,
        "password": Config.ADMIN_PASSWORD,
        "role": "admin"
    },
    # Staff accounts
    {
        "name": "Senior Tech Vikram",
        "email": "vikram.staff@campus.edu",
        "password": "Staff@Secure2026",
        "role": "staff",
        "department": "IT & Network Infrastructure"
    },
    {
        "name": "Accounts Officer Meera",
        "email": "meera.staff@campus.edu",
        "password": "Staff@Secure2026",
        "role": "staff",
        "department": "Finance & Accounts Office"
    },
    {
        "name": "Facilities Supervisor Sunil",
        "email": "facilities.staff@campus.edu",
        "password": "Staff@Secure2026",
        "role": "staff",
        "department": "Estate & Maintenance Operations"
    },
    {
        "name": "Patrol Lead Singh",
        "email": "security.staff@campus.edu",
        "password": "Staff@Secure2026",
        "role": "staff",
        "department": "Campus Security & Safety"
    },
    {
        "name": "Inspector K. Verma",
        "email": "dining.staff@campus.edu",
        "password": "Staff@Secure2026",
        "role": "staff",
        "department": "Cafeteria & Dining Services"
    },
    # Student accounts
    {
        "name": "Aarav Sharma",
        "email": "aarav.sharma@campus.edu",
        "password": "Student@Secure2026",
        "role": "student",
        "student_id": "1MS21CS001"
    },
    {
        "name": "Priya Nair",
        "email": "priya.nair@campus.edu",
        "password": "Student@Secure2026",
        "role": "student",
        "student_id": "1MS21IS045"
    },
    {
        "name": "Rohan Deshmukh",
        "email": "rohan.d@campus.edu",
        "password": "Student@Secure2026",
        "role": "student",
        "student_id": "1MS21EC089"
    },
    {
        "name": "Ananya Sen",
        "email": "ananya.sen@campus.edu",
        "password": "Student@Secure2026",
        "role": "student",
        "student_id": "1MS21BT012"
    },
    {
        "name": "Kavita Reddy",
        "email": "kavita.reddy@campus.edu",
        "password": "Student@Secure2026",
        "role": "student",
        "student_id": "1MS21CS078"
    }
]

SAMPLE_COMPLAINTS = [
    {
        "ticket_id": "RES-20261110-WIFI1",
        "student_name": "Aarav Sharma",
        "student_email": "aarav.sharma@campus.edu",
        "subject": "Complete Wi-Fi outage in Hostel Block C during midterms",
        "raw_description": "The wireless internet across the 2nd and 3rd floors of Hostel Block C has been completely down for 14 hours. We have online submissions due tonight for Database Systems and cannot access course repositories or submission portals.",
        "location": "Hostel Block C, Floors 2 & 3",
        "category": "Network & Wi-Fi",
        "priority": "CRITICAL",
        "severity_score": 5,
        "department": "IT & Network Infrastructure",
        "status": "In Progress",
        "assigned_staff_role": "Senior Network Engineer",
        "assigned_staff_email": "vikram.staff@campus.edu",
        "estimated_sla_hours": 4,
        "logs": [
            ("Complaint Understanding Agent", "Entity & Intent Extraction",
             {"intent": "Network outage", "location": "Hostel Block C, Floors 2 & 3", "scope": "Multi-floor student housing during examination window"},
             "Identified catastrophic connectivity failure affecting large student cohort with imminent academic deadline."),
            ("Priority Assessment Agent", "Priority Calculation",
             {"urgency": 5, "severity": 5, "impact": 5, "priority": "CRITICAL"},
             "Critical priority assigned due to active examination deadline impact and broad multi-floor student outage."),
            ("Department Assignment Agent", "Routing & Ticket Generation",
             {"department": "IT & Network Infrastructure", "target_team": "NOC & Access Point Field Support", "SLA": "4 hours"},
             "Assigned to IT Network Infrastructure team with high-priority dispatch.")
        ],
        "history": [
            ("Submitted", "Assigned", "System Orchestrator", "Automated pipeline intake and assignment."),
            ("Assigned", "In Progress", "Senior Tech Vikram", "Technician dispatched to replace burnt PoE switch in rack C-02.")
        ]
    },
    {
        "ticket_id": "RES-20261111-LEAK2",
        "student_name": "Priya Nair",
        "student_email": "priya.nair@campus.edu",
        "subject": "Ceiling water leakage dripping over Central Library reference stacks",
        "raw_description": "Water is actively leaking from the ceiling on the 3rd floor of Central Library near Stack 14 (Computer Science & AI section). Several reference books have already gotten wet, and students have moved tables away to prevent slips.",
        "location": "Central Library, 3rd Floor, Stack 14",
        "category": "Facilities & Plumbing",
        "priority": "HIGH",
        "severity_score": 4,
        "department": "Estate & Maintenance Operations",
        "status": "Assigned",
        "assigned_staff_role": "Facilities Operations Supervisor",
        "assigned_staff_email": "facilities.staff@campus.edu",
        "estimated_sla_hours": 8,
        "logs": [
            ("Complaint Understanding Agent", "Physical Hazard & Damage Assessment",
             {"hazard": "Ceiling water leakage", "asset_at_risk": "Reference library books", "safety_risk": "Slip and fall"},
             "Physical infrastructure leak identified posing risk to physical library collection and patron safety."),
            ("Priority Assessment Agent", "Severity Scoring",
             {"urgency": 4, "severity": 4, "impact": 4, "priority": "HIGH"},
             "High priority warranted because institutional assets (reference books) and slip hazards are actively present."),
            ("Department Assignment Agent", "Facilities Dispatch",
             {"department": "Estate & Maintenance Operations", "action": "Urgent plumbing and roofing inspection"},
             "Routed directly to Estate Operations plumbing emergency queue.")
        ],
        "history": [
            ("Submitted", "Assigned", "System Orchestrator", "Complaint verified and escalated to Estate Operations.")
        ]
    },
    {
        "ticket_id": "RES-20261108-FEE03",
        "student_name": "Rohan Deshmukh",
        "student_email": "rohan.d@campus.edu",
        "subject": "Duplicate tuition fee deduction on online student portal",
        "raw_description": "I tried paying my semester registration fee of ₹45,000 on Nov 7th. The first transaction timed out with a gateway error, so I retried. Both transactions succeeded in my bank account (Ref TXN90281 & TXN90282) but portal shows only one credit.",
        "location": "Finance Portal / Online Gateway",
        "category": "Finance & Billing",
        "priority": "HIGH",
        "severity_score": 4,
        "department": "Finance & Accounts Office",
        "status": "Resolved",
        "assigned_staff_role": "Accounts Reconciliation Officer",
        "assigned_staff_email": "meera.staff@campus.edu",
        "estimated_sla_hours": 24,
        "resolution_notes": "Cross-verified merchant gateway bank statement with HDFC Payment Gateway. Confirmed double swipe. Initiated automated reversal for TXN90281 (₹45,000). Funds credited back to student's source bank account.",
        "closure_summary": "Issue successfully verified and resolved. The second charge was caused by an upstream gateway callback timeout. A full refund of ₹45,000 was processed via PG-Ref #REF-90281-REV and verified with our nodal banking partner. Gateway timeout thresholds have been adjusted.",
        "logs": [
            ("Complaint Understanding Agent", "Financial Extraction",
             {"amount": "₹45,000", "txn_ids": ["TXN90281", "TXN90282"], "financial_impact": "High"},
             "Extracted duplicate financial transaction tokens and confirmed bank debit confirmation."),
            ("Priority Assessment Agent", "Financial Risk Assessment",
             {"urgency": 4, "severity": 4, "impact": 3, "priority": "HIGH"},
             "Assigned High priority due to substantial monetary deduction and student distress."),
            ("Department Assignment Agent", "Finance Allocation",
             {"department": "Finance & Accounts Office", "action": "Payment gateway audit & refund initiation"},
             "Assigned to Accounts Reconciliation Desk."),
            ("Resolution Tracking Agent", "Resolution Verification & Closure Summary",
             {"resolution_verified": True, "refund_processed": True},
             "Authorized staff recorded full refund reconciliation. Verified bank trace and synthesized formal closure summary.")
        ],
        "history": [
            ("Submitted", "Assigned", "System Orchestrator", "Financial complaint ingested."),
            ("Assigned", "In Progress", "Accounts Officer Meera", "Initiating gateway transaction log audit."),
            ("In Progress", "Resolved", "Accounts Officer Meera", "Refund processed and settled. Student notified.")
        ]
    },
    {
        "ticket_id": "RES-20261112-FOOD4",
        "student_name": "Ananya Sen",
        "student_email": "ananya.sen@campus.edu",
        "subject": "Unhygienic food handling and sour milk in South Mess",
        "raw_description": "During dinner at the South Dining Mess, the curd and paneer dishes smelled sour and several students reported stomach discomfort. Servers were also not wearing hairnets or gloves behind the serving counters.",
        "location": "South Campus Dining Hall",
        "category": "Food & Cafeteria",
        "priority": "HIGH",
        "severity_score": 4,
        "department": "Cafeteria & Dining Services",
        "status": "In Progress",
        "assigned_staff_role": "Campus Health & Food Inspector",
        "assigned_staff_email": "dining.staff@campus.edu",
        "estimated_sla_hours": 6,
        "logs": [
            ("Complaint Understanding Agent", "Health & Hygiene Diagnostics",
             {"domain": "Food safety", "symptoms": "Stomach discomfort", "hygiene_violations": "Uncovered hair, no gloves"},
             "Flagged potential food safety violation posing student health risk."),
            ("Priority Assessment Agent", "Health Risk Scoring",
             {"urgency": 4, "severity": 4, "impact": 4, "priority": "HIGH"},
             "High priority established to prevent foodborne illness escalation."),
            ("Department Assignment Agent", "Health Audit Dispatch",
             {"department": "Cafeteria & Dining Services", "action": "Mandatory hygiene inspection & sample testing"},
             "Assigned to Dining Services supervisory staff.")
        ],
        "history": [
            ("Submitted", "Assigned", "System Orchestrator", "Complaint registered and flagged for food safety check."),
            ("Assigned", "In Progress", "Inspector K. Verma", "On-site kitchen hygiene inspection commenced.")
        ]
    },
    {
        "ticket_id": "RES-20261109-SEC05",
        "student_name": "Kavita Reddy",
        "student_email": "kavita.reddy@campus.edu",
        "subject": "Dark pathway with dead streetlights near East Gate boundary wall",
        "raw_description": "The entire 200m walkway connecting Academic Block 4 to East Gate has three completely broken streetlights. It is pitch black after 7 PM, creating safety concerns for female students walking back from late evening research labs.",
        "location": "East Gate Perimeter Walkway, near Block 4",
        "category": "Campus Safety & Lighting",
        "priority": "CRITICAL",
        "severity_score": 5,
        "department": "Campus Security & Safety",
        "status": "In Progress",
        "assigned_staff_role": "Chief Security Officer & Electrical Maintenance",
        "assigned_staff_email": "security.staff@campus.edu",
        "estimated_sla_hours": 6,
        "logs": [
            ("Complaint Understanding Agent", "Physical Security Analysis",
             {"location": "East Gate Perimeter Walkway", "hazard": "Complete darkness, broken streetlights", "vulnerable_cohort": "Late night students"},
             "Identified critical campus perimeter safety vulnerability."),
            ("Priority Assessment Agent", "Threat & Safety Evaluation",
             {"urgency": 5, "severity": 5, "impact": 4, "priority": "CRITICAL"},
             "Critical priority assigned due to student physical safety risk on unlit boundary pathways."),
            ("Department Assignment Agent", "Security Dispatch",
             {"department": "Campus Security & Safety", "action": "Immediate patrol deployment and electrical repair work order"},
             "Assigned jointly to Security Operations and Electrical Maintenance.")
        ],
        "history": [
            ("Submitted", "Assigned", "System Orchestrator", "Security alert processed."),
            ("Assigned", "In Progress", "Patrol Lead Singh", "Security guard stationed at post until electrical repair is completed.")
        ]
    }
]

def seed_database(force_reseed: bool = False):
    init_db()

    # 1. Seed Users
    for user_info in SEED_USERS:
        existing = get_user_by_email(user_info["email"])
        if not existing:
            try:
                create_user(
                    name=user_info["name"],
                    email=user_info["email"],
                    password=user_info["password"],
                    role=user_info["role"],
                    student_id=user_info.get("student_id"),
                    department=user_info.get("department")
                )
            except Exception as e:
                print(f"User seed notice: {e}")

    # 2. Check complaints
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM complaints")
    existing_count = cursor.fetchone()["count"]
    conn.close()

    if existing_count > 0 and not force_reseed:
        # Check if existing complaints need student_user_id / assigned_staff_id backfilled
        backfill_complaint_users()
        return

    print("Seeding database with realistic complaint scenarios, users, and agent traces...")

    for sample in SAMPLE_COMPLAINTS:
        # Check if already exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM complaints WHERE ticket_id = ?", (sample["ticket_id"],))
        if cursor.fetchone():
            conn.close()
            continue
        conn.close()

        # Lookup student user ID
        student_user = get_user_by_email(sample["student_email"])
        student_user_id = student_user["id"] if student_user else None

        # Lookup staff user ID
        staff_user_id = None
        if "assigned_staff_email" in sample:
            staff_user = get_user_by_email(sample["assigned_staff_email"])
            if staff_user:
                staff_user_id = staff_user["id"]

        ticket_id = create_complaint({
            "ticket_id": sample["ticket_id"],
            "student_name": sample["student_name"],
            "student_email": sample["student_email"],
            "student_user_id": student_user_id,
            "assigned_staff_id": staff_user_id,
            "subject": sample["subject"],
            "raw_description": sample["raw_description"],
            "location": sample["location"],
            "category": sample["category"],
            "priority": sample["priority"],
            "severity_score": sample["severity_score"],
            "department": sample["department"],
            "status": sample["status"],
            "assigned_staff_role": sample["assigned_staff_role"],
            "estimated_sla_hours": sample["estimated_sla_hours"]
        })

        # Add agent logs
        for log in sample.get("logs", []):
            agent_name, action, output_data, reasoning = log
            add_agent_log(
                ticket_id=ticket_id,
                agent_name=agent_name,
                action=action,
                input_data={"complaint_subject": sample["subject"], "location": sample["location"]},
                output_data=output_data,
                reasoning=reasoning,
                execution_status="SUCCESS"
            )

        # Update status if resolved or history
        if sample.get("resolution_notes"):
            update_complaint_status(
                ticket_id=ticket_id,
                new_status=sample["status"],
                updated_by="Authorized Staff",
                notes=sample["resolution_notes"],
                closure_summary=sample.get("closure_summary"),
                assigned_staff_id=staff_user_id
            )

        # Replay additional history
        for hist in sample.get("history", []):
            old_s, new_s, updated_by, notes = hist
            conn = get_db_connection()
            with conn:
                conn.execute("""
                    INSERT INTO status_history (ticket_id, old_status, new_status, updated_by, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (ticket_id, old_s, new_s, updated_by, notes))
            conn.close()

    backfill_complaint_users()
    print("Seeding completed successfully!")

def backfill_complaint_users():
    """
    Backfills student_user_id for complaints based on student_email if missing.
    """
    conn = get_db_connection()
    with conn:
        conn.execute("""
            UPDATE complaints
            SET student_user_id = (SELECT id FROM users WHERE users.email = complaints.student_email COLLATE NOCASE)
            WHERE student_user_id IS NULL AND student_email IN (SELECT email FROM users)
        """)
    conn.close()

if __name__ == "__main__":
    seed_database(force_reseed=False)
