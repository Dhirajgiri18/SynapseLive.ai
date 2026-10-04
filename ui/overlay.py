import html
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import config
from ui.signals import OverlaySignals
from ui.styles import ALERT_STYLESHEET, OVERLAY_STYLESHEET


class SynapseOverlay(QWidget):
    def __init__(self, signals: OverlaySignals, on_end_call: Callable[[], None]):
        super().__init__()
        self._on_end_call = on_end_call
        self.setObjectName("overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(410, 390)
        self.setStyleSheet(OVERLAY_STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(9)

        header = QHBoxLayout()
        self.title = QLabel("SynapseLive.ai")
        self.title.setObjectName("title")
        self.status = QLabel("Starting...")
        self.status.setObjectName("status")
        self.close_button = QPushButton("×")
        self.close_button.setObjectName("close")
        self.close_button.setFixedWidth(30)
        self.close_button.setToolTip("Close")
        self.close_button.clicked.connect(self.close)
        header.addWidget(self.title)
        header.addStretch(1)
        header.addWidget(self.status)
        header.addWidget(self.close_button)
        root.addLayout(header)

        self.cue = QLabel("Listening for useful context…")
        self.cue.setObjectName("cue")
        self.cue.setWordWrap(True)
        self.cue.setOpenExternalLinks(False)
        root.addWidget(self.cue)

        self.transcript = QPlainTextEdit()
        self.transcript.setObjectName("transcript")
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText("Live transcript will appear here.")
        root.addWidget(self.transcript, 1)

        self.save_button = QPushButton("End Call & Save Notes")
        self.save_button.clicked.connect(self._on_end_call)
        root.addWidget(self.save_button)

        signals.transcript_received.connect(self.append_transcript)
        signals.cue_received.connect(self.show_cue)
        signals.status_changed.connect(self.set_status)
        signals.saving_changed.connect(self.set_saving)
        signals.quota_alert.connect(self.display_quota_alert)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            bounds = screen.availableGeometry()
            self.move(bounds.right() - self.width() - 24, bounds.bottom() - self.height() - 24)

    def append_transcript(self, speaker: str, text: str) -> None:
        self.transcript.appendPlainText(f"{speaker}: {text}")
        scrollbar = self.transcript.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def show_cue(self, text: str) -> None:
        self.cue.setTextFormat(Qt.TextFormat.PlainText)
        self.cue.setOpenExternalLinks(False)
        self.cue.setStyleSheet("")
        self.cue.setText(text)

    def display_quota_alert(self, message: str) -> None:
        plans_url = html.escape(config.PLANS_URL, quote=True)
        self.cue.setTextFormat(Qt.TextFormat.RichText)
        self.cue.setOpenExternalLinks(True)
        self.cue.setStyleSheet(ALERT_STYLESHEET)
        self.cue.setText(
            f"{html.escape(message)} "
            f'<a href="{plans_url}" style="color:#68d7d0;">View plans</a>'
        )
        self.save_button.setEnabled(True)

    def set_status(self, text: str) -> None:
        self.status.setText(text)

    def set_saving(self, saving: bool) -> None:
        self.save_button.setEnabled(not saving)
        if saving:
            self.status.setText("Saving notes…")
