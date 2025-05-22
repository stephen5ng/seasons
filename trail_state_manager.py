"""Trail state management for the rhythm game."""

from typing import Dict, List, Callable, Optional, Any, Union
import pygame
from pygame import Color
import easing_functions

from game_constants import (
    TARGET_COLORS, TargetType
)

class TrailStateManager:
    """Manages the state of LED trails and their rendering.
    
    This class encapsulates all functionality related to:
    - Main trail positions and colors
    - Trail rendering with easing effects
    """
    
    def __init__(self) -> None:
        """Initialize the trail state manager."""
        # Main trail state
        self.lit_positions: Dict[int, float] = {}  # Maps LED position to timestamp when it was lit
        self.lit_colors: Dict[int, Color] = {}     # Maps LED position to base color when it was lit
        
    def update_position(self, position: int, timestamp_s: float, base_color: Color = Color(255, 255, 255)) -> None:
        """Update the trail when a new LED position is reached.
        
        Args:
            position: The LED position
            timestamp_s: Current timestamp in seconds
            base_color: The base color for this position (default: white)
        """
        # Store the timestamp and color for the new position
        self.lit_positions[position] = timestamp_s
        self.lit_colors[position] = base_color
    
    def draw_main_trail(self, 
                       fade_duration: float,
                       ease_func: Any,
                       button_handler,
                       display_func: Callable[[int, Color], None]) -> None:
        """Draw the main trail with easing effects.
        
        Args:
            fade_duration: Duration of the fade effect in seconds
            ease_func: Easing function to use
            button_handler: Button handler to check if positions are in valid windows
            display_func: Function to call to display a pixel
            
        Returns:
            None - positions are cleaned up internally
        """
        positions_to_remove = self._draw_trail_with_easing(
            self.lit_positions,
            fade_duration,
            ease_func,
            lambda brightness, pos: self._get_target_trail_color(pos, brightness, button_handler),
            display_func
        )
        
        # Clean up old trail positions
        for pos in positions_to_remove:
            if pos in self.lit_positions:
                del self.lit_positions[pos]
            if pos in self.lit_colors:
                del self.lit_colors[pos]
    
    def _get_target_trail_color(self, pos: int, brightness: float, button_handler) -> Color:
        """Get color for target trail with brightness.
        
        Args:
            pos: LED position
            brightness: Brightness factor (0-1)
            button_handler: Button handler to check if position is in valid window
            
        Returns:
            Color for the target trail
        """
        base_color = self.lit_colors.get(pos, Color(255, 255, 255))
        if button_handler.is_in_valid_window(pos):
            pos_target_type = button_handler.get_target_type(pos)
            if pos_target_type:
                base_color = TARGET_COLORS[pos_target_type]
        return Color(
            int(base_color[0] * brightness),
            int(base_color[1] * brightness),
            int(base_color[2] * brightness),
            255
        )
    
    def _draw_trail_with_easing(self, 
                              positions: Dict[int, float],
                              fade_duration: float,
                              ease_func: Any,
                              color_func: Callable[[float, int], Color],
                              display_func: Callable[[int, Color], None]) -> List[int]:
        """Draw a trail with temporal easing.
        
        Args:
            positions: Dictionary mapping positions to timestamps
            fade_duration: Duration of the fade effect in seconds
            ease_func: Easing function to use
            color_func: Function to get color for a position
            display_func: Function to display a pixel
            
        Returns:
            List of positions to remove
        """
        current_time_s = pygame.time.get_ticks() / 1000.0
        positions_to_remove = []
        
        for pos, lit_time in positions.items():
            elapsed_s = current_time_s - lit_time
            if elapsed_s > fade_duration:
                positions_to_remove.append(pos)
            else:
                brightness = ease_func.ease(elapsed_s)
                color = color_func(brightness, pos)
                display_func(pos, color)
        
        return positions_to_remove 