"""Run Ragas evaluation for the policy RAG service.

This evaluates the retrieval/context quality and answer grounding for a small
golden dataset in evals/datasets/policy_rag_eval.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "api"
DEFAULT_DATASET = PROJECT_ROOT / "evals" / "datasets" / "policy_rag_eval.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "evals" / "experiments" / "policy_rag_ragas.csv"

sys.path.insert(0, str(API_ROOT))


def load_eval_rows(dataset_path: Path) -> list[dict[str, str]]:
    rows = []
    with dataset_path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_evaluation_records(rows: list[dict[str, str]], top_k: int) -> list[dict[str, object]]:
    from app.services.rag_service import PolicyRAGService

    rag = PolicyRAGService(top_k=top_k)
    records = []
    for row in rows:
        user_input = row["user_input"]
        retrieved_chunks = rag.retrieve(user_input)
        retrieved_contexts = [
            f"Source: {chunk.source}\nSection: {chunk.section}\n{chunk.text.strip()}"
            for chunk in retrieved_chunks
        ]
        records.append(
            {
                "user_input": user_input,
                "retrieved_contexts": retrieved_contexts,
                # The reference doubles as a stable response for evaluating retrieval
                # and grounding. Swap this for real API responses for end-to-end evals.
                "response": row["reference"],
                "reference": row["reference"],
            }
        )
    return records


def run_ragas(records: list[dict[str, object]], output_path: Path) -> None:
    from app.services.ragas_service import ragas_service

    result = ragas_service.evaluate_records(records)

    print(result)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result.to_pandas().to_csv(output_path, index=False)
        print(f"Saved Ragas results to {output_path}")
    except AttributeError:
        output_path.write_text(str(result), encoding="utf-8")
        print(f"Saved Ragas results to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate policy RAG with Ragas.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the Ragas dataset records without calling the evaluator LLM.",
    )
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(API_ROOT / ".env", override=True)

    rows = load_eval_rows(args.dataset)
    records = build_evaluation_records(rows, args.top_k)
    if args.dry_run:
        print(json.dumps(records, indent=2))
        return

    run_ragas(records, args.output)


if __name__ == "__main__":
    main()
