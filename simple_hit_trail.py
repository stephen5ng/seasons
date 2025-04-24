"""Simple hit trail implementation for the rhythm game.

This module provides a simplified hit trail visualization where each hit
simply lights up the closest LED and fades it out over time, rather than
creating a trailing effect.
"""

from typing import Dict, List, Optional, Tuple
import time
import pygame
from pygame import Color

class SimpleHitTrail:
    """A simple hit trail implementation that lights up LEDs at the current position only."""
    
    def __init__(self, fade_duration_ms: int = 500):
        """Initialize the simple hit trail.
        
        Args:
            fade_duration_ms: Duration in milliseconds for the fade-out effect
        """
        self.hit_positions: Dict[int, Tuple[Color, int]] = {}  # Maps position -> (color, timestamp)
        self.fade_duration_ms = fade_duration_ms
        print(f"SimpleHitTrail initialized with fade_duration={fade_duration_ms}ms")
    
    def add_hit(self, position: int, color: Color) -> None:
        """Add a hit at the specified position with the given color.
        
        Args:
            position: The LED position to light up
            color: The color to display at this position
        """
        # Store a copy of the color to avoid any reference issues
        stored_color = Color(color.r, color.g, color.b, color.a if hasattr(color, 'a') else 255)
        self.hit_positions[position] = (stored_color, pygame.time.get_ticks())
        print(f"SimpleHitTrail: Added hit at position {position} with color {stored_color}")
        print(f"SimpleHitTrail: Current hit positions: {list(self.hit_positions.keys())}")
    
    def draw(self, display_func) -> None:
        """Draw the simple hit trail.
        
        Args:
            display_func: Function to call to display a pixel
        """
        current_time_ms = pygame.time.get_ticks()
        positions_to_remove = []
        
        for pos, (color, timestamp) in self.hit_positions.items():
            elapsed_ms = current_time_ms - timestamp
            
            # If the fade duration has elapsed, mark for removal
            if elapsed_ms > self.fade_duration_ms:
                positions_to_remove.append(pos)
                continue
            
            # Calculate brightness based on elapsed time (non-linear fade for better effect)
            progress = elapsed_ms / self.fade_duration_ms
            brightness = 1.0 - (progress * progress)  # Quadratic fade
            
            # Apply brightness to color
            faded_color = Color(
                int(color.r * brightness),
                int(color.g * brightness),
                int(color.b * brightness),
                255  # Always full alpha
            )
            
            # Display the pixel
            display_func(pos, faded_color)
        
        # Remove expired positions
        for pos in positions_to_remove:
            del self.hit_positions[pos]
            print(f"SimpleHitTrail: Removed expired position {pos}")
        
        # Debug output for remaining positions
        if self.hit_positions:
            print(f"SimpleHitTrail: Remaining hit positions: {list(self.hit_positions.keys())}") 