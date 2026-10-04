from __future__ import annotations

from collections.abc import Callable

import cv2
import numpy as np
import torch

from app.config import model_path
from app.core.image_ops import from_nchw, to_nchw


class Upscaler:
    def __init__(self, device: torch.device) -> None:
        from spandrel import ImageModelDescriptor, ModelLoader

        loaded = ModelLoader().load_from_file(str(model_path("realesrgan_x4")))
        if not isinstance(loaded, ImageModelDescriptor):
            raise RuntimeError("Real-ESRGAN weights did not load as an image model.")
        self.model = loaded.to(device).eval()
        self.device = device
        self.scale = int(getattr(loaded, "scale", 4) or 4)

    @torch.inference_mode()
    def run(
        self,
        rgb: np.ndarray,
        outscale: float = 4.0,
        tile: int = 400,
        overlap: int = 16,
        progress: Callable[[str], None] | None = None,
    ) -> np.ndarray:
        if progress:
            progress("Upscaling detail with Real-ESRGAN…")

        upscaled = self._tiled(rgb, tile=tile, overlap=overlap)
        if abs(outscale - self.scale) > 0.05:
            target_w = max(1, int(round(rgb.shape[1] * outscale)))
            target_h = max(1, int(round(rgb.shape[0] * outscale)))
            interp = cv2.INTER_AREA if outscale < self.scale else cv2.INTER_LANCZOS4
            upscaled = cv2.resize(upscaled, (target_w, target_h), interpolation=interp)
        return upscaled

    def _tiled(self, rgb: np.ndarray, tile: int, overlap: int) -> np.ndarray:
        height, width = rgb.shape[:2]
        if max(height, width) <= tile:
            tensor = to_nchw(rgb).to(self.device)
            return from_nchw(self.model(tensor))

        output = np.zeros((height * self.scale, width * self.scale, 3), dtype=np.float32)
        weight = np.zeros((height * self.scale, width * self.scale, 1), dtype=np.float32)
        step = max(1, tile - overlap)

        for top in range(0, height, step):
            for left in range(0, width, step):
                bottom = min(top + tile, height)
                right = min(left + tile, width)
                top_i = max(0, bottom - tile)
                left_i = max(0, right - tile)
                crop = rgb[top_i:bottom, left_i:right]
                restored = from_nchw(self.model(to_nchw(crop).to(self.device)))
                out_top, out_left = top_i * self.scale, left_i * self.scale
                out_bottom = bottom * self.scale
                out_right = right * self.scale
                tile_h, tile_w = out_bottom - out_top, out_right - out_left
                mask = _soft_mask(tile_h, tile_w, fade=overlap * self.scale)
                output[out_top:out_bottom, out_left:out_right] += restored.astype(np.float32) * mask
                weight[out_top:out_bottom, out_left:out_right] += mask

        output /= np.clip(weight, 1e-6, None)
        return np.clip(output, 0, 255).astype(np.uint8)


def _soft_mask(height: int, width: int, fade: int) -> np.ndarray:
    fade = max(1, min(fade, height // 2, width // 2))
    mask = np.ones((height, width, 1), dtype=np.float32)
    ramp = np.linspace(0.15, 1.0, fade, dtype=np.float32)
    mask[:fade, :, 0] *= ramp[:, None]
    mask[-fade:, :, 0] *= ramp[::-1, None]
    mask[:, :fade, 0] *= ramp[None, :]
    mask[:, -fade:, 0] *= ramp[::-1][None, :]
    return mask
