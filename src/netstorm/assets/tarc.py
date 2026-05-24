"""
NetStorm .tarc (TAFF v0.2) archive decoder.

Format: TAFF (Titanic Archive File Format)
Version: 0.2

Layout:
  - Header: "TAFF v0.2\x1a" (10 bytes) + 6 bytes padding
  - Entry Count: uint32 at offset 20 (0x14)
  - Descriptor Block Start: uint32 at offset 32 (0x20)
  - Data Block Start: uint32 at offset 40 (0x28)
  - Descriptors (starting at Descriptor Block Start):
      - data_off: uint32 (relative to Data Block Start)
      - data_size: uint32
      - file_name: null-terminated string
"""

from __future__ import annotations
import struct
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TarcEntry:
    name: str
    data: bytes
    offset: int  # byte offset in archive file
    size: int


@dataclass
class TarcArchive:
    entries: list[TarcEntry] = field(default_factory=list)
    _index: dict[str, TarcEntry] = field(default_factory=dict, repr=False)
    _crypt_key: bytes = b"mydoghasfleas"

    def get(self, name: str, decrypt: bool = True) -> bytes | None:
        name = name.replace("/", "\\").lower()
        if not name.startswith("\\"):
            name = "\\" + name
        entry = self._index.get(name)
        if not entry:
            return None
            
        data = entry.data
        # Decrypt if requested and file type is known to be encrypted.
        # Discovery 2026-05-03: .col files are also XOR-encrypted with same key.
        # Verified by decrypting sunarcher.col -> palette renders sprites correctly
        # (no more random colored noise). Magic 0x0803 0x0000 23b1 after decrypt.
        encrypted_exts = (".type", ".fort", ".english", ".cfg", ".col",
                          ".german", ".french", ".spanish", ".portuguese")
        if decrypt and any(name.endswith(ext) for ext in encrypted_exts):
            data = bytes([b ^ self._crypt_key[i % len(self._crypt_key)] for i, b in enumerate(data)])
            
        return data

    def __contains__(self, name: str) -> bool:
        name = name.replace("/", "\\").lower()
        if not name.startswith("\\"):
            name = "\\" + name
        return name in self._index

    def names(self) -> list[str]:
        return [e.name for e in self.entries]


def load(path: Path | str) -> TarcArchive:
    data = Path(path).read_bytes()
    return _parse(data)


def _parse(data: bytes) -> TarcArchive:
    if not data.startswith(b"TAFF v0.2\x1a"):
        raise ValueError("Not a TAFF v0.2 archive")

    count = struct.unpack_from("<I", data, 20)[0]
    desc_start = struct.unpack_from("<I", data, 32)[0]
    data_start = struct.unpack_from("<I", data, 40)[0]
    
    entries = []
    pos = desc_start
    for _ in range(count):
        data_off = struct.unpack_from("<I", data, pos)[0]
        data_size = struct.unpack_from("<I", data, pos + 4)[0]
        
        name_start = pos + 8
        name_end = data.find(b"\x00", name_start)
        name = data[name_start:name_end].decode("ascii", errors="replace")
        
        # Advance position to next descriptor (after null terminator)
        pos = name_end + 1
        
        # Extract data
        abs_off = data_start + data_off
        file_data = data[abs_off : abs_off + data_size]
        
        entries.append(TarcEntry(
            name=name.lower(),
            data=file_data,
            offset=abs_off,
            size=data_size
        ))

    archive = TarcArchive(entries=entries)
    archive._index = {e.name: e for e in entries}
    return archive
