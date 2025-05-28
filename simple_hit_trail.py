"""Simple hit trail implementation for the rhythm game.

This module provides a simplified hit trail visualization where each hit
simply lights up the closest LED, rather than creating a trailing effect.
"""
import pygame
from typing import Dict, Tuple, Optional, List, Protocol
from pygame import Color
from game_constants import TargetType, TARGET_COLORS
from display_manager import DisplayManager

LEDS_PER_HIT = 4

class TrailDisplay(Protocol):
    """Protocol for trail display implementations."""
    def set_pixel(self, position: int, color: Color, duration: float) -> None: ...
    def clear(self) -> None: ...
    def update(self) -> None: ...

class DefaultTrailDisplay:
    """Default display implementation that shows individual pixels."""
    
    def __init__(self, display: DisplayManager, led_count: int) -> None:
        """Initialize the default trail display.
        
        Args:
            display: DisplayManager instance for controlling the LED display
            led_count: Number of LEDs in the strip
        """
        self.display = display
        self.led_count = led_count

    def set_pixel(self, position: int, color: Color, duration: float) -> None:
        """Set a pixel in the display.
        
        Args:
            position: Position to set
            color: Color to set
            duration: Duration for the pixel
        """
        self.display.set_hit_trail_pixel(position, color, duration)

    def clear(self) -> None:
        """Clear the display."""
        for i in range(self.led_count):
            self.display.set_hit_trail_pixel(i, Color(0, 0, 0), -1)

    def update(self) -> None:
        """Update the display state. No-op for default display."""
        pass

class SimpleHitTrail:
    """A simple hit trail implementation that lights up a single LED position."""
    
    def __init__(self, display: DisplayManager, led_count: int, trail_display: Optional[TrailDisplay] = None) -> None:
        """Initialize the simple hit trail.
        
        Args:
            display: DisplayManager instance for controlling the LED display
            led_count: Number of LEDs in the strip
            trail_display: Optional display implementation to use (defaults to DefaultTrailDisplay)
        """
        self.led_count = led_count
        self.max_hits = led_count // LEDS_PER_HIT
        self.max_hits_per_target = self.max_hits // 4
        self.trail_display = trail_display or DefaultTrailDisplay(display, led_count)
        self._initialize_state()

    def _initialize_state(self) -> None:
        """Initialize or reset the hit trail state variables."""
        self.number_of_hits_by_type: Dict[TargetType, int] = {
            target_type: 0 for target_type in TargetType
        }
        self.hits_by_type: Dict[TargetType, List[int]] = {
            target_type: [] for target_type in TargetType
        }
        self.total_hits: int = 0
        self.trail_display.clear()

    def reset(self) -> None:
        """Reset the hit trail to its initial state."""
        self._initialize_state()

    def get_score(self) -> float:
        """Calculate current score based on total hits.
        
        Returns:
            Current score value
        """
        return self.total_hits / 4.0

    def add_hit(self, target_type: TargetType) -> None:
        """Add a hit to the trail.
        
        Args:
            target_type: Type of target that was hit
        """
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
        """Set LEDs for a hit position.
        
        Args:
            target_position: Position to set
            color: Color to set
        """
        for x in range(LEDS_PER_HIT):
            self.trail_display.set_pixel(target_position*LEDS_PER_HIT + x, color, -1)

    def remove_half_hits(self) -> None:
        """Remove half of the hits for each target type."""
        for target_type in TargetType:
            hits = self.hits_by_type[target_type]
            hits_to_remove = len(hits) // 2  # Integer division to remove half
            
            # Remove the most recent hits
            for _ in range(hits_to_remove):
                self.remove_hit(target_type)
        
        print(f"Removed half of hits, new total: {self.total_hits}")