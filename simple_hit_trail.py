"""Simple hit trail implementation for the rhythm game.

This module provides a simplified hit trail visualization where each hit
simply lights up the closest LED, rather than creating a trailing effect.
"""
import pygame
from typing import Dict, Tuple, Optional, List, Callable
from pygame import Color
from game_constants import TargetType, TARGET_COLORS
from easing_functions import QuadEaseOut  # type: ignore
from display_manager import DisplayManager

LEDS_PER_HIT = 4
class SimpleHitTrail:
    """A simple hit trail implementation that lights up a single LED position."""
    
    def __init__(self, display: DisplayManager, led_count: int, fade_duration_ms: int = 90000000000) -> None:
        """Initialize the simple hit trail.
        
        Args:
            display: DisplayManager instance for controlling the LED display
            led_count: Number of LEDs in the strip
            fade_duration_ms: Duration in milliseconds for the fade-out effect
        """
        self.display = display
        self.led_count = led_count
        self.easing = QuadEaseOut(start=1.0, end=0.0, duration=fade_duration_ms)
        self.active_hits: Dict[int, Tuple[TargetType, int]] = {}  # position -> (target_type, start_time)
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
            Current score value (total_hits / 4.0)
        """
        return self.total_hits / (LEDS_PER_HIT * 4.0)

    def clear_all_hits(self) -> None:
        """Clear all hits from the hit trail and display."""
        while self.total_hits > 0:
            for target_type in TargetType:
                if self.hits_by_type[target_type]:
                    self.remove_hit(target_type)
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
            
        # Add the hit at the target position
        for n in range(LEDS_PER_HIT):
            self._add_hit_at_position(target_pos + n, target_type)

    def _add_hit_at_position(self, position: int, target_type: TargetType) -> None:
        """Internal method to add a hit at a specific position.
        
        Args:
            position: The LED position to light up
            target_type: The type of target that was hit
        """
        self.total_hits += 1
        new_position = position + self.number_of_hits_by_type[target_type]
        self.number_of_hits_by_type[target_type] += 1
        self.active_hits[new_position] = (target_type, pygame.time.get_ticks())
        self.hits_by_type[target_type].append(new_position)

    def remove_hit(self, target_type: TargetType) -> None:
        """Remove a hit of the specified target type from the hit trail.
        
        This method removes the hit from the trail and clears the LED by drawing black
        at that position.
        
        Args:
            target_type: Type of target to remove
        """
        # Get the position before removing the hit
        if self.hits_by_type[target_type]:
            position = self.hits_by_type[target_type][-1]
            # Clear the LED by drawing black permanently
            self.display.set_hit_trail_pixel(position, Color(0, 0, 0), -1)
            
            # Remove from tracking dictionaries
            self.number_of_hits_by_type[target_type] -= 1
            self.hits_by_type[target_type].pop()
            
            if position in self.active_hits:
                self.total_hits = max(0, self.total_hits - 1)
                print(f"total_hits: {self.total_hits}")
                del self.active_hits[position]

    def draw_trail(self, led_position: int) -> None:
        """Draw the hit trail at the given LED position.
        
        Args:
            led_position: Current LED position to draw at
        """
        if self.total_hits > 60:
            self.rotate_speed = -0.002
        elif self.total_hits > 50:
            self.rotate_speed = 0.002
        elif self.total_hits > 33:
            self.rotate_speed = 0.001
        else:
            self.rotate_speed = 0.0

        current_time = pygame.time.get_ticks()
        positions_to_remove = []
        
        for pos, (target_type, start_time) in self.active_hits.items():
            elapsed_ms = current_time - start_time
            
            if elapsed_ms > self.easing.duration:
                positions_to_remove.append(pos)
                continue
                
            brightness = self.easing(elapsed_ms)
            
            hit_color = TARGET_COLORS[target_type]
            faded_color = Color(
                int(hit_color.r * brightness),
                int(hit_color.g * brightness),
                int(hit_color.b * brightness),
                255  # Always full alpha
            )
            
            self.rotate += self.rotate_speed
            r = int(self.rotate) % 300
            r = 0
            self.display.set_hit_trail_pixel(pos + r, faded_color, -1)
        
        # Remove expired positions
        for pos in positions_to_remove:
            del self.active_hits[pos]

    @property
    def hit_colors(self) -> List[Color]:
        """Get the current hit colors.
        
        Returns:
            List of colors in the hit trail
        """
        if self.hit_position:
            _, color, _ = self.hit_position
            return [color]
        return [] 