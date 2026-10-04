from PySide6.QtCore import QObject, Signal


class OverlaySignals(QObject):
    transcript_received = Signal(str, str)
    cue_received = Signal(str)
    status_changed = Signal(str)
    saving_changed = Signal(bool)
