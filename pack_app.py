"""Pack/unpack the portable app folder so chunker.py can split it.

    python pack_app.py              # dist/Lumina/ -> dist/Lumina.zip -> runableparts/
    python pack_app.py --unpack     # runableparts/ -> dist/Lumina.zip -> dist/Lumina/

weights/, parts/, and outputs/ are never put in the zip. After unpack, put
those folders next to Lumina.exe (or run: python chunker.py merge).
"""
from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_DIR = HERE / "dist" / "Lumina"
ARCHIVE = HERE / "dist" / "Lumina.zip"
PARTS = HERE / "runableparts"
SKIP_DIRS = {"weights", "parts", "outputs", "__pycache__"}


def _zip_app(app_dir: Path, archive: Path) -> None:
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        for path in sorted(app_dir.rglob("*")):
            rel = path.relative_to(app_dir)
            if any(part in SKIP_DIRS for part in rel.parts):
                continue
            if path.is_dir():
                continue
            zf.write(path, rel.as_posix())
            print(f"  + {rel}  ({path.stat().st_size} bytes)")


def pack() -> int:
    if not (APP_DIR / "Lumina.exe").is_file():
        print(f"Missing {APP_DIR / 'Lumina.exe'}.", file=sys.stderr)
        return 1
    if not (APP_DIR / "Lumina-engine.exe").is_file():
        print(f"Missing {APP_DIR / 'Lumina-engine.exe'}.", file=sys.stderr)
        return 1
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    print(f"Zipping {APP_DIR} -> {ARCHIVE}  (skipping {', '.join(sorted(SKIP_DIRS))})")
    _zip_app(APP_DIR, ARCHIVE)
    print(f"Archive {ARCHIVE.stat().st_size} bytes")
    print(f"Splitting {ARCHIVE} -> {PARTS}")
    from chunker import cmd_split

    args = argparse.Namespace(src=str(ARCHIVE), parts=str(PARTS), size="1000000", all=False)
    return cmd_split(args)


def unpack(dest: Path | None = None) -> int:
    from chunker import assemble

    dest_dir = dest or APP_DIR
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    print(f"Merging {PARTS} -> {ARCHIVE}")
    assemble(str(PARTS), str(ARCHIVE.parent), force=True)
    if not ARCHIVE.is_file():
        print(f"Merge did not produce {ARCHIVE}", file=sys.stderr)
        return 1
    if dest_dir.exists() and dest is None:
        for child in dest_dir.iterdir():
            if child.name.lower() in SKIP_DIRS:
                continue
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            elif child.is_file():
                child.unlink()
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {ARCHIVE} -> {dest_dir}")
    with zipfile.ZipFile(ARCHIVE) as zf:
        zf.extractall(dest_dir)
    exe = dest_dir / "Lumina.exe"
    engine = dest_dir / "Lumina-engine.exe"
    for name in ("weights", "parts"):
        target = HERE / name
        link = dest_dir / name
        if target.is_dir() and not link.exists():
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError:
                pass
    print(f"Ready: {exe}  exists={exe.is_file()}  engine={engine.is_file()}")
    return 0 if exe.is_file() and engine.is_file() else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unpack", action="store_true", help="merge parts and extract the app")
    parser.add_argument("--dest", default=None, help="extract here instead of dist/Lumina")
    args = parser.parse_args()
    if args.unpack:
        dest = Path(args.dest) if args.dest else None
        return unpack(dest)
    return pack()


if __name__ == "__main__":
    raise SystemExit(main())
