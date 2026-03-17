"""
Metric: performance

Measures latency and cost of LLM calls.
"""

# Token pricing per 1M tokens (input / output) as of March 2026.
# Update these when pricing changes.
MODEL_PRICING = {
    "gpt-4o":             {"input": 2.50,  "output": 10.00},
    "gpt-4o-mini":        {"input": 0.15,  "output": 0.60},
    "claude-3-5-sonnet":  {"input": 3.00,  "output": 15.00},
    "claude-3-5-haiku":   {"input": 0.80,  "output": 4.00},
    "llama3.1":           {"input": 0.0,   "output": 0.0},
    "mistral":            {"input": 0.0,   "output": 0.0},
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate USD cost for a single LLM call.

    Args:
        model: Model name matching a key in MODEL_PRICING.
        prompt_tokens: Number of input tokens.
        completion_tokens: Number of output tokens.

    Returns:
        Estimated cost in USD.
    """
    raise NotImplementedError


def summarize(results: list[dict]) -> dict:
    """
    Aggregate performance metrics across multiple benchmark runs.

    Args:
        results: List of per-PDF result dicts each containing
                 latency_ms, cost_usd, tokens_used.

    Returns:
        {
            "avg_latency_ms": float,
            "p50_latency_ms": float,
            "p95_latency_ms": float,
            "total_cost_usd": float,
            "avg_cost_usd": float,
            "avg_tokens": int,
        }
    """
    raise NotImplementedError
