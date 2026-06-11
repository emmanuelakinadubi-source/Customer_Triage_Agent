import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
SECTION_PATTERN = re.compile(r"(?m)^##\s+(.+)$")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "have",
    "how",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "our",
    "the",
    "to",
    "us",
    "was",
    "we",
    "what",
    "with",
    "you",
    "your",
}
RETURN_POLICY_TERMS = {
    "refund",
    "refunds",
    "return",
    "returns",
    "returned",
    "returning",
    "exchange",
    "exchanges",
}
REQUIRED_RETURN_SECTIONS = ("timeframe",)


@dataclass(frozen=True)
class RetrievedChunk:
    section: str
    text: str
    source: str
    score: int


class PolicyRAGService:
    def __init__(self, document_path: str | None = None, top_k: int | None = None):
        self.document_path = document_path or settings.RAG_POLICY_DOCUMENT_PATH
        self.top_k = top_k or settings.RAG_TOP_K

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        is_return_policy_query = bool(query_tokens & RETURN_POLICY_TERMS)
        scored_chunks = []
        for chunk in self._load_chunks(self._resolve_document_path()):
            chunk_tokens = self._tokenize(f"{chunk.section} {chunk.text}")
            score = len(query_tokens & chunk_tokens)
            section_name = chunk.section.lower()
            is_required_return_section = (
                is_return_policy_query
                and any(required in section_name for required in REQUIRED_RETURN_SECTIONS)
            )
            if is_required_return_section:
                score += 100

            if score > 0:
                scored_chunks.append(
                    RetrievedChunk(
                        section=chunk.section,
                        text=chunk.text,
                        source=chunk.source,
                        score=score,
                    )
                )

        scored_chunks.sort(key=lambda item: item.score, reverse=True)
        return scored_chunks[: self.top_k]

    def build_context(self, query: str) -> str:
        chunks = self.retrieve(query)
        if not chunks:
            return ""

        return "\n\n".join(
            f"Source: {chunk.source}\nSection: {chunk.section}\n{chunk.text.strip()}"
            for chunk in chunks
        )

    def _resolve_document_path(self) -> Path:
        configured_path = Path(self.document_path)
        if configured_path.is_absolute():
            return configured_path

        project_root = Path(__file__).resolve().parents[3]
        return project_root / configured_path

    @staticmethod
    @lru_cache(maxsize=8)
    def _load_chunks(document_path: Path) -> tuple[RetrievedChunk, ...]:
        if not document_path.exists():
            return tuple()

        document_text = document_path.read_text(encoding="utf-8")
        matches = list(SECTION_PATTERN.finditer(document_text))
        chunks = []

        if not matches:
            return (
                RetrievedChunk(
                    section=document_path.stem,
                    text=document_text.strip(),
                    source=document_path.name,
                    score=0,
                ),
            )

        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(document_text)
            chunks.append(
                RetrievedChunk(
                    section=match.group(1).strip(),
                    text=document_text[start:end].strip(),
                    source=document_path.name,
                    score=0,
                )
            )

        return tuple(chunks)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {
            token
            for token in TOKEN_PATTERN.findall(text.lower())
            if token not in STOP_WORDS and len(token) > 1
        }


rag_service = PolicyRAGService()
