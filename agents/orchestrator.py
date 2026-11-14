import datetime
from typing import Dict, Any, List
from config import Config
from database.db import (
    generate_ticket_id,
    create_complaint,
    add_agent_log,
    get_agent_logs_by_ticket_id,
    get_complaint_by_ticket_id
)
from .understanding_agent import ComplaintUnderstandingAgent
from .priority_agent import PriorityAssessmentAgent
from .assignment_agent import DepartmentAssignmentAgent
from .tracking_agent import ResolutionTrackingAgent

class CentralOrchestrator:
    """
    Core Agent 5: Central Orchestrator
    Coordinates the multi-agent pipeline:
    1. Validates intake inputs.
    2. Runs Complaint Understanding Agent.
    3. Runs Priority Assessment Agent.
    4. Runs Department Assignment Agent.
    5. Validates structured outputs.
    6. Persists ticket and agent activity traces to SQLite.
    7. Provides real-time orchestration traces.
    """
    def __init__(self):
        self.understanding_agent = ComplaintUnderstandingAgent()
        self.priority_agent = PriorityAssessmentAgent()
        self.assignment_agent = DepartmentAssignmentAgent()
        self.tracking_agent = ResolutionTrackingAgent()

    def process_complaint_submission(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinates the entire end-to-end complaint intake workflow.
        """
        student_name = form_data.get("student_name", "").strip() or "Student"
        student_email = form_data.get("student_email", "").strip() or "student@campus.edu"
        subject = form_data.get("subject", "").strip()
        raw_description = form_data.get("raw_description", "").strip()
        location = form_data.get("location", "").strip() or "Campus Premises"

        # Validation
        if not subject or not raw_description:
            raise ValueError("Subject and complaint description are strictly required.")

        # 1. Generate unique Ticket ID
        ticket_id = generate_ticket_id()
        traces: List[Dict[str, Any]] = []

        # ------------------------------------------------------------------
        # Agent 1: Complaint Understanding Agent
        # ------------------------------------------------------------------
        understanding_result = self.understanding_agent.process(
            subject=subject,
            raw_description=raw_description,
            location_hint=location
        )

        trace_step1 = {
            "agent": self.understanding_agent.agent_name,
            "action": "Semantic Analysis & Entity Extraction",
            "input": {"subject": subject, "description_snippet": raw_description[:100], "location": location},
            "output": understanding_result,
            "reasoning": understanding_result.get("reasoning", "Natural language analysis completed.")
        }
        traces.append(trace_step1)
        add_agent_log(
            ticket_id=ticket_id,
            agent_name=self.understanding_agent.agent_name,
            action=trace_step1["action"],
            input_data=trace_step1["input"],
            output_data=trace_step1["output"],
            reasoning=trace_step1["reasoning"]
        )

        # ------------------------------------------------------------------
        # Agent 2: Priority Assessment Agent
        # ------------------------------------------------------------------
        priority_result = self.priority_agent.process(
            understanding_data=understanding_result,
            raw_description=raw_description
        )

        trace_step2 = {
            "agent": self.priority_agent.agent_name,
            "action": "Urgency, Severity & Impact Assessment",
            "input": {
                "category": understanding_result.get("category"),
                "scope": understanding_result.get("affected_scope"),
                "urgency_cues": understanding_result.get("urgency_cues")
            },
            "output": priority_result,
            "reasoning": priority_result.get("priority_rationale", "Priority assessed.")
        }
        traces.append(trace_step2)
        add_agent_log(
            ticket_id=ticket_id,
            agent_name=self.priority_agent.agent_name,
            action=trace_step2["action"],
            input_data=trace_step2["input"],
            output_data=trace_step2["output"],
            reasoning=trace_step2["reasoning"]
        )

        # ------------------------------------------------------------------
        # Agent 3: Department Assignment Agent
        # ------------------------------------------------------------------
        assignment_result = self.assignment_agent.process(
            understanding=understanding_result,
            priority_data=priority_result
        )

        trace_step3 = {
            "agent": self.assignment_agent.agent_name,
            "action": "Department Routing & SLA Allocation",
            "input": {
                "category": understanding_result.get("category"),
                "priority": priority_result.get("priority")
            },
            "output": assignment_result,
            "reasoning": assignment_result.get("assignment_reasoning", "Routed to department.")
        }
        traces.append(trace_step3)
        add_agent_log(
            ticket_id=ticket_id,
            agent_name=self.assignment_agent.agent_name,
            action=trace_step3["action"],
            input_data=trace_step3["input"],
            output_data=trace_step3["output"],
            reasoning=trace_step3["reasoning"]
        )

        # ------------------------------------------------------------------
        # Validation & Database Storage
        # ------------------------------------------------------------------
        final_department = assignment_result.get("department")
        if final_department not in Config.DEPARTMENTS:
            final_department = "Estate & Maintenance Operations"

        final_priority = priority_result.get("priority", "MEDIUM")
        if final_priority not in Config.PRIORITIES:
            final_priority = "MEDIUM"

        resolved_location = understanding_result.get("extracted_location") or location

        complaint_record = {
            "ticket_id": ticket_id,
            "student_name": student_name,
            "student_email": student_email,
            "student_user_id": form_data.get("student_user_id"),
            "assigned_staff_id": form_data.get("assigned_staff_id"),
            "subject": subject,
            "raw_description": raw_description,
            "location": resolved_location,
            "category": understanding_result.get("category", "General"),
            "priority": final_priority,
            "severity_score": priority_result.get("severity_score", 2),
            "department": final_department,
            "status": form_data.get("status") or ("Assigned" if form_data.get("assigned_staff_id") else "Submitted"),
            "assigned_staff_role": form_data.get("assigned_staff_role") or (assignment_result.get("assigned_staff_role") if form_data.get("assigned_staff_id") else f"Recommended: {assignment_result.get('assigned_staff_role')}"),
            "estimated_sla_hours": priority_result.get("recommended_sla_hours", 24)
        }

        # Persist to SQLite
        created_ticket_id = create_complaint(complaint_record)

        # Orchestrator Log
        add_agent_log(
            ticket_id=created_ticket_id,
            agent_name="Central Orchestrator",
            action="Workflow Orchestration & Persistence",
            input_data={"student": student_name, "ticket": created_ticket_id},
            output_data={"status": complaint_record["status"], "department": final_department, "priority": final_priority},
            reasoning=f"Successfully orchestrated all 3 intake agents, validated schemas, and persisted ticket {created_ticket_id} to SQLite in {complaint_record['status']} state."
        )

        return {
            "ticket_id": created_ticket_id,
            "complaint": complaint_record,
            "understanding": understanding_result,
            "priority": priority_result,
            "assignment": assignment_result,
            "traces": traces
        }
