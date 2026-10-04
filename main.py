from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# Offline: never let torch / huggingface / opencv phone home.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
os.environ.setdefault("OPENCV_OPENCL_RUNTIME", "")
# Import native ML libs before Qt. PyQt5 and torch both load C runtimes;
# loading Qt first makes torch's c10.dll fail with WinError 1114 on Windows.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: F401
import torch  # noqa: F401
import torchvision  # noqa: F401

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox

from app.config import APP_NAME, OUTPUTS_DIR, ROOT, WEIGHTS_DIR
from app.core.offline import ensure_local_weights
from app.ui.main_window import MainWindow, center_on_screen
from app.ui.setup_dialog import SetupDialog
from app.ui.workers import models_ready


def _log(message: str) -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    log = OUTPUTS_DIR / "lumina.log"
    previous = log.read_text(encoding="utf-8") if log.exists() else ""
    log.write_text(previous + message + "\n", encoding="utf-8")
    print(message, flush=True)


def _dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#0c0b09"))
    palette.setColor(QPalette.WindowText, QColor("#f3ede2"))
    palette.setColor(QPalette.Base, QColor("#16140f"))
    palette.setColor(QPalette.AlternateBase, QColor("#1b1813"))
    palette.setColor(QPalette.Text, QColor("#f3ede2"))
    palette.setColor(QPalette.Button, QColor("#1d1a14"))
    palette.setColor(QPalette.ButtonText, QColor("#f3ede2"))
    palette.setColor(QPalette.Highlight, QColor("#c9a36a"))
    palette.setColor(QPalette.HighlightedText, QColor("#1a140c"))
    palette.setColor(QPalette.ToolTipBase, QColor("#1b1813"))
    palette.setColor(QPalette.ToolTipText, QColor("#f3ede2"))
    return palette


def main() -> int:
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    _log(f"Lumina starting… torch={torch.__version__} cuda={torch.cuda.is_available()}")

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setPalette(_dark_palette())
    app.setFont(QFont("Segoe UI", 10))

    preview = "--ui-preview" in sys.argv
    if not preview and not models_ready():
        try:
            ensure_local_weights(progress=lambda message: _log(message))
        except Exception as exc:  # noqa: BLE001
            _log(str(exc))

    # Always show the window first. A frozen exe that returns before show()
    # looks like "console only" / a silent hang.
    ready = preview or models_ready()
    window = MainWindow(load_models=ready and not preview)
    center_on_screen(window)
    window.show()
    window.raise_()
    window.activateWindow()
    app.processEvents()
    _log(f"Main window shown. root={ROOT}")

    if not preview and not models_ready():
        setup = SetupDialog(window)
        if setup.exec_() == QDialog.Accepted and models_ready():
            window._load_models = True
            window._load_models_now()
        else:
            window._set_status("Put weights\\ or parts\\ next to Lumina.exe, then restart.")
            _log("Local models are missing. Run: python chunker.py merge")

    if preview:
        shot = OUTPUTS_DIR / "ui_preview.png"
        window.grab().save(str(shot))
        _log(f"Wrote {shot}")
        return 0
    return app.exec_()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        text = traceback.format_exc()
        try:
            OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
            (OUTPUTS_DIR / "lumina.log").write_text(text, encoding="utf-8")
        except Exception:
            pass
        print(text, flush=True)
        try:
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "Lumina", text)
        except Exception:
            pass
        raise SystemExit(1)
