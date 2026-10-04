from __future__ import annotations

import numpy as np
from PIL import Image


def load_rgb(path: str) -> np.ndarray:
    image = Image.open(path)
    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, (0, 0, 0))
        background.paste(image, mask=image.split()[-1])
        image = background
    else:
        image = image.convert("RGB")
    return np.asarray(image)


def save_rgb(path: str, rgb: np.ndarray) -> None:
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(path)


def is_grayscale(rgb: np.ndarray, chroma_threshold: float = 6.0) -> bool:
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        return True
    sample = rgb
    if rgb.size > 1_200_000:
        step = max(1, int(np.sqrt(rgb.size / 1_200_000)))
        sample = rgb[::step, ::step]
    channels = sample.astype(np.float32)
    chroma = np.mean(np.abs(channels[:, :, 0] - channels[:, :, 1])) + np.mean(
        np.abs(channels[:, :, 1] - channels[:, :, 2])
    )
    return chroma < chroma_threshold


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    import cv2

    bgr = rgb[:, :, ::-1]
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab[:, :, 0] = lab[:, :, 0] * (100.0 / 255.0)
    lab[:, :, 1] = lab[:, :, 1] - 128.0
    lab[:, :, 2] = lab[:, :, 2] - 128.0
    return lab


def lab_to_rgb(lab: np.ndarray) -> np.ndarray:
    import cv2

    converted = np.empty_like(lab, dtype=np.float32)
    converted[:, :, 0] = np.clip(lab[:, :, 0] * (255.0 / 100.0), 0, 255)
    converted[:, :, 1] = np.clip(lab[:, :, 1] + 128.0, 0, 255)
    converted[:, :, 2] = np.clip(lab[:, :, 2] + 128.0, 0, 255)
    bgr = cv2.cvtColor(converted.astype(np.uint8), cv2.COLOR_LAB2BGR)
    return bgr[:, :, ::-1]


def to_nchw(rgb: np.ndarray) -> "object":
    import torch

    tensor = torch.from_numpy(rgb.astype(np.float32) / 255.0)
    return tensor.permute(2, 0, 1).unsqueeze(0)


def from_nchw(tensor) -> np.ndarray:
    rgb = tensor.detach().float().clamp(0, 1).squeeze(0).permute(1, 2, 0).cpu().numpy()
    return np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
