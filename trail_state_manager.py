"""Trail state management for the rhythm game."""

from typing import Dict, List, Callable, Optional, Any, Union
import pygame
from pygame import Color
import easing_functions

from game_constants import (
    TARGET_WINDOW_SIZE, TARGET_COLORS, TargetType,
    TRAIL_FADE_DURATION_S, TRAIL_EASE,
    BONUS_TRAIL_FADE_DURATION_S, BONUS_TRAIL_EASE
)

class TrailStateManager:
    """Manages the state of LED trails and their rendering.
    
    This class encapsulates all functionality related to:
    - Main trail positions and colors
    - Bonus trail positions
    - Trail rendering with easing effects
    """
    
    def __init__(self, get_rainbow_color_func: Callable[[int, int], Color]) -> None:
        """Initialize the trail state manager.
        
        Args:
            get_rainbow_color_func: Function to generate rainbow colors
        """
        # Main trail state
        self.lit_positions: Dict[int, float] = {}  # Maps LED position to timestamp when it was lit
        self.lit_colors: Dict[int, Color] = {}     # Maps LED position to base color when it was lit
        
        # Bonus trail state
        self.bonus_trail_positions: Dict[int, float] = {}  # Maps LED position to timestamp when it was lit
        
        # Required functions
        self.get_rainbow_color_func = get_rainbow_color_func
        
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
        
        # Update bonus trail
        self.bonus_trail_positions[position] = timestamp_s
    
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
                
    def draw_bonus_trail(self, 
                        fade_duration: float,
                        ease_func: Any,
                        display_func: Callable[[int, Color], None],
                        position_transform: Callable[[int], int] = lambda x: x) -> None:
        """Draw the bonus trail with easing effects.
        
        Args:
            fade_duration: Duration of the fade effect in seconds
            ease_func: Easing function to use
            display_func: Function to call to display a pixel
            position_transform: Optional function to transform positions (default: identity)
        """
        positions_to_remove = self._draw_trail_with_easing(
            self.bonus_trail_positions,
            fade_duration,
            ease_func,
            lambda brightness, _: self._get_bonus_trail_color(brightness),
            lambda pos, color: display_func(position_transform(pos), color)
        )
        
        # Clean up old bonus trail positions
        for pos in positions_to_remove:
            if pos in self.bonus_trail_positions:
                del self.bonus_trail_positions[pos]
    
    def _draw_trail_with_easing(self, 
                              positions: Dict[int, float], 
                              fade_duration: float, 
                              ease_func: Any,
                              color_func: Callable[[float, int], Color], 
                              display_func: Callable[[int, Color], None]) -> List[int]:
        """Helper method to draw a trail with temporal easing.
        
        Args:
            positions: Dictionary mapping positions to timestamps
            fade_duration: Duration of the fade effect in seconds
            ease_func: Easing function to use
            color_func: Function to get color for a position with brightness
            display_func: Function to display a pixel
            
        Returns:
            List of positions to remove
        """
        current_time_s: float = pygame.time.get_ticks() / 1000.0
        positions_to_remove: List[int] = []
        
        for pos, lit_time in positions.items():
            elapsed_s: float = current_time_s - lit_time
            if elapsed_s > fade_duration:
                positions_to_remove.append(pos)
            else:
                brightness: float = ease_func.ease(elapsed_s)
                color: Color = color_func(brightness, pos)
                display_func(pos, color)
        
        return positions_to_remove
    
    def _get_target_trail_color(self, pos: int, brightness: float, button_handler) -> Color:
        """Get color for target trail with brightness.
        
        Args:
            pos: LED position
            brightness: Brightness factor (0.0-1.0)
            button_handler: Button handler to check if in valid window
            
        Returns:
            Color with applied brightness
        """
        if pos not in self.lit_colors:
            return Color(0, 0, 0)  # Safety check
            
        base_color: Color = self.lit_colors[pos]
        
        if button_handler.is_in_valid_window(pos):
            target_type: Optional[TargetType] = button_handler.get_target_type(pos)
            if target_type:
                base_color = TARGET_COLORS[target_type]
                
        return Color(
            int(base_color[0] * brightness),
            int(base_color[1] * brightness),
            int(base_color[2] * brightness),
            base_color[3] if len(base_color) > 3 else 255
        )
    
    def _get_bonus_trail_color(self, brightness: float) -> Color:
        """Get color for bonus trail with brightness.
        
        Args:
            brightness: Brightness factor (0.0-1.0)
            
        Returns:
            Color with applied brightness
        """
        current_time_ms: int = pygame.time.get_ticks()
        # Use offset for different rainbow pattern
        rainbow_color: Color = self.get_rainbow_color_func(current_time_ms, 10)
        
        return Color(
            int(rainbow_color[0] * brightness),
            int(rainbow_color[1] * brightness),
            int(rainbow_color[2] * brightness),
            rainbow_color[3] if len(rainbow_color) > 3 else 255
        ) 