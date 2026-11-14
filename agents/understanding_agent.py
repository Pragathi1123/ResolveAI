import re
from typing import Dict, Any
from .base_agent import BaseAgent

class ComplaintUnderstandingAgent(BaseAgent):
    """
    Core Agent 1: Complaint Understanding Agent
    Understands natural-language complaints and extracts category, issue, location,
    scope of impact, urgency cues, and important entities.
    """
    def __init__(self):
        super().__init__("Complaint Understanding Agent")

    def process(self, subject: str, raw_description: str, location_hint: str = "") -> Dict[str, Any]:
        """
        Processes a complaint text and returns a structured understanding object.
        """
        combined_text = f"Subject: {subject}\nLocation Provided: {location_hint}\nDescription: {raw_description}"

        prompt = f"""
You are the Complaint Understanding Agent in ResolveAI, an automated campus grievance resolution system.
Analyze the following student complaint carefully and extract key structured information in valid JSON.

Complaint Text:
{combined_text}

Return ONLY a JSON object with this exact schema:
{{
    "category": "<one of: IT & Network, Facilities & Maintenance, Campus Security, Academic & Examination, Finance & Fees, Food & Cafeteria, Transport & Logistics, General>",
    "issue_summary": "<concise 1-2 sentence description of the core problem>",
    "extracted_location": "<specific location where the problem exists, synthesized from location input and description>",
    "affected_scope": "<Individual Student | Floor or Wing | Lab or Classroom | Entire Building or Cohort | Campus-wide>",
    "urgency_cues": ["<list of urgency or hazard indicators found in the text>"],
    "key_entities": ["<names, room numbers, transaction IDs, or equipment mentioned>"],
    "reasoning": "<brief explanation of how you analyzed this complaint>"
}}
"""

        system_instruction = "You are a precise, objective AI agent specializing in grievance analysis. Always output strictly valid JSON."

        # Attempt Gemini AI execution
        if self.is_ai_enabled:
            raw_response = self.call_gemini(prompt, system_instruction)
            parsed = self.extract_json(raw_response)
            if parsed and "category" in parsed and "issue_summary" in parsed:
                parsed["source"] = "Gemini AI"
                return parsed

        # Fallback Heuristic & NLP Engine
        return self._fallback_understanding(subject, raw_description, location_hint)

    def _fallback_understanding(self, subject: str, raw_desc: str, location_hint: str) -> Dict[str, Any]:
        text_lower = f"{subject} {raw_desc} {location_hint}".lower()

        # Category Detection
        category = "General"
        if any(w in text_lower for w in ["wifi", "wi-fi", "internet", "router", "ethernet", "lan", "server", "portal", "login", "website"]):
            category = "IT & Network"
        elif any(w in text_lower for w in ["fee", "payment", "tuition", "refund", "deduction", "transaction", "receipt", "bank", "scholarship"]):
            category = "Finance & Fees"
        elif any(w in text_lower for w in ["food", "mess", "cafeteria", "canteen", "curd", "milk", "meal", "hygiene", "roach", "sour", "dinner", "lunch"]):
            category = "Food & Cafeteria"
        elif any(w in text_lower for w in ["security", "guard", "theft", "stolen", "dark", "light", "streetlight", "unsafe", "gate", "stranger"]):
            category = "Campus Security"
        elif any(w in text_lower for w in ["bus", "shuttle", "route", "driver", "transport", "parking"]):
            category = "Transport & Logistics"
        elif any(w in text_lower for w in ["grade", "gpa", "exam", "marks", "credit", "transcript", "attendance", "syllabus", "professor"]):
            category = "Academic & Examination"
        elif any(w in text_lower for w in ["leak", "water", "plumbing", "pipe", "ac", "air condition", "fan", "flush", "toilet", "roof", "elevator", "lift", "switch"]):
            category = "Facilities & Maintenance"

        # Scope Detection
        affected_scope = "Individual Student"
        if any(w in text_lower for w in ["campus-wide", "all students", "entire campus"]):
            affected_scope = "Campus-wide"
        elif any(w in text_lower for w in ["building", "hostel", "wing", "floor", "everyone", "cohort", "30 students"]):
            affected_scope = "Floor or Wing"
        elif any(w in text_lower for w in ["lab", "classroom", "hall", "library"]):
            affected_scope = "Lab or Classroom"

        # Urgency Cues
        urgency_cues = []
        for word in ["urgent", "immediately", "deadline", "exam", "midterms", "leak", "fire", "smoke", "dark", "danger", "overheating", "sour", "down"]:
            if word in text_lower:
                urgency_cues.append(word)

        # Location extraction
        extracted_location = location_hint.strip() if location_hint.strip() else "Campus Grounds"
        loc_patterns = [
            r"(?:in|at|near|inside)\s+([A-Z][a-zA-Z0-9\s,-]+(?:Hostel|Block|Room|Floor|Lab|Hall|Gate|Library|Mess))",
            r"(?:Hostel\s+[A-Za-z0-9]+|Block\s+[A-Za-z0-9]+|Room\s+[0-9]+)"
        ]
        for pat in loc_patterns:
            m = re.search(pat, raw_desc, re.IGNORECASE)
            if m:
                extracted_location = m.group(0).strip()
                break

        # Key entities
        entities = []
        txns = re.findall(r"\b(?:TXN|REF|#)[A-Za-z0-9-]+\b", f"{subject} {raw_desc}")
        entities.extend(txns)
        room_matches = re.findall(r"\b(?:Room|Lab|Stack|Block|Route)\s+[A-Za-z0-9-]+\b", f"{subject} {raw_desc}", re.IGNORECASE)
        entities.extend(room_matches)

        return {
            "category": category,
            "issue_summary": f"{subject.strip()}: {raw_desc.strip()[:140]}..." if len(raw_desc) > 140 else f"{subject.strip()}: {raw_desc.strip()}",
            "extracted_location": extracted_location,
            "affected_scope": affected_scope,
            "urgency_cues": list(set(urgency_cues)),
            "key_entities": list(set(entities)),
            "reasoning": f"Heuristic analysis detected category '{category}' based on semantic keyword mapping and identified scope '{affected_scope}'.",
            "source": "Rule-Based Natural Language Engine"
        }
