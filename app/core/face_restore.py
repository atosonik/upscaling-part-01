from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import cv2
import numpy as np
import torch

from app.config import FFHQ_TEMPLATE_512, model_path
from app.core.image_ops import from_nchw, to_nchw


@dataclass
class FaceHit:
    box: tuple[int, int, int, int]
    landmarks: np.ndarray
    score: float


class FaceRestorer:
    def __init__(self, device: torch.device, fallback=None) -> None:
        from spandrel import ImageModelDescriptor, ModelLoader

        self.device = device
        self.fallback = fallback
        self.model = None
        try:
            loaded = ModelLoader().load_from_file(str(model_path("gfpgan")))
            if isinstance(loaded, ImageModelDescriptor):
                self.model = loaded.to(device).eval()
        except Exception:
            self.model = None
        if self.model is None and fallback is None:
            raise RuntimeError("GFPGAN could not be loaded and no fallback upscaler was provided.")
        self.detector = _load_yunet()
        self.template = np.array(FFHQ_TEMPLATE_512, dtype=np.float32)

    def detect(self, rgb: np.ndarray) -> list[FaceHit]:
        bgr = rgb[:, :, ::-1]
        height, width = bgr.shape[:2]
        if self.detector is None:
            return _haar_faces(bgr)

        self.detector.setInputSize((width, height))
        _, faces = self.detector.detect(bgr)
        hits: list[FaceHit] = []
        if faces is None:
            return hits
        for face in faces:
            x, y, w, h = face[:4]
            score = float(face[-1])
            raw = face[4:14].reshape(5, 2).astype(np.float32)
            landmarks = _order_landmarks(raw)
            hits.append(
                FaceHit(
                    box=(int(x), int(y), int(w), int(h)),
                    landmarks=landmarks,
                    score=score,
                )
            )
        return hits

    @torch.inference_mode()
    def run(
        self,
        rgb: np.ndarray,
        strength: float = 0.85,
        progress: Callable[[str], None] | None = None,
    ) -> tuple[np.ndarray, int]:
        faces = self.detect(rgb)
        if progress:
            if faces:
                progress(f"Restoring {len(faces)} face{'s' if len(faces) != 1 else ''}…")
            else:
                progress("No faces found — keeping the upscaled frame.")

        if not faces:
            return rgb, 0

        result = rgb.astype(np.float32)
        strength = float(np.clip(strength, 0.0, 1.0))
        for face in sorted(faces, key=lambda item: item.box[2] * item.box[3], reverse=True):
            restored, matrix = self._restore_aligned(rgb, face)
            if restored is None or matrix is None:
                continue
            inverse = cv2.invertAffineTransform(matrix)
            warped = cv2.warpAffine(
                restored,
                inverse,
                (rgb.shape[1], rgb.shape[0]),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
            )
            mask = _face_blend_mask(rgb.shape[1], rgb.shape[0], inverse)
            alpha = mask * strength
            result = warped.astype(np.float32) * alpha + result * (1.0 - alpha)
        return np.clip(result, 0, 255).astype(np.uint8), len(faces)

    def _restore_aligned(
        self, rgb: np.ndarray, face: FaceHit
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        if face.landmarks is not None and len(face.landmarks) == 5:
            matrix, _ = cv2.estimateAffinePartial2D(face.landmarks, self.template, method=cv2.LMEDS)
        else:
            matrix = _box_matrix(face.box, rgb.shape[1], rgb.shape[0])
        if matrix is None:
            return None, None

        aligned = cv2.warpAffine(
            rgb, matrix, (512, 512), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101
        )
        if self.model is not None:
            tensor = to_nchw(aligned).to(self.device)
            restored = from_nchw(self.model(tensor))
        elif self.fallback is not None:
            restored = self.fallback.run(aligned, outscale=1.0, tile=512, overlap=0)
        else:
            return None, None
        if restored.shape[0] != 512 or restored.shape[1] != 512:
            restored = cv2.resize(restored, (512, 512), interpolation=cv2.INTER_CUBIC)
        return restored, matrix


def _load_yunet():
    path = str(model_path("yunet"))
    try:
        detector = cv2.FaceDetectorYN.create(path, "", (320, 320), 0.7, 0.3, 5000)
        return detector
    except Exception:
        return None


def _order_landmarks(points: np.ndarray) -> np.ndarray:
    eyes = sorted(points[:2], key=lambda point: point[0])
    mouth = sorted(points[3:5], key=lambda point: point[0])
    return np.array([eyes[0], eyes[1], points[2], mouth[0], mouth[1]], dtype=np.float32)


def _box_matrix(box: tuple[int, int, int, int], width: int, height: int) -> np.ndarray:
    x, y, w, h = box
    side = int(max(w, h) * 1.4)
    cx, cy = x + w / 2, y + h / 2
    left = int(np.clip(cx - side / 2, 0, width - 1))
    top = int(np.clip(cy - side / 2, 0, height - 1))
    src = np.array(
        [[left, top], [left + side, top], [left, top + side]],
        dtype=np.float32,
    )
    dst = np.array([[0, 0], [512, 0], [0, 512]], dtype=np.float32)
    return cv2.getAffineTransform(src, dst)


def _face_blend_mask(width: int, height: int, inverse: np.ndarray) -> np.ndarray:
    yy, xx = np.ogrid[:512, :512]
    cx, cy = 256.0, 270.0
    rx, ry = 210.0, 230.0
    ellipse = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    mask = np.clip(1.2 - ellipse, 0.0, 1.0).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (0, 0), 18)
    warped = cv2.warpAffine(
        mask,
        inverse,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
    )
    return warped[:, :, None]


def _haar_faces(bgr: np.ndarray) -> list[FaceHit]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    boxes = cascade.detectMultiScale(gray, 1.1, 4, minSize=(32, 32))
    hits = []
    for x, y, w, h in boxes:
        hits.append(FaceHit(box=(int(x), int(y), int(w), int(h)), landmarks=np.zeros((0, 2)), score=0.5))
    return hits
