"""Base class for hit trails with easing support."""

from typing import Tuple, Callable, Dict
import pygame
from pygame import Color
from easing_functions import QuadEaseOut  # type: ignore

class HitTrailBase:
    """Base class for hit trails with easing support."""
    
    def __init__(self, fade_duration_ms: int) -> None:
        """Initialize the hit trail.
        
        Args:
            fade_duration_ms: Duration in milliseconds for the fade-out effect
        """
        self.easing = QuadEaseOut(start=1.0, end=0.0, duration=fade_duration_ms)
        self.active_hits: Dict[int, Tuple[Color, int]] = {}  # position -> (color, start_time)
    
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
                positions_to_remove.append(pos)
                continue
                
            brightness = self.easing(elapsed_ms)
                
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