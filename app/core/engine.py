from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from app.core.image_ops import is_grayscale, load_rgb


@dataclass
class RestoreSettings:
    colorize: bool = True
    upscale: bool = True
    face_restore: bool = True
    scale: float = 4.0
    face_strength: float = 0.88
    vividness: float = 1.05
    only_if_gray: bool = True


class RestoreEngine:
    def __init__(self) -> None:
        self.device = None
        self.colorizer = None
        self.upscaler = None
        self.faces = None
        self.loaded = False
        self.load_errors: list[str] = []

    @property
    def device_label(self) -> str:
        if self.device is None:
            return "Models not loaded"
        if getattr(self.device, "type", "") == "cuda":
            try:
                import torch

                return torch.cuda.get_device_name(0)
            except Exception:
                return "CUDA GPU"
        return "CPU"

    def load(self, progress: Callable[[str], None] | None = None) -> None:
        if self.loaded:
            return
        import torch

        from app.core.colorize import Colorizer
        from app.core.face_restore import FaceRestorer
        from app.core.upscale import Upscaler

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        errors: list[str] = []
        self.load_errors = []
        if progress:
            progress("Loading colorization model…")
        try:
            self.colorizer = Colorizer(self.device)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"colorizer: {exc}")
        if progress:
            progress("Loading Real-ESRGAN upscaler…")
        try:
            self.upscaler = Upscaler(self.device)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"upscaler: {exc}")
        if progress:
            progress("Loading GFPGAN face restorer…")
        try:
            self.faces = FaceRestorer(self.device, fallback=self.upscaler)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"face restorer: {exc}")
        self.load_errors = errors
        if self.colorizer is None and self.upscaler is None and self.faces is None:
            raise RuntimeError("No restoration models could be loaded. " + " | ".join(errors))
        self.loaded = True

    def inspect(self, path: str) -> dict:
        rgb = load_rgb(path)
        faces = 0
        if self.faces is not None:
            faces = len(self.faces.detect(rgb))
        return {
            "width": int(rgb.shape[1]),
            "height": int(rgb.shape[0]),
            "gray": is_grayscale(rgb),
            "faces": faces,
        }

    def restore(
        self,
        path: str,
        settings: RestoreSettings,
        progress: Callable[[str], None] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, dict]:
        if not self.loaded:
            self.load(progress)

        source = load_rgb(path)
        current = source
        gray = is_grayscale(source)
        notes: list[str] = []

        if settings.colorize and (gray or not settings.only_if_gray):
            if self.colorizer is None:
                raise RuntimeError("Colorizer model is not available.")
            current = self.colorizer.run(current, vividness=settings.vividness, progress=progress)
            notes.append("colorized")
        elif settings.colorize:
            notes.append("already in color")

        if settings.upscale:
            if self.upscaler is None:
                raise RuntimeError("Upscaler model is not available.")
            current = self.upscaler.run(current, outscale=settings.scale, progress=progress)
            notes.append(f"{settings.scale:g}× upscale")

        face_count = 0
        if settings.face_restore:
            if self.faces is None:
                raise RuntimeError("Face restoration model is not available.")
            current, face_count = self.faces.run(
                current, strength=settings.face_strength, progress=progress
            )
            notes.append(f"{face_count} face{'s' if face_count != 1 else ''} restored")

        info = {
            "gray": gray,
            "faces": face_count,
            "source_size": (source.shape[1], source.shape[0]),
            "result_size": (current.shape[1], current.shape[0]),
            "notes": notes,
        }
        return source, current, info
