from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


RESPONSE_SYSTEM_PROMPT = """You are a helpful network operations assistant.

You receive:
- the original user question
- structured topology and inventory data
- a machine-generated summary

Your goal is to produce a clear, concise natural language explanation
for a NOC/NMC engineer. Use accurate, neutral language and avoid hallucinations.
If some information is missing, say so explicitly.

Do NOT invent circuits, sites, or customers that are not present in the data.
"""


RESPONSE_USER_TEMPLATE = """User question:
{question}

Structured data (JSON):
{structured_data}

Draft summary:
{draft_summary}
"""


def build_response_prompt() -> ChatPromptTemplate:
    """
    Build a ChatPromptTemplate for the response-polish chain.

    Invocation dict should contain:
      - question
      - structured_data
      - draft_summary
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", RESPONSE_SYSTEM_PROMPT),
            ("user", RESPONSE_USER_TEMPLATE),
        ]
    )
