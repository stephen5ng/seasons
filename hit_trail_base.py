"""Base class for hit trails with easing support."""

from typing import Optional, Tuple, Callable, Dict, List
import pygame
from pygame import Color
from easing_functions import QuadEaseOut

class HitTrailBase:
    """Base class for hit trails with easing support."""
    
    def __init__(self, fade_duration_ms: int = 500) -> None:  # 30 seconds
        """Initialize the hit trail.
        
        Args:
            fade_duration_ms: Duration in milliseconds for the fade-out effect
        """
        self.easing = QuadEaseOut(start=1.0, end=0.0, duration=fade_duration_ms)
        self.active_hits: Dict[int, Tuple[Color, int]] = {}  # position -> (color, start_time)
    
    def add_hit(self, position: int, color: Color) -> None:
        """Add a hit at the specified position with the given color.
        
        Args:
            position: The LED position to light up
            color: The color to display at this position
        """
        # Store a copy of the color to avoid any reference issues
        stored_color = Color(color.r, color.g, color.b, color.a if hasattr(color, 'a') else 255)
        self.active_hits[position] = (stored_color, pygame.time.get_ticks())
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
    
    def _display(self, display_func: Callable[[int, Color], None]) -> bool:
        """Display all active hits.
        
        Args:
            display_func: Function to call to display a pixel
            
        Returns:
            True if there are any active hits, False otherwise
        """
        current_time = pygame.time.get_ticks()
        positions_to_remove = []
        
        # Display all active hits
        for pos, (hit_color, start_time) in self.active_hits.items():
            elapsed_ms = current_time - start_time
            
            if elapsed_ms > self.easing.duration:
                print(f"deleting elapsed_ms: {elapsed_ms}, duration: {self.easing.duration}")
                positions_to_remove.append(pos)
                continue
                
            brightness = self.easing(elapsed_ms)
            print(f"elapsed_ms: {elapsed_ms}, brightness: {brightness}")
                
            faded_color = Color(
                int(hit_color.r * brightness),
                int(hit_color.g * brightness),
                int(hit_color.b * brightness),
                255  # Always full alpha
            )
            
            display_func(pos, faded_color)
        
        # Remove expired positions
        for pos in positions_to_remove:
            del self.active_hits[pos]
            
        return len(self.active_hits) > 0 