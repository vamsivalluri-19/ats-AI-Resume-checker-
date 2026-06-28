import argparse
import json
import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.utils.resume_mistakes import train_from_dataset


def _default_dataset_path():
    candidates = [
        os.path.join(os.path.dirname(__file__), "data", "resume_mistakes_dataset.csv"),
        os.path.join(os.path.dirname(__file__), "data", "resume_mistakes_dataset.json"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


def main():
    parser = argparse.ArgumentParser(description="Train the resume mistake detector from a labeled dataset.")
    parser.add_argument("--dataset", default=_default_dataset_path(), help="Path to a CSV or JSON dataset")
    parser.add_argument("--model-path", default=None, help="Optional output path for the trained model")
    args = parser.parse_args()

    model_path = args.model_path
    if model_path is None:
        model_path = os.path.join(os.path.dirname(__file__), "models", "resume_mistake_model.pkl")

    result = train_from_dataset(args.dataset, model_path=model_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()