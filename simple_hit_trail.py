"""Simple hit trail implementation for the rhythm game.

This module provides a simplified hit trail visualization where each hit
simply lights up the closest LED and fades it out over time, rather than
creating a trailing effect.
"""

from typing import Optional, Tuple
import time
import pygame
from pygame import Color

class SimpleHitTrail:
    """A simple hit trail implementation that lights up a single LED position."""
    
    def __init__(self, fade_duration_ms: int = 500):
        """Initialize the simple hit trail.
        
        Args:
            fade_duration_ms: Duration in milliseconds for the fade-out effect
        """
        self.hit_position: Optional[Tuple[int, Color, int]] = None  # (position, color, timestamp)
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
        self.hit_position = (position, stored_color, pygame.time.get_ticks())
    
    def draw(self, display_func) -> None:
        """Draw the simple hit trail.
        
        Args:
            display_func: Function to call to display a pixel
        """
        if not self.hit_position:
            return
            
        current_time_ms = pygame.time.get_ticks()
        position, color, timestamp = self.hit_position
        elapsed_ms = current_time_ms - timestamp
        
        # If the fade duration has elapsed, clear the hit
        if elapsed_ms > self.fade_duration_ms:
            self.hit_position = None
            return
        
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
        
        # Display the pixel at its actual position
        display_func(position, faded_color) 