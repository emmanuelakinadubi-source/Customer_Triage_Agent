from contextlib import contextmanager

from app.core.config import settings

try:
    from langfuse import Langfuse
except Exception:  # pragma: no cover - Langfuse is optional for local tests.
    Langfuse = None


class NoopObservation:
    def update(self, **kwargs):
        return None

    def set_trace_io(self, **kwargs):
        return None

    def score(self, **kwargs):
        return None


class LangfuseService:
    def __init__(self):
        self.enabled = bool(
            settings.LANGFUSE_PUBLIC_KEY
            and settings.LANGFUSE_SECRET_KEY
            and Langfuse is not None
        )
        self.client = (
            Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                base_url=settings.LANGFUSE_BASE_URL,
            )
            if self.enabled
            else None
        )

    @contextmanager
    def observation(self, *, name: str, as_type: str = "span", **kwargs):
        if not self.enabled:
            yield NoopObservation()
            return

        with self.client.start_as_current_observation(
            name=name,
            as_type=as_type,
            **kwargs,
        ) as observation:
            yield observation
        self.flush()

    def flush(self):
        if self.enabled:
            self.client.flush()


langfuse_service = LangfuseService()
