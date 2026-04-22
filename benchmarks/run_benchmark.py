"""
PDF Autofillr Benchmark Runner

Usage:
    # All models on all datasets
    python benchmarks/run_benchmark.py

    # Specific model and dataset
    python benchmarks/run_benchmark.py --model gpt-4o-mini --dataset financial

    # Specific task only
    python benchmarks/run_benchmark.py --task field_mapping

    # Specific model, dataset, task
    python benchmarks/run_benchmark.py --model llama3.1 --dataset hr --task field_mapping
"""

import argparse

DATASETS = ["financial", "medical", "legal", "government", "hr", "insurance"]
MODELS = ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "claude-3-5-haiku", "llama3.1", "mistral"]
TASKS = ["field_extraction", "field_mapping", "form_filling"]


def parse_args():
    parser = argparse.ArgumentParser(description="Run PDF Autofillr benchmarks")
    parser.add_argument("--model",   choices=MODELS,   default=None, help="Model to benchmark (default: all)")
    parser.add_argument("--dataset", choices=DATASETS, default=None, help="Dataset category (default: all)")
    parser.add_argument("--task",    choices=TASKS,    default=None, help="Task to run (default: all)")
    parser.add_argument("--output",  default="benchmarks/results", help="Output directory for results")
    return parser.parse_args()


def run(model: str, dataset: str, task: str, output_dir: str):
    """Run a single model × dataset × task combination."""
    raise NotImplementedError(
        f"Benchmark not yet implemented: model={model}, dataset={dataset}, task={task}"
    )


def main():
    args = parse_args()

    models  = [args.model]   if args.model   else MODELS
    datasets = [args.dataset] if args.dataset else DATASETS
    tasks   = [args.task]    if args.task    else TASKS

    print(f"Models:   {models}")
    print(f"Datasets: {datasets}")
    print(f"Tasks:    {tasks}")
    print(f"Output:   {args.output}")
    print()

    for model in models:
        for dataset in datasets:
            for task in tasks:
                print(f"Running: {model} / {dataset} / {task} ...")
                try:
                    run(model, dataset, task, args.output)
                    print(f"  done")
                except NotImplementedError as e:
                    print(f"  skipped — {e}")


if __name__ == "__main__":
    main()
