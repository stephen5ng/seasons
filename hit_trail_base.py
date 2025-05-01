"""Base class for hit trails with easing support."""

from typing import Tuple, Callable, Dict
import pygame
from pygame import Color
from easing_functions import QuadEaseOut  # type: ignore
import game_constants
from game_constants import TargetType

class HitTrailBase:
    """Base class for hit trails with easing support."""
    
    def __init__(self, fade_duration_ms: int) -> None:
        """Initialize the hit trail.
        
        Args:
            fade_duration_ms: Duration in milliseconds for the fade-out effect
        """
        self.easing = QuadEaseOut(start=1.0, end=0.0, duration=fade_duration_ms)
        self.active_hits: Dict[int, Tuple[TargetType, int]] = {}  # position -> (target_type, start_time)
        self.rotate = 0.0
        self.rotate_speed = 0.0
        
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
        for pos, (target_type, start_time) in self.active_hits.items():
            elapsed_ms = current_time - start_time
            
            if elapsed_ms > self.easing.duration:
                positions_to_remove.append(pos)
                continue
                
            brightness = self.easing(elapsed_ms)
            
            # Get the color for this target type and apply brightness
            hit_color = game_constants.TARGET_COLORS[target_type]
            faded_color = Color(
                int(hit_color.r * brightness),
                int(hit_color.g * brightness),
                int(hit_color.b * brightness),
                255  # Always full alpha
            )
            
            self.rotate += self.rotate_speed
            r = int(self.rotate) % 300
            print(f"r: {r}, {self.rotate}, {self.rotate_speed}")
            display_func(pos + r, faded_color)
        
        # Remove expired positions
        for pos in positions_to_remove:
            del self.active_hits[pos]
            
        return len(self.active_hits) > 0 