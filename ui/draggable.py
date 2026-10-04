from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QWidget


class DraggableMixin:
    CLICK_SLOP = 4

    def _init_drag(self) -> None:
        self._drag_offset: QPoint | None = None
        self._press_pos: QPoint | None = None
        self._dragged = False

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
            self._dragged = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (
            self._drag_offset is None
            or self._press_pos is None
            or not event.buttons() & Qt.MouseButton.LeftButton
        ):
            super().mouseMoveEvent(event)
            return

        current_pos = event.globalPosition().toPoint()
        if not self._dragged and (current_pos - self._press_pos).manhattanLength() < self.CLICK_SLOP:
            return
        self._dragged = True
        self.move(self._clamp(current_pos - self._drag_offset))
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            was_dragged = self._dragged
            self._drag_offset = None
            self._press_pos = None
            self._dragged = False
            if was_dragged:
                self.on_dragged()
            else:
                self.on_clicked()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def on_dragged(self) -> None:
        pass

    def on_clicked(self) -> None:
        pass

    def _clamp(self, top_left: QPoint) -> QPoint:
        center = top_left + QPoint(self.width() // 2, self.height() // 2)
        screen = QApplication.screenAt(center) or self.screen() or QApplication.primaryScreen()
        if screen is None:
            return top_left

        area = screen.availableGeometry()
        max_x = max(area.left(), area.right() - self.width() + 1)
        max_y = max(area.top(), area.bottom() - self.height() + 1)
        return QPoint(
            max(area.left(), min(top_left.x(), max_x)),
            max(area.top(), min(top_left.y(), max_y)),
        )
