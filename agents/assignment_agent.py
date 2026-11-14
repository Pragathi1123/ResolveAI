from typing import Dict, Any
from config import Config
from .base_agent import BaseAgent

class DepartmentAssignmentAgent(BaseAgent):
    """
    Core Agent 3: Department Assignment Agent
    Matches complaint semantics and category to the correct campus department,
    designates the assigned staff role, and outlines the initial action plan.
    """
    def __init__(self):
        super().__init__("Department Assignment Agent")

    def process(self, understanding: Dict[str, Any], priority_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determines the appropriate department and dispatch role.
        """
        dept_options = ", ".join([f'"{d}"' for d in Config.DEPARTMENTS])

        prompt = f"""
You are the Department Assignment Agent in ResolveAI.
Assign the following campus complaint to the most appropriate university department.

Departments Available:
[{dept_options}]

Complaint Details:
Category: {understanding.get('category')}
Issue Summary: {understanding.get('issue_summary')}
Location: {understanding.get('extracted_location')}
Priority: {priority_data.get('priority')} (Urgency: {priority_data.get('urgency')}, Severity: {priority_data.get('severity')})

Instructions:
1. Select exactly one department from the available list.
2. Designate a realistic staff role (e.g. "Lead Network Engineer", "Campus Maintenance Lead", "Dining Services Supervisor", "Security Field Officer", "Accounts Reconciliation Officer").
3. Outline a 1-sentence recommended action plan.

Return ONLY a JSON object with this exact schema:
{{
    "department": "<Must be one of the available departments>",
    "assigned_staff_role": "<Specific staff position>",
    "action_plan": "<Recommended initial step for the department>",
    "assignment_reasoning": "<Explanation of why this department is responsible>"
}}
"""

        system_instruction = "You are a university administrative workflow routing agent. Output valid JSON only."

        if self.is_ai_enabled:
            raw_response = self.call_gemini(prompt, system_instruction)
            parsed = self.extract_json(raw_response)
            if parsed and parsed.get("department") in Config.DEPARTMENTS:
                parsed["source"] = "Gemini AI"
                return parsed

        # Fallback Heuristics
        return self._fallback_assignment(understanding, priority_data)

    def _fallback_assignment(self, understanding: Dict[str, Any], priority_data: Dict[str, Any]) -> Dict[str, Any]:
        category = understanding.get("category", "")
        summary_lower = understanding.get("issue_summary", "").lower()
        loc_lower = understanding.get("extracted_location", "").lower()

        # Mapping rules
        if "IT" in category or any(w in summary_lower for w in ["wifi", "wi-fi", "internet", "portal", "login", "server", "lan"]):
            department = "IT & Network Infrastructure"
            staff_role = "Senior Network Operations Engineer"
            action = "Dispatch technician to test access point connectivity and switch ports."
        elif "Security" in category or any(w in summary_lower for w in ["streetlight", "dark", "theft", "stolen", "harassment", "gate", "guard"]):
            department = "Campus Security & Safety"
            staff_role = "Campus Patrol Supervisor"
            action = "Deploy physical security patrol and issue urgent lighting repair ticket."
        elif "Food" in category or any(w in summary_lower for w in ["food", "mess", "cafeteria", "canteen", "curd", "hygiene", "sour", "meal"]):
            department = "Cafeteria & Dining Services"
            staff_role = "Food Safety & Quality Inspector"
            action = "Inspect food preparation area and test ingredient batches immediately."
        elif "Finance" in category or any(w in summary_lower for w in ["fee", "payment", "tuition", "refund", "receipt", "deduction", "bank"]):
            department = "Finance & Accounts Office"
            staff_role = "Accounts Reconciliation Desk"
            action = "Audit bank payment gateway transaction logs and reconcile student ledger."
        elif "Transport" in category or any(w in summary_lower for w in ["bus", "shuttle", "route", "driver"]):
            department = "Transport & Logistics"
            staff_role = "Transport Operations Coordinator"
            action = "Verify bus GPS tracking logs and enforce route pickup schedule."
        elif "Academic" in category or any(w in summary_lower for w in ["grade", "gpa", "exam", "marks", "credit", "transcript", "attendance"]):
            department = "Academic & Examination Affairs"
            staff_role = "Academic Records Registrar"
            action = "Audit student academic credits against the department handbook."
        elif "Hostel" in loc_lower or "Hostel" in category:
            department = "Hostel & Residential Facilities"
            staff_role = "Hostel Warden & Facilities Supervisor"
            action = "Coordinate with hostel maintenance wing for immediate inspection."
        else:
            department = "Estate & Maintenance Operations"
            staff_role = "General Maintenance Lead"
            action = "Dispatch maintenance crew to assess physical damage and commence repairs."

        return {
            "department": department,
            "assigned_staff_role": staff_role,
            "action_plan": action,
            "assignment_reasoning": f"Complaint categorized under '{category}' mapped deterministically to '{department}'.",
            "source": "Rule-Based Department Router"
        }
