from prometheus_client import Counter

TOPOLOGY_QUERY_SUCCESS = Counter(
    "topology_query_success_total",
    "Number of successful topology queries (end-to-end)",
)

TOPOLOGY_QUERY_FAILURE = Counter(
    "topology_query_failure_total",
    "Number of failed topology queries (unhandled errors or invalid response)",
)

PLANNER_FALLBACK_USED = Counter(
    "topology_planner_fallback_total",
    "Number of times the planner fell back to a simple plan (LLM output invalid).",
)

COMMENT_RAG_HIT = Counter(
    "topology_comment_rag_hit_total",
    "Number of queries where comment RAG returned at least one result.",
)

COMMENT_RAG_MISS = Counter(
    "topology_comment_rag_miss_total",
    "Number of queries where comment RAG returned zero results.",
)
