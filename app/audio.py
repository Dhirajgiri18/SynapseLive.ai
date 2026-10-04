import queue
import threading
import warnings
from collections import defaultdict
from collections.abc import Callable

import numpy as np
import soundcard as sc
from scipy.signal import resample_poly

from config import (
    AUDIO_BLOCK_SIZE,
    AUDIO_CHUNK_SECONDS,
    NATIVE_SAMPLE_RATE,
    TARGET_SAMPLE_RATE,
)

warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)

AudioCallback = Callable[[str, np.ndarray], None]
ErrorCallback = Callable[[str], None]


class AudioCaptureEngine:
    def __init__(
        self,
        on_audio: AudioCallback,
        on_error: ErrorCallback | None = None,
        block_size: int = AUDIO_BLOCK_SIZE,
        chunk_seconds: int = AUDIO_CHUNK_SECONDS,
    ):
        self.on_audio = on_audio
        self.on_error = on_error or (lambda message: print(message))
        self.block_size = block_size
        self.chunk_seconds = chunk_seconds
        self._stop_event = threading.Event()
        self._audio_queue: queue.Queue[tuple[str, np.ndarray] | None] = queue.Queue()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        if self._threads:
            return
        speaker = sc.default_speaker()
        microphone = sc.default_microphone()
        if speaker is None or microphone is None:
            raise RuntimeError("A default speaker and microphone are required.")

        loopback = sc.get_microphone(id=str(speaker.id), include_loopback=True)
        self._stop_event.clear()
        self._threads = [
            threading.Thread(target=self._process_audio, daemon=True, name="audio-processor"),
            threading.Thread(
                target=self._capture_stream,
                args=(microphone, "[You]"),
                daemon=True,
                name="microphone-capture",
            ),
            threading.Thread(
                target=self._capture_stream,
                args=(loopback, "[Speaker]"),
                daemon=True,
                name="loopback-capture",
            ),
        ]
        for thread in self._threads:
            thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._audio_queue.put(None)
        for thread in self._threads:
            if thread is not threading.current_thread():
                thread.join(timeout=2)
        self._threads.clear()

    def _capture_stream(self, device, speaker_tag: str) -> None:
        try:
            with device.recorder(samplerate=NATIVE_SAMPLE_RATE) as recorder:
                while not self._stop_event.is_set():
                    data = recorder.record(numframes=self.block_size)
                    if data is None or len(data) == 0:
                        continue
                    mono_audio = np.asarray(data, dtype=np.float32).mean(axis=1)
                    self._audio_queue.put((speaker_tag, mono_audio))
        except Exception as error:
            if not self._stop_event.is_set():
                self.on_error(f"Audio stream {speaker_tag} failed: {error}")

    def _process_audio(self) -> None:
        buffers: dict[str, list[np.ndarray]] = defaultdict(list)
        buffered_samples: dict[str, int] = defaultdict(int)
        required_samples = NATIVE_SAMPLE_RATE * self.chunk_seconds
        gcd = int(np.gcd(NATIVE_SAMPLE_RATE, TARGET_SAMPLE_RATE))
        up = TARGET_SAMPLE_RATE // gcd
        down = NATIVE_SAMPLE_RATE // gcd

        while not self._stop_event.is_set():
            try:
                item = self._audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is None:
                break

            speaker_tag, chunk = item
            buffers[speaker_tag].append(chunk)
            buffered_samples[speaker_tag] += len(chunk)
            if buffered_samples[speaker_tag] < required_samples:
                continue

            raw_audio = np.concatenate(buffers[speaker_tag])
            buffers[speaker_tag].clear()
            buffered_samples[speaker_tag] = 0
            audio_16k = resample_poly(raw_audio, up, down).astype(np.float32)
            try:
                self.on_audio(speaker_tag, audio_16k)
            except Exception as error:
                self.on_error(f"Audio processing failed for {speaker_tag}: {error}")
