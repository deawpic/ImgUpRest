from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.models import SUPPORTED_EXTS
from src.gui.theme import STATUS_COLORS


class BatchQueueTable(QWidget):
    """File list table with drag-and-drop support and status indicators."""

    files_changed = Signal(int)  # Emits new count of files
    file_selected = Signal(str)  # Emits selected file path for preview

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._files: list[Path] = []
        self._is_dark: bool = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header toolbar
        toolbar = QHBoxLayout()
        self.lbl_title = QLabel("📁 Input Files / Batch Queue (0 items)")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        toolbar.addWidget(self.lbl_title)
        toolbar.addStretch()

        btn_style = "padding: 3px 8px; font-size: 12px;"
        self.btn_add_files = QPushButton("➕ Add Files")
        self.btn_add_folder = QPushButton("📂 Add Folder")
        self.btn_remove = QPushButton("🗑️ Remove")
        self.btn_clear = QPushButton("❌ Clear All")
        for btn in (
            self.btn_add_files,
            self.btn_add_folder,
            self.btn_remove,
            self.btn_clear,
        ):
            btn.setStyleSheet(btn_style)

        toolbar.addWidget(self.btn_add_files)
        toolbar.addWidget(self.btn_add_folder)
        toolbar.addWidget(self.btn_remove)
        toolbar.addWidget(self.btn_clear)
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["#", "Name", "Resolution", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.setMinimumHeight(100)
        layout.addWidget(self.table)

        # Drag-and-drop prompt label
        self.drop_hint = QLabel("💡 Drag & drop images or directories here")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setStyleSheet(
            "color: #64748b; font-style: italic; font-size: 11px; padding: 2px;"
        )
        layout.addWidget(self.drop_hint)

        # Signals
        self.btn_add_files.clicked.connect(self._on_add_files)
        self.btn_add_folder.clicked.connect(self._on_add_folder)
        self.btn_remove.clicked.connect(self._on_remove_selected)
        self.btn_clear.clicked.connect(self.clear_all)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            if 0 <= row < len(self._files):
                self.file_selected.emit(str(self._files[row]))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        new_paths: list[Path] = []
        for url in urls:
            p = Path(url.toLocalFile())
            if p.is_dir():
                for item in p.rglob("*"):
                    if item.is_file() and item.suffix.lower() in SUPPORTED_EXTS:
                        new_paths.append(item)
            elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                new_paths.append(p)
        self.add_paths(new_paths)

    def _on_add_files(self):
        filters = "Images (*.jpg *.jpeg *.png *.webp *.bmp);;All Files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images", "", filters)
        if files:
            self.add_paths([Path(f) for f in files])

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Images Folder")
        if folder:
            p = Path(folder)
            files = [
                f
                for f in p.iterdir()
                if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
            ]
            self.add_paths(files)

    def _on_remove_selected(self):
        selected_rows = sorted(
            [idx.row() for idx in self.table.selectionModel().selectedRows()],
            reverse=True,
        )
        for row in selected_rows:
            if 0 <= row < len(self._files):
                del self._files[row]
                self.table.removeRow(row)

        # Renumber rows
        for r in range(self.table.rowCount()):
            self.table.item(r, 0).setText(str(r + 1))

        self._update_label()

    def clear_all(self):
        self._files.clear()
        self.table.setRowCount(0)
        self._update_label()

    def add_paths(self, paths: list[Path]):
        existing_set = set(self._files)
        for p in paths:
            resolved = p.resolve()
            if (
                resolved not in existing_set
                and resolved.suffix.lower() in SUPPORTED_EXTS
            ):
                self._files.append(resolved)
                existing_set.add(resolved)
                row = self.table.rowCount()
                self.table.insertRow(row)

                item_num = QTableWidgetItem(str(row + 1))
                item_num.setTextAlignment(Qt.AlignCenter)
                item_name = QTableWidgetItem(resolved.name)
                item_name.setToolTip(str(resolved))

                # Image dimensions
                dim_text = "-"
                try:
                    from PIL import Image

                    with Image.open(resolved) as im:
                        dim_text = f"{im.width}×{im.height}"
                except Exception:
                    pass

                item_dim = QTableWidgetItem(dim_text)
                item_dim.setTextAlignment(Qt.AlignCenter)

                colors = STATUS_COLORS["dark" if self._is_dark else "light"]
                item_status = QTableWidgetItem("Queued")
                item_status.setTextAlignment(Qt.AlignCenter)
                item_status.setForeground(QColor(colors.get("Queued", "#2563eb")))

                self.table.setItem(row, 0, item_num)
                self.table.setItem(row, 1, item_name)
                self.table.setItem(row, 2, item_dim)
                self.table.setItem(row, 3, item_status)

        self._update_label()

    def set_theme(self, is_dark: bool):
        self._is_dark = is_dark
        colors = STATUS_COLORS["dark" if is_dark else "light"]
        for r in range(self.table.rowCount()):
            item_status = self.table.item(r, 3)
            if item_status and item_status.text() in colors:
                item_status.setForeground(QColor(colors[item_status.text()]))

    def _update_label(self):
        self.lbl_title.setText(
            f"📁 Input Files / Batch Queue ({len(self._files)} items)"
        )
        self.files_changed.emit(len(self._files))

    def get_files(self) -> list[Path]:
        return list(self._files)

    def set_file_status(self, file_path: str, status: str, error: str | None = None):
        target = Path(file_path).name
        colors = STATUS_COLORS["dark" if self._is_dark else "light"]
        for r in range(self.table.rowCount()):
            item_name = self.table.item(r, 1)
            if item_name and item_name.text() == target:
                item_status = self.table.item(r, 3)
                if not item_status:
                    item_status = QTableWidgetItem()
                    self.table.setItem(r, 3, item_status)

                item_status.setText(status)
                if status in colors:
                    item_status.setForeground(QColor(colors[status]))
                if error and status == "Failed":
                    item_status.setToolTip(error)
                break
