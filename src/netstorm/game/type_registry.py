"""
Registry for unit and building types.
Loads and caches definitions from .type files.
"""

from __future__ import annotations
from pathlib import Path
from netstorm.assets import tarc, type_parser


class TypeRegistry:
    def __init__(self, archive: tarc.TarcArchive) -> None:
        self.archive = archive
        self.types: dict[str, type_parser.TypeDefinition] = {}

    def load_all(self) -> None:
        """Scan the archive and load all .type files."""
        for name in self.archive.names():
            if name.endswith(".type"):
                # .get() automatically decrypts with "mydoghasfleas"
                data = self.archive.get(name)
                if data:
                    try:
                        text = data.decode("ascii", errors="replace")
                        defn = type_parser.parse(text)
                        self.types[defn.name.lower()] = defn
                    except Exception as e:
                        print(f"Error parsing {name}: {e}")

    def get(self, type_name: str) -> type_parser.TypeDefinition | None:
        return self.types.get(type_name.lower())
