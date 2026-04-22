# Results

Benchmark run outputs are stored here as JSON files and summarised below.

Results are gitignored (large files). The leaderboard table is updated manually
after each run.

---

## File naming

```
results/<model>_<dataset>_<task>_<date>.json
```

Example:
```
results/gpt-4o-mini_financial_field_mapping_2026-03-16.json
```

---

## Leaderboard — Field Mapping Accuracy (%)

_Populated after first benchmark run._

| Model | Financial | Medical | Legal | Government | HR | Insurance | Avg |
|-------|-----------|---------|-------|------------|----|-----------|-----|
| — | — | — | — | — | — | — | — |

## Leaderboard — Performance

_Populated after first benchmark run._

| Model | Avg Latency (ms) | Avg Cost ($/PDF) |
|-------|-----------------|-----------------|
| — | — | — |

---

## Running benchmarks

```bash
# All models, all datasets
python benchmarks/run_benchmark.py

# Single model + dataset
python benchmarks/run_benchmark.py --model gpt-4o-mini --dataset financial

# Results saved to benchmarks/results/
```
