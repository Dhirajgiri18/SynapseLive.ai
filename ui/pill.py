from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ui import styles
from ui.draggable import DraggableMixin
from ui.signals import OverlaySignals


class SynapsePill(DraggableMixin, QWidget):
    expand_requested = Signal()

    def __init__(self, signals: OverlaySignals):
        super().__init__()
        self._init_drag()
        self.setObjectName("pill")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)
        self.dot = QLabel("●")
        self.title = QLabel("SynapseLive")
        self.title.setStyleSheet(styles.PILL_TITLE)
        for label in (self.dot, self.title):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.dot)
        layout.addWidget(self.title)

        self.setStyleSheet(styles.PILL)
        self._set_dot(styles.DOT_IDLE)
        self.adjustSize()
        signals.cue_received.connect(self._on_cue)
        signals.quota_alert.connect(self._on_alert)

    def _set_dot(self, color: str) -> None:
        self.dot.setStyleSheet(styles.dot_style(color))

    def _on_cue(self, cue: str) -> None:
        self._set_dot(styles.DOT_CUE)
        self.setToolTip(cue[:200])

    def _on_alert(self, message: str) -> None:
        self._set_dot(styles.DOT_ALERT)
        self.setToolTip(message[:200])

    def show_at_anchor(self, anchor: QPoint) -> None:
        self._set_dot(styles.DOT_IDLE)
        self.setToolTip("Click to expand")
        top_left = QPoint(anchor.x() - self.width() + 1, anchor.y())
        self.move(self._clamp(top_left))
        self.show()
        self.raise_()

    def on_clicked(self) -> None:
        self.expand_requested.emit()
