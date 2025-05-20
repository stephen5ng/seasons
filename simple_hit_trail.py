"""Simple hit trail implementation for the rhythm game.

This module provides a simplified hit trail visualization where each hit
simply lights up the closest LED, rather than creating a trailing effect.
"""
import pygame
from typing import Dict, Tuple, Optional, List, Callable
from pygame import Color
from game_constants import TargetType, TARGET_COLORS
from display_manager import DisplayManager

LEDS_PER_HIT = 4

class SimpleHitTrail:
    """A simple hit trail implementation that lights up a single LED position."""
    
    def __init__(self, display: DisplayManager, led_count: int) -> None:
        """Initialize the simple hit trail.
        
        Args:
            display: DisplayManager instance for controlling the LED display
            led_count: Number of LEDs in the strip
        """
        self.display = display
        self.led_count = led_count
        self.max_hits = led_count // LEDS_PER_HIT
        self.max_hits_per_target = self.max_hits // 4

        self.number_of_hits_by_type: Dict[TargetType, int] = {
            target_type: 0 for target_type in TargetType
        }
        self.hits_by_type: Dict[TargetType, List[int]] = {
            target_type: [] for target_type in TargetType
        }
        self.total_hits: int = 0

    def get_score(self) -> float:
        """Calculate current score based on total hits.
        
        Returns:
            Current score value
        """
        return self.total_hits / 4.0

    def clear_some_hits(self) -> None:
        """Clear half of the hits from the hit trail, cycling through target types."""
        print(f"clearing half of hits, total_hits: {self.total_hits}")
        
        # Calculate how many hits to clear
        hits_to_clear = self.total_hits // 2
        hits_cleared = 0
        
        while hits_cleared < hits_to_clear:
            for target_type in TargetType:
                if self.hits_by_type[target_type]:
                    self.remove_hit(target_type)
                    hits_cleared += 1
                    if hits_cleared >= hits_to_clear:
                        return

    def add_hit(self, target_type: TargetType) -> None:
        print(f"adding hit for target_type: {target_type}")
        self.total_hits += 1
        while self.number_of_hits_by_type[target_type] >= self.max_hits_per_target:
            target_type = target_type.next()

        target_position = (target_type.value-1) * self.max_hits_per_target + self.number_of_hits_by_type[target_type]
        self.number_of_hits_by_type[target_type] += 1
        self._set_leds(target_position, TARGET_COLORS[target_type])
        self.hits_by_type[target_type].append(target_position)
    
    def remove_hit(self, target_type: TargetType) -> None:
        """Remove a hit of the specified target type from the hit trail.
        
        Args:
            target_type: Type of target to remove
        """
        if self.hits_by_type[target_type]:
            target_position = self.hits_by_type[target_type].pop()
            
            self._set_leds(target_position, Color(0, 0, 0))
            
            self.number_of_hits_by_type[target_type] -= 1
            self.total_hits = max(0, self.total_hits - 1)

    def _set_leds(self, target_position: int, color: Color) -> None:
        for x in range(LEDS_PER_HIT):
            self.display.set_hit_trail_pixel(
                target_position*LEDS_PER_HIT + x, color, -1)