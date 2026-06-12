"""Run Ragas evaluation for the policy RAG service.

This evaluates the retrieval/context quality and answer grounding for a small
golden dataset in evals/datasets/policy_rag_eval.jsonl.
"""

from __future__ import annotations

import argparse
import json
import os
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


def build_azure_evaluator_llm():
    patch_optional_ragas_imports()

    import litellm
    from ragas.llms import llm_factory

    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini")

    litellm.api_base = endpoint
    litellm.api_key = api_key
    litellm.api_version = api_version

    return llm_factory(
        f"azure/{deployment}",
        provider="litellm",
        client=litellm.completion,
        system_prompt=(
            "You are evaluating a customer support policy RAG system. "
            "Judge strictly against the retrieved policy context and reference answer."
        ),
    )


def patch_optional_ragas_imports() -> None:
    """Patch optional integrations that Ragas imports even when unused.

    Some Ragas/LangChain version combinations import VertexAI adapters at module
    import time. This project evaluates with Azure OpenAI only, so a tiny shim is
    enough to keep those unused optional imports from blocking Ragas startup.
    """
    import sys
    import types

    module_name = "langchain_community.chat_models.vertexai"
    if module_name in sys.modules:
        return

    vertexai_module = types.ModuleType(module_name)

    class ChatVertexAI:  # pragma: no cover - only used as an import shim.
        def __init__(self, *args, **kwargs):
            raise RuntimeError("VertexAI is not configured for this project.")

    vertexai_module.ChatVertexAI = ChatVertexAI
    sys.modules[module_name] = vertexai_module


def build_ragas_metrics():
    """Return the four core RAGAS metrics for this project.

    Ragas has used both class-based and module-level metric APIs across
    versions, so this keeps the script usable across the supported range.
    """
    patch_optional_ragas_imports()

    try:
        from ragas.metrics import (
            Faithfulness,
            LLMContextPrecisionWithReference,
            LLMContextRecall,
            ResponseRelevancy,
        )

        return [
            Faithfulness(),
            ResponseRelevancy(),
            LLMContextPrecisionWithReference(),
            LLMContextRecall(),
        ]
    except ImportError:
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        return [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ]


def run_ragas(records: list[dict[str, object]], output_path: Path) -> None:
    from ragas import EvaluationDataset, evaluate

    dataset = EvaluationDataset.from_list(records)
    evaluator_llm = build_azure_evaluator_llm()
    result = evaluate(
        dataset=dataset,
        metrics=build_ragas_metrics(),
        llm=evaluator_llm,
    )

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
