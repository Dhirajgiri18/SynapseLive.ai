import html
import json
from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import config
from ui import styles
from ui.draggable import DraggableMixin
from ui.pill import SynapsePill
from ui.signals import OverlaySignals


class SynapseOverlay(DraggableMixin, QWidget):
    def __init__(
        self,
        signals: OverlaySignals,
        on_end_call: Callable[[], None],
        has_unsaved: Callable[[], bool] | None = None,
    ):
        super().__init__()
        self._init_drag()
        self._on_end_call = on_end_call
        self._has_unsaved = has_unsaved or (lambda: False)
        self.pill = SynapsePill(signals)
        self.pill.expand_requested.connect(self.expand_from_pill)
        self.setObjectName("overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(config.OVERLAY_WIDTH, config.OVERLAY_HEIGHT)
        self.setStyleSheet(styles.OVERLAY)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(9)

        header = QHBoxLayout()
        self.title = QLabel("SynapseLive.ai")
        self.title.setObjectName("title")
        self.title.setStyleSheet(styles.HEADER)
        self.title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.status = QLabel("Starting...")
        self.status.setObjectName("status")
        self.status.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.close_button = QPushButton("×")
        self.close_button.setObjectName("close")
        self.close_button.setFixedWidth(30)
        self.close_button.setToolTip("Close SynapseLive")
        self.close_button.setStyleSheet(styles.CLOSE_BUTTON)
        self.close_button.clicked.connect(self._confirm_close)
        self.minimize_button = QPushButton("−")
        self.minimize_button.setFixedWidth(30)
        self.minimize_button.setToolTip("Minimize to pill")
        self.minimize_button.setStyleSheet(styles.ICON_BUTTON)
        self.minimize_button.clicked.connect(self.minimize_to_pill)
        header.addWidget(self.title)
        header.addStretch(1)
        header.addWidget(self.status)
        header.addWidget(self.minimize_button)
        header.addWidget(self.close_button)
        root.addLayout(header)

        self.cue = QLabel("Listening for useful context…")
        self.cue.setObjectName("cue")
        self.cue.setWordWrap(True)
        self.cue.setTextFormat(Qt.TextFormat.PlainText)
        self.cue.setOpenExternalLinks(False)
        self.cue.setStyleSheet(styles.CUE)
        root.addWidget(self.cue)

        self.transcript = QPlainTextEdit()
        self.transcript.setObjectName("transcript")
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText("Live transcript will appear here.")
        root.addWidget(self.transcript, 1)

        self.save_button = QPushButton("End Call & Save Notes")
        self.save_button.setStyleSheet(styles.SAVE_BUTTON)
        self.save_button.clicked.connect(self._handle_save_click)
        root.addWidget(self.save_button)

        saved_position = self._load_position()
        if saved_position is not None:
            self.move(self._clamp(saved_position))
        else:
            screen = QApplication.primaryScreen()
            if screen is not None:
                bounds = screen.availableGeometry()
                position = QPoint(
                    bounds.right() - self.width() - config.OVERLAY_MARGIN_RIGHT + 1,
                    bounds.bottom() - self.height() - config.OVERLAY_MARGIN_BOTTOM + 1,
                )
                self.move(self._clamp(position))

        signals.transcript_received.connect(self.append_transcript)
        signals.cue_received.connect(self.show_cue)
        signals.status_changed.connect(self.set_status)
        signals.summary_status.connect(self.display_summary_status)
        signals.saving_changed.connect(self.set_saving)
        signals.quota_alert.connect(self.display_quota_alert)

    def _load_position(self) -> QPoint | None:
        try:
            saved = json.loads(config.UI_STATE.read_text(encoding="utf-8"))
            point = QPoint(int(saved["x"]), int(saved["y"]))
        except (OSError, ValueError, KeyError, TypeError):
            return None
        center = point + QPoint(self.width() // 2, self.height() // 2)
        return self._clamp(point) if QApplication.screenAt(center) is not None else None

    def _save_position(self) -> None:
        try:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            config.UI_STATE.write_text(
                json.dumps({"x": self.x(), "y": self.y()}),
                encoding="utf-8",
            )
        except OSError:
            pass

    def on_dragged(self) -> None:
        self._save_position()

    def minimize_to_pill(self) -> None:
        anchor = self.frameGeometry().topRight()
        self.hide()
        self.pill.show_at_anchor(anchor)

    def expand_from_pill(self) -> None:
        anchor = self.pill.frameGeometry().topRight()
        self.pill.hide()
        self.move(self._clamp(QPoint(anchor.x() - self.width() + 1, anchor.y())))
        self.show()
        self.raise_()
        self._save_position()

    def append_transcript(self, speaker: str, text: str) -> None:
        self.transcript.appendPlainText(f"{speaker}: {text}")
        scrollbar = self.transcript.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def show_cue(self, text: str) -> None:
        self.cue.setTextFormat(Qt.TextFormat.PlainText)
        self.cue.setOpenExternalLinks(False)
        self.cue.setStyleSheet(styles.CUE)
        self.cue.setText(text)

    def display_summary_status(self, text: str) -> None:
        self.cue.setTextFormat(Qt.TextFormat.PlainText)
        self.cue.setOpenExternalLinks(False)
        self.cue.setStyleSheet(styles.CUE)
        self.cue.setText(text)
        self.save_button.setEnabled(True)

    def display_quota_alert(self, message: str) -> None:
        plans_url = html.escape(config.PLANS_URL, quote=True)
        self.cue.setTextFormat(Qt.TextFormat.RichText)
        self.cue.setOpenExternalLinks(True)
        self.cue.setStyleSheet(styles.ALERT_STYLESHEET)
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

    def _handle_save_click(self) -> None:
        self.save_button.setEnabled(False)
        self.cue.setTextFormat(Qt.TextFormat.PlainText)
        self.cue.setOpenExternalLinks(False)
        self.cue.setStyleSheet(styles.CUE)
        self.cue.setText("Generating meeting summary…")
        self._on_end_call()

    def _confirm_close(self) -> None:
        if self._has_unsaved() or not self.save_button.isEnabled():
            response = QMessageBox.question(
                self,
                "Close SynapseLive?",
                "There is an unsaved transcript or a summary is still generating.\n"
                "Closing now will discard it. Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                return
        self._allow_close = True
        QApplication.quit()

    def closeEvent(self, event) -> None:
        if getattr(self, "_allow_close", False):
            event.accept()
            return
        event.ignore()
        self._confirm_close()
