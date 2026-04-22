# Metrics

Scoring functions used across all benchmark tasks.

---

## mapping_accuracy.py

Scores the field_mapping task.

| Metric | Description |
|--------|-------------|
| `accuracy_exact` | % of fields where `predicted_key == expected_key` |
| `accuracy_fuzzy` | % with token overlap ≥ 0.5 between predicted and expected key |
| `avg_confidence` | Mean of model-reported confidence scores across all fields |

---

## fill_accuracy.py

Scores the form_filling task.

| Metric | Description |
|--------|-------------|
| `fill_accuracy` | % of fields where filled value matches expected value (exact string match after normalisation) |

Normalisation: lowercase, strip whitespace, remove punctuation before comparing.

---

## performance.py

Measures speed and cost — model-agnostic.

| Metric | Description |
|--------|-------------|
| `latency_ms` | Wall-clock time for the LLM call(s) |
| `cost_usd` | Estimated cost based on token counts and published pricing |
| `tokens_used` | Total prompt + completion tokens |
| `tokens_prompt` | Prompt tokens only |
| `tokens_completion` | Completion tokens only |
