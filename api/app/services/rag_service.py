import re
from dataclasses import dataclass
from functools import lru_cache
from hashlib import blake2b
from math import sqrt
from pathlib import Path

from app.core.config import settings


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
SECTION_PATTERN = re.compile(r"(?m)^##\s+(.+)$")
PLAIN_HEADING_PATTERN = re.compile(r"(?m)^([A-Z][A-Z0-9 /&()-]{2,})$")
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
REQUIRED_RETURN_SECTIONS = ("timeframe", "non-returnable")
NON_RETURNABLE_QUERY_PATTERNS = (
    re.compile(r"\bgift[-\s]?cards?\b", re.IGNORECASE),
    re.compile(
        r"\b(?:downloadable\s+)?software(?:\s+products?)?\b|\bsoftware\s+downloads?\b|\bdigital\s+downloads?\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:custom[-\s]?made|personalized)\s+items?\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class RetrievedChunk:
    section: str
    text: str
    source: str
    score: float


@dataclass(frozen=True)
class PolicyChunk:
    section: str
    text: str
    source: str
    embedding: tuple[float, ...]


class PolicyRAGService:
    def __init__(
        self,
        document_path: str | None = None,
        document_paths: list[str] | tuple[str, ...] | str | None = None,
        top_k: int | None = None,
        chunk_token_size: int | None = None,
        chunk_token_overlap: int | None = None,
        embedding_dimensions: int | None = None,
    ):
        configured_paths = document_paths or settings.RAG_POLICY_DOCUMENT_PATHS
        if document_path is not None:
            configured_paths = [document_path]

        self.document_paths = self._normalize_document_paths(configured_paths)
        self.document_path = self.document_paths[0] if self.document_paths else settings.RAG_POLICY_DOCUMENT_PATH
        self.top_k = top_k or settings.RAG_TOP_K
        self.chunk_token_size = chunk_token_size or settings.RAG_CHUNK_TOKEN_SIZE
        self.chunk_token_overlap = chunk_token_overlap or settings.RAG_CHUNK_TOKEN_OVERLAP
        self.embedding_dimensions = embedding_dimensions or settings.RAG_EMBEDDING_DIMENSIONS

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        is_return_policy_query = bool(query_tokens & RETURN_POLICY_TERMS)
        is_non_returnable_item_query = self._is_non_returnable_item_query(query)
        required_return_sections = self._required_return_sections(query)
        query_embedding = self._embed_text(query, self.embedding_dimensions)
        scored_chunks = []
        for document_path in self._resolve_document_paths():
            for chunk in self._load_chunks(
                document_path,
                self.chunk_token_size,
                self.chunk_token_overlap,
                self.embedding_dimensions,
            ):
                lexical_score = len(query_tokens & self._tokenize(f"{chunk.section} {chunk.text}"))
                score = self._cosine_similarity(query_embedding, chunk.embedding)
                section_name = chunk.section.lower()
                if is_non_returnable_item_query and "timeframe" in section_name:
                    continue
                if (
                    is_non_returnable_item_query
                    and (
                        chunk.source != "refund_policy.txt"
                        or "non-returnable" not in section_name
                    )
                ):
                    continue
                is_required_return_section = is_return_policy_query and any(
                    required in section_name for required in required_return_sections
                )
                if is_required_return_section:
                    score += 100

                if score > 0 or lexical_score > 0:
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

    @staticmethod
    def _required_return_sections(query: str) -> tuple[str, ...]:
        if PolicyRAGService._is_non_returnable_item_query(query):
            return ("non-returnable",)

        return REQUIRED_RETURN_SECTIONS

    @staticmethod
    def _is_non_returnable_item_query(query: str) -> bool:
        return any(pattern.search(query) for pattern in NON_RETURNABLE_QUERY_PATTERNS)

    def build_context(self, query: str) -> str:
        chunks = self.retrieve(query)
        if not chunks:
            return ""

        return "\n\n".join(
            f"Source: {chunk.source}\nSection: {chunk.section}\n{chunk.text.strip()}"
            for chunk in chunks
        )

    def _resolve_document_paths(self) -> tuple[Path, ...]:
        return tuple(self._resolve_document_path(path) for path in self.document_paths)

    @staticmethod
    def _resolve_document_path(document_path: str) -> Path:
        configured_path = Path(document_path)
        if configured_path.is_absolute():
            return configured_path

        service_path = Path(__file__).resolve()
        candidate_roots = (
            service_path.parents[3],
            service_path.parents[2],
            Path.cwd(),
        )
        for root in candidate_roots:
            candidate = root / configured_path
            if candidate.exists():
                return candidate

        return candidate_roots[0] / configured_path

    @staticmethod
    def _normalize_document_paths(
        document_paths: list[str] | tuple[str, ...] | str,
    ) -> tuple[str, ...]:
        if isinstance(document_paths, str):
            paths = document_paths.split(",")
        else:
            paths = document_paths

        return tuple(path.strip() for path in paths if path and path.strip())

    @staticmethod
    @lru_cache(maxsize=8)
    def _load_chunks(
        document_path: Path,
        chunk_token_size: int,
        chunk_token_overlap: int,
        embedding_dimensions: int,
    ) -> tuple[PolicyChunk, ...]:
        if not document_path.exists():
            return tuple()

        document_text = document_path.read_text(encoding="utf-8")
        sections = PolicyRAGService._split_sections(document_text, document_path.stem)
        chunks = []

        for section, text in sections:
            for chunk_index, chunk_text in enumerate(
                PolicyRAGService._split_token_windows(
                    text,
                    chunk_token_size,
                    chunk_token_overlap,
                ),
                start=1,
            ):
                chunk_section = section
                if len(PolicyRAGService._tokenize(text)) > chunk_token_size:
                    chunk_section = f"{section} chunk {chunk_index}"

                chunks.append(
                    PolicyChunk(
                        section=chunk_section,
                        text=chunk_text,
                        source=document_path.name,
                        embedding=PolicyRAGService._embed_text(
                            f"{chunk_section} {chunk_text}",
                            embedding_dimensions,
                        ),
                    )
                )

        return tuple(chunks)

    @staticmethod
    def _split_sections(document_text: str, default_section: str) -> list[tuple[str, str]]:
        markdown_matches = list(SECTION_PATTERN.finditer(document_text))
        if markdown_matches:
            return PolicyRAGService._sections_from_matches(document_text, markdown_matches)

        heading_matches = list(PLAIN_HEADING_PATTERN.finditer(document_text))
        if heading_matches:
            return PolicyRAGService._sections_from_matches(document_text, heading_matches)

        cleaned_text = document_text.strip()
        return [(default_section, cleaned_text)] if cleaned_text else []

    @staticmethod
    def _sections_from_matches(
        document_text: str,
        matches: list[re.Match[str]],
    ) -> list[tuple[str, str]]:
        sections = []
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(document_text)
            section = next(group for group in match.groups() if group).strip()
            text = document_text[start:end].strip()
            if (
                text
                and index + 1 < len(matches)
                and matches[index + 1].group(1).strip().lower() == "owner assignment"
                and section.lower() != "owner assignment"
            ):
                owner_start = matches[index + 1].end()
                owner_end = matches[index + 2].start() if index + 2 < len(matches) else len(document_text)
                owner_text = document_text[owner_start:owner_end].strip()
                if owner_text:
                    text = f"{text}\n\nOWNER ASSIGNMENT\n{owner_text}"
            if text:
                sections.append((section, text))
        return sections

    @staticmethod
    def _split_token_windows(
        text: str,
        chunk_token_size: int,
        chunk_token_overlap: int,
    ) -> list[str]:
        words = text.split()
        if not words:
            return []
        if len(words) <= chunk_token_size:
            return [text.strip()]

        overlap = max(0, min(chunk_token_overlap, chunk_token_size - 1))
        step = chunk_token_size - overlap
        chunks = []
        for start in range(0, len(words), step):
            window = words[start : start + chunk_token_size]
            if not window:
                break
            chunks.append(" ".join(window).strip())
            if start + chunk_token_size >= len(words):
                break
        return chunks

    @staticmethod
    def _embed_text(text: str, dimensions: int) -> tuple[float, ...]:
        vector = [0.0] * dimensions
        for token in PolicyRAGService._tokenize(text):
            digest = blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        magnitude = sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return tuple(vector)

        return tuple(value / magnitude for value in vector)

    @staticmethod
    def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        return sum(left_value * right_value for left_value, right_value in zip(left, right))

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {
            token
            for token in TOKEN_PATTERN.findall(text.lower())
            if token not in STOP_WORDS and len(token) > 1
        }


rag_service = PolicyRAGService()
