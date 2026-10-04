from __future__ import annotations

from collections.abc import Callable

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from app.config import model_path
from app.core.image_ops import lab_to_rgb, rgb_to_lab
from app.models_arch.colorizers import SIGGRAPHGenerator


class Colorizer:
    def __init__(self, device: torch.device) -> None:
        self.device = device
        self.model = SIGGRAPHGenerator()
        state = torch.load(model_path("siggraph17"), map_location="cpu", weights_only=False)
        self.model.load_state_dict(state)
        self.model.to(device).eval()

    @torch.inference_mode()
    def run(
        self,
        rgb: np.ndarray,
        vividness: float = 1.0,
        progress: Callable[[str], None] | None = None,
    ) -> np.ndarray:
        if progress:
            progress("Colorizing the photograph…")

        work = cv2.resize(rgb, (256, 256), interpolation=cv2.INTER_CUBIC)
        lab = rgb_to_lab(work)
        light = lab[:, :, 0]
        tens_rs = torch.from_numpy(light).float()[None, None].to(self.device)
        out_ab = self.model(tens_rs)

        orig_lab = rgb_to_lab(rgb)
        orig_l = torch.from_numpy(orig_lab[:, :, 0]).float()[None, None].to(self.device)
        out_ab = F.interpolate(out_ab, size=orig_l.shape[-2:], mode="bilinear", align_corners=False)
        out_ab = out_ab * float(np.clip(vividness, 0.4, 1.6))

        merged = torch.cat((orig_l, out_ab), dim=1)
        lab_np = merged.squeeze(0).permute(1, 2, 0).cpu().numpy()
        colorized = lab_to_rgb(lab_np)
        return colorized
