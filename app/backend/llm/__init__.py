from app.backend.llm.query import ask_fastcolis
from app.backend.llm.sources import detect_sources_in_question, resolve_scope

__all__ = ["ask_fastcolis", "detect_sources_in_question", "resolve_scope"]
