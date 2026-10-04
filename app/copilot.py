from collections.abc import Callable

from app import llm
from app.rag_engine import LocalRAG
from config import CACHE_SIMILARITY_THRESHOLD, RAG_TOP_K


class LiveCopilot:
    def __init__(
        self,
        rag: LocalRAG,
        on_error: Callable[[str], None] | None = None,
    ):
        self.rag = rag
        self.on_error = on_error or (lambda message: print(message))

    def generate_cue(self, speaker: str, transcript: str) -> str | None:
        cached = self.rag.check_cache(
            transcript,
            similarity_threshold=CACHE_SIMILARITY_THRESHOLD,
        )
        if cached is not None:
            return None if cached == "NO_CUE" else cached

        context = self.rag.query(transcript, top_k=RAG_TOP_K)
        prompt = f"""You are SynapseLive.ai, a concise live meeting co-pilot.
Analyze one line from an ongoing conversation.

Speaker: {speaker}
Relevant project context:
{context or "No relevant project context was found."}

Rules:
- For a technical or project question from [Speaker], give [You] one accurate talking point or direct answer, at most 15 words.
- For [You], only cue an immediate commitment, follow-up, or important correction.
- For ordinary small talk or non-actionable lines, respond exactly NO_CUE.
- Return only the cue text or NO_CUE.

Transcript line: {transcript}
"""
        try:
            cue = llm.generate(prompt).strip()
        except Exception as error:
            self.on_error(f"LLM cue generation failed: {error}")
            return None

        if not cue:
            return None
        self.rag.store_cache(transcript, cue)
        return None if cue == "NO_CUE" else cue
