import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.core import MODELS, PRESETS, UpscaleConfig, get_default_cpu_workers


class ControlPanel(QWidget):
    """Configuration panel for model parameters, output options, and hardware concurrency."""

    config_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._applying_preset = False
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # 0. Preset Selection Group
        grp_preset = QGroupBox("🎯 Quick Photography & Art Preset")
        layout_preset = QVBoxLayout(grp_preset)
        layout_preset.setSpacing(4)

        preset_row = QHBoxLayout()
        self.cmb_preset = QComboBox()
        self.cmb_preset.addItem("⚙️ Custom Tuning (กำหนดค่าเอง)", "custom")
        for key, p in PRESETS.items():
            self.cmb_preset.addItem(p.name, key)

        preset_row.addWidget(QLabel("Preset:"))
        preset_row.addWidget(self.cmb_preset, stretch=1)
        layout_preset.addLayout(preset_row)

        self.lbl_preset_desc = QLabel("Select a preset or customize settings below.")
        self.lbl_preset_desc.setStyleSheet(
            "color: #64748b; font-size: 12px; font-style: italic;"
        )
        self.lbl_preset_desc.setWordWrap(True)
        layout_preset.addWidget(self.lbl_preset_desc)

        main_layout.addWidget(grp_preset)

        # 1. Model & Scale Group
        grp_model = QGroupBox("🤖 Model & Scaling")
        layout_model = QFormLayout(grp_model)

        self.cmb_model = QComboBox()
        for key, info in MODELS.items():
            self.cmb_model.addItem(f"{info.display_name} ({info.name})", key)

        default_idx = self.cmb_model.findData("x4plus")
        if default_idx >= 0:
            self.cmb_model.setCurrentIndex(default_idx)

        self.lbl_model_desc = QLabel(MODELS["x4plus"].recommended_for)
        self.lbl_model_desc.setStyleSheet(
            "color: #475569; font-size: 13px; padding-top: 2px;"
        )
        self.lbl_model_desc.setWordWrap(True)

        # Scale radio buttons
        scale_box = QHBoxLayout()
        self.scale_group = QButtonGroup(self)
        self.rb_scale_2 = QRadioButton("2x (Native / Downscale)")
        self.rb_scale_4 = QRadioButton("4x (Native 4K)")
        self.rb_scale_4.setChecked(True)
        self.scale_group.addButton(self.rb_scale_2, 2)
        self.scale_group.addButton(self.rb_scale_4, 4)
        scale_box.addWidget(self.rb_scale_2)
        scale_box.addWidget(self.rb_scale_4)

        # Tile size slider
        tile_box = QHBoxLayout()
        self.slider_tile = QSlider(Qt.Horizontal)
        self.slider_tile.setRange(0, 800)
        self.slider_tile.setSingleStep(50)
        self.slider_tile.setValue(0)
        self.lbl_tile_val = QLabel("0 (Auto / Fast)")
        self.lbl_tile_val.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.lbl_tile_val.setFixedWidth(120)
        tile_box.addWidget(self.slider_tile)
        tile_box.addWidget(self.lbl_tile_val)

        # Denoise slider
        denoise_box = QHBoxLayout()
        self.slider_denoise = QSlider(Qt.Horizontal)
        self.slider_denoise.setRange(0, 100)
        self.slider_denoise.setValue(0)
        self.lbl_denoise_val = QLabel("0% (Preserve Grain)")
        self.lbl_denoise_val.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.lbl_denoise_val.setFixedWidth(150)
        denoise_box.addWidget(self.slider_denoise)
        denoise_box.addWidget(self.lbl_denoise_val)

        # Film Grain slider
        grain_box = QHBoxLayout()
        self.slider_grain = QSlider(Qt.Horizontal)
        self.slider_grain.setRange(0, 10)
        self.slider_grain.setValue(0)
        self.lbl_grain_val = QLabel("0% (Off)")
        self.lbl_grain_val.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.lbl_grain_val.setFixedWidth(150)
        grain_box.addWidget(self.slider_grain)
        grain_box.addWidget(self.lbl_grain_val)

        layout_model.addRow("AI Model:", self.cmb_model)
        layout_model.addRow("", self.lbl_model_desc)
        layout_model.addRow("Scale Factor:", scale_box)
        layout_model.addRow("Tile Size:", tile_box)
        layout_model.addRow("Denoise:", denoise_box)
        layout_model.addRow("Film Grain:", grain_box)

        # 2. Hardware & Concurrency Group
        grp_hw = QGroupBox("⚡ Hardware & Concurrency")
        layout_hw = QFormLayout(grp_hw)

        self.chk_gpu = QCheckBox("Enable GPU Worker (Device 0: Vulkan)")
        self.chk_gpu.setChecked(True)

        hw_box = QHBoxLayout()
        max_cpus = os.cpu_count() or 6
        self.spin_cpu_workers = QSpinBox()
        self.spin_cpu_workers.setRange(0, max_cpus)
        self.spin_cpu_workers.setValue(min(3, get_default_cpu_workers()))
        hw_box.addWidget(self.spin_cpu_workers)
        hw_box.addWidget(QLabel(f"Workers (Available Cores: {max_cpus})"))

        layout_hw.addRow("GPU Acceleration:", self.chk_gpu)
        layout_hw.addRow("CPU Workers:", hw_box)

        # 3. Face Enhancement Group (GFPGAN / CodeFormer ONNX)
        grp_face = QGroupBox("👤 Face Enhancement (GFPGAN / CodeFormer ONNX)")
        layout_face = QFormLayout(grp_face)

        self.chk_face_enhance = QCheckBox("Enable AI Face Restoration")
        self.chk_face_enhance.setChecked(False)

        self.cmb_face_model = QComboBox()
        self.cmb_face_model.addItem(
            "CodeFormer (Natural Teeth & Identity - Best for Smiles)", "codeformer"
        )
        self.cmb_face_model.addItem(
            "GFPGAN v1.4 (Skin Texture - Best for Closed Mouth)", "gfpgan"
        )
        self.cmb_face_model.setToolTip(
            "• CodeFormer: Best for smiling portraits (prevents extra teeth/hallucinations).\n"
            "• GFPGAN v1.4: Best for closed-mouth portraits (enhances skin/hair texture)."
        )
        self.cmb_face_model.setEnabled(False)

        fidelity_box = QHBoxLayout()
        self.slider_fidelity = QSlider(Qt.Horizontal)
        self.slider_fidelity.setRange(10, 100)
        self.slider_fidelity.setValue(80)
        self.slider_fidelity.setEnabled(False)
        self.slider_fidelity.setToolTip(
            "Higher (0.75-0.85) retains natural real face & teeth; Lower (0.3-0.5) generates more AI detail."
        )
        self.lbl_fidelity_val = QLabel("0.80")
        self.lbl_fidelity_val.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.lbl_fidelity_val.setFixedWidth(50)
        fidelity_box.addWidget(self.slider_fidelity)
        fidelity_box.addWidget(self.lbl_fidelity_val)

        self.chk_mask_mouth = QCheckBox(
            "👄 Preserve Real Smile (มาสก์ฟัน & รอยยิ้มเดิม)"
        )
        self.chk_mask_mouth.setChecked(False)
        self.chk_mask_mouth.setEnabled(False)
        self.chk_mask_mouth.setToolTip(
            "Excludes mouth and teeth from AI generation to guarantee 100% genuine smile without extra teeth."
        )

        layout_face.addRow("Status:", self.chk_face_enhance)
        layout_face.addRow("Model:", self.cmb_face_model)
        layout_face.addRow("Fidelity Weight:", fidelity_box)
        layout_face.addRow("Natural Smile:", self.chk_mask_mouth)

        # 4. Output Settings Group
        grp_output = QGroupBox("💾 Output Settings")
        layout_output = QFormLayout(grp_output)

        self.cmb_format = QComboBox()
        self.cmb_format.addItems(["JPG (Lossy Compressed)", "PNG (Lossless)", "WebP"])

        # Quality slider
        qual_box = QHBoxLayout()
        self.slider_quality = QSlider(Qt.Horizontal)
        self.slider_quality.setRange(50, 100)
        self.slider_quality.setValue(92)
        self.lbl_quality_val = QLabel("92%")
        self.lbl_quality_val.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.lbl_quality_val.setFixedWidth(60)
        qual_box.addWidget(self.slider_quality)
        qual_box.addWidget(self.lbl_quality_val)

        # Output directory row
        dir_box = QHBoxLayout()
        self.txt_output_dir = QLineEdit(str(Path.cwd() / "output"))
        self.btn_browse_dir = QPushButton("Browse...")
        dir_box.addWidget(self.txt_output_dir)
        dir_box.addWidget(self.btn_browse_dir)

        layout_output.addRow("Format:", self.cmb_format)
        layout_output.addRow("Quality:", qual_box)
        layout_output.addRow("Destination:", dir_box)

        # 2-column layout to make settings compact and never squished
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(12)

        col_left = QVBoxLayout()
        col_left.setSpacing(8)
        col_left.addWidget(grp_model)
        col_left.addWidget(grp_hw)
        col_left.addStretch()

        col_right = QVBoxLayout()
        col_right.setSpacing(8)
        col_right.addWidget(grp_face)
        col_right.addWidget(grp_output)
        col_right.addStretch()

        columns_layout.addLayout(col_left, stretch=1)
        columns_layout.addLayout(col_right, stretch=1)
        main_layout.addLayout(columns_layout)

        # Connect signals
        self.cmb_preset.currentIndexChanged.connect(self._on_preset_changed)
        self.cmb_model.currentIndexChanged.connect(self._on_model_changed)
        self.scale_group.buttonClicked.connect(lambda _: self._mark_as_custom())
        self.slider_tile.valueChanged.connect(self._on_tile_changed)
        self.slider_denoise.valueChanged.connect(self._on_denoise_changed)
        self.slider_grain.valueChanged.connect(self._on_grain_changed)
        self.chk_face_enhance.toggled.connect(self._on_face_enhance_toggled)
        self.cmb_face_model.currentIndexChanged.connect(self._on_face_model_changed)
        self.slider_fidelity.valueChanged.connect(self._on_fidelity_changed)
        self.chk_mask_mouth.toggled.connect(
            lambda _: (self._mark_as_custom(), self.config_changed.emit())
        )
        self.slider_quality.valueChanged.connect(self._on_quality_changed)
        self.cmb_format.currentIndexChanged.connect(self._on_format_changed)
        self.btn_browse_dir.clicked.connect(self._on_browse_output)

    def _mark_as_custom(self):
        """Switches preset dropdown to 'Custom' if user modifies any setting."""
        if not self._applying_preset and self.cmb_preset.currentIndex() != 0:
            self._applying_preset = True
            try:
                self.cmb_preset.setCurrentIndex(0)
                self.lbl_preset_desc.setText("Custom manual tuning mode.")
            finally:
                self._applying_preset = False

    def _on_preset_changed(self, idx: int):
        if self._applying_preset:
            return
        key = self.cmb_preset.currentData()
        if key == "custom":
            self.lbl_preset_desc.setText("Custom manual tuning mode.")
            return

        if key in PRESETS:
            preset = PRESETS[key]
            self.lbl_preset_desc.setText(preset.description)
            self._applying_preset = True
            try:
                # Set model
                m_idx = self.cmb_model.findData(preset.model)
                if m_idx >= 0:
                    self.cmb_model.setCurrentIndex(m_idx)
                    info = MODELS.get(preset.model)
                    if info:
                        self.lbl_model_desc.setText(info.recommended_for)

                # Set scale
                if preset.scale == 4:
                    self.rb_scale_4.setChecked(True)
                else:
                    self.rb_scale_2.setChecked(True)

                # Set denoise and grain
                self.slider_denoise.setValue(preset.denoise_strength)
                self.lbl_denoise_val.setText(
                    "0% (Preserve Grain)"
                    if preset.denoise_strength == 0
                    else f"{preset.denoise_strength}%"
                )
                self.slider_grain.setValue(preset.grain_strength)
                self.lbl_grain_val.setText(
                    "0% (Off)"
                    if preset.grain_strength == 0
                    else f"{preset.grain_strength}% (Organic 35mm)"
                )

                # Set face enhance
                self.chk_face_enhance.setChecked(preset.enable_face_enhance)
                self.cmb_face_model.setEnabled(preset.enable_face_enhance)
                self.slider_fidelity.setEnabled(preset.enable_face_enhance)
                self.chk_mask_mouth.setEnabled(preset.enable_face_enhance)
                self.chk_mask_mouth.setChecked(preset.mask_mouth)

                f_idx = self.cmb_face_model.findData(preset.face_model)
                if f_idx >= 0:
                    self.cmb_face_model.setCurrentIndex(f_idx)

                fid_val = int(preset.face_fidelity * 100)
                self.slider_fidelity.setValue(fid_val)
                self.lbl_fidelity_val.setText(f"{preset.face_fidelity:.2f}")
            finally:
                self._applying_preset = False
            self.config_changed.emit()

    def _on_model_changed(self):
        key = self.cmb_model.currentData()
        if key in MODELS:
            info = MODELS[key]
            self.lbl_model_desc.setText(info.recommended_for)
            if info.native_scale == 4:
                self.rb_scale_4.setChecked(True)
            else:
                self.rb_scale_2.setChecked(True)
        self._mark_as_custom()
        self.config_changed.emit()

    def _on_tile_changed(self, val: int):
        if val == 0:
            self.lbl_tile_val.setText("0 (Auto / Fast)")
        else:
            self.lbl_tile_val.setText(f"{val} px")
        self.config_changed.emit()

    def _on_denoise_changed(self, val: int):
        if val == 0:
            self.lbl_denoise_val.setText("0% (Preserve Grain)")
        else:
            self.lbl_denoise_val.setText(f"{val}%")
        self._mark_as_custom()
        self.config_changed.emit()

    def _on_grain_changed(self, val: int):
        if val == 0:
            self.lbl_grain_val.setText("0% (Off)")
        else:
            self.lbl_grain_val.setText(f"{val}% (Organic 35mm)")
        self._mark_as_custom()
        self.config_changed.emit()

    def _on_face_enhance_toggled(self, checked: bool):
        self.cmb_face_model.setEnabled(checked)
        self.slider_fidelity.setEnabled(checked)
        self.chk_mask_mouth.setEnabled(checked)
        self._mark_as_custom()
        self.config_changed.emit()

    def _on_face_model_changed(self):
        self._mark_as_custom()
        self.config_changed.emit()

    def _on_fidelity_changed(self, val: int):
        self.lbl_fidelity_val.setText(f"{val / 100.0:.2f}")
        self._mark_as_custom()
        self.config_changed.emit()

    def _on_quality_changed(self, val: int):
        self.lbl_quality_val.setText(f"{val}%")
        self.config_changed.emit()

    def _on_format_changed(self, idx: int):
        is_png = idx == 1
        self.slider_quality.setEnabled(not is_png)
        self.lbl_quality_val.setEnabled(not is_png)
        self.config_changed.emit()

    def _on_browse_output(self):
        d = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.txt_output_dir.text()
        )
        if d:
            self.txt_output_dir.setText(d)
            self.config_changed.emit()

    def get_config(self) -> UpscaleConfig:
        model_key = self.cmb_model.currentData()
        scale = self.scale_group.checkedId()
        tile_size = self.slider_tile.value()
        denoise_strength = self.slider_denoise.value()
        grain_strength = self.slider_grain.value()
        enable_face_enhance = self.chk_face_enhance.isChecked()
        mask_mouth = self.chk_mask_mouth.isChecked() and enable_face_enhance
        face_model = self.cmb_face_model.currentData() or "codeformer"
        face_fidelity = self.slider_fidelity.value() / 100.0
        quality = self.slider_quality.value()
        output_dir = Path(self.txt_output_dir.text()).resolve()
        enable_gpu = self.chk_gpu.isChecked()
        cpu_workers = self.spin_cpu_workers.value()

        fmt_map = {0: "jpg", 1: "png", 2: "webp"}
        fmt = fmt_map.get(self.cmb_format.currentIndex(), "jpg")

        return UpscaleConfig(
            output_dir=output_dir,
            scale=scale,
            model=model_key,
            tile_size=tile_size,
            quality=quality,
            cpu_workers=cpu_workers,
            enable_gpu=enable_gpu,
            gpuid=0,
            output_format=fmt,
            denoise_strength=denoise_strength,
            grain_strength=grain_strength,
            enable_face_enhance=enable_face_enhance,
            face_model=face_model,
            face_fidelity=face_fidelity,
            mask_mouth=mask_mouth,
        )
