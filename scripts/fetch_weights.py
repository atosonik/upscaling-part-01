"""Resume-friendly weight downloader for flaky networks."""

from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import MIN_BYTES, MODELS, WEIGHTS_DIR, model_path


def download_with_resume(url: str, dest: Path, min_bytes: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = dest.stat().st_size if dest.exists() else 0
    request = urllib.request.Request(url, headers={"User-Agent": "Lumina/1.0"})
    if existing:
        request.add_header("Range", f"bytes={existing}-")
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            mode = "ab" if existing and response.status == 206 else "wb"
            if mode == "wb":
                existing = 0
            total_header = response.headers.get("Content-Length")
            total = int(total_header) + existing if total_header else min_bytes
            downloaded = existing
            with dest.open(mode) as handle:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    handle.write(chunk)
                    downloaded += len(chunk)
                    print(f"{dest.name}: {downloaded / 1_048_576:.1f} MB", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"{dest.name}: {exc}", flush=True)


def main() -> int:
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    pending = [key for key, spec in MODELS.items() if (model_path(key).stat().st_size if model_path(key).exists() else 0) < MIN_BYTES[key]]
    if not pending:
        print("All models ready.")
        return 0
    while pending:
        for key in list(pending):
            dest = model_path(key)
            have = dest.stat().st_size if dest.exists() else 0
            if have >= MIN_BYTES[key]:
                pending.remove(key)
                print(f"{dest.name}: complete ({have} bytes)")
                continue
            for url in MODELS[key]["urls"]:
                print(f"Fetching {key} from {url} (have {have} bytes)")
                download_with_resume(url, dest, MIN_BYTES[key])
                have = dest.stat().st_size if dest.exists() else 0
                if have >= MIN_BYTES[key]:
                    break
            time.sleep(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
