"""Set a PE file's subsystem to WINDOWS (no console)."""

from __future__ import annotations

import struct
import sys
from pathlib import Path


def make_windowed(path: Path) -> None:
    data = bytearray(path.read_bytes())
    if data[:2] != b"MZ":
        raise SystemExit(f"{path} is not a PE file")
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew : e_lfanew + 4] != b"PE\0\0":
        raise SystemExit(f"{path} is missing a PE header")
    subsystem_off = e_lfanew + 0x5C
    current = struct.unpack_from("<H", data, subsystem_off)[0]
    # 2 = IMAGE_SUBSYSTEM_WINDOWS_GUI, 3 = IMAGE_SUBSYSTEM_WINDOWS_CUI
    data[subsystem_off : subsystem_off + 2] = struct.pack("<H", 2)
    path.write_bytes(data)
    print(f"{path.name}: subsystem {current} -> 2 (WINDOWS GUI)")


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\upscaling\dist\Lumina.exe")
    make_windowed(target)
