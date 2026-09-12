from datetime import datetime

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme import LOG_COLORS


class LogViewer(QWidget):
    """Filterable, color-coded logging console."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dark: bool = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        self.lbl_title = QLabel("📜 Activity Logs")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setFixedHeight(26)
        self.btn_clear.setStyleSheet("padding: 2px 10px; font-size: 12px;")

        toolbar.addWidget(self.lbl_title)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_clear)
        layout.addLayout(toolbar)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(1000)
        layout.addWidget(self.text_edit)

        self.btn_clear.clicked.connect(self.text_edit.clear)

    def set_theme(self, is_dark: bool):
        self._is_dark = is_dark

    def append_log(self, message: str, level: str = "INFO"):
        time_str = datetime.now().strftime("%H:%M:%S")
        color_scheme = LOG_COLORS["dark" if self._is_dark else "light"]
        color = color_scheme.get(level.upper(), color_scheme["INFO"])
        time_color = color_scheme["TIME"]

        html = (
            f'<span style="color:{time_color};">[{time_str}]</span> '
            f'<span style="color:{color}; font-weight:bold;">[{level.upper()}]</span> '
            f'<span style="color:{color};">{message}</span>'
        )
        self.text_edit.appendHtml(html)
        self.text_edit.moveCursor(QTextCursor.End)
