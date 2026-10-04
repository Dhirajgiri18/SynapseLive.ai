import re

import numpy as np

import config


def rms(audio: np.ndarray) -> float:
    samples = np.asarray(audio, dtype=np.float32)
    if not samples.size:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples))))


def normalize_gently(
    audio: np.ndarray,
    target_peak: float = 0.9,
    max_gain: float = 4.0,
) -> np.ndarray:
    samples = np.asarray(audio, dtype=np.float32)
    if not samples.size:
        return samples
    peak = float(np.max(np.abs(samples)))
    if peak <= 0:
        return samples
    gain = min(target_peak / peak, max_gain)
    return (samples * gain).astype(np.float32)


def is_hallucination(text: str) -> bool:
    normalized = text.strip().lower()
    if normalized in config.HALLUCINATIONS:
        return True

    words = re.findall(r"[a-z']+", normalized)
    if not words:
        return True
    if len(words) >= 3 and len(set(words)) == 1:
        return True
    if len(words) >= 4 and len(set(words)) / len(words) <= 0.34:
        return True
    return False
