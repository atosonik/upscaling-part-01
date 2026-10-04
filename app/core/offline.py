"""Assemble local model parts. Never touches the network."""

from __future__ import annotations

from collections.abc import Callable

from app.config import PARTS_DIR, WEIGHTS_DIR, missing_models


def parts_available() -> bool:
    return (PARTS_DIR / "manifest.json").is_file()


def ensure_local_weights(progress: Callable[[str], None] | None = None) -> None:
    if not missing_models():
        return
    if not parts_available():
        raise RuntimeError(
            "Model weights are missing and no local parts/ folder was found. "
            "On a machine that already has weights/, run: python chunker.py split"
        )
    if progress:
        progress("Assembling models from local parts…")
    from chunker import assemble

    assemble(str(PARTS_DIR), str(WEIGHTS_DIR))
    if missing_models():
        raise RuntimeError(
            "Assembled weights are still incomplete. "
            "Run: python chunker.py merge"
        )
