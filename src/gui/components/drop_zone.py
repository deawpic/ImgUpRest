from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
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
    load_session,
    save_session,
)
from src.gui.theme import STATUS_COLORS

COL_NUM = 0
COL_NAME = 1
COL_RES = 2
COL_DEST = 3
COL_STATUS = 4


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
                for f in p.rglob("*")
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
                key = str(self._files[row])
                self._item_data.pop(key, None)
                del self._files[row]
                self.table.removeRow(row)

        # Renumber rows
        for r in range(self.table.rowCount()):
            self.table.item(r, COL_NUM).setText(str(r + 1))

        self._update_label()

    def clear_all(self):
        self._files.clear()
        self._item_data.clear()
        self.table.setRowCount(0)
        self._update_label()

    def set_default_destination(self, path: str):
        self._default_destination = str(path)

    def get_default_destination(self) -> str:
        return self._default_destination

    def set_files_destination(
        self, file_paths: list[str | Path], dest_dir: str
    ):
        dest_path = Path(dest_dir).resolve()
        dest_str = str(dest_path)
        dest_display = dest_path.name or dest_str
        targets = {str(Path(fp).resolve()) for fp in file_paths}

        for r in range(self.table.rowCount()):
            if r < len(self._files) and str(self._files[r]) in targets:
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

    def _prompt_destination_for_rows(
        self, rows: list[int], is_all: bool = False
    ):
        if not rows:
            return

        valid_files = [
            self._files[r] for r in rows if 0 <= r < len(self._files)
        ]
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

    def add_paths(self, paths: list[Path], destination_dir: str | None = None):
        existing_set = set(self._files)
        target_dest = destination_dir or self._default_destination
        dest_p = Path(target_dest).resolve() if target_dest else None

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

                dest_display = dest_p.name if dest_p else "Default"
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
        return list(self._files)

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
        target = Path(file_path).name
        colors = STATUS_COLORS["dark" if self._is_dark else "light"]
        for r in range(self.table.rowCount()):
            item_name = self.table.item(r, COL_NAME)
            if item_name and item_name.text() == target:
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

                if r < len(self._files):
                    resolved_str = str(self._files[r])
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

    # Context Menu & Smart Resume Helpers
    def _show_context_menu(self, pos):
        menu = QMenu(self)
        selected_rows = [
            idx.row() for idx in self.table.selectionModel().selectedRows()
        ]
        has_sel = len(selected_rows) > 0
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
        if selected_action == action_set_dest:
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
            if r < len(self._files):
                file_p = self._files[r]
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
            self.clear_all()
        colors = STATUS_COLORS["dark" if self._is_dark else "light"]

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
                        if not dest_p.parent.exists():
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

            item_num = QTableWidgetItem(str(row + 1))
            item_num.setTextAlignment(Qt.AlignCenter)
            item_name = QTableWidgetItem(resolved.name)
            item_name.setToolTip(str(resolved))

            item_dim = QTableWidgetItem(item.resolution or "-")
            item_dim.setTextAlignment(Qt.AlignCenter)

            dest_display = Path(dest_str).name if dest_str else "Default"
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
            if r < len(self._files):
                st = self._get_row_status(r)
                if st != "Done":
                    pending.append(self._files[r])
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
                if r < len(self._files):
                    key = str(self._files[r])
                    if key in self._item_data:
                        self._item_data[key].status = "Queued"
                        self._item_data[key].error = None

    def clear_completed(self) -> None:
        rows_to_remove = [
            r for r in range(self.table.rowCount()) if self._get_row_status(r) == "Done"
        ]
        for r in reversed(rows_to_remove):
            if r < len(self._files):
                key = str(self._files[r])
                self._item_data.pop(key, None)
                del self._files[r]
            self.table.removeRow(r)

        for r in range(self.table.rowCount()):
            self.table.item(r, COL_NUM).setText(str(r + 1))
        self._update_label()

    def reset_all_to_queued(self) -> None:
        colors = STATUS_COLORS["dark" if self._is_dark else "light"]
        for r in range(self.table.rowCount()):
            item_st = self.table.item(r, COL_STATUS)
            if item_st:
                item_st.setText("Queued")
                item_st.setForeground(QColor(colors.get("Queued", "#2563eb")))
                item_st.setToolTip("")
            if r < len(self._files):
                key = str(self._files[r])
                if key in self._item_data:
                    self._item_data[key].status = "Queued"
                    self._item_data[key].error = None

