"""
NetStorm World simulation.
Integrates entities, types, and RNG.
"""

from __future__ import annotations
import numpy as np
from netstorm.game.squid import GameState, MAX_SQUIDS
from netstorm.game.type_registry import TypeRegistry
from netstorm.engine.rng import RNG


class World:
    """The central simulation engine."""

    def __init__(self, types: TypeRegistry, rng: RNG) -> None:
        self.state = GameState()
        self.types = types
        self.rng = rng
        self.frame: int = 0
        
        # Resource state (per player, assume 4 players max for now)
        self.mana = np.zeros(4, dtype=np.float32)
        self.money = np.zeros(4, dtype=np.int32)

    def tick(self) -> None:
        """Advance the simulation by one frame (at 71 Hz)."""
        self.frame += 1
        
        # 1. Process economy
        self._update_resources()
        
        # 2. Process all entities (Squids)
        for i in range(MAX_SQUIDS):
            # Check if squid is active (free bit TBD)
            # For now, just a placeholder loop
            pass
            
        # 3. Combat & Interactions
        self._process_combat()

    def _update_resources(self) -> None:
        # Placeholder: passive mana gain
        # In NetStorm, mana comes from priests and geysers.
        for p in range(len(self.mana)):
            self.mana[p] = (self.mana[p] + np.float32(0.01)).astype(np.float32)

    def _process_combat(self) -> None:
        """Mark squids with no power as dead (state=0 → free)."""
        for i in range(MAX_SQUIDS):
            if not self.state.is_free(i) and self.state.get_state(i) == 0:
                self.state.set_free(i, True)

    def apply_damage(self, target_index: int, amount: int) -> None:
        """Reduce a unit's power state by the given amount (clamped to 0)."""
        current = self.state.get_state(target_index)
        self.state.set_state(target_index, max(0, current - amount))

    def spawn_unit(self, type_name: str, x: float, y: float, player: int) -> int:
        """Find a free squid slot and initialize it with the given type."""
        defn = self.types.get(type_name)
        if not defn:
            return -1

        # Find free slot (placeholder — real engine uses a free-list)
        for i in range(MAX_SQUIDS):
            if self.state.is_free(i):
                self.state.set_free(i, False)
                self.state.set_id(i, i)

                # Initial power state: 3=strong (fully powered on spawn)
                self.state.set_state(i, 3)

                self.state.set_pos(i, x, y)
                self.state.set_owner(i, player)

                cost = defn.properties.get("cost", 0)
                if self.money[player] >= cost:
                    self.money[player] -= int(cost)

                return i
        return -1
