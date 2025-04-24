"""Simple hit trail implementation for the rhythm game.

This module provides a simplified hit trail visualization where each hit
simply lights up the closest LED, rather than creating a trailing effect.
"""

from typing import Optional, Tuple
from pygame import Color
from hit_trail_base import HitTrailBase

class SimpleHitTrail(HitTrailBase):
    """A simple hit trail implementation that lights up a single LED position."""
    
    def __init__(self, fade_duration_ms: int = 500) -> None:
        """Initialize the simple hit trail.
        
        Args:
            fade_duration_ms: Duration in milliseconds for the fade-out effect
        """
        super().__init__(fade_duration_ms)
        self.hit_position: Optional[Tuple[int, Color]] = None  # (position, color)
    
    def _add_hit_impl(self, position: int, color: Color) -> None:
        """Implementation of add_hit for subclasses.
        
        Args:
            position: The LED position to light up
            color: The color to display at this position
        """
        # Store a copy of the color to avoid any reference issues
        stored_color = Color(color.r, color.g, color.b, color.a if hasattr(color, 'a') else 255)
        self.hit_position = (position, stored_color)
    
    def draw(self, display_func) -> None:
        """Draw the simple hit trail.
        
        Args:
            display_func: Function to call to display a pixel
        """
        if not self.hit_position:
            return
            
        position, color = self.hit_position
        if not self._display(position, color, display_func):
            self.hit_position = None 