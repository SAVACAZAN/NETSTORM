"""
NetStorm .type file parser.
Extracts unit properties and animation cluster definitions.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TypeDefinition:
    name: str
    base_type: str | None = None
    flags: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    clusters: list[ClusterEntry] = field(default_factory=list)


@dataclass
class ClusterEntry:
    id: str
    tags: list[str]
    files: list[tuple[str, int]]  # (filename, frame_index)


class TypeParser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def parse(self) -> TypeDefinition:
        # 1. Parse header: typename <name> [base]
        header_match = re.search(r"typename\s+(\w+)(?:\s+(\w+))?", self.text)
        if not header_match:
            raise ValueError("Missing typename")
        
        name = header_match.group(1)
        base = header_match.group(2)
        
        # 2. Parse flags: typeflags <f1> <f2> ...;
        flags_match = re.search(r"typeflags\s+([^;]+);", self.text)
        flags = flags_match.group(1).split() if flags_match else []
        
        # 3. Parse properties block: { ... }
        props = {}
        props_block_match = re.search(r"\{([^}]+)\}", self.text, re.DOTALL)
        if props_block_match:
            props_text = props_block_match.group(1)
            # Remove comments
            props_text = re.sub(r"//.*", "", props_text)
            # Match key = value;
            prop_matches = re.finditer(r"(\w+)\s*=\s*([^;]+);", props_text)
            for m in prop_matches:
                k = m.group(1)
                v = m.group(2).strip()
                # Try to convert to int/float
                if v.startswith('"') and v.endswith('"'):
                    v = v[1:-1]
                elif "." in v:
                    try: v = float(v)
                    except: pass
                else:
                    try: v = int(v)
                    except: pass
                props[k] = v

        # 4. Parse clusters
        # Format: ID : [tags] : "file.gif" #idx [: "file2.gif" #idx2];
        clusters = []
        cluster_lines = re.finditer(r"^(\w+)\s*:\s*([^:]*)\s*:\s*([^;]+);", self.text, re.MULTILINE)
        for m in cluster_lines:
            cid = m.group(1)
            tags = [t.strip() for t in m.group(2).split() if t.strip()]
            
            # Parse file parts
            files_part = m.group(3)
            # Match "file.gif" #idx
            file_matches = re.finditer(r'"([^"]+)"\s*#(\d+)', files_part)
            files = []
            for fm in file_matches:
                files.append((fm.group(1).lower(), int(fm.group(2))))
            
            clusters.append(ClusterEntry(cid, tags, files))

        return TypeDefinition(name, base, flags, props, clusters)


def parse(text: str) -> TypeDefinition:
    return TypeParser(text).parse()
