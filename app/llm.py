import threading
import time

from google import genai
from google.genai import types

import config
from local_secrets import GEMINI_API_KEY


_PLACEHOLDER_PREFIX = "PASTE_"
COOLDOWN_SECONDS = 60

_client = None
_client_lock = threading.Lock()
_cooldown_until: dict[str, float] = {}
_cooldown_lock = threading.Lock()
_generate_config = types.GenerateContentConfig(
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
)


def _get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def generate(prompt: str) -> str:
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith(_PLACEHOLDER_PREFIX):
        raise RuntimeError(
            "Set GEMINI_API_KEY in the ignored local_secrets.py before using Gemini."
        )

    now = time.monotonic()
    with _cooldown_lock:
        candidates = [
            model for model in config.MODEL_CHAIN
            if _cooldown_until.get(model, 0) <= now
        ] or list(config.MODEL_CHAIN)

    client = _get_client()
    last_error = None
    for model_name in candidates:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=_generate_config,
            )
            text = (response.text or "").strip()
            if text:
                return text
            last_error = RuntimeError(f"{model_name} returned an empty response")
        except Exception as error:
            last_error = error
        with _cooldown_lock:
            _cooldown_until[model_name] = time.monotonic() + COOLDOWN_SECONDS
        warning = f"[LLM] {model_name} failed: {last_error}"
        try:
            print(f"⚠️ {warning}", flush=True)
        except UnicodeEncodeError:
            print(f"WARNING {warning}", flush=True)

    raise RuntimeError("All configured Gemini models failed.") from last_error
