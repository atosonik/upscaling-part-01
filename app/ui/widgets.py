from __future__ import annotations

from PyQt5.QtCore import QPoint, QRect, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt5.QtWidgets import QWidget


class DropZone(QWidget):
    file_dropped = pyqtSignal(str)
    clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(220)
        self._hover = False
        self._path = ""
        self._thumb = QPixmap()
        self.setCursor(Qt.PointingHandCursor)

    def set_preview(self, path: str, pixmap: QPixmap | None = None) -> None:
        self._path = path
        self._thumb = pixmap or QPixmap()
        self.update()

    def clear(self) -> None:
        self._path = ""
        self._thumb = QPixmap()
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._hover = True
            self.update()

    def dragLeaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        self._hover = False
        urls = event.mimeData().urls()
        if urls:
            self.file_dropped.emit(urls[0].toLocalFile())
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 18, 18)

        fill = QColor("#14120e")
        if self._hover:
            fill = QColor("#1c1812")
        painter.fillPath(path, fill)

        pen = QPen(QColor("#c9a36a" if self._hover else "#3a3428"), 1.6)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawPath(path)

        if not self._thumb.isNull():
            target = rect.adjusted(14, 14, -14, -14)
            scaled = self._thumb.scaled(
                int(target.width()),
                int(target.height()),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            x = target.x() + (target.width() - scaled.width()) / 2
            y = target.y() + (target.height() - scaled.height()) / 2
            clip = QPainterPath()
            clip.addRoundedRect(target, 12, 12)
            painter.setClipPath(clip)
            painter.drawPixmap(int(x), int(y), scaled)
            painter.setClipping(False)
            return

        painter.setPen(QColor("#e4c48a"))
        font = QFont("Palatino Linotype", 16)
        painter.setFont(font)
        painter.drawText(rect.adjusted(0, -18, 0, 0), Qt.AlignCenter, "Drop a photograph")
        painter.setPen(QColor("#8d8476"))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(rect.adjusted(0, 28, 0, 0), Qt.AlignCenter, "or click to browse  ·  JPG PNG WEBP TIF")


class CompareView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._before = QPixmap()
        self._after = QPixmap()
        self._split = 0.5
        self._dragging = False
        self.setMinimumSize(520, 420)
        self.setMouseTracking(True)

    def set_images(self, before: QPixmap, after: QPixmap | None = None) -> None:
        self._before = before
        self._after = after or QPixmap()
        self._split = 0.5 if not self._after.isNull() else 1.0
        self.update()

    def clear(self) -> None:
        self._before = QPixmap()
        self._after = QPixmap()
        self.update()

    def _canvas_rect(self) -> QRect:
        return self.rect().adjusted(18, 18, -18, -18)

    def _fitted(self, pixmap: QPixmap) -> tuple[QPixmap, QRect]:
        area = self._canvas_rect()
        if pixmap.isNull():
            return QPixmap(), area
        scaled = pixmap.scaled(area.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = area.x() + (area.width() - scaled.width()) // 2
        y = area.y() + (area.height() - scaled.height()) // 2
        return scaled, QRect(x, y, scaled.width(), scaled.height())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._update_split(event.pos())

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            self._update_split(event.pos())

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False

    def _update_split(self, pos: QPoint) -> None:
        _, rect = self._fitted(self._before if not self._after.isNull() else self._before)
        if rect.width() <= 0:
            return
        self._split = min(1.0, max(0.0, (pos.x() - rect.x()) / rect.width()))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        frame = QRectF(self.rect())
        bg = QLinearGradient(frame.topLeft(), frame.bottomRight())
        bg.setColorAt(0.0, QColor("#100e0b"))
        bg.setColorAt(1.0, QColor("#16130f"))
        path = QPainterPath()
        path.addRoundedRect(frame.adjusted(1, 1, -1, -1), 22, 22)
        painter.fillPath(path, bg)
        painter.setPen(QPen(QColor("#2b261d"), 1))
        painter.drawPath(path)

        if self._before.isNull():
            painter.setPen(QColor("#8d8476"))
            painter.setFont(QFont("Palatino Linotype", 18))
            painter.drawText(self.rect(), Qt.AlignCenter, "A photograph will appear here")
            return

        show = self._after if not self._after.isNull() else self._before
        fitted, rect = self._fitted(show)
        before_fit = self._before.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        clip = QPainterPath()
        clip.addRoundedRect(QRectF(rect), 14, 14)
        painter.setClipPath(clip)
        painter.drawPixmap(rect, before_fit)

        if not self._after.isNull():
            split_x = rect.x() + int(rect.width() * self._split)
            painter.setClipRect(QRect(split_x, rect.y(), rect.right() - split_x + 1, rect.height()))
            painter.drawPixmap(rect, fitted)
            painter.setClipping(False)
            painter.setClipPath(clip)
            painter.setPen(QPen(QColor("#e4c48a"), 2))
            painter.drawLine(split_x, rect.y(), split_x, rect.bottom())
            painter.setBrush(QColor("#e4c48a"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(split_x, rect.center().y()), 11, 11)
            painter.setPen(QColor("#1a140c"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(split_x - 8, rect.center().y() + 4, "<>")
            painter.setClipping(False)
            painter.setPen(QColor("#d8c4a0"))
            painter.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
            painter.drawText(rect.adjusted(14, 10, 0, 0), Qt.AlignLeft | Qt.AlignTop, "BEFORE")
            painter.drawText(rect.adjusted(0, 10, -14, 0), Qt.AlignRight | Qt.AlignTop, "AFTER")
        else:
            painter.setClipping(False)


class StepCard(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, title: str, subtitle: str, parent=None) -> None:
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle
        self._checked = True
        self.setFixedHeight(78)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        self._checked = value
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._checked = not self._checked
            self.toggled.emit(self._checked)
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        painter.fillPath(path, QColor("#1b1813" if self._checked else "#14120e"))
        painter.setPen(QPen(QColor("#c9a36a" if self._checked else "#2b261d"), 1))
        painter.drawPath(path)

        box = QRectF(16, 28, 18, 18)
        painter.setBrush(QColor("#c9a36a") if self._checked else Qt.NoBrush)
        painter.setPen(QPen(QColor("#c9a36a"), 1.4))
        painter.drawRoundedRect(box, 5, 5)
        if self._checked:
            painter.setPen(QPen(QColor("#1a140c"), 2))
            painter.drawLine(20, 37, 24, 41)
            painter.drawLine(24, 41, 31, 32)

        painter.setPen(QColor("#f3ede2"))
        painter.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        painter.drawText(QRectF(46, 16, rect.width() - 58, 24), Qt.AlignVCenter, self._title)
        painter.setPen(QColor("#9b9284"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QRectF(46, 40, rect.width() - 58, 22), Qt.AlignVCenter, self._subtitle)
