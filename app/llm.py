import re
import threading
import time

from google import genai
from google.genai import types

import config
from local_secrets import GEMINI_API_KEY


_PLACEHOLDER_PREFIX = "PASTE_"
COOLDOWN_SECONDS = 60
MAX_COOLDOWN_SECONDS = 6 * 60 * 60
MAX_QUOTA_WAIT_SECONDS = 24 * 60 * 60

_client = None
_client_lock = threading.Lock()
_cooldown_until: dict[str, float] = {}
_quota_until: dict[str, float] = {}
_cooldown_lock = threading.Lock()
_generate_config = types.GenerateContentConfig(
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
)


class QuotaExhausted(RuntimeError):
    """Every model in the requested chain has reached its daily quota."""

    def __init__(self, retry_seconds: float):
        super().__init__("Gemini daily quota exhausted")
        self.retry_seconds = retry_seconds


def _get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _is_quota_error(error: Exception) -> bool:
    return getattr(error, "code", None) == 429 or "RESOURCE_EXHAUSTED" in str(error)


def _is_daily_quota(error: Exception) -> bool:
    return _is_quota_error(error) and "PerDay" in str(error)


def _retry_seconds(error: Exception) -> float | None:
    match = re.search(
        r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s",
        str(error),
    )
    return float(match.group(1)) if match else None


def _all_quota_blocked(models: list[str]) -> bool:
    if not models:
        return False
    now = time.monotonic()
    with _cooldown_lock:
        return all(_quota_until.get(model, 0) > now for model in models)


def _quota_wait(models: list[str]) -> float:
    now = time.monotonic()
    with _cooldown_lock:
        recoveries = [_quota_until[model] for model in models if model in _quota_until]
    return max(0.0, min(recoveries) - now) if recoveries else 0.0


def describe_quota(error: QuotaExhausted) -> str:
    hours, remainder = divmod(int(error.retry_seconds), 3600)
    minutes = remainder // 60
    wait = f"{hours}h {minutes}m" if hours else f"{max(minutes, 1)}m"
    return (
        f"Daily limit reached. Cues and summaries paused for about {wait}. "
        "Upgrade for more usage."
    )


def reset_quota_state() -> None:
    """Clear remembered quota and transient cooldowns after billing changes."""
    with _cooldown_lock:
        _quota_until.clear()
        _cooldown_until.clear()


def _cooldown_for(error: Exception) -> float:
    match = re.search(
        r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s",
        str(error),
    )
    if match:
        return min(max(float(match.group(1)), COOLDOWN_SECONDS), MAX_COOLDOWN_SECONDS)
    return COOLDOWN_SECONDS


def generate(
    prompt: str,
    chain: tuple[str, ...] | None = None,
    temperature: float | None = None,
) -> str:
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith(_PLACEHOLDER_PREFIX):
        raise RuntimeError(
            "Set GEMINI_API_KEY in the ignored local_secrets.py before using Gemini."
        )

    model_chain = chain or config.MODEL_CHAIN
    with _cooldown_lock:
        now = time.monotonic()
        if model_chain and all(_quota_until.get(model, 0) > now for model in model_chain):
            retry_seconds = max(
                0.0,
                min(_quota_until[model] for model in model_chain) - now,
            )
            raise QuotaExhausted(retry_seconds)

        usable_models = [
            model for model in model_chain
            if _quota_until.get(model, 0) <= now
        ]
        candidates = [
            model for model in usable_models
            if _cooldown_until.get(model, 0) <= now
        ] or usable_models

    client = _get_client()
    generate_config = _generate_config
    if temperature is not None:
        generate_config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=temperature,
        )
    last_error = None
    for model_name in candidates:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=generate_config,
            )
            text = (response.text or "").strip()
            if text:
                return text
            last_error = RuntimeError(f"{model_name} returned an empty response")
        except Exception as error:
            last_error = error
        with _cooldown_lock:
            now = time.monotonic()
            if _is_daily_quota(last_error):
                delay = _retry_seconds(last_error) or 3600
                _quota_until[model_name] = now + min(
                    max(delay, COOLDOWN_SECONDS),
                    MAX_QUOTA_WAIT_SECONDS,
                )
            else:
                delay = max(_retry_seconds(last_error) or 0, COOLDOWN_SECONDS)
                _cooldown_until[model_name] = now + min(delay, MAX_COOLDOWN_SECONDS)
        warning = f"[LLM] {model_name} failed: {str(last_error)[:160]}"
        try:
            print(f"⚠️ {warning}", flush=True)
        except UnicodeEncodeError:
            print(f"WARNING {warning}", flush=True)

    if _all_quota_blocked(model_chain):
        raise QuotaExhausted(_quota_wait(model_chain))
    raise RuntimeError("All configured Gemini models failed.") from last_error
