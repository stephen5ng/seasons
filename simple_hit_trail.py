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
        self.active_hits: Dict[int, TargetType] = {}  # position -> target_type
        self.rotate = 0.0
        self.rotate_speed = 0.0
        self.hit_position: Optional[Tuple[int, TargetType]] = None  # (position, target_type)        
        # Initialize dictionaries with default values for all target types
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
                        break

    def add_hit(self, target_type: TargetType) -> None:
        """Add a hit of the specified target type to the hit trail.
        
        Args:
            target_type: Type of target to add
        """
        # Calculate target position based on target type
        if target_type == TargetType.RED:
            target_pos = 0  # 12 o'clock
        elif target_type == TargetType.GREEN:
            target_pos = int(self.led_count * 0.25)  # 3 o'clock
        elif target_type == TargetType.BLUE:
            target_pos = int(self.led_count * 0.5)  # 6 o'clock
        else:  # YELLOW
            target_pos = int(self.led_count * 0.75)  # 9 o'clock
            
        self._add_hit_at_position(target_pos, target_type)

    def _add_hit_at_position(self, position: int, target_type: TargetType) -> None:
        """Internal method to add a hit at a specific position.
        
        Args:
            position: The LED position to light up
            target_type: The type of target that was hit
        """
        self.total_hits += 1
        new_position = position + self.number_of_hits_by_type[target_type]*LEDS_PER_HIT
        self.number_of_hits_by_type[target_type] += 1
        self.active_hits[new_position] = target_type
        for x in range(LEDS_PER_HIT):
            self.display.set_hit_trail_pixel(new_position + x, TARGET_COLORS[target_type], -1)         
        self.hits_by_type[target_type].append(new_position)

    def remove_hit(self, target_type: TargetType) -> None:
        """Remove a hit of the specified target type from the hit trail.
        
        Args:
            target_type: Type of target to remove
        """
        if self.hits_by_type[target_type]:
            position = self.hits_by_type[target_type].pop()
            
            # Clear all LEDs in the trail
            for x in range(LEDS_PER_HIT):
                self.display.set_hit_trail_pixel(position + x, Color(0, 0, 0), -1)
            
            self.number_of_hits_by_type[target_type] -= 1
            self.total_hits = max(0, self.total_hits - 1)
            del self.active_hits[position]

