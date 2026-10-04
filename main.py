import sys
import threading

from PySide6.QtWidgets import QApplication

from app.audio import AudioCaptureEngine
from app.copilot import LiveCopilot
from app.rag_engine import LocalRAG
from app.state import MeetingState
from app.summarizer import summarize_and_save
from app.transcriber import TranscriptionService
from ui.overlay import SynapseOverlay
from ui.signals import OverlaySignals


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("SynapseLive.ai")
    signals = OverlaySignals()
    state = MeetingState()

    def report_error(message: str) -> None:
        print(f"[SynapseLive] {message}", flush=True)
        signals.status_changed.emit(message)

    print("[SynapseLive] Initializing local knowledge base...", flush=True)
    rag = LocalRAG()
    rag.ingest_directory()
    copilot = LiveCopilot(rag, on_error=report_error)

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
                output_path = summarize_and_save(state)
                message = f"Saved notes: {output_path}"
                print(f"[SynapseLive] {message}", flush=True)
                signals.status_changed.emit("Notes saved")
            except Exception as error:
                message = f"Could not save notes: {error}"
                report_error(message)
            finally:
                signals.saving_changed.emit(False)
                save_lock.release()

        threading.Thread(target=save_worker, daemon=True, name="meeting-save").start()

    overlay = SynapseOverlay(signals, on_end_call=save_meeting)

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


if __name__ == "__main__":
    raise SystemExit(main())
