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
        self._initialize_state()

    def _initialize_state(self) -> None:
        """Initialize or reset the hit trail state variables.
        
        This internal method sets up the hit tracking variables and clears
        the LED display. It is used by both __init__ and reset.
        """
        self.number_of_hits_by_type: Dict[TargetType, int] = {
            target_type: 0 for target_type in TargetType
        }
        self.hits_by_type: Dict[TargetType, List[int]] = {
            target_type: [] for target_type in TargetType
        }
        self.total_hits: int = 0
        
        # Clear all LEDs in the hit trail
        for i in range(self.led_count):
            self.display.set_hit_trail_pixel(i, Color(0, 0, 0), -1)

    def reset(self) -> None:
        """Reset the hit trail to its initial state.
        
        This method reinitializes all hit tracking variables while preserving
        the display and LED configuration.
        """
        self._initialize_state()

    def get_score(self) -> float:
        """Calculate current score based on total hits.
        
        Returns:
            Current score value
        """
        return self.total_hits / 4.0

    def add_hit(self, target_type: TargetType) -> None:
        print(f"adding hit for target_type: {target_type}")
        self.total_hits += 1
        targets_tried = 0
        while self.number_of_hits_by_type[target_type] >= self.max_hits_per_target:
            target_type = target_type.next()
            targets_tried += 1
            if targets_tried > 4:
                return

        target_position = target_type.value * self.max_hits_per_target + self.number_of_hits_by_type[target_type]
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