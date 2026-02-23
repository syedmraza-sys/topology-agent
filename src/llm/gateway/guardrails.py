import json
import logging
import re
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

logger = logging.getLogger(__name__)

# Basic PII regex patterns
PII_PATTERNS = {
    # SSN (AAA-GG-SSSS)
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    # Basic Credit Card (16 digits)
    "credit_card": re.compile(r'\b(?:\d[ -]*?){13,16}\b'),
    # Email
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    # Can add IPv4, etc., but often IPs are needed for topology tools.
}

# Comprehensive prompt injection & jailbreak heuristics
INJECTION_PATTERNS = [
    re.compile(r"(?i)\bignore\s+(all\s+)?(previous\s+)?(instructions|directions|prompts)\b"),
    re.compile(r"(?i)\b(system\s+prompt|initial\s+prompt|core\s+instructions)\b"),
    re.compile(r"(?i)\b(you\s+are\s+now|act\s+as|from\s+now\s+on\s+you)\b"),
    re.compile(r"(?i)\b(dan\b|do\s+anything\s+now|developer\s+mode|unfiltered\s+mode)\b"),
    re.compile(r"(?i)\b(disregard\s+the\s+above)\b"),
    re.compile(r"(?i)\b(print\s+your\s+instructions|output\s+initial\s+prompt)\b"),
    re.compile(r"(?i)[\b\s]*(forget\s+everything)[\b\s]*")
]

class GatewayGuardrails:
    """
    Pluggable Guardrails for Pre-Generation, Post-Generation, and Execution safety.
    """

    @classmethod
    def apply_input_guardrails(cls, messages: List[BaseMessage], config: Dict[str, Any]) -> List[BaseMessage]:
        """
        Pre-Generation Guardrails: Redact PII or other sensitive data before the LLM sees it.
        """
        if not config.get("pii_redaction", False):
            return messages

        new_messages = []
        for msg in messages:
            # We only want to redact Human inputs typically, as System prompts are ours.
            if isinstance(msg, HumanMessage) and isinstance(msg.content, str):
                content = msg.content
                for pii_type, pattern in PII_PATTERNS.items():
                    content = pattern.sub(f"[REDACTED_{pii_type.upper()}]", content)
                
                # Check for explicit instructions and jailbreaks via heuristics
                is_injection = any(pattern.search(content) for pattern in INJECTION_PATTERNS)
                
                # We also add a threshold-based keyword check to catch sneaky variants
                suspicious_keywords = ["ignore", "prompt", "system", "instruction", "bypass", "override", "developer"]
                keyword_score = sum(1 for word in suspicious_keywords if word in content.lower())
                
                if is_injection or keyword_score >= 3:
                    logger.warning("Guardrail: Potential prompt injection detected. Scrubbing input.")
                    content = "BLOCKED: Prompt Injection Attempt Detected."
                    
                new_messages.append(HumanMessage(content=content))
            else:
                new_messages.append(msg)
                
        return new_messages

    @classmethod
    def apply_output_guardrails(cls, message: AIMessage, config: Dict[str, Any]) -> AIMessage:
        """
        Post-Generation and Execution Guardrails: Ensure JSON format, strip markdown, enforce RBAC.
        """
        content = message.content
        if not isinstance(content, str):
            return message

        modified_content = content
        is_json_valid = False
        parsed_json = None

        # 1. Post-Generation: JSON Enforcement & Markdown Stripping
        if config.get("json_enforcement", False):
            # Attempt to strip markdown blocks if present
            json_match = re.search(r'```(?:json)?(.*?)```', modified_content, re.DOTALL)
            if json_match:
                modified_content = json_match.group(1).strip()
            
            # Additional cleanup for rogue prefixes (e.g., "Here is the plan:\n {")
            try:
                # Find the first { and last }
                start_idx = modified_content.find('{')
                end_idx = modified_content.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    modified_content = modified_content[start_idx:end_idx+1]
                
                parsed_json = json.loads(modified_content)
                is_json_valid = True
                # Re-dump to ensure it's a perfectly clean string without weird spacing
                modified_content = json.dumps(parsed_json, indent=2)
            except json.JSONDecodeError as e:
                logger.warning(f"Guardrail: Failed to enforce JSON. LLM output was invalid. Error: {e}")
                # Inject an error JSON indicating failure, so the application doesn't crash on parsing
                modified_content = json.dumps({"error": "LLM failed to produce valid JSON", "details": str(e)})
                parsed_json = None
                is_json_valid = False

        # 2. Execution Guardrails: RBAC (Role-Based Access Control)
        # We only check RBAC if we have a valid JSON plan and rbac checking is enabled.
        rbac_level = config.get("rbac_level", "read_only")
        if is_json_valid and parsed_json and "steps" in parsed_json:
            # Check restricted tools
            # Example logic: "read_only" users can't use "reboot_tool"
            restricted_tools = {
                "read_only": ["reboot_tool", "config_push_tool", "outage_remediation_tool"]
            }
            
            disallowed = restricted_tools.get(rbac_level, [])
            if disallowed:
                modified_steps = []
                for step in parsed_json.get("steps", []):
                    tool_name = step.get("tool")
                    if tool_name in disallowed:
                        logger.warning(f"Guardrail (RBAC): User with level '{rbac_level}' attempted to use restricted tool '{tool_name}'.")
                        # Nullify the tool
                        step["error"] = f"UNAUTHORIZED: rbac_level '{rbac_level}' cannot execute {tool_name}"
                        step["tool"] = "unauthorized_tool"
                    modified_steps.append(step)
                
                parsed_json["steps"] = modified_steps
                modified_content = json.dumps(parsed_json, indent=2)

        # Return a new AIMessage with the modified content to preserve tracking metadata
        new_message = AIMessage(
            content=modified_content,
            additional_kwargs=message.additional_kwargs,
            response_metadata=message.response_metadata,
            usage_metadata=getattr(message, "usage_metadata", None),
            id=message.id,
            name=message.name,
        )
        return new_message
