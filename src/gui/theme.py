"""Theme definitions and color schemes for Light and Dark modes."""

LIGHT_THEME = """
QMainWindow, QWidget {
    background-color: #f4f6f9;
    color: #1e293b;
    font-family: 'Segoe UI', 'Ubuntu', 'Cantarell', 'Helvetica Neue', sans-serif;
    font-size: 14px;
}

QGroupBox {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: #1d4ed8;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 12px;
    background-color: #ffffff;
}

QLineEdit, QComboBox, QSpinBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0f172a;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 2px solid #2563eb;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QTabWidget::pane {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background-color: #ffffff;
    top: -1px;
}

QTabBar::tab {
    background-color: #e2e8f0;
    color: #475569;
    padding: 8px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    font-size: 13px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #1d4ed8;
    font-weight: bold;
    border: 1px solid #cbd5e1;
    border-bottom: 1px solid #ffffff;
}

QPushButton {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 14px;
    color: #1e293b;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #94a3b8;
}

QPushButton:pressed {
    background-color: #e2e8f0;
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    font-size: 13px;
    color: #0f172a;
    selection-background-color: #e0e7ff;
    selection-color: #1e40af;
}

QTableWidget::item {
    background-color: #ffffff;
    padding: 2px 4px;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #1e293b;
    padding: 3px 6px;
    border: 1px solid #cbd5e1;
    font-weight: bold;
    font-size: 12px;
}

QPlainTextEdit {
    background-color: #ffffff;
    color: #0f172a;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px;
}

QSlider::groove:horizontal {
    border: 1px solid #cbd5e1;
    height: 8px;
    background: #e2e8f0;
    border-radius: 4px;
}

QSlider::sub-page:horizontal {
    background: #2563eb;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #2563eb;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #eff6ff;
    border-color: #1d4ed8;
}

QScrollBar:vertical {
    border: none;
    background-color: #f1f5f9;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}

QSplitter::handle {
    background-color: #cbd5e1;
}

QSplitter::handle:hover {
    background-color: #94a3b8;
}
"""

DARK_THEME = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', 'Ubuntu', 'Cantarell', 'Helvetica Neue', sans-serif;
    font-size: 14px;
}

QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: #89b4fa;
    background-color: #181825;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 12px;
    background-color: #181825;
}

QLineEdit, QComboBox, QSpinBox {
    background-color: #11111b;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 6px 10px;
    color: #cdd6f4;
    font-size: 13px;
    selection-background-color: #89b4fa;
    selection-color: #11111b;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 2px solid #89b4fa;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 8px;
    background-color: #181825;
    top: -1px;
}

QTabBar::tab {
    background-color: #11111b;
    color: #a6adc8;
    padding: 8px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    font-size: 13px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #181825;
    color: #89b4fa;
    font-weight: bold;
    border: 1px solid #313244;
    border-bottom: 1px solid #181825;
}

QPushButton {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 14px;
    color: #cdd6f4;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #45475a;
    border-color: #585b70;
}

QPushButton:pressed {
    background-color: #585b70;
}

QTableWidget {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
    gridline-color: #313244;
    font-size: 13px;
    color: #cdd6f4;
    selection-background-color: #313244;
    selection-color: #cdd6f4;
}

QTableWidget::item {
    background-color: #181825;
    padding: 2px 4px;
}

QHeaderView::section {
    background-color: #11111b;
    color: #cdd6f4;
    padding: 3px 6px;
    border: 1px solid #313244;
    font-weight: bold;
    font-size: 12px;
}

QPlainTextEdit {
    background-color: #11111b;
    color: #cdd6f4;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 6px;
}

QSlider::groove:horizontal {
    border: 1px solid #313244;
    height: 8px;
    background: #11111b;
    border-radius: 4px;
}

QSlider::sub-page:horizontal {
    background: #89b4fa;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #cdd6f4;
    border: 2px solid #89b4fa;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #b4befe;
    border-color: #b4befe;
}

QScrollBar:vertical {
    border: none;
    background-color: #181825;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #313244;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background-color: #45475a;
}

QSplitter::handle {
    background-color: #313244;
}

QSplitter::handle:hover {
    background-color: #45475a;
}
"""

STATUS_COLORS = {
    "light": {
        "Queued": "#2563eb",
        "Processing": "#d97706",
        "Done": "#15803d",
        "Failed": "#b91c1c",
    },
    "dark": {
        "Queued": "#89b4fa",
        "Processing": "#f9e2af",
        "Done": "#a6e3a1",
        "Failed": "#f38ba8",
    },
}

LOG_COLORS = {
    "light": {
        "INFO": "#0f172a",
        "WARNING": "#b45309",
        "ERROR": "#b91c1c",
        "SUCCESS": "#15803d",
        "TIME": "#64748b",
    },
    "dark": {
        "INFO": "#cdd6f4",
        "WARNING": "#fab387",
        "ERROR": "#f38ba8",
        "SUCCESS": "#a6e3a1",
        "TIME": "#6c7086",
    },
}
