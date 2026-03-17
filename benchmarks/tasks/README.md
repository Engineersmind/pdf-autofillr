# Benchmark Tasks

Three tasks cover the full PDF autofill pipeline.

---

## Task 1 — field_extraction

**What it measures:** Does the extractor find all form fields in the PDF?

| | |
|-|-|
| **Input** | PDF file |
| **Output** | `{field_id: {label, type, page}}` |
| **Ground truth** | `ground_truth/<name>_gt.json` → `fields` keys |
| **Metrics** | Precision, Recall, F1 |

A field is "found" if its `field_id` appears in the output.

---

## Task 2 — field_mapping

**What it measures:** Does the LLM map each PDF field to the correct schema key?

| | |
|-|-|
| **Input** | PDF file + schema keys JSON |
| **Output** | `{field_id: {schema_key, confidence}}` |
| **Ground truth** | `ground_truth/<name>_gt.json` → `fields[id].expected_key` |
| **Metrics** | Mapping Accuracy (exact), Mapping Accuracy (fuzzy), Avg Confidence |

A mapping is "correct" if `predicted_key == expected_key`.
Fuzzy match uses token overlap for partial credit.

---

## Task 3 — form_filling

**What it measures:** After embedding, does filling produce the correct values?

| | |
|-|-|
| **Input** | Embedded PDF + user data JSON |
| **Output** | Filled PDF |
| **Ground truth** | Expected field values from user data |
| **Metrics** | Fill Accuracy % (correct values / total fields) |

---

## Running a task

```bash
python benchmarks/run_benchmark.py --task field_mapping --model gpt-4o-mini --dataset financial
```
