import signal
import sys
import threading

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtWidgets import QApplication

import config
from app.audio import AudioCaptureEngine
from app.copilot import LiveCopilot
from app.rag_engine import LocalRAG
from app.state import MeetingState
from app.summarizer import summarize_and_save
from app.transcriber import TranscriptionService
from ui.overlay import SynapseOverlay
from ui.signals import OverlaySignals


def _install_sigint_handler(application: QApplication) -> QTimer:
    signal.signal(signal.SIGINT, lambda *_: application.quit())
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(250)
    return timer


def _run_application() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("SynapseLive.ai")
    sigint_timer = _install_sigint_handler(application)
    signals = OverlaySignals()
    state = MeetingState()

    def report_error(message: str) -> None:
        print(f"[SynapseLive] {message}", flush=True)
        signals.status_changed.emit(message)

    print("[SynapseLive] Initializing local knowledge base...", flush=True)
    rag = LocalRAG()
    rag.ingest_directory()
    copilot = LiveCopilot(
        rag,
        on_error=report_error,
        on_quota=signals.quota_alert.emit,
    )

    def show_transcript(entry) -> None:
        print(f"{entry.speaker}: {entry.text}", flush=True)
        signals.transcript_received.emit(entry.speaker, entry.text)

    def show_cue(text: str) -> None:
        print(f"[Cue] {text}", flush=True)
        signals.cue_received.emit(text)

    transcriber = TranscriptionService(
        state=state,
        copilot=copilot,
        on_transcript=show_transcript,
        on_cue=show_cue,
        on_error=report_error,
    )
    audio = AudioCaptureEngine(on_audio=transcriber.submit, on_error=report_error)
    save_lock = threading.Lock()

    def save_meeting() -> None:
        if not save_lock.acquire(blocking=False):
            return
        signals.saving_changed.emit(True)

        def save_worker() -> None:
            try:
                audio.stop()
                transcriber.stop()
                output_path = summarize_and_save(
                    state,
                    on_quota=signals.quota_alert.emit,
                )
                if output_path is None:
                    message = "Transcript too short to summarize."
                    print(f"[SynapseLive] {message}", flush=True)
                    signals.summary_status.emit(message)
                    return
                if output_path.name.startswith("meeting_raw_"):
                    print(f"[SynapseLive] Raw transcript saved: {output_path}", flush=True)
                    return
                state.clear()
                message = f"Saved notes: {output_path}"
                print(f"[SynapseLive] {message}", flush=True)
                signals.summary_status.emit("Notes saved")
            except Exception as error:
                message = f"Could not save notes: {error}"
                report_error(message)
            finally:
                signals.saving_changed.emit(False)
                save_lock.release()

        threading.Thread(target=save_worker, daemon=True, name="meeting-save").start()

    overlay = SynapseOverlay(
        signals,
        on_end_call=save_meeting,
        has_unsaved=lambda: bool(state.snapshot()),
    )

    def shutdown() -> None:
        audio.stop()
        transcriber.stop()

    application.aboutToQuit.connect(shutdown)
    transcriber.start()
    try:
        audio.start()
        signals.status_changed.emit("Listening to mic and speaker")
    except Exception as error:
        report_error(f"Audio capture could not start: {error}")

    overlay.show()
    return application.exec()


def main() -> int:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(config.DATA_DIR / "synapselive.lock"))
    if not lock.tryLock(100):
        print("SynapseLive is already running. Close the other instance first.", flush=True)
        return 1

    try:
        return _run_application()
    finally:
        lock.unlock()


if __name__ == "__main__":
    raise SystemExit(main())
