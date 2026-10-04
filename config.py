from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR / "app"
DOCS_DIR = BASE_DIR / "docs"
DATA_DIR = BASE_DIR / "data"
LANCEDB_DIR = DATA_DIR / "lancedb"
NOTES_DIR = BASE_DIR / "notes"
UI_STATE = DATA_DIR / "ui_state.json"

NATIVE_SAMPLE_RATE = 48_000
TARGET_SAMPLE_RATE = 16_000
AUDIO_CHUNK_SECONDS = 3
AUDIO_BLOCK_SIZE = 4_096
MIN_RMS = 0.01
HALLUCINATIONS = frozenset({
	"bye",
	"bye!",
	"you",
	"thank you",
	"thank you.",
	"mb1",
	"subtitles by",
	"donga!",
})

WHISPER_MODEL_SIZE = "base.en"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_FALLBACK_MODEL = "gemini-3.5-flash-lite"
CUE_MODEL_CHAIN = (GEMINI_FALLBACK_MODEL,)
SUMMARY_MODEL_CHAIN = (GEMINI_MODEL, GEMINI_FALLBACK_MODEL)
MODEL_CHAIN = SUMMARY_MODEL_CHAIN
PLANS_URL = "https://ai.google.dev/gemini-api/docs/rate-limits"
RAG_TOP_K = 2
CACHE_SIMILARITY_THRESHOLD = 0.88
OVERLAY_WIDTH = 410
OVERLAY_HEIGHT = 390
OVERLAY_MARGIN_RIGHT = 24
OVERLAY_MARGIN_BOTTOM = 24
