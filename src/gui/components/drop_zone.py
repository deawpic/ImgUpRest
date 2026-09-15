from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.models import SUPPORTED_EXTS
from src.core.session import (
    QueueItemData,
    QueueSession,
    clear_auto_session,
    load_session,
    save_session,
)
from src.gui.theme import STATUS_COLORS

COL_NUM = 0
COL_NAME = 1
COL_RES = 2
COL_DEST = 3
COL_STATUS = 4


class DestinationPromptDialog(QDialog):
    """Modal dialog prompting the user for destination directory when adding files or folders."""

    def __init__(
        self,
        parent=None,
        default_destination: str = "output",
        count: int = 1,
        has_folders: bool = False,
        folder_names: list[str] | None = None,
        is_dark: bool = True,
    ):
        super().__init__(parent)
        self.setWindowTitle("📁 Set Destination Folder")
        self.setMinimumWidth(520)
        self.setModal(True)

        self.default_destination = default_destination
        self.chosen_destination: str | None = None
        self.dont_ask_again: bool = False

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header description
        if has_folders and folder_names:
            names_display = ", ".join(folder_names[:3])
            if len(folder_names) > 3:
                names_display += f" (+{len(folder_names) - 3} more)"
            msg = (
                f"<b>Set destination folder for {count} image(s) from:</b><br>"
                f"<span style='color: #3b82f6;'>{names_display}</span>"
            )
        else:
            msg = f"<b>Set destination folder for {count} added image(s):</b>"

        self.lbl_info = QLabel(msg)
        self.lbl_info.setWordWrap(True)
        layout.addWidget(self.lbl_info)

        # Input row: LineEdit + Browse
        input_layout = QHBoxLayout()
        self.txt_dest = QLineEdit(self.default_destination)
        self.txt_dest.setPlaceholderText("Select or enter destination directory...")
        input_layout.addWidget(self.txt_dest, 1)

        self.btn_browse = QPushButton("📁 Browse...")
        self.btn_browse.clicked.connect(self._on_browse)
        input_layout.addWidget(self.btn_browse)
        layout.addLayout(input_layout)

        # Subfolder notice if folder added
        if has_folders:
            hint_color = "#94a3b8" if is_dark else "#64748b"
            self.lbl_hint = QLabel(
                "💡 <i>Subfolder structure will be mirrored automatically inside this destination folder.</i>"
            )
            self.lbl_hint.setStyleSheet(f"color: {hint_color}; font-size: 11px;")
            self.lbl_hint.setWordWrap(True)
            layout.addWidget(self.lbl_hint)

        # Don't ask again checkbox
        self.chk_dont_ask = QCheckBox("Don't ask again (always use default destination)")
        layout.addWidget(self.chk_dont_ask)

        # Buttons row
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_default = QPushButton("⚡ Use Default")
        self.btn_default.clicked.connect(self._on_use_default)

        self.btn_confirm = QPushButton("✓ Confirm")
        self.btn_confirm.setDefault(True)
        self.btn_confirm.setStyleSheet(
            "background-color: #2563eb; color: white; font-weight: bold; padding: 4px 12px;"
        )
        self.btn_confirm.clicked.connect(self._on_confirm)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_default)
        btn_layout.addWidget(self.btn_confirm)
        layout.addLayout(btn_layout)

    def _on_browse(self):
        start_dir = self.txt_dest.text().strip() or self.default_destination or ""
        selected = QFileDialog.getExistingDirectory(
            self, "Select Destination Directory", start_dir
        )
        if selected:
            self.txt_dest.setText(selected)

    def _on_use_default(self):
        self.chosen_destination = self.default_destination
        self.dont_ask_again = self.chk_dont_ask.isChecked()
        self.accept()

    def _on_confirm(self):
        text = self.txt_dest.text().strip()
        self.chosen_destination = text if text else self.default_destination
        self.dont_ask_again = self.chk_dont_ask.isChecked()
        self.accept()


class BatchQueueTable(QWidget):
    """File list table with drag-and-drop support, persistence, destination per item, and status indicators."""

    files_changed = Signal(int)  # Emits new count of files
    file_selected = Signal(str)  # Emits selected file path for preview
    session_saved = Signal(str)  # Emits saved session file path
    session_loaded = Signal(dict)  # Emits loaded config dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._files: list[Path] = []
        self._item_data: dict[str, QueueItemData] = {}
        self._default_destination: str = "output"
        self.config_provider: Callable[[], dict] | None = None
        self._is_dark: bool = False
        self.prompt_on_add: bool = True
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
        self.btn_set_dest = QPushButton("📁 Destination")
        self.btn_set_dest.setToolTip(
            "Set custom destination folder for selected file(s) or all files"
        )
        self.btn_save_queue = QPushButton("💾 Save")
        self.btn_save_queue.setToolTip("Export batch queue and progress to a JSON file")
        self.btn_load_queue = QPushButton("📂 Load")
        self.btn_load_queue.setToolTip("Load a saved batch queue session from a JSON file")
        self.btn_remove = QPushButton("🗑️ Remove")
        self.btn_clear = QPushButton("❌ Clear All")
        for btn in (
            self.btn_add_files,
            self.btn_add_folder,
            self.btn_set_dest,
            self.btn_save_queue,
            self.btn_load_queue,
            self.btn_remove,
            self.btn_clear,
        ):
            btn.setStyleSheet(btn_style)

        toolbar.addWidget(self.btn_add_files)
        toolbar.addWidget(self.btn_add_folder)
        toolbar.addWidget(self.btn_set_dest)
        toolbar.addWidget(self.btn_save_queue)
        toolbar.addWidget(self.btn_load_queue)
        toolbar.addWidget(self.btn_remove)
        toolbar.addWidget(self.btn_clear)
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["#", "Name", "Resolution", "Destination", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            COL_NUM, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            COL_NAME, QHeaderView.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            COL_RES, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            COL_DEST, QHeaderView.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            COL_STATUS, QHeaderView.ResizeToContents
        )
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setMinimumHeight(100)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSortIndicator(COL_NUM, Qt.AscendingOrder)
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
        self.btn_set_dest.clicked.connect(self._on_set_destination_clicked)
        self.btn_save_queue.clicked.connect(self._on_save_queue)
        self.btn_load_queue.clicked.connect(self._on_load_queue)
        self.btn_remove.clicked.connect(self._on_remove_selected)
        self.btn_clear.clicked.connect(self.clear_all)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)


    def _get_row_file_str(self, row: int) -> str | None:
        if 0 <= row < self.table.rowCount():
            item = self.table.item(row, COL_NAME)
            if item:
                val = item.data(Qt.UserRole)
                if val:
                    return str(val)
            if row < len(self._files):
                return str(self._files[row])
        return None

    def _get_row_file(self, row: int) -> Path | None:
        s = self._get_row_file_str(row)
        return Path(s) if s else None

    def _on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            f = self._get_row_file(row)
            if f:
                self.file_selected.emit(str(f))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        folder_paths: list[Path] = []
        file_paths: list[Path] = []

        for url in urls:
            p = Path(url.toLocalFile()).resolve()
            if p.is_dir():
                folder_paths.append(p)
            elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                file_paths.append(p)

        if not folder_paths and not file_paths:
            return

        total_files = len(file_paths)
        for fp in folder_paths:
            total_files += sum(
                1
                for item in fp.rglob("*")
                if item.is_file() and item.suffix.lower() in SUPPORTED_EXTS
            )

        if total_files == 0:
            return

        dest = self._prompt_add_destination_dialog(
            count=total_files,
            has_folders=bool(folder_paths),
            folder_names=[fp.name for fp in folder_paths],
        )
        if dest is not None:
            for fp in folder_paths:
                self.add_folder(fp, destination_dir=dest)
            if file_paths:
                self.add_paths(file_paths, destination_dir=dest)

    def _on_add_files(self):
        filters = "Images (*.jpg *.jpeg *.png *.webp *.bmp);;All Files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images", "", filters)
        if files:
            paths = [Path(f) for f in files]
            dest = self._prompt_add_destination_dialog(
                count=len(paths), has_folders=False
            )
            if dest is not None:
                self.add_paths(paths, destination_dir=dest)

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Images Folder")
        if folder:
            p = Path(folder).resolve()
            count = sum(
                1
                for f in p.rglob("*")
                if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
            )
            if count == 0:
                QMessageBox.information(
                    self,
                    "No Images Found",
                    f"No supported image files found in:\n{p}",
                )
                return
            dest = self._prompt_add_destination_dialog(
                count=count, has_folders=True, folder_names=[p.name]
            )
            if dest is not None:
                self.add_folder(p, destination_dir=dest)

    def _on_remove_selected(self):
        selected_rows = sorted(
            [idx.row() for idx in self.table.selectionModel().selectedRows()],
            reverse=True,
        )
        for row in selected_rows:
            f = self._get_row_file(row)
            if f:
                key = str(f)
                self._item_data.pop(key, None)
                if f in self._files:
                    self._files.remove(f)
            self.table.removeRow(row)

        # Renumber rows
        for r in range(self.table.rowCount()):
            item_num = self.table.item(r, COL_NUM)
            if item_num:
                item_num.setData(Qt.DisplayRole, r + 1)

        self._update_label()
        if not self._files:
            clear_auto_session()

    def clear_all(self, clear_saved_session: bool = True):
        self._files.clear()
        self._item_data.clear()
        self.table.setRowCount(0)
        self._update_label()
        if clear_saved_session:
            clear_auto_session()

    def _format_dest_display(self, dest_p: Path | None) -> str:
        if not dest_p:
            return "Default"
        if self._default_destination:
            try:
                base_path = Path(self._default_destination).resolve()
                rel = dest_p.resolve().relative_to(base_path)
                if str(rel) != ".":
                    return str(rel)
                return base_path.name or "Default"
            except (ValueError, Exception):
                pass
        return dest_p.name or str(dest_p)

    def set_default_destination(self, path: str):
        self._default_destination = str(path)

    def get_default_destination(self) -> str:
        return self._default_destination

    def set_files_destination(
        self, file_paths: list[str | Path], dest_dir: str
    ):
        dest_path = Path(dest_dir).resolve()
        dest_str = str(dest_path)
        dest_display = self._format_dest_display(dest_path)
        targets = {str(Path(fp).resolve()) for fp in file_paths}

        for r in range(self.table.rowCount()):
            row_file_str = self._get_row_file_str(r)
            if row_file_str and row_file_str in targets:
                item_dest = self.table.item(r, COL_DEST)
                if not item_dest:
                    item_dest = QTableWidgetItem()
                    self.table.setItem(r, COL_DEST, item_dest)
                item_dest.setText(dest_display)
                item_dest.setToolTip(dest_str)

        for t in targets:
            if t in self._item_data:
                self._item_data[t].destination_dir = dest_str

    def set_file_destination(self, file_path: str, dest_dir: str):
        self.set_files_destination([file_path], dest_dir)

    def get_file_destination(self, file_path: str) -> str | None:
        resolved_str = str(Path(file_path).resolve())
        if resolved_str in self._item_data:
            return self._item_data[resolved_str].destination_dir
        return self._default_destination

    def _prompt_add_destination_dialog(
        self,
        count: int,
        has_folders: bool = False,
        folder_names: list[str] | None = None,
    ) -> str | None:
        if not self.prompt_on_add:
            return self._default_destination

        dlg = DestinationPromptDialog(
            parent=self,
            default_destination=self._default_destination,
            count=count,
            has_folders=has_folders,
            folder_names=folder_names or [],
            is_dark=self._is_dark,
        )
        if dlg.exec() == QDialog.Accepted:
            if dlg.dont_ask_again:
                self.prompt_on_add = False
            return dlg.chosen_destination
        return None

    def _prompt_destination_for_rows(
        self, rows: list[int], is_all: bool = False
    ):
        if not rows:
            return

        valid_files = [f for f in (self._get_row_file(r) for r in rows) if f is not None]
        if not valid_files:
            return

        first_dest = self.get_file_destination(str(valid_files[0]))
        count = len(valid_files)
        if is_all:
            title = f"Select Destination for All {count} Files in Queue"
        elif count == 1:
            title = f"Select Destination for {valid_files[0].name}"
        else:
            title = f"Select Destination for {count} Selected Files"

        new_dir = QFileDialog.getExistingDirectory(
            self,
            title,
            first_dest or self._default_destination or "",
        )
        if new_dir:
            self.set_files_destination(valid_files, new_dir)

    def _on_set_destination_clicked(self):
        if not self._files:
            QMessageBox.information(
                self, "Empty Queue", "No files in the batch queue."
            )
            return

        selected_rows = [
            idx.row() for idx in self.table.selectionModel().selectedRows()
        ]
        if selected_rows:
            self._prompt_destination_for_rows(selected_rows)
        else:
            reply = QMessageBox.question(
                self,
                "Change Destination",
                f"No specific files selected.\nDo you want to set the destination for all {len(self._files)} files in the queue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                self._prompt_destination_for_rows(
                    list(range(len(self._files))), is_all=True
                )

    def _on_cell_double_clicked(self, row: int, column: int):
        if column == COL_DEST and 0 <= row < len(self._files):
            selected_rows = [
                idx.row() for idx in self.table.selectionModel().selectedRows()
            ]
            if len(selected_rows) > 1 and row in selected_rows:
                self._prompt_destination_for_rows(selected_rows)
            else:
                self._prompt_destination_for_rows([row])

    def add_folder(
        self, folder: Path | str, destination_dir: str | None = None
    ) -> list[Path]:
        folder_p = Path(folder).resolve()
        if not folder_p.is_dir():
            return []

        base_dest = Path(
            destination_dir or self._default_destination or "output"
        ).resolve()
        new_files: list[Path] = []
        file_dests: dict[str, str] = {}

        for item in sorted(folder_p.rglob("*")):
            if item.is_file() and item.suffix.lower() in SUPPORTED_EXTS:
                resolved = item.resolve()
                rel_sub = resolved.relative_to(folder_p).parent
                dest = (base_dest / folder_p.name / rel_sub).resolve()
                new_files.append(resolved)
                file_dests[str(resolved)] = str(dest)

        self.add_paths(new_files, file_destinations=file_dests)
        return new_files

    def add_paths(
        self,
        paths: list[Path],
        destination_dir: str | None = None,
        file_destinations: dict[str | Path, str | Path] | None = None,
    ):
        existing_set = set(self._files)
        default_target = destination_dir or self._default_destination
        default_dest_p = Path(default_target).resolve() if default_target else None

        norm_dests: dict[str, Path] = {}
        if file_destinations:
            for k, v in file_destinations.items():
                norm_dests[str(Path(k).resolve())] = Path(v).resolve()

        sorting_was_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        try:
            for p in paths:
                if p.is_dir():
                    self.add_folder(p, destination_dir=destination_dir)
                    continue

                resolved = p.resolve()
                if (
                    resolved not in existing_set
                    and resolved.suffix.lower() in SUPPORTED_EXTS
                ):
                    self._files.append(resolved)
                    existing_set.add(resolved)
                    row = self.table.rowCount()
                    self.table.insertRow(row)

                    item_num = QTableWidgetItem()
                    item_num.setData(Qt.DisplayRole, row + 1)
                    item_num.setData(Qt.UserRole, str(resolved))
                    item_num.setTextAlignment(Qt.AlignCenter)

                    item_name = QTableWidgetItem(resolved.name)
                    item_name.setToolTip(str(resolved))
                    item_name.setData(Qt.UserRole, str(resolved))

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

                    dest_p = norm_dests.get(str(resolved), default_dest_p)
                    dest_display = self._format_dest_display(dest_p)
                    item_dest = QTableWidgetItem(dest_display)
                    item_dest.setTextAlignment(Qt.AlignCenter)
                    if dest_p:
                        item_dest.setToolTip(str(dest_p))

                    colors = STATUS_COLORS["dark" if self._is_dark else "light"]
                    item_status = QTableWidgetItem("Queued")
                    item_status.setTextAlignment(Qt.AlignCenter)
                    item_status.setForeground(QColor(colors.get("Queued", "#2563eb")))

                    self.table.setItem(row, COL_NUM, item_num)
                    self.table.setItem(row, COL_NAME, item_name)
                    self.table.setItem(row, COL_RES, item_dim)
                    self.table.setItem(row, COL_DEST, item_dest)
                    self.table.setItem(row, COL_STATUS, item_status)

                    self._item_data[str(resolved)] = QueueItemData(
                        file_path=str(resolved),
                        status="Queued",
                        resolution=dim_text,
                        destination_dir=str(dest_p) if dest_p else None,
                    )
        finally:
            self.table.setSortingEnabled(sorting_was_enabled)

        self._update_label()


    def set_theme(self, is_dark: bool):
        self._is_dark = is_dark
        colors = STATUS_COLORS["dark" if is_dark else "light"]
        for r in range(self.table.rowCount()):
            item_status = self.table.item(r, COL_STATUS)
            if item_status and item_status.text() in colors:
                item_status.setForeground(QColor(colors[item_status.text()]))

    def _update_label(self):
        self.lbl_title.setText(
            f"📁 Input Files / Batch Queue ({len(self._files)} items)"
        )
        self.files_changed.emit(len(self._files))

    def get_files(self) -> list[Path]:
        res: list[Path] = []
        for r in range(self.table.rowCount()):
            f = self._get_row_file(r)
            if f:
                res.append(f)
        return res if res else list(self._files)

    def _get_row_status(self, row: int) -> str:
        item = self.table.item(row, COL_STATUS)
        return item.text() if item else ""

    def set_file_status(
        self,
        file_path: str,
        status: str,
        error: str | None = None,
        output_path: str | None = None,
    ):
        target_path_str = str(Path(file_path).resolve())
        target_name = Path(file_path).name
        colors = STATUS_COLORS["dark" if self._is_dark else "light"]
        for r in range(self.table.rowCount()):
            row_file_str = self._get_row_file_str(r)
            item_name = self.table.item(r, COL_NAME)
            matched = False
            if row_file_str and row_file_str == target_path_str:
                matched = True
            elif item_name and item_name.text() == target_name:
                matched = True

            if matched:
                item_status = self.table.item(r, COL_STATUS)
                if not item_status:
                    item_status = QTableWidgetItem()
                    self.table.setItem(r, COL_STATUS, item_status)

                item_status.setText(status)
                if status in colors:
                    item_status.setForeground(QColor(colors[status]))
                if error and status == "Failed":
                    item_status.setToolTip(error)
                else:
                    item_status.setToolTip("")

                resolved_str = row_file_str or str(Path(file_path).resolve())
                dim_text = (
                    self.table.item(r, COL_RES).text()
                    if self.table.item(r, COL_RES)
                    else "-"
                )
                existing_dest = self.get_file_destination(resolved_str)
                self._item_data[resolved_str] = QueueItemData(
                    file_path=resolved_str,
                    status=status,
                    resolution=dim_text,
                    destination_dir=existing_dest,
                    output_path=output_path,
                    error=error,
                )
                break

    def _open_selected_destination(self, rows: list[int]):
        if not rows:
            return
        row = rows[0]
        f = self._get_row_file(row)
        dest_dir = self.get_file_destination(str(f)) if f else self._default_destination
        if dest_dir:
            p = Path(dest_dir).resolve()
            p.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def _view_selected_output(self, row: int):
        f = self._get_row_file(row)
        if not f:
            return
        item_data = self._item_data.get(str(f))
        out_path = item_data.output_path if item_data else None
        if out_path and Path(out_path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(out_path).resolve())))
        else:
            dest_dir = self.get_file_destination(str(f))
            if dest_dir and Path(dest_dir).is_dir():
                candidates = list(Path(dest_dir).glob(f"{f.stem}*.*"))
                if candidates:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(candidates[0].resolve())))
                else:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(dest_dir).resolve())))

    # Context Menu & Smart Resume Helpers
    def _show_context_menu(self, pos):
        menu = QMenu(self)
        selected_rows = [
            idx.row() for idx in self.table.selectionModel().selectedRows()
        ]
        has_sel = len(selected_rows) > 0
        single_sel = len(selected_rows) == 1

        selected_file_p = self._get_row_file(selected_rows[0]) if single_sel else None
        selected_file_str = str(selected_file_p) if selected_file_p else None
        item_data = self._item_data.get(selected_file_str) if selected_file_str else None

        action_open_dest = menu.addAction("📂 Open Destination Folder")
        action_open_dest.setEnabled(has_sel)

        is_done = item_data is not None and item_data.status == "Done"
        action_view_output = menu.addAction("🖼️ View Output Image")
        action_view_output.setEnabled(single_sel and is_done)

        menu.addSeparator()
        dest_text = (
            f"📁 Change Destination ({len(selected_rows)} selected)..."
            if has_sel
            else "📁 Change Destination..."
        )
        action_set_dest = menu.addAction(dest_text)
        action_set_dest.setEnabled(has_sel)
        menu.addSeparator()
        action_retry = menu.addAction("🔄 Retry Failed Items")
        action_clear_done = menu.addAction("🧹 Clear Completed (Done)")
        action_reset_all = menu.addAction("↺ Reset All to Queued")
        menu.addSeparator()
        action_remove_sel = menu.addAction("🗑️ Remove Selected")

        has_failed = any(
            self._get_row_status(r) == "Failed" for r in range(self.table.rowCount())
        )
        has_done = any(
            self._get_row_status(r) == "Done" for r in range(self.table.rowCount())
        )

        action_retry.setEnabled(has_failed)
        action_clear_done.setEnabled(has_done)
        action_remove_sel.setEnabled(has_sel)

        selected_action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if selected_action == action_open_dest:
            self._open_selected_destination(selected_rows)
        elif selected_action == action_view_output:
            self._view_selected_output(selected_rows[0])
        elif selected_action == action_set_dest:
            self._prompt_destination_for_rows(selected_rows)
        elif selected_action == action_retry:
            self.retry_failed()
        elif selected_action == action_clear_done:
            self.clear_completed()
        elif selected_action == action_reset_all:
            self.reset_all_to_queued()
        elif selected_action == action_remove_sel:
            self._on_remove_selected()

    def _on_save_queue(self):
        if not self._files:
            QMessageBox.information(
                self, "Empty Queue", "No files in the batch queue to save."
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Queue Session",
            "batch_queue.json",
            "JSON Queue Files (*.json);;All Files (*)",
        )
        if path:
            target_path = Path(path)
            if target_path.suffix.lower() != ".json":
                target_path = target_path.with_suffix(".json")
            try:
                cfg = self.config_provider() if self.config_provider else {}
                saved_file = self.save_session_to_file(
                    target_path, config_dict=cfg
                )
                self.session_saved.emit(str(saved_file))
            except Exception as e:
                QMessageBox.critical(
                    self, "Save Error", f"Failed to save queue: {e}"
                )

    def _on_load_queue(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Load Queue Session(s)",
            "",
            "JSON Queue Files (*.json);;All Files (*)",
        )
        if not files:
            return

        append = False
        if self._files:
            reply = QMessageBox.question(
                self,
                "Append or Replace",
                "Do you want to append the loaded session(s) to the existing queue?\n\n"
                "Click 'Yes' to append, or 'No' to replace the current queue.",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Cancel:
                return
            append = reply == QMessageBox.Yes

        last_cfg = {}
        for f in files:
            try:
                cfg = self.load_session_from_file(Path(f), append=append)
                if cfg:
                    last_cfg = cfg
                append = True  # Subsequent files in the selection are appended
            except Exception as e:
                QMessageBox.critical(
                    self, "Load Error", f"Failed to load {Path(f).name}: {e}"
                )

        if last_cfg:
            self.session_loaded.emit(last_cfg)

    def export_session_items(self) -> list[QueueItemData]:
        items: list[QueueItemData] = []
        for r in range(self.table.rowCount()):
            file_p = self._get_row_file(r)
            if not file_p:
                continue
            key = str(file_p)
            dim_item = self.table.item(r, COL_RES)
            res = dim_item.text() if dim_item else "-"
            status = self._get_row_status(r) or "Queued"

            existing_data = self._item_data.get(key)
            dest = (
                existing_data.destination_dir
                if existing_data
                else self._default_destination
            )
            out_p = existing_data.output_path if existing_data else None
            err = existing_data.error if existing_data else None

            items.append(
                QueueItemData(
                    file_path=key,
                    status=status,
                    resolution=res,
                    destination_dir=dest,
                    output_path=out_p,
                    error=err,
                )
            )
        return items

    def import_session_items(
        self, items: list[QueueItemData], append: bool = False
    ) -> None:
        if not append:
            self.clear_all(clear_saved_session=False)
        colors = STATUS_COLORS["dark" if self._is_dark else "light"]

        sorting_was_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        try:
            for item in items:
                p = Path(item.file_path)
                if not p.is_file():
                    continue
                resolved = p.resolve()
                if resolved in self._files:
                    continue

                # Fallback destination check: if destination_dir doesn't exist or is invalid, fallback to _default_destination
                dest_str = item.destination_dir
                if dest_str:
                    dest_p = Path(dest_str)
                    if not dest_p.is_dir():
                        try:
                            is_sub_of_default = False
                            if self._default_destination:
                                try:
                                    dest_p.resolve().relative_to(
                                        Path(self._default_destination).resolve()
                                    )
                                    is_sub_of_default = True
                                except ValueError:
                                    pass

                            if not dest_p.parent.exists() and not is_sub_of_default:
                                dest_str = self._default_destination
                        except Exception:
                            dest_str = self._default_destination
                else:
                    dest_str = self._default_destination

                item.destination_dir = dest_str

                self._files.append(resolved)
                self._item_data[str(resolved)] = item
                row = self.table.rowCount()
                self.table.insertRow(row)

                item_num = QTableWidgetItem()
                item_num.setData(Qt.DisplayRole, row + 1)
                item_num.setData(Qt.UserRole, str(resolved))
                item_num.setTextAlignment(Qt.AlignCenter)

                item_name = QTableWidgetItem(resolved.name)
                item_name.setToolTip(str(resolved))
                item_name.setData(Qt.UserRole, str(resolved))

                item_dim = QTableWidgetItem(item.resolution or "-")
                item_dim.setTextAlignment(Qt.AlignCenter)

                dest_display = self._format_dest_display(
                    Path(dest_str) if dest_str else None
                )
                item_dest = QTableWidgetItem(dest_display)
                item_dest.setTextAlignment(Qt.AlignCenter)
                if dest_str:
                    item_dest.setToolTip(dest_str)

                item_status = QTableWidgetItem(item.status)
                item_status.setTextAlignment(Qt.AlignCenter)
                if item.status in colors:
                    item_status.setForeground(QColor(colors[item.status]))
                if item.error and item.status == "Failed":
                    item_status.setToolTip(item.error)

                self.table.setItem(row, COL_NUM, item_num)
                self.table.setItem(row, COL_NAME, item_name)
                self.table.setItem(row, COL_RES, item_dim)
                self.table.setItem(row, COL_DEST, item_dest)
                self.table.setItem(row, COL_STATUS, item_status)
        finally:
            self.table.setSortingEnabled(sorting_was_enabled)

        self._update_label()

    def save_session_to_file(
        self, file_path: Path, config_dict: dict | None = None
    ) -> Path:
        target = Path(file_path)
        if target.suffix.lower() != ".json":
            target = target.with_suffix(".json")
        items = self.export_session_items()
        session = QueueSession(
            config=config_dict or {},
            items=items,
        )
        return save_session(session, target)

    def load_session_from_file(self, file_path: Path, append: bool = False) -> dict:
        session = load_session(file_path)
        self.import_session_items(session.items, append=append)
        return session.config

    def get_pending_files(self) -> list[Path]:
        pending: list[Path] = []
        for r in range(self.table.rowCount()):
            f = self._get_row_file(r)
            if f and self._get_row_status(r) != "Done":
                pending.append(f)
        return pending

    def get_completed_count(self) -> int:
        return sum(
            1 for r in range(self.table.rowCount()) if self._get_row_status(r) == "Done"
        )

    def get_pending_count(self) -> int:
        return sum(
            1 for r in range(self.table.rowCount()) if self._get_row_status(r) != "Done"
        )

    def retry_failed(self) -> None:
        colors = STATUS_COLORS["dark" if self._is_dark else "light"]
        for r in range(self.table.rowCount()):
            if self._get_row_status(r) == "Failed":
                item_st = self.table.item(r, COL_STATUS)
                if item_st:
                    item_st.setText("Queued")
                    item_st.setForeground(QColor(colors.get("Queued", "#2563eb")))
                    item_st.setToolTip("")
                f = self._get_row_file(r)
                if f:
                    key = str(f)
                    if key in self._item_data:
                        self._item_data[key].status = "Queued"
                        self._item_data[key].error = None

    def clear_completed(self) -> None:
        rows_to_remove = [
            r for r in range(self.table.rowCount()) if self._get_row_status(r) == "Done"
        ]
        for r in reversed(rows_to_remove):
            f = self._get_row_file(r)
            if f:
                key = str(f)
                self._item_data.pop(key, None)
                if f in self._files:
                    self._files.remove(f)
            self.table.removeRow(r)

        for r in range(self.table.rowCount()):
            item_num = self.table.item(r, COL_NUM)
            if item_num:
                item_num.setData(Qt.DisplayRole, r + 1)
        self._update_label()
        if not self._files:
            clear_auto_session()

    def reset_all_to_queued(self) -> None:
        colors = STATUS_COLORS["dark" if self._is_dark else "light"]
        for r in range(self.table.rowCount()):
            item_st = self.table.item(r, COL_STATUS)
            if item_st:
                item_st.setText("Queued")
                item_st.setForeground(QColor(colors.get("Queued", "#2563eb")))
                item_st.setToolTip("")
            f = self._get_row_file(r)
            if f:
                key = str(f)
                if key in self._item_data:
                    self._item_data[key].status = "Queued"
                    self._item_data[key].error = None

