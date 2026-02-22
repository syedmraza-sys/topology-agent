import os
import sys

# Ensure we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm.planner_prompt import build_planner_prompt
from src.llm.llm_factory import get_planner_chain

def run_test():
    prompt_template = build_planner_prompt()
    inputs = {
        "question": "Show me the connectivity between Dallas POP and San Antonio and any related outages and tech comments.",
        "ui_context": "{\"selected_site\": [\"Dallas POP\", \"San Antonio\"], \"layer\": \"L2\"}",
        "history": "[]",
        "memory_snippets": "[]",
        "previous_plan": "null",
        "validation_feedback": "null"
    }

    print("--- FORMATTED PROMPT ---")
    formatted = prompt_template.format(**inputs)
    print(formatted)
    print("------------------------\n")

    print("--- EXECUTING CHAIN ---")
    chain = get_planner_chain()
    result = chain.invoke(inputs)
    
    print("\n--- RESULT ---")
    print(result.content if hasattr(result, "content") else result)
    print("----------------------\n")

if __name__ == "__main__":
    run_test()
