from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDesktopWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, APP_TAGLINE, OUTPUTS_DIR
from app.core.engine import RestoreEngine, RestoreSettings
from app.core.image_ops import save_rgb
from app.ui.styles import QSS
from app.ui.widgets import CompareView, DropZone, StepCard


def _app_log(message: str) -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    log = OUTPUTS_DIR / "lumina.log"
    previous = log.read_text(encoding="utf-8") if log.exists() else ""
    log.write_text(previous + message + "\n", encoding="utf-8")
    print(message, flush=True)


class MainWindow(QMainWindow):
    def __init__(self, load_models: bool = True) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  ·  {APP_TAGLINE}")
        self.resize(1280, 800)
        self.setMinimumSize(1000, 680)
        self.setStyleSheet(QSS)

        self.engine = RestoreEngine()
        self.source_path = ""
        self.result_rgb: np.ndarray | None = None
        self._load_models = load_models
        self._busy_flag = False

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(16)
        layout.addLayout(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(self._build_left(), 0)
        body.addWidget(self._build_center(), 1)
        body.addWidget(self._build_right(), 0)
        layout.addLayout(body, 1)
        layout.addWidget(self._build_footer())

        if load_models:
            self.device_label.setText("STARTING ENGINE…")
            self._set_status("Window is open. Models will load in a moment…")
        else:
            self.device_label.setText("PREVIEW MODE")
            self._set_status("Interface preview — models are not loaded.")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._load_models:
            self._load_models = False
            QTimer.singleShot(150, self._load_models_now)

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        brand = QLabel(APP_NAME.upper())
        brand.setObjectName("Brand")
        tag = QLabel(APP_TAGLINE.upper())
        tag.setObjectName("Tagline")
        self.device_label = QLabel("Preparing models…")
        self.device_label.setObjectName("Meta")
        self.device_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(brand)
        col.addWidget(tag)
        row.addLayout(col)
        row.addStretch()
        row.addWidget(self.device_label)
        return row

    def _build_left(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setFixedWidth(300)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("SOURCE")
        title.setObjectName("Section")
        self.drop = DropZone()
        self.drop.clicked.connect(self._browse)
        self.drop.file_dropped.connect(self._open_path)

        self.meta_size = QLabel("No image loaded")
        self.meta_size.setObjectName("Value")
        self.meta_kind = QLabel("Drop a faded or gray photograph")
        self.meta_kind.setObjectName("Muted")
        self.meta_faces = QLabel("")
        self.meta_faces.setObjectName("Muted")

        browse = QPushButton("Browse files")
        browse.setObjectName("Ghost")
        browse.clicked.connect(self._browse)

        layout.addWidget(title)
        layout.addWidget(self.drop)
        layout.addWidget(self.meta_size)
        layout.addWidget(self.meta_kind)
        layout.addWidget(self.meta_faces)
        layout.addStretch()
        layout.addWidget(browse)
        return panel

    def _build_center(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Canvas")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self.compare = CompareView()
        layout.addWidget(self.compare)
        return panel

    def _build_right(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setFixedWidth(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("PIPELINE")
        title.setObjectName("Section")
        self.step_color = StepCard("Colorize", "Bring gray photographs back to color")
        self.step_upscale = StepCard("Upscale", "Real-ESRGAN reconstruction")
        self.step_face = StepCard("Face restore", "GFPGAN · tuned for portraits")

        scale_label = QLabel("UPSCALE")
        scale_label.setObjectName("Section")
        scale_row = QHBoxLayout()
        self.radio_2x = QRadioButton("2×")
        self.radio_4x = QRadioButton("4×")
        self.radio_4x.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.radio_2x)
        group.addButton(self.radio_4x)
        scale_row.addWidget(self.radio_2x)
        scale_row.addWidget(self.radio_4x)
        scale_row.addStretch()

        self.vivid_label = QLabel("Color vividness  ·  105%")
        self.vivid_label.setObjectName("Muted")
        self.vivid_slider = QSlider(Qt.Horizontal)
        self.vivid_slider.setRange(60, 150)
        self.vivid_slider.setValue(105)
        self.vivid_slider.valueChanged.connect(
            lambda value: self.vivid_label.setText(f"Color vividness  ·  {value}%")
        )

        self.face_label = QLabel("Face strength  ·  88%")
        self.face_label.setObjectName("Muted")
        self.face_slider = QSlider(Qt.Horizontal)
        self.face_slider.setRange(20, 100)
        self.face_slider.setValue(88)
        self.face_slider.valueChanged.connect(
            lambda value: self.face_label.setText(f"Face strength  ·  {value}%")
        )

        self.restore_btn = QPushButton("RESTORE PHOTOGRAPH")
        self.restore_btn.setObjectName("Primary")
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self._restore)
        self.save_btn = QPushButton("Save result")
        self.save_btn.setObjectName("Ghost")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)

        layout.addWidget(title)
        layout.addWidget(self.step_color)
        layout.addWidget(self.step_upscale)
        layout.addWidget(self.step_face)
        layout.addSpacing(6)
        layout.addWidget(scale_label)
        layout.addLayout(scale_row)
        layout.addWidget(self.vivid_label)
        layout.addWidget(self.vivid_slider)
        layout.addWidget(self.face_label)
        layout.addWidget(self.face_slider)
        layout.addStretch()
        layout.addWidget(self.restore_btn)
        layout.addWidget(self.save_btn)
        return panel

    def _build_footer(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("Panel")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)
        self.status = QLabel("Load a photograph to begin.")
        self.status.setObjectName("Value")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(220)
        self.progress.hide()
        layout.addWidget(self.status)
        layout.addStretch()
        layout.addWidget(self.progress)
        return bar

    def _pump(self, message: str | None = None) -> None:
        if message:
            self._set_status(message)
        QApplication.processEvents()

    def _load_models_now(self) -> None:
        _app_log("Loading models on the UI thread…")
        self._busy(True, "Loading AI models…")
        self._pump()
        try:
            self.engine.load(progress=self._pump)
        except Exception as exc:  # noqa: BLE001
            _app_log(f"Model load failed: {exc}")
            self._fail(str(exc))
            return
        extra = "  ·  some models failed" if self.engine.load_errors else ""
        self._busy(False, f"Ready  ·  {self.engine.device_label}{extra}")
        self.device_label.setText(f"ENGINE   {self.engine.device_label.upper()}")
        _app_log(f"Models ready on {self.engine.device_label}")

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open photograph",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)",
        )
        if path:
            self._open_path(path)

    def _open_path(self, path: str) -> None:
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, APP_NAME, "That file could not be opened as an image.")
            return
        self.source_path = path
        self.result_rgb = None
        self.save_btn.setEnabled(False)
        self.drop.set_preview(path, pixmap)
        self.compare.set_images(pixmap)
        self.meta_size.setText(f"{pixmap.width()} × {pixmap.height()}")
        self.meta_kind.setText(Path(path).name)
        self.meta_faces.setText("Faces will be detected during restore.")
        if self.engine.loaded:
            try:
                info = self.engine.inspect(path)
                kind = "Grayscale original" if info["gray"] else "Color original"
                faces = info["faces"]
                self.meta_kind.setText(kind)
                self.meta_faces.setText(f"{faces} face{'s' if faces != 1 else ''} detected")
                self.meta_size.setText(f"{info['width']} × {info['height']}")
            except Exception:
                pass
        self._set_status("Photograph loaded. Choose a pipeline and restore.")

    def _settings(self) -> RestoreSettings:
        return RestoreSettings(
            colorize=self.step_color.isChecked(),
            upscale=self.step_upscale.isChecked(),
            face_restore=self.step_face.isChecked(),
            scale=4.0 if self.radio_4x.isChecked() else 2.0,
            face_strength=self.face_slider.value() / 100.0,
            vividness=self.vivid_slider.value() / 100.0,
        )

    def _restore(self) -> None:
        if self._busy_flag:
            return
        if not self.source_path:
            QMessageBox.information(self, APP_NAME, "Drop or browse a photograph first.")
            return
        if not self.engine.loaded:
            QMessageBox.information(self, APP_NAME, "Models are still loading.")
            return
        settings = self._settings()
        if not (settings.colorize or settings.upscale or settings.face_restore):
            QMessageBox.information(self, APP_NAME, "Turn on at least one restoration step.")
            return
        self._busy(True, "Restoring photograph…")
        self._pump()
        try:
            source, result, info = self.engine.restore(
                self.source_path, settings, progress=self._pump
            )
        except Exception as exc:  # noqa: BLE001
            self._fail(str(exc))
            return
        self._on_restored(source, result, info)

    def _on_restored(self, source, result, info) -> None:
        self.result_rgb = result
        self.compare.set_images(_numpy_to_pixmap(source), _numpy_to_pixmap(result))
        src_w, src_h = info["source_size"]
        out_w, out_h = info["result_size"]
        self.meta_size.setText(f"{src_w} × {src_h}  →  {out_w} × {out_h}")
        self.meta_faces.setText(f"{info['faces']} face{'s' if info['faces'] != 1 else ''} restored")
        self.save_btn.setEnabled(True)
        self._busy(False, "  ·  ".join(info["notes"]) if info["notes"] else "Done.")

    def _save(self) -> None:
        if self.result_rgb is None:
            return
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        default = OUTPUTS_DIR / f"lumina_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save restored photograph",
            str(default),
            "PNG (*.png);;JPEG (*.jpg)",
        )
        if not path:
            return
        save_rgb(path, self.result_rgb)
        self._set_status(f"Saved  ·  {path}")

    def _busy(self, busy: bool, message: str) -> None:
        self._busy_flag = busy
        self.restore_btn.setEnabled(not busy)
        self.progress.setVisible(busy)
        self._set_status(message)

    def _set_status(self, message: str) -> None:
        self.status.setText(message)

    def _fail(self, message: str) -> None:
        self._busy(False, "Something went wrong.")
        QMessageBox.critical(self, APP_NAME, message)


def center_on_screen(window: QMainWindow) -> None:
    screen = QApplication.primaryScreen()
    if screen is None:
        desktop = QDesktopWidget()
        geo = desktop.availableGeometry()
    else:
        geo = screen.availableGeometry()
    frame = window.frameGeometry()
    frame.moveCenter(geo.center())
    window.move(frame.topLeft())


def _numpy_to_pixmap(rgb: np.ndarray) -> QPixmap:
    rgb = np.ascontiguousarray(rgb)
    height, width, _ = rgb.shape
    image = QImage(rgb.data, width, height, width * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(image.copy())
