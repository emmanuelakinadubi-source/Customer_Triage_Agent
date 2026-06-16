from __future__ import annotations

import asyncio
import sys
import types
from hashlib import blake2b
from math import sqrt
import re

from app.core.config import settings


RAGAS_CONTEXTS_KEY = "_ragas_retrieved_contexts"
RAGAS_METRIC_PREFIX = "ragas_"
RAGAS_SCORE_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)


class LocalHashRagasEmbeddings:
    TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
    SYNONYMS = {
        "refund": ("return", "moneyback"),
        "refunded": ("refund", "return", "moneyback"),
        "return": ("refund", "returned"),
        "returned": ("return", "refund"),
        "non": ("nonreturnable",),
        "returnable": ("nonreturnable",),
        "software": ("downloadable", "digital", "product"),
        "downloadable": ("software", "digital"),
        "digital": ("software", "downloadable"),
        "bought": ("purchase", "purchased", "product"),
        "purchase": ("bought", "product"),
        "purchased": ("bought", "purchase", "product"),
        "products": ("product", "purchase"),
        "item": ("product", "purchase"),
        "items": ("item", "product", "purchase"),
        "cannot": ("not", "ineligible"),
        "eligible": ("eligibility", "returnable"),
        "ineligible": ("cannot", "not"),
    }

    def set_run_config(self, run_config):
        self.run_config = run_config

    def embed_query(self, text: str) -> list[float]:
        dimensions = settings.RAG_EMBEDDING_DIMENSIONS
        vector = [0.0] * dimensions
        for feature, weight in self._features(text):
            digest = blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign * weight

        magnitude = sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector

        return [value / magnitude for value in vector]

    def _features(self, text: str) -> list[tuple[str, float]]:
        normalized = text.lower()
        tokens = self.TOKEN_PATTERN.findall(normalized)
        features: list[tuple[str, float]] = []
        for token in tokens:
            features.append((f"tok:{token}", 1.0))
            for synonym in self.SYNONYMS.get(token, ()):
                features.append((f"tok:{synonym}", 0.9))
            if token.endswith("s") and len(token) > 3:
                features.append((f"tok:{token[:-1]}", 0.7))

        compact = "".join(tokens)
        for size in (3, 4, 5):
            for index in range(max(0, len(compact) - size + 1)):
                features.append((f"char:{compact[index:index + size]}", 0.2))

        return features

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    async def embed_text(self, text: str, is_async=True) -> list[float]:
        return self.embed_query(text)

    async def embed_texts(self, texts: list[str], is_async: bool = True) -> list[list[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        return self.embed_query(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)


class RagasEvaluationService:
    async def evaluate_response(
        self,
        *,
        user_input: str,
        response: str | None,
        retrieved_contexts: list[str],
        reference: str | None = None,
    ) -> dict[str, float]:
        if not response or not retrieved_contexts:
            return {}

        return await asyncio.to_thread(
            self._evaluate_response_sync,
            user_input=user_input,
            response=response,
            retrieved_contexts=retrieved_contexts,
            reference=reference,
        )

    def _evaluate_response_sync(
        self,
        *,
        user_input: str,
        response: str,
        retrieved_contexts: list[str],
        reference: str | None = None,
    ) -> dict[str, float]:
        self._patch_optional_ragas_imports()

        from ragas import SingleTurnSample
        from ragas.metrics import (
            Faithfulness,
            LLMContextPrecisionWithoutReference,
            LLMContextRecall,
            ResponseRelevancy,
        )

        sample = SingleTurnSample(
            user_input=user_input,
            response=response,
            retrieved_contexts=retrieved_contexts,
            reference=reference or response,
        )

        evaluator_llm = self._build_azure_evaluator_llm()
        embeddings = LocalHashRagasEmbeddings()

        metrics = {
            "faithfulness": Faithfulness(),
            "answer_relevancy": ResponseRelevancy(),
            "context_precision": LLMContextPrecisionWithoutReference(),
            "context_recall": LLMContextRecall(),
        }
        for metric in metrics.values():
            if hasattr(metric, "llm"):
                metric.llm = evaluator_llm
            if hasattr(metric, "embeddings"):
                metric.embeddings = embeddings

        scores = {}
        for metric_name, metric in metrics.items():
            scores[metric_name] = float(metric.single_turn_score(sample))

        return scores

    def _build_azure_evaluator_llm(self):
        self._patch_optional_ragas_imports()

        from langchain_openai import AzureChatOpenAI
        from ragas.llms import LangchainLLMWrapper

        evaluator_llm = AzureChatOpenAI(
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            temperature=0.0,
        )
        return LangchainLLMWrapper(evaluator_llm)

    @staticmethod
    def _patch_optional_ragas_imports() -> None:
        module_name = "langchain_community.chat_models.vertexai"
        if module_name in sys.modules:
            return

        vertexai_module = types.ModuleType(module_name)

        class ChatVertexAI:  # pragma: no cover - only used as an import shim.
            def __init__(self, *args, **kwargs):
                raise RuntimeError("VertexAI is not configured for this project.")

        vertexai_module.ChatVertexAI = ChatVertexAI
        sys.modules[module_name] = vertexai_module


ragas_service = RagasEvaluationService()
