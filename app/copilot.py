import threading
import time
from collections.abc import Callable

from app import llm
from app.rag_engine import LocalRAG
from config import CACHE_SIMILARITY_THRESHOLD, CUE_MODEL_CHAIN, RAG_TOP_K

MIN_CUE_INTERVAL = 8.0
QUESTION_WORDS = {
    "what", "how", "why", "when", "where", "who", "which",
    "can", "could", "would", "should", "do", "does", "did",
    "is", "are", "will",
}


class LiveCopilot:
    def __init__(
        self,
        rag: LocalRAG,
        on_error: Callable[[str], None] | None = None,
        on_quota: Callable[[str], None] | None = None,
    ):
        self.rag = rag
        self.on_error = on_error or (lambda message: print(message))
        self.on_quota = on_quota or (lambda message: print(message))
        self._cue_lock = threading.Lock()
        self._inflight = False
        self._last_api_call = 0.0

    @staticmethod
    def _worth_a_call(speaker: str, transcript: str) -> bool:
        if speaker != "[Speaker]":
            return False
        words = transcript.split()
        if len(words) < 4:
            return False
        first_word = words[0].strip(".,!?;:'\"()[]{}")
        return "?" in transcript or first_word.lower() in QUESTION_WORDS

    def generate_cue(self, speaker: str, transcript: str) -> str | None:
        if not self._worth_a_call(speaker, transcript):
            return None

        cached = self.rag.check_cache(
            transcript,
            similarity_threshold=CACHE_SIMILARITY_THRESHOLD,
        )
        if cached is not None:
            return None if cached == "NO_CUE" else cached

        context = self.rag.query(transcript, top_k=RAG_TOP_K)
        with self._cue_lock:
            now = time.monotonic()
            if self._inflight or now - self._last_api_call < MIN_CUE_INTERVAL:
                return None
            self._inflight = True
            self._last_api_call = now

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
            cue = llm.generate(prompt, chain=CUE_MODEL_CHAIN).strip()
        except llm.QuotaExhausted as error:
            self.on_quota(llm.describe_quota(error))
            return None
        except Exception as error:
            self.on_error(f"LLM cue generation failed: {error}")
            return None
        finally:
            with self._cue_lock:
                self._inflight = False

        if not cue:
            return None
        self.rag.store_cache(transcript, cue)
        return None if cue == "NO_CUE" else cue
