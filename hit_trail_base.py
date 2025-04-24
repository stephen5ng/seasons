"""Base class for hit trails with easing support."""

from typing import Optional, Tuple, Callable
import pygame
from pygame import Color
from easing_functions import QuadEaseOut

class HitTrailBase:
    """Base class for hit trails with easing support."""
    
    def __init__(self, fade_duration_ms: int = 500) -> None:
        """Initialize the hit trail.
        
        Args:
            fade_duration_ms: Duration in milliseconds for the fade-out effect
        """
        self.easing = QuadEaseOut(start=1.0, end=0.0, duration=1.0)
        self.duration_ms = fade_duration_ms
        self.start_time: Optional[int] = None
    
    def add_hit(self, position: int, color: Color) -> None:
        """Add a hit at the specified position with the given color.
        
        Args:
            position: The LED position to light up
            color: The color to display at this position
        """
        self.start_time = pygame.time.get_ticks()
        self._add_hit_impl(position, color)
    
    def _add_hit_impl(self, position: int, color: Color) -> None:
        """Implementation of add_hit for subclasses.
        
        Args:
            position: The LED position to light up
            color: The color to display at this position
        """
        raise NotImplementedError("Subclasses must implement _add_hit_impl()")
    
    def draw(self, display_func: Callable[[int, Color], None]) -> None:
        """Draw the hit trail.
        
        Args:
            display_func: Function to call to display a pixel
        """
        raise NotImplementedError("Subclasses must implement draw()")
    
    def _display(self, position: int, color: Color, display_func: Callable[[int, Color], None]) -> bool:
        """Display a pixel.
        
        Args:
            position: The LED position to display
            color: The color to display
            display_func: Function to call to display a pixel
            
        Returns:
            True if the pixel was displayed, False if the display is complete
        """
        if self.start_time is None:
            return False
            
        current_time = pygame.time.get_ticks()
        elapsed_ms = current_time - self.start_time
        
        if elapsed_ms > self.duration_ms:
            self.start_time = None
            return False
            
        progress = elapsed_ms / self.duration_ms
        brightness = self.easing(progress)
            
        faded_color = Color(
            int(color.r * brightness),
            int(color.g * brightness),
            int(color.b * brightness),
            255  # Always full alpha
        )
        
        display_func(position, faded_color)
        return True 