"""NetStorm reimplementation entry point."""

from __future__ import annotations
import sys
import struct
from pathlib import Path

from netstorm.engine.rng import RNG
from netstorm.engine.timer import GameTimer
from netstorm.render.renderer import Renderer, RAYLIB_AVAILABLE
from netstorm.assets import tarc, shp
from netstorm.game.world import World
from netstorm.game.type_registry import TypeRegistry

# Path to the original game assets
ASSETS_DIR = Path(__file__).parents[3] / "netstorm" / "NetStorm RIP"

def load_palette(archive: tarc.TarcArchive) -> list[tuple[int, int, int]]:
    col_data = archive.get("\\d\\bulf.col")
    if not col_data:
        return [(i, i, i) for i in range(256)]

    palette = []
    for i in range(256):
        r, g, b = struct.unpack_from("BBB", col_data, 8 + i*3)
        palette.append((r, g, b))
    return palette

def main() -> None:
    # 1. Load foundational assets
    tarc_path = ASSETS_DIR / "netstorm.tarc"
    if not tarc_path.exists():
        print(f"Error: {tarc_path} not found")
        return

    archive = tarc.load(tarc_path)
    palette = load_palette(archive)

    from netstorm.assets import tarc, shp, fort
    ...
        # 2. Initialize Game Systems
        types = TypeRegistry(archive)
        types.load_all()

        rng = RNG(seed=1)
        world = World(types, rng)

        # 3. Load Map
        map_data = archive.get(r"\d\thewarbegins.fort")
        m = fort.FortMap(map_data)
        m.decode()

        # 4. Spawn initial units (Example: Altar and Bulf)
        world.spawn_unit("altar", 16, 16, 0)
        world.spawn_unit("bulf", 18, 16, 0)

        timer = GameTimer()
        renderer = Renderer()

        # 5. Sprite loading for tiles
        shp_path = ASSETS_DIR / "d" / "_shapes.shp"
        shp_decoder = shp.load(shp_path)

        if not RAYLIB_AVAILABLE:
            print("raylib not available — headless mode only")
            return

        renderer.init()
        try:
            while not renderer.should_close():
                # Fixed 71Hz logic tick
                while timer.should_tick():
                    world.tick()

                # Rendering
                renderer.begin_frame()
                renderer.draw_map(m, shp_decoder, palette)

                # TODO: draw units from world.state

                renderer.end_frame()
        finally:
            renderer.close()
    pass  # TODO: game logic


if __name__ == "__main__":
    main()
