from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal

from app.config import missing_models
from app.core.engine import RestoreEngine, RestoreSettings
from app.core.image_ops import save_rgb
from app.core.offline import ensure_local_weights


class AssembleWorker(QThread):
    failed = pyqtSignal(str)
    finished_ok = pyqtSignal()

    def run(self) -> None:
        try:
            ensure_local_weights()
            self.finished_ok.emit()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class LoadWorker(QThread):
    status = pyqtSignal(str)
    failed = pyqtSignal(str)
    finished_ok = pyqtSignal()

    def __init__(self, engine: RestoreEngine) -> None:
        super().__init__()
        self.engine = engine

    def run(self) -> None:
        try:
            self.engine.load(progress=self.status.emit)
            self.finished_ok.emit()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RestoreWorker(QThread):
    status = pyqtSignal(str)
    failed = pyqtSignal(str)
    finished_ok = pyqtSignal(object, object, object)

    def __init__(self, engine: RestoreEngine, path: str, settings: RestoreSettings) -> None:
        super().__init__()
        self.engine = engine
        self.path = path
        self.settings = settings

    def run(self) -> None:
        try:
            source, result, info = self.engine.restore(self.path, self.settings, progress=self.status.emit)
            self.finished_ok.emit(source, result, info)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


def models_ready() -> bool:
    return not missing_models()


def write_result(path: str, rgb) -> None:
    save_rgb(path, rgb)
