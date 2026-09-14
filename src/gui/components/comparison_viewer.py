from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SplitWipeCanvas(QWidget):
    """Interactive canvas that paints Before/After images with a draggable split line and zoom/pan."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(220, 120)
        self._pix_before: QPixmap | None = None
        self._pix_after: QPixmap | None = None
        self._split_ratio: float = 0.5  # 0.0 to 1.0
        self._dragging: bool = False
        self._zoom: float = 1.0  # 1.0x to 8.0x
        self._pan_offset: QPoint = QPoint(0, 0)
        self._panning: bool = False
        self._last_pan_pos: QPoint = QPoint()

    def reset_view(self):
        """Resets zoom to 1.0x and centers the canvas."""
        self._zoom = 1.0
        self._pan_offset = QPoint(0, 0)
        self.update()

    def set_images(self, before_path: Path | None, after_path: Path | None):
        self._pix_before = (
            QPixmap(str(before_path))
            if before_path and Path(before_path).exists()
            else None
        )
        self._pix_after = (
            QPixmap(str(after_path))
            if after_path and Path(after_path).exists()
            else None
        )
        self.reset_view()

    def set_before_image(self, path: Path):
        self._pix_before = QPixmap(str(path)) if Path(path).exists() else None
        self._pix_after = None
        self.reset_view()

    def set_after_image(self, path: Path | None):
        self._pix_after = QPixmap(str(path)) if path and Path(path).exists() else None
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._update_split(event.pos().x())
        elif event.button() in (Qt.RightButton, Qt.MiddleButton):
            self._panning = True
            self._last_pan_pos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            self._update_split(event.pos().x())
        elif self._panning:
            delta = event.pos() - self._last_pan_pos
            self._last_pan_pos = event.pos()
            self._pan_offset += delta
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._dragging = False
        elif event.button() in (Qt.RightButton, Qt.MiddleButton):
            self._panning = False

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.reset_view()

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        if angle == 0:
            return
        factor = 1.2 if angle > 0 else (1.0 / 1.2)
        old_zoom = self._zoom
        new_zoom = max(1.0, min(8.0, old_zoom * factor))
        if abs(new_zoom - old_zoom) < 0.001:
            return

        mouse_pos = (
            event.position().toPoint() if hasattr(event, "position") else event.pos()
        )
        w, h = self.width(), self.height()
        center = QPoint(w // 2, h // 2)

        current_img_center = center + self._pan_offset
        d = mouse_pos - current_img_center
        ratio = new_zoom / old_zoom

        if new_zoom <= 1.01:
            self._pan_offset = QPoint(0, 0)
            self._zoom = 1.0
        else:
            self._pan_offset = QPoint(
                int(self._pan_offset.x() - d.x() * (ratio - 1)),
                int(self._pan_offset.y() - d.y() * (ratio - 1)),
            )
            self._zoom = new_zoom

        self.update()
        event.accept()

    def _update_split(self, mouse_x: int):
        if self.width() > 0:
            self._split_ratio = max(0.02, min(0.98, mouse_x / self.width()))
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw canvas background
        painter.fillRect(self.rect(), QColor("#1e293b"))

        if not self._pix_before and not self._pix_after:
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("sans-serif", 13))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Select an image from queue and click 'Generate Preview'\nto inspect Before/After quality here.",
            )
            return

        w, h = self.width(), self.height()
        split_x = int(w * self._split_ratio)

        # Determine target aspect-fit bounding box with zoom and pan
        ref_pix = self._pix_after or self._pix_before
        if ref_pix:
            scaled = ref_pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            base_w = scaled.width()
            base_h = scaled.height()
            target_w = int(base_w * self._zoom)
            target_h = int(base_h * self._zoom)
            target_x = (w - target_w) // 2 + self._pan_offset.x()
            target_y = (h - target_h) // 2 + self._pan_offset.y()
            target_rect = QRect(target_x, target_y, target_w, target_h)
        else:
            target_rect = self.rect()

        # 1. Draw Right Side: Upscaled (or After)
        if self._pix_after:
            painter.save()
            painter.setClipRect(QRect(split_x, 0, w - split_x, h))
            painter.drawPixmap(target_rect, self._pix_after)
            painter.restore()

        # 2. Draw Left Side: Original (Before)
        if self._pix_before:
            painter.save()
            if self._pix_after:
                painter.setClipRect(QRect(0, 0, split_x, h))
            else:
                painter.setClipRect(QRect(0, 0, w, h))
            painter.drawPixmap(target_rect, self._pix_before)
            painter.restore()

        # 3. Draw Split Wiper & Labels only when both before and after are present
        if self._pix_after:
            # Draw Split Line
            pen = QPen(QColor("#2563eb"), 2)
            painter.setPen(pen)
            painter.drawLine(split_x, 0, split_x, h)

            # Draw Center Handle
            handle_y = h // 2
            painter.setBrush(QColor("#2563eb"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(split_x, handle_y), 16, 16)
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("sans-serif", 9, QFont.Bold))
            painter.drawText(
                QRect(split_x - 16, handle_y - 16, 32, 32),
                Qt.AlignCenter,
                "◀▶",
            )

            # Draw ORIGINAL & UPSCALED Badges
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(15, 23, 42, 190))
            painter.drawRoundedRect(12, 12, 90, 26, 4, 4)
            painter.drawRoundedRect(w - 106, 12, 94, 26, 4, 4)

            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("sans-serif", 10, QFont.Bold))
            painter.drawText(QRect(12, 12, 90, 26), Qt.AlignCenter, "ORIGINAL")
            painter.drawText(QRect(w - 106, 12, 94, 26), Qt.AlignCenter, "UPSCALED")
        elif self._pix_before:
            # Only Original badge
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(15, 23, 42, 190))
            painter.drawRoundedRect(12, 12, 90, 26, 4, 4)
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("sans-serif", 10, QFont.Bold))
            painter.drawText(QRect(12, 12, 90, 26), Qt.AlignCenter, "ORIGINAL")

        # 6. Draw Zoom & Pan HUD indicator
        zoom_pct = int(self._zoom * 100)
        hud_text = f"🔍 {zoom_pct}%"
        if self._zoom > 1.01:
            hud_text += " • Right-drag: Pan • Double-click: Reset"

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(15, 23, 42, 190))
        hud_w = 80 if self._zoom <= 1.01 else 280
        painter.drawRoundedRect((w - hud_w) // 2, h - 30, hud_w, 22, 4, 4)
        painter.setPen(QColor("#94a3b8") if self._zoom <= 1.01 else QColor("#38bdf8"))
        painter.setFont(QFont("sans-serif", 9))
        painter.drawText(
            QRect((w - hud_w) // 2, h - 30, hud_w, 22), Qt.AlignCenter, hud_text
        )


class ComparisonViewer(QWidget):
    """Wrapper component with comparison canvas and preview generation action."""

    request_preview = Signal(str)  # Emits file path to preview

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_file: Path | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header toolbar
        bar = QHBoxLayout()
        self.lbl_status = QLabel("🔍 Before/After Comparison Wiper")
        self.lbl_status.setStyleSheet("font-weight: bold; font-size: 13px;")
        bar.addWidget(self.lbl_status)
        bar.addStretch()

        self.btn_preview = QPushButton("⚡ Generate Preview")
        self.btn_preview.setEnabled(False)
        self.btn_preview.setStyleSheet(
            """
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                padding: 3px 12px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #cbd5e1;
                color: #94a3b8;
            }
            """
        )
        bar.addWidget(self.btn_preview)
        layout.addLayout(bar)

        # Canvas
        self.canvas = SplitWipeCanvas(self)
        layout.addWidget(self.canvas)

        self.btn_preview.clicked.connect(self._on_preview_clicked)

    def set_selected_file(self, file_path: str):
        self._current_file = Path(file_path)
        self.lbl_status.setText(f"🔍 Inspecting: {self._current_file.name}")
        self.btn_preview.setEnabled(True)
        self.btn_preview.setText("⚡ Generate Preview")
        self.canvas.set_before_image(self._current_file)

    def set_upscaled_result(self, upscaled_path: Path):
        self.canvas.set_after_image(upscaled_path)
        self.btn_preview.setText("🔄 Re-generate Preview")
        self.btn_preview.setEnabled(True)

    def clear_preview(self):
        self.canvas.set_after_image(None)
        self.btn_preview.setText("⚡ Generate Preview")
        self.btn_preview.setEnabled(True)

    def _on_preview_clicked(self):
        if self._current_file:
            self.request_preview.emit(str(self._current_file))
