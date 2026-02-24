# Internal LLM Gateway Architecture

This document maps the flow of the Transparent LLM Gateway built for the `topology-agent`. The primary purpose of this gateway is to enforce budgets, isolate LLM infrastructure from business logic, and transparently inject enterprise safety policies (Guardrails, RBAC, Data Loss Prevention) into the LangChain pipeline dynamically.

## High-Level Pipeline Flow

```text
+-----------------------+               +--------------------------+
| Application           |  request()    | llm_factory.py           |
| (Planner / Validator) |-------------->| (Defines configuration & |
|                       |               |  required guardrails)    |
+-----------------------+               +--------------------------+
           ^                                         |
           |                                         v
           |                        +--------------------------------+
           |                        | GatewayClient.get_model()      |
           |                        | 1. Checks budget (UsageStore)|
           |                        | 2. Downgrades Backend if over|
           |                        | 3. Chains Middlewares          |
           |                        +--------------------------------+
           |                                         |
           | Returns assembled LangChain Runnable    |
           |                                         |
 .......................................................................
 .                        GATEWAY MIDDLEWARE CHAIN                     .
 .                                                                     .
 .   +------------------+    +-------------------+    +--------------+ .
 .   | Input Guardrails |    | Safety Policy     |    | Underlying   | .
 .   | - RegEx PII      |--->| - Appends SysMsg  |--->| Model (GPT,  | .
 .   | - Heuristics for |    | - Injects DEV or  |    | Anthropic,   | .
 .   | Prompt Injection |    | PROD instructions |    | Ollama)      | .
 .   +------------------+    +-------------------+    +--------------+ .
 .           ^                                               |         .
 .           | (1) Run Query                                 |         .
 .           |                                               v         .
 .   +------------------+                            +---------------+ .
 .   | Application /    |                            | Output Guards | .
 .   | User             |<---------------------------| - Enforce JSON| .
 .   +------------------+     (2) Final Clean Output | - Strip MD    | .
 .                                                   | - RBAC Checks | .
 .                                                   +---------------+ .
 .                                                           |         .
 .                                                           v         .
 .                                                   +---------------+ .
 .                                                   | Usage Tracking| .
 .                                                   | (Cost & Token | .
 .                                                   | Logging)      | .
 .                                                   +---------------+ .
 .......................................................................
```

## Directory Structure & Responsibilities

The logic has been decoupled entirely from `src/llm/llm_factory.py` and modularized into `src/llm/gateway/`:

*   **`client.py` (`GatewayClient`)**
    *   The entry point for the application. Evaluates user limits, manages fallbacks, and weaves the LangChain `RunnableLambda` middlewares (Guardrails and Safety Policies) around the core model.
*   **`guardrails.py` (`GatewayGuardrails`)**
    *   The pluggable interceptors.
    *   **Pre-Generation:** Regex-based PII Redaction (`[REDACTED_SSN]`) and robust Heuristic Prompt Injection Defense.
    *   **Post-Generation:** Strict JSON enforcement, Markdown stripping, and Execution RBAC (e.g., blocking `read_only` users from generating `reboot_tool` plans).
*   **`budget.py` (`UsageTrackingCallbackHandler` & Cost Logic)**
    *   Contains the `calculate_cost()` dollar map.
    *   Injects an asynchronous callback into the LLM that triggers `on_llm_end` to pull exact `prompt_tokens` and `completion_tokens` from LangChain's native `usage_metadata` outputs.
*   **`storage.py` (`UsageStore` Interface)**
    *   Manages concurrent writes to the local `.llm_usage.json` (for real-time budgeting limits) and `.llm_call_logs.jsonl` (for per-invocation audit trails readable by Elasticsearch or Redis).
*   **`models.py` (`create_openai_chat`, etc.)**
    *   The literal factory wrappers that securely instantiate `ChatOllama`, `ChatOpenAI`, `ChatAnthropic`, etc., based on environment configurations.

## Guardrail Configuration Architecture

Instead of hardcoding safety constraints directly into the agents, the Application's `llm_factory.py` declares what guardrails it wants turned ON or OFF during the initial request:

```python
# Planner agent needs precise JSON and Topology IPs but doesn't need basic user chat redaction.
guardrail_config={
    "json_enforcement": True,
    "rbac_level": "none",
    "pii_redaction": False, 
}
```

This flexibility allows `test_planner.py` to seamlessly execute complex chains via local models (like `mistral`) without crashing, while ensuring toxic logic or over-budget conditions are gracefully thwarted without the application ever knowing.
