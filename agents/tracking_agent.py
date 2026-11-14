from typing import Dict, Any, Optional
from config import Config
from database.db import (
    get_complaint_by_ticket_id,
    update_complaint_status,
    add_agent_log,
    get_agent_logs_by_ticket_id,
    get_status_history
)
from .base_agent import BaseAgent

class ResolutionTrackingAgent(BaseAgent):
    """
    Core Agent 4: Resolution Tracking Agent
    Retrieves ticket status, validates lifecycle transitions, records updates,
    and generates formal closure summaries ONLY when an authorized resolution is submitted.
    Ensures no false resolution claims are made.
    """
    def __init__(self):
        super().__init__("Resolution Tracking Agent")

    def track_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves complete live tracking status for a ticket including logs and timeline.
        """
        complaint = get_complaint_by_ticket_id(ticket_id)
        if not complaint:
            return None

        agent_logs = get_agent_logs_by_ticket_id(ticket_id)
        history = get_status_history(ticket_id)

        # Compute progress percentage for progress bar
        status_progress = {
            "Submitted": 20,
            "Assigned": 40,
            "In Progress": 70,
            "Resolved": 100,
            "Closed": 100
        }

        return {
            "complaint": complaint,
            "progress_percentage": status_progress.get(complaint["status"], 20),
            "agent_logs": agent_logs,
            "history": history
        }

    def update_resolution(
        self,
        ticket_id: str,
        new_status: str,
        updated_by: str,
        notes: str,
        assigned_staff_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validates and records a status update. Generates an authorized closure summary
        only when status is 'Resolved' or 'Closed' with real resolution notes.
        """
        complaint = get_complaint_by_ticket_id(ticket_id)
        if not complaint:
            return {"success": False, "error": f"Ticket {ticket_id} not found"}

        if new_status not in Config.STATUSES:
            return {"success": False, "error": f"Invalid status: {new_status}"}

        # Guardrail: Never mark as Resolved or Closed without substantive resolution notes
        if new_status in ("Resolved", "Closed"):
            if not notes or len(notes.strip()) < 10:
                return {
                    "success": False,
                    "error": "Resolution requires clear, verifiable resolution notes detailing actions taken."
                }

        closure_summary = None
        if new_status in ("Resolved", "Closed"):
            closure_summary = self._generate_closure_summary(complaint, notes, updated_by)

        # Update database
        updated = update_complaint_status(
            ticket_id=ticket_id,
            new_status=new_status,
            updated_by=updated_by or "Authorized Staff",
            notes=notes,
            closure_summary=closure_summary,
            assigned_staff_id=assigned_staff_id
        )

        if updated:
            # Log agent activity
            action_desc = f"Ticket Status Updated: {complaint['status']} -> {new_status}"
            reasoning = f"Authorized user '{updated_by}' updated status to '{new_status}' with operational notes."
            if closure_summary:
                reasoning += " AI synthesized formal resolution closure summary."

            add_agent_log(
                ticket_id=ticket_id,
                agent_name=self.agent_name,
                action=action_desc,
                input_data={"previous_status": complaint["status"], "new_status": new_status, "notes": notes},
                output_data={"status": new_status, "closure_summary": closure_summary},
                reasoning=reasoning,
                execution_status="SUCCESS"
            )

            return {
                "success": True,
                "ticket_id": ticket_id,
                "old_status": complaint["status"],
                "new_status": new_status,
                "closure_summary": closure_summary
            }

        return {"success": False, "error": "Database update failed"}

    def _generate_closure_summary(self, complaint: Dict[str, Any], notes: str, updated_by: str) -> str:
        """
        Synthesizes a structured closure summary using Gemini or fallback rule synthesis.
        """
        prompt = f"""
You are the Resolution Tracking Agent in ResolveAI.
An authorized resolution has been recorded for the following grievance. Synthesize a professional, concise closure summary.

Complaint Context:
Ticket ID: {complaint.get('ticket_id')}
Subject: {complaint.get('subject')}
Department: {complaint.get('department')}
Location: {complaint.get('location')}

Staff Resolution Notes (recorded by {updated_by}):
{notes}

Instructions:
Synthesize a professional 2-3 sentence closure summary stating:
1. What was resolved.
2. The key action taken.
3. Confirmation of operational restoration or verification.

Output ONLY the plain text summary without markdown headers or fluff.
"""

        if self.is_ai_enabled:
            raw_response = self.call_gemini(prompt)
            if raw_response and len(raw_response.strip()) > 20:
                return raw_response.strip()

        # Fallback Synthesis
        return (
            f"Resolution Confirmed by {updated_by}: The reported issue regarding '{complaint.get('subject')}' "
            f"at {complaint.get('location')} has been addressed. Action taken: {notes.strip()} "
            f"Department {complaint.get('department')} confirms normal operations restored."
        )
