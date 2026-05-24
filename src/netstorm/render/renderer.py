"""
Raylib-based renderer for NetStorm reimplementation.

Rendering pipeline:
  1. Load palette from asset data (TBD — likely embedded in .shp)
  2. Convert palettized sprites → RGBA textures on first use
  3. Each tick: clear → draw map tiles → draw units → draw UI → present

All coordinates are in the game's isometric space; renderer handles
the isometric → screen projection.
"""

from __future__ import annotations
from dataclasses import dataclass, field

try:
    import pyray as rl
    RAYLIB_AVAILABLE = True
except ImportError:
    RAYLIB_AVAILABLE = False

SCREEN_W = 640   # original resolution
SCREEN_H = 480


@dataclass
class Renderer:
    width: int = SCREEN_W
    height: int = SCREEN_H
    title: str = "NetStorm: Islands at War"
    _texture_cache: dict[int, object] = field(default_factory=dict, repr=False)

    def init(self) -> None:
        if not RAYLIB_AVAILABLE:
            raise RuntimeError("raylib not installed — pip install raylib")
        rl.init_window(self.width, self.height, self.title)
        rl.set_target_fps(71)

    def close(self) -> None:
        if RAYLIB_AVAILABLE:
            rl.close_window()

    def begin_frame(self) -> None:
        rl.begin_drawing()
        rl.clear_background(rl.BLACK)

    def end_frame(self) -> None:
        rl.end_drawing()

    def should_close(self) -> bool:
        return rl.window_should_close() if RAYLIB_AVAILABLE else True

    def iso_to_screen(self, x: float, y: float) -> tuple[int, int]:
        """Convert isometric logical coordinates to screen pixels."""
        # Baseline projection confirmed via RE: 64x32 logical grid
        sx = int((x - y) * 32) + (self.width // 2)
        sy = int((x + y) * 16)
        return sx, sy

    def draw_map(self, m: object, shp_decoder: object, palette: list[tuple[int, int, int]]) -> None:
        """Render the 2D grid from a FortMap."""
        if not RAYLIB_AVAILABLE:
            return
            
        # Draw tiles in a specific order (back to front) for isometric depth
        for y in range(m.height):
            for x in range(m.width):
                tile_id = m.tiles[y, x]
                # Map tile_id to shp frame (placeholder: assume group 0)
                if tile_id < len(shp_decoder.groups[0].frames):
                    frame = shp_decoder.groups[0].frames[tile_id]
                    sx, sy = self.iso_to_screen(x, y)
                    self.draw_frame(frame, palette, sx, sy)

    def draw_frame(self, frame: object, palette: list[tuple[int, int, int]], x: int, y: int) -> None:
        """Draw a decoded ShapeFrame at the specified screen coordinates."""
        if not RAYLIB_AVAILABLE:
            return
            
        # For efficiency, we should cache the texture. 
        # For now, we'll draw pixel by pixel (slow, but works for testing).
        # Optimization: convert to rl.Image and then rl.Texture.
        
        # Check if we have a cached texture for this frame object
        frame_id = id(frame)
        if frame_id not in self._texture_cache:
            self._texture_cache[frame_id] = self._create_texture(frame, palette)
            
        texture = self._texture_cache[frame_id]
        rl.draw_texture(texture, x - frame.pivot_x, y - frame.pivot_y, rl.WHITE)

    def _create_texture(self, frame: object, palette: list[tuple[int, int, int]]) -> object:
        # Use the frame's built-in RGBA conversion
        rgba = frame.to_rgba(palette)
        img = rl.Image(rgba, frame.width, frame.height, 1, rl.PIXELFORMAT_UNCOMPRESSED_R8G8B8A8)
        tex = rl.load_texture_from_image(img)
        return tex
