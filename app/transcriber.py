import queue
import threading
from collections.abc import Callable

import numpy as np
from faster_whisper import WhisperModel

from app.copilot import LiveCopilot
from app.state import MeetingState, TranscriptEntry
from config import (
    AUDIO_MIN_PEAK,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
    WHISPER_MODEL_SIZE,
)


class TranscriptionService:
    def __init__(
        self,
        state: MeetingState,
        copilot: LiveCopilot,
        on_transcript: Callable[[TranscriptEntry], None],
        on_cue: Callable[[str], None],
        on_error: Callable[[str], None] | None = None,
    ):
        self.state = state
        self.copilot = copilot
        self.on_transcript = on_transcript
        self.on_cue = on_cue
        self.on_error = on_error or (lambda message: print(message))
        self._audio_queue: queue.Queue[tuple[str, np.ndarray] | None] = queue.Queue()
        self._cue_queue: queue.Queue[tuple[str, str] | None] = queue.Queue()
        self._threads: list[threading.Thread] = []
        self._model: WhisperModel | None = None
        self._running = False
        self._hallucinations = {
            "bye", "bye!", "you", "thank you", "thank you.", "mb1", "subtitles by"
        }

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._threads = [
            threading.Thread(target=self._transcription_worker, daemon=True, name="transcription-worker"),
            threading.Thread(target=self._cue_worker, daemon=True, name="cue-worker"),
        ]
        for thread in self._threads:
            thread.start()

    def submit(self, speaker: str, audio: np.ndarray) -> None:
        if self._running:
            self._audio_queue.put((speaker, audio))

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._audio_queue.put(None)
        transcription_thread = self._threads[0] if self._threads else None
        cue_thread = self._threads[1] if len(self._threads) > 1 else None
        if transcription_thread is not None and transcription_thread is not threading.current_thread():
            transcription_thread.join(timeout=3)
        self._cue_queue.put(None)
        if cue_thread is not None and cue_thread is not threading.current_thread():
            cue_thread.join(timeout=3)
        self._threads.clear()

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
        return self._model

    def _transcription_worker(self) -> None:
        while True:
            item = self._audio_queue.get()
            if item is None:
                break
            speaker, audio = item
            try:
                peak = float(np.max(np.abs(audio))) if audio.size else 0.0
                if peak < AUDIO_MIN_PEAK:
                    continue
                normalized_audio = audio / peak
                segments, _ = self._get_model().transcribe(
                    normalized_audio,
                    beam_size=3,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 400, "speech_pad_ms": 150},
                    initial_prompt=f"Conversational meeting audio stream from {speaker}.",
                )
                transcript = " ".join(segment.text for segment in segments).strip()
                normalized_text = transcript.lower().strip(" .!?,")
                if len(transcript) <= 3 or normalized_text in self._hallucinations:
                    continue
                entry = self.state.add_transcript(speaker, transcript)
                self.on_transcript(entry)
                self._cue_queue.put((speaker, transcript))
            except Exception as error:
                self.on_error(f"Transcription failed for {speaker}: {error}")

    def _cue_worker(self) -> None:
        while True:
            item = self._cue_queue.get()
            if item is None:
                break
            speaker, transcript = item
            try:
                cue = self.copilot.generate_cue(speaker, transcript)
                if cue:
                    self.on_cue(cue)
            except Exception as error:
                self.on_error(f"Cue processing failed: {error}")
