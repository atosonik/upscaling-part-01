"""Split large files into small parts, and put them back together byte-exact.

Two part sets live in this project:

    parts/          the four model files the app loads   (weights/)
    runableparts/   the portable app zip                 (dist/Lumina.zip)

    python chunker.py split                            # weights/ -> parts/
    python chunker.py merge                            # parts/ -> weights/

    python pack_app.py                                 # dist/Lumina/ -> runableparts/
    python chunker.py verify --parts runableparts
    python pack_app.py --unpack                        # restores dist/Lumina/

Parts are capped at 1,000,000 bytes by default -- under "1 MB" whether that is
read as 10^6 or 2^20, so the output is safe either way.

Every part carries a SHA-256 and so does each whole file, both recorded in the
manifest. merge refuses to assemble anything that does not match.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEIGHTS = os.path.join(HERE, "weights")
PARTS = os.path.join(HERE, "parts")
MANIFEST = "manifest.json"
DEFAULT_CHUNK = 1_000_000
READ_BLOCK = 1 << 20

REQUIRED = [
    "RealESRGAN_x4plus.pth",
    "GFPGANv1.4.pth",
    "siggraph17-df00044c.pth",
    "face_detection_yunet_2023mar.onnx",
]


class ChunkError(Exception):
    """A part is missing, the wrong size, or fails its checksum."""


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1000 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1000.0
    return f"{n} B"


def parse_size(text: str) -> int:
    t = text.strip().upper().replace(" ", "")
    for suffix, mult in (
        ("KIB", 1 << 10),
        ("MIB", 1 << 20),
        ("GIB", 1 << 30),
        ("KB", 1000),
        ("MB", 1000_000),
        ("GB", 1000_000_000),
        ("K", 1000),
        ("M", 1000_000),
        ("G", 1000_000_000),
    ):
        if t.endswith(suffix):
            return int(float(t[: -len(suffix)]) * mult)
    return int(t)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(READ_BLOCK), b""):
            h.update(block)
    return h.hexdigest()


def resolve_sources(src: str, all_files: bool) -> tuple[str, list[str]]:
    src = os.path.abspath(src)
    if os.path.isfile(src):
        return os.path.dirname(src), [os.path.basename(src)]
    if not os.path.isdir(src):
        raise ChunkError(f"No such file or directory: {src}")

    is_weights = os.path.normcase(src) == os.path.normcase(os.path.abspath(WEIGHTS))
    if is_weights and not all_files:
        return src, [name for name in REQUIRED if os.path.exists(os.path.join(src, name))]

    found = []
    for root, _, names in os.walk(src):
        for name in sorted(names):
            found.append(os.path.relpath(os.path.join(root, name), src))
    return src, sorted(found)


def split_file(root: str, rel: str, parts_root: str, part_dir: str, chunk: int) -> dict:
    src = os.path.join(root, rel)
    out_dir = os.path.join(parts_root, part_dir) if part_dir else parts_root
    if part_dir and os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    total = os.path.getsize(src)
    count = max(1, -(-total // chunk))
    width = max(5, len(str(max(0, count - 1))))
    whole = hashlib.sha256()
    parts = []

    with open(src, "rb") as fh:
        for index in range(count):
            name = f"{index:0{width}d}.bin"
            part_hash = hashlib.sha256()
            written = 0
            with open(os.path.join(out_dir, name), "wb") as out:
                while written < chunk:
                    block = fh.read(min(READ_BLOCK, chunk - written))
                    if not block:
                        break
                    out.write(block)
                    part_hash.update(block)
                    whole.update(block)
                    written += len(block)
            if written == 0:
                os.remove(os.path.join(out_dir, name))
                break
            parts.append({"file": name, "size": written, "sha256": part_hash.hexdigest()})

    return {
        "path": rel.replace(os.sep, "/"),
        "parts_dir": part_dir.replace(os.sep, "/"),
        "size": total,
        "sha256": whole.hexdigest(),
        "parts": parts,
    }


def cmd_split(args) -> int:
    chunk = parse_size(args.size)
    if chunk < 1024:
        print("Chunk size must be at least 1 KB.", file=sys.stderr)
        return 2

    root, files = resolve_sources(args.src, args.all)
    if not files:
        print(f"Nothing to split under {root}.", file=sys.stderr)
        return 1

    parts_root = os.path.abspath(args.parts)
    os.makedirs(parts_root, exist_ok=True)
    flat = len(files) == 1 and os.path.isfile(os.path.abspath(args.src))

    entries, n_parts = [], 0
    for rel in files:
        part_dir = "" if flat else rel + ".parts"
        entry = split_file(root, rel, parts_root, part_dir, chunk)
        entries.append(entry)
        n_parts += len(entry["parts"])
        print(f"  {rel}  {human(entry['size'])} -> {len(entry['parts'])} parts")

    manifest = {
        "version": 2,
        "chunk_size": chunk,
        "root": os.path.relpath(root, HERE).replace(os.sep, "/"),
        "files": entries,
    }
    with open(os.path.join(parts_root, MANIFEST), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    total = sum(e["size"] for e in entries)
    print(
        f"\n{len(entries)} file(s), {n_parts} parts, {human(total)} in "
        f"{os.path.relpath(parts_root, HERE)}/"
    )
    return 0


def load_manifest(parts_root: str) -> dict:
    path = os.path.join(parts_root, MANIFEST)
    if not os.path.exists(path):
        raise ChunkError(f"No manifest at {path}. Run chunker.py split first.")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def entry_part_dir(parts_root: str, entry: dict) -> str:
    sub = entry.get("parts_dir", "")
    return os.path.join(parts_root, sub.replace("/", os.sep)) if sub else parts_root


def merge_file(entry: dict, parts_root: str, dest_root: str, force: bool) -> str:
    rel = entry["path"].replace("/", os.sep)
    dest = os.path.join(dest_root, rel)
    part_dir = entry_part_dir(parts_root, entry)

    if os.path.exists(dest) and not force:
        if os.path.getsize(dest) == entry["size"] and sha256_file(dest) == entry["sha256"]:
            return "skipped"

    missing = [
        part["file"]
        for part in entry["parts"]
        if not os.path.exists(os.path.join(part_dir, part["file"]))
    ]
    if missing:
        raise ChunkError(f"{rel}: {len(missing)} part(s) missing, first {missing[0]}")

    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    tmp = dest + ".merging"
    whole = hashlib.sha256()
    try:
        with open(tmp, "wb") as out:
            for part in entry["parts"]:
                with open(os.path.join(part_dir, part["file"]), "rb") as fh:
                    data = fh.read()
                if len(data) != part["size"]:
                    raise ChunkError(
                        f"{rel}: part {part['file']} is {len(data)} bytes, expected {part['size']}"
                    )
                if hashlib.sha256(data).hexdigest() != part["sha256"]:
                    raise ChunkError(f"{rel}: part {part['file']} failed its checksum")
                out.write(data)
                whole.update(data)
        if whole.hexdigest() != entry["sha256"]:
            raise ChunkError(f"{rel}: assembled file failed its checksum")
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise

    os.replace(tmp, dest)
    return "written"


def assemble(parts_root: str, dest_root: str | None = None, force: bool = False) -> tuple[int, int]:
    """Merge parts into dest_root. Returns (written, skipped)."""
    parts_root = os.path.abspath(parts_root)
    manifest = load_manifest(parts_root)
    dest = os.path.abspath(dest_root) if dest_root else os.path.abspath(
        os.path.join(HERE, manifest.get("root", "weights"))
    )
    written = skipped = 0
    for entry in manifest["files"]:
        result = merge_file(entry, parts_root, dest, force)
        written += result == "written"
        skipped += result == "skipped"
    return written, skipped


def cmd_merge(args) -> int:
    parts_root = os.path.abspath(args.parts)
    dest_root = os.path.abspath(args.dest) if args.dest else None
    written, skipped = assemble(parts_root, dest_root, args.force)
    manifest = load_manifest(parts_root)
    dest = os.path.abspath(args.dest) if args.dest else os.path.abspath(
        os.path.join(HERE, manifest.get("root", "weights"))
    )
    print(f"\n{written} written, {skipped} already correct, into {os.path.relpath(dest, HERE)}/")
    return 0


def cmd_verify(args) -> int:
    parts_root = os.path.abspath(args.parts)
    manifest = load_manifest(parts_root)
    bad = 0
    for entry in manifest["files"]:
        part_dir = entry_part_dir(parts_root, entry)
        problems = []
        for part in entry["parts"]:
            src = os.path.join(part_dir, part["file"])
            if not os.path.exists(src):
                problems.append(f"{part['file']} missing")
            elif os.path.getsize(src) != part["size"]:
                problems.append(f"{part['file']} wrong size")
            elif sha256_file(src) != part["sha256"]:
                problems.append(f"{part['file']} bad checksum")
        bad += len(problems)
        status = "ok" if not problems else f"{len(problems)} PROBLEM(S)"
        print(f"  [{status}] {entry['path']}  {len(entry['parts'])} parts")
        for problem in problems[:5]:
            print(f"       {problem}")
    print("\nAll parts verified." if not bad else f"\n{bad} bad part(s).")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    split_p = sub.add_parser("split", help="cut a file or folder into parts")
    split_p.add_argument("--src", default=WEIGHTS, help="file or folder (default: weights/)")
    split_p.add_argument("--parts", default=PARTS, help="output folder (default: parts/)")
    split_p.add_argument(
        "--size",
        default=str(DEFAULT_CHUNK),
        help="max part size, e.g. 1MB, 900KB (default 1000000)",
    )
    split_p.add_argument(
        "--all",
        action="store_true",
        help="for weights/, include files the app never loads",
    )
    split_p.set_defaults(func=cmd_split)

    merge_p = sub.add_parser("merge", help="rebuild the original from parts")
    merge_p.add_argument("--parts", default=PARTS, help="parts folder (default: parts/)")
    merge_p.add_argument(
        "--dest",
        default=None,
        help="where to restore (default: the folder recorded at split)",
    )
    merge_p.add_argument(
        "--force",
        action="store_true",
        help="rebuild even if the destination is already correct",
    )
    merge_p.set_defaults(func=cmd_merge)

    verify_p = sub.add_parser("verify", help="checksum every part without writing")
    verify_p.add_argument("--parts", default=PARTS, help="parts folder (default: parts/)")
    verify_p.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    try:
        if args.cmd == "merge":
            parts_root = os.path.abspath(args.parts)
            dest_root = os.path.abspath(args.dest) if args.dest else None
            manifest = load_manifest(parts_root)
            dest = dest_root or os.path.abspath(os.path.join(HERE, manifest.get("root", "weights")))
            written = skipped = 0
            for entry in manifest["files"]:
                result = merge_file(entry, parts_root, dest, args.force)
                written += result == "written"
                skipped += result == "skipped"
                print(f"  [{result}] {entry['path']}  {human(entry['size'])}")
            print(
                f"\n{written} written, {skipped} already correct, "
                f"into {os.path.relpath(dest, HERE)}/"
            )
            return 0
        return args.func(args)
    except ChunkError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        print("Re-split from a good copy, or re-fetch the damaged part.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
