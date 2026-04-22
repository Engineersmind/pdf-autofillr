# PDF Autofillr Benchmarks

Standardized evaluation of LLM models on PDF form field mapping and filling across real-world form categories.

---

## Leaderboard

> Results are populated after running `python benchmarks/run_benchmark.py`.
> Higher is better for accuracy metrics. Lower is better for latency and cost.

### Field Mapping Accuracy (%)

| Model | Financial | Medical | Legal | Government | HR | Insurance | **Avg** |
|-------|-----------|---------|-------|------------|----|-----------|---------|
| gpt-4o | — | — | — | — | — | — | — |
| gpt-4o-mini | — | — | — | — | — | — | — |
| claude-3-5-sonnet | — | — | — | — | — | — | — |
| claude-3-5-haiku | — | — | — | — | — | — | — |
| llama3.1 (local) | — | — | — | — | — | — | — |
| mistral (local) | — | — | — | — | — | — | — |

### Performance

| Model | Avg Latency (ms) | Avg Cost ($/PDF) | Tokens/PDF |
|-------|-----------------|-----------------|------------|
| gpt-4o | — | — | — |
| gpt-4o-mini | — | — | — |
| claude-3-5-sonnet | — | — | — |
| claude-3-5-haiku | — | — | — |
| llama3.1 (local) | — | $0 | — |
| mistral (local) | — | $0 | — |

---

## Structure

```
benchmarks/
├── datasets/           # PDF categories with ground truth
│   ├── financial/
│   ├── medical/
│   ├── legal/
│   ├── government/
│   ├── hr/
│   └── insurance/
├── tasks/              # Evaluation task definitions
├── metrics/            # Scoring functions
├── models/             # Model config cards
├── results/            # Benchmark run outputs
└── run_benchmark.py    # Entry point
```

---

## Quick start

```bash
# Run all models on all datasets
python benchmarks/run_benchmark.py

# Run a specific model on a specific dataset
python benchmarks/run_benchmark.py --model gpt-4o-mini --dataset financial

# Run a specific task only
python benchmarks/run_benchmark.py --task field_mapping
```

---

## Datasets

| Category | Forms | PDFs | Status |
|----------|-------|------|--------|
| [financial](datasets/financial/README.md) | Investment, loan, tax | 0 | Pending |
| [medical](datasets/medical/README.md) | Patient intake, claims | 0 | Pending |
| [legal](datasets/legal/README.md) | Contracts, compliance | 0 | Pending |
| [government](datasets/government/README.md) | Visa, W-2, benefits | 0 | Pending |
| [hr](datasets/hr/README.md) | Onboarding, payroll | 0 | Pending |
| [insurance](datasets/insurance/README.md) | Life, health, property | 0 | Pending |

---

## Tasks

| Task | Description | Key Metric |
|------|-------------|------------|
| [field_extraction](tasks/README.md) | Detect all form fields in a PDF | Precision / Recall / F1 |
| [field_mapping](tasks/README.md) | Map PDF fields to schema keys via LLM | Mapping Accuracy % |
| [form_filling](tasks/README.md) | Fill embedded PDF with user data | Fill Accuracy % |

---

## Adding a new PDF

1. Drop the PDF into `datasets/<category>/pdfs/`
2. Add its schema keys JSON to `datasets/<category>/schema_keys/`
3. Add the expected mapping to `datasets/<category>/ground_truth/`
4. Run `python benchmarks/run_benchmark.py --dataset <category>`

See `datasets/README.md` for the ground truth format.
