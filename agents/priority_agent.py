from typing import Dict, Any
from .base_agent import BaseAgent

class PriorityAssessmentAgent(BaseAgent):
    """
    Core Agent 2: Priority Assessment Agent
    Analyzes urgency, severity and impact.
    Assigns LOW, MEDIUM, HIGH or CRITICAL priority with transparent rationale.
    """
    def __init__(self):
        super().__init__("Priority Assessment Agent")

    def process(self, understanding_data: Dict[str, Any], raw_description: str) -> Dict[str, Any]:
        """
        Assesses priority based on understanding data and complaint description.
        """
        prompt = f"""
You are the Priority Assessment Agent in ResolveAI.
Evaluate the grievance details below and assess its urgency, severity, and student impact.

Complaint Context:
Category: {understanding_data.get('category')}
Summary: {understanding_data.get('issue_summary')}
Location: {understanding_data.get('extracted_location')}
Affected Scope: {understanding_data.get('affected_scope')}
Urgency Cues Detected: {', '.join(understanding_data.get('urgency_cues', []))}
Full Text: {raw_description}

Instructions:
1. Rate Urgency (1 to 5): How time-critical is this? Is an exam, deadline, or immediate danger present?
2. Rate Severity (1 to 5): How severe is the disruption or safety/health/financial risk?
3. Rate Impact (1 to 5): How many students/facilities are affected? (1 = single student, 5 = entire hostel/campus)
4. Assign Priority:
   - CRITICAL: Immediate health/safety risk, active flooding, fire hazard, or total campus/exam blocker.
   - HIGH: Significant disruption, food hygiene issues, financial deductions, large cohort outage.
   - MEDIUM: Localized failures, room AC issues, transit delays, non-emergency equipment breakdowns.
   - LOW: Minor cosmetic issues, elective grade queries with distant deadlines, general suggestions.

Return ONLY a JSON object with this exact schema:
{{
    "urgency": <integer 1-5>,
    "severity": <integer 1-5>,
    "impact": <integer 1-5>,
    "priority": "<LOW | MEDIUM | HIGH | CRITICAL>",
    "severity_score": <integer 1-5 representing overall severity>,
    "recommended_sla_hours": <integer 2, 4, 8, 12, 24, or 48>,
    "priority_rationale": "<thorough explanation of the rating factors and why this priority was determined>"
}}
"""

        system_instruction = "You are an expert risk-assessment agent for university campus operations. Output valid JSON only."

        if self.is_ai_enabled:
            raw_response = self.call_gemini(prompt, system_instruction)
            parsed = self.extract_json(raw_response)
            if parsed and "priority" in parsed and parsed["priority"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                parsed["source"] = "Gemini AI"
                return parsed

        # Fallback Heuristic
        return self._fallback_priority(understanding_data, raw_description)

    def _fallback_priority(self, understanding: Dict[str, Any], raw_desc: str) -> Dict[str, Any]:
        text_lower = f"{raw_desc} {understanding.get('issue_summary', '')}".lower()
        urgency_cues = understanding.get("urgency_cues", [])
        scope = understanding.get("affected_scope", "Individual Student")

        urgency = 2
        severity = 2
        impact = 2

        # Urgency indicators
        if any(w in text_lower for w in ["immediately", "tonight", "exam", "midterm", "deadline", "urgent", "active"]):
            urgency += 2
        if len(urgency_cues) >= 2:
            urgency += 1
        urgency = min(max(urgency, 1), 5)

        # Severity indicators
        if any(w in text_lower for w in ["fire", "smoke", "shock", "flood", "leak", "sour food", "stomach", "theft", "pitch black", "broken streetlight"]):
            severity += 2
        if any(w in text_lower for w in ["overheating", "duplicate deduction", "refund", "outage", "down for 14 hours"]):
            severity += 1
        severity = min(max(severity, 1), 5)

        # Impact indicators
        if scope in ["Entire Building or Cohort", "Campus-wide"]:
            impact = 5
        elif scope in ["Floor or Wing", "Lab or Classroom"]:
            impact = 4
        elif any(w in text_lower for w in ["everyone", "30 students", "all of us", "entire floor"]):
            impact = 4
        else:
            impact = 1

        # Composite score
        composite = (urgency * 0.35) + (severity * 0.40) + (impact * 0.25)

        if composite >= 3.8 or (severity == 5 and urgency >= 4) or (impact >= 4 and urgency >= 4):
            priority = "CRITICAL"
            sla_hours = 4
        elif composite >= 3.0 or severity >= 4 or urgency >= 4:
            priority = "HIGH"
            sla_hours = 12
        elif composite >= 2.0:
            priority = "MEDIUM"
            sla_hours = 24
        else:
            priority = "LOW"
            sla_hours = 48

        rationale = (
            f"Determined {priority} priority (Urgency: {urgency}/5, Severity: {severity}/5, Impact: {impact}/5). "
            f"Scope identified as '{scope}' with {len(urgency_cues)} urgency indicators."
        )

        return {
            "urgency": urgency,
            "severity": severity,
            "impact": impact,
            "priority": priority,
            "severity_score": severity,
            "recommended_sla_hours": sla_hours,
            "priority_rationale": rationale,
            "source": "Rule-Based Risk Matrix"
        }
