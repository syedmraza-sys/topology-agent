from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


VALIDATOR_SYSTEM_PROMPT = """You are a strict validator for topology and inventory answers.

Given:
- the original user question
- the structured tool results (topology, inventory, comments, memory, hierarchy)
- a candidate UI response (paths, circuits, summary, warnings)

Your job is to:
1. Check if the answer is factually consistent with the tool data.
2. Check if the answer appears complete enough for an NOC/NMC engineer.
3. Identify any obvious gaps or contradictions.

Output a short JSON object:
{
  "status": "ok" | "needs_refinement" | "error",
  "confidence": 0.0-1.0,
  "reasons": ["..."],
  "warnings": ["..."],
  "needs_refinement": true/false
}
"""


VALIDATOR_USER_TEMPLATE = """User question:
{question}

Tool results (JSON):
{tool_results}

Candidate UI response (JSON):
{candidate_ui_response}
"""


def build_validator_prompt() -> ChatPromptTemplate:
    """
    Build a ChatPromptTemplate for the validator chain.

    Invocation dict should contain:
      - question
      - tool_results
      - candidate_ui_response
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", VALIDATOR_SYSTEM_PROMPT),
            ("user", VALIDATOR_USER_TEMPLATE),
        ]
    )
