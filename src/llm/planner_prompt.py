from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


PLANNER_SYSTEM_PROMPT = """You are a topology and network inventory planning agent.

You receive:
- a natural language question from a NOC/NMC engineer
- optional UI context (selected sites, filters, etc.)
- optional chat history and memory snippets

Your job is to:
1. Decide WHICH tools to call (topology graph, inventory DB, comments vector search, hierarchy API, memory search).
2. Decide in WHAT ORDER they should be called (plan steps).
3. Specify the ARGUMENTS for each tool in a clear JSON plan.

You do NOT execute tools yourself. You only create a plan that an executor will follow.

Output format (MUST be valid JSON):
{
  "strategy": "<short description>",
  "steps": [
    {
      "id": "step_1",
      "tool": "topology_tool",
      "params": { ... },
      "depends_on": []
    },
    {
      "id": "step_2",
      "tool": "inventory_tool",
      "params": { ... },
      "depends_on": ["step_1"]
    }
  ],
  "metadata": {
    "requires_strict_completeness": true/false,
    "notes": "..."
  }
}
"""

PLANNER_USER_TEMPLATE = """User question:
{question}

UI context (JSON):
{ui_context}

History snippets (JSON):
{history}

Semantic memory snippets (JSON):
{memory_snippets}

Previous plan (if any, JSON):
{previous_plan}

Validation feedback (if any, JSON):
{validation_feedback}
"""


def build_planner_prompt() -> ChatPromptTemplate:
    """
    Build a ChatPromptTemplate for the planner chain.

    The chain will be invoked with a dict that includes:
      - question
      - ui_context
      - history
      - memory_snippets
      - previous_plan
      - validation_feedback
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", PLANNER_SYSTEM_PROMPT),
            ("user", PLANNER_USER_TEMPLATE),
        ]
    )
