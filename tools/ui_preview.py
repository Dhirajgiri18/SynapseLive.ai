import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ui.overlay import SynapseOverlay
from ui.signals import OverlaySignals


application = QApplication.instance() or QApplication(sys.argv)
signals = OverlaySignals()
overlay = SynapseOverlay(
    signals,
    on_end_call=lambda: _preview_save(signals),
    has_unsaved=lambda: True,
)
overlay.show()

transcript_lines = [
    ("[Speaker]", "What is the expected response latency?"),
    ("[You]", "About two seconds end to end."),
]
cues = [
    "Target: under two seconds end to end.",
    "Use the local Whisper model for transcription.",
]
step = 0


def _preview_save(preview_signals: OverlaySignals) -> None:
    preview_signals.saving_changed.emit(True)
    QTimer.singleShot(
        350,
        lambda: preview_signals.summary_status.emit("Saved (preview)"),
    )


def emit_preview_update() -> None:
    global step
    speaker, text = transcript_lines[step % len(transcript_lines)]
    signals.transcript_received.emit(speaker, text)
    if speaker == "[Speaker]":
        signals.cue_received.emit(cues[(step // 2) % len(cues)])
    step += 1


preview_timer = QTimer()
preview_timer.timeout.connect(emit_preview_update)
preview_timer.start(3000)
auto_close_ms = int(os.environ.get("SYNAPSE_UI_PREVIEW_AUTOCLOSE_MS", "0"))
auto_close_timer = None
if auto_close_ms > 0:
    auto_close_timer = QTimer()
    auto_close_timer.setSingleShot(True)
    auto_close_timer.timeout.connect(lambda: application.exit(0))
    auto_close_timer.start(auto_close_ms)
raise SystemExit(application.exec())
