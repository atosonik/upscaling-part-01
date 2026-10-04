"""Tiny windowed starter so Lumina shows a UI immediately.

The engine exe is a large PyInstaller onefile. It spends a while
extracting before any window appears. This starter opens first.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

_USER32 = ctypes.windll.user32


def _pid_has_window(pid: int) -> bool:
    found = ctypes.c_int(0)

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _each(hwnd, _lparam):
        if _USER32.IsWindowVisible(hwnd):
            out = ctypes.c_ulong()
            _USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(out))
            if out.value == pid and _USER32.GetWindow(hwnd, 4) == 0:
                found.value = 1
                return False
        return True

    _USER32.EnumWindows(_each, 0)
    return bool(found.value)


def _engine_path() -> Path:
    here = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    for name in ("Lumina-engine.exe", "Lumina.exe"):
        candidate = here / name
        if candidate.is_file() and candidate.resolve() != Path(sys.executable).resolve():
            return candidate
    raise SystemExit("Lumina-engine.exe is missing next to this starter.")


class Splash(QWidget):
    def __init__(self, engine: Path) -> None:
        super().__init__()
        self.engine = engine
        self.proc: subprocess.Popen | None = None
        self.setWindowTitle("Lumina")
        self.setFixedSize(460, 200)
        self.ticks = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Lumina")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        body = QLabel("Opening the studio…\nThe first launch can take a minute.")
        body.setAlignment(Qt.AlignCenter)
        body.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(body)
        self.setStyleSheet(
            """
            QWidget { background: #0c0b09; color: #f3ede2; }
            QLabel#title { font-size: 28px; color: #c9a36a; font-weight: 600; }
            QLabel { font-size: 13px; color: #c8bba8; }
            """
        )

    def start_engine(self) -> None:
        env = os.environ.copy()
        self.proc = subprocess.Popen(
            [str(self.engine)],
            cwd=str(self.engine.parent),
            env=env,
        )
        QTimer.singleShot(800, self._watch)

    def _watch(self) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is not None:
            QApplication.quit()
            return
        self.ticks += 1
        if _pid_has_window(self.proc.pid) or self.ticks >= 120:
            self.close()
            QApplication.quit()
            return
        QTimer.singleShot(800, self._watch)


def main() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#0c0b09"))
    palette.setColor(QPalette.WindowText, QColor("#f3ede2"))
    app.setPalette(palette)
    splash = Splash(_engine_path())
    splash.show()
    splash.raise_()
    QTimer.singleShot(100, splash.start_engine)
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
