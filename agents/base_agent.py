import json
import re
import logging
from typing import Dict, Any, Optional
from config import Config

logger = logging.getLogger("ResolveAI.Agents")

class BaseAgent:
    """
    Base Agent class providing shared capabilities:
    - Gemini API client connection & prompt dispatch
    - Markdown JSON extraction & parsing
    - Fallback determination
    """
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.gemini_client = None
        self.is_ai_enabled = False
        self._init_client()

    def _init_client(self):
        if Config.is_gemini_configured():
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
                self.is_ai_enabled = True
                logger.info(f"[{self.agent_name}] Initialized Gemini client with model {Config.GEMINI_MODEL}")
            except Exception as e:
                logger.warning(f"[{self.agent_name}] Failed to initialize Gemini client: {e}. Will use intelligent rule-based fallback.")
                self.gemini_client = None
                self.is_ai_enabled = False
        else:
            logger.info(f"[{self.agent_name}] No Gemini API key provided. Operating in deterministic intelligent rule-based fallback mode.")
            self.is_ai_enabled = False

    def call_gemini(self, prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
        """
        Invokes Gemini API and returns the raw string response.
        Returns None if Gemini is not configured or throws an exception.
        """
        if not self.is_ai_enabled or not self.gemini_client:
            return None

        try:
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"System Instructions:\n{system_instruction}\n\nUser Request:\n{prompt}"

            response = self.gemini_client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=full_prompt
            )
            if response and hasattr(response, "text"):
                return response.text
        except Exception as e:
            logger.error(f"[{self.agent_name}] Gemini API call failed: {e}. Triggering fallback.")
        return None

    @staticmethod
    def extract_json(raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Extracts and parses JSON from LLM text output, handling code blocks and trailing characters.
        """
        if not raw_text:
            return None

        clean_text = raw_text.strip()

        # Handle ```json ... ``` or ``` ... ```
        if "```" in clean_text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
            if match:
                clean_text = match.group(1).strip()

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            # Try finding the first '{' and last '}'
            start = clean_text.find('{')
            end = clean_text.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(clean_text[start:end+1])
                except json.JSONDecodeError:
                    pass
        return None
