from dataclasses import dataclass
from datetime import datetime
from threading import Lock


@dataclass(frozen=True)
class TranscriptEntry:
    speaker: str
    text: str
    timestamp: datetime


class MeetingState:
    def __init__(self):
        self._entries: list[TranscriptEntry] = []
        self._lock = Lock()

    def add_transcript(self, speaker: str, text: str) -> TranscriptEntry:
        entry = TranscriptEntry(speaker=speaker, text=text, timestamp=datetime.now())
        with self._lock:
            self._entries.append(entry)
        return entry

    def snapshot(self) -> list[TranscriptEntry]:
        with self._lock:
            return list(self._entries)

    def transcript_text(self) -> str:
        return "\n".join(
            f"[{entry.timestamp:%H:%M:%S}] {entry.speaker}: {entry.text}"
            for entry in self.snapshot()
        )
