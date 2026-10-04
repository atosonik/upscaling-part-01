from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from app.config import APP_NAME, MODELS, missing_models
from app.core.offline import ensure_local_weights, parts_available
from app.ui.styles import QSS


class SetupDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} · local models")
        self.setModal(True)
        self.resize(520, 420)
        self.setStyleSheet(QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(36, 36, 36, 28)
        root.setSpacing(14)

        brand = QLabel(APP_NAME)
        brand.setObjectName("Brand")
        brand.setAlignment(Qt.AlignCenter)
        hint = QLabel(
            "This app is offline. Models are assembled from the local\n"
            "parts/ folder — nothing is downloaded."
        )
        hint.setObjectName("Muted")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        missing = missing_models()
        for key, spec in MODELS.items():
            state = "needed" if key in missing else "ready"
            row = QLabel(f"{spec['label']}   ·   {state}")
            row.setObjectName("Value")
            card_layout.addWidget(row)

        self.status = QLabel(
            "Local parts are ready." if parts_available() else "No parts/ folder found."
        )
        self.status.setObjectName("Meta")
        self.status.setAlignment(Qt.AlignCenter)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.hide()

        self.start_btn = QPushButton("Assemble local models")
        self.start_btn.setObjectName("Primary")
        self.start_btn.setEnabled(parts_available())
        self.start_btn.clicked.connect(self._assemble)

        root.addWidget(brand)
        root.addWidget(hint)
        root.addWidget(card)
        root.addSpacing(8)
        root.addWidget(self.status)
        root.addWidget(self.bar)
        root.addWidget(self.start_btn)

        if not missing:
            self.accept()

    def _assemble(self) -> None:
        self.start_btn.setEnabled(False)
        self.bar.show()
        self.status.setText("Assembling models from parts…")
        try:
            ensure_local_weights(progress=self.status.setText)
        except Exception as exc:  # noqa: BLE001
            self.status.setText(str(exc))
            self.start_btn.setEnabled(True)
            self.bar.hide()
            return
        if missing_models():
            self.status.setText("Assembly finished, but some weights are still missing.")
            self.start_btn.setEnabled(True)
            self.bar.hide()
            return
        self.accept()
