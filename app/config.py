import sys
from pathlib import Path


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates = [exe_dir, exe_dir.parent, exe_dir.parent.parent, Path.cwd()]
        for candidate in candidates:
            if (candidate / "weights").is_dir() or (candidate / "parts" / "manifest.json").is_file():
                return candidate
        return exe_dir
    return Path(__file__).resolve().parent.parent


ROOT = _project_root()
WEIGHTS_DIR = ROOT / "weights"
OUTPUTS_DIR = ROOT / "outputs"
PARTS_DIR = ROOT / "parts"

APP_NAME = "Lumina"
APP_TAGLINE = "Photo Restoration Studio"

MODELS = {
    "realesrgan_x4": {
        "filename": "RealESRGAN_x4plus.pth",
        "label": "Real-ESRGAN 4×",
    },
    "gfpgan": {
        "filename": "GFPGANv1.4.pth",
        "label": "GFPGAN face restore",
    },
    "siggraph17": {
        "filename": "siggraph17-df00044c.pth",
        "label": "SIGGRAPH 2017 colorizer",
    },
    "yunet": {
        "filename": "face_detection_yunet_2023mar.onnx",
        "label": "YuNet face detector",
    },
}

REQUIRED_WEIGHTS = [spec["filename"] for spec in MODELS.values()]

# FFHQ 512 aligned 5-point template used by GFPGAN.
FFHQ_TEMPLATE_512 = (
    (192.98138, 239.94708),
    (318.90277, 240.19360),
    (256.63416, 314.01935),
    (201.26117, 371.41043),
    (313.00718, 371.15118),
)

MIN_BYTES = {
    "realesrgan_x4": 60_000_000,
    "gfpgan": 330_000_000,
    "siggraph17": 120_000_000,
    "yunet": 200_000,
}


def model_path(key: str) -> Path:
    return WEIGHTS_DIR / MODELS[key]["filename"]


def model_ready(key: str) -> bool:
    path = model_path(key)
    return path.is_file() and path.stat().st_size >= MIN_BYTES[key]


def missing_models() -> list[str]:
    return [key for key in MODELS if not model_ready(key)]
