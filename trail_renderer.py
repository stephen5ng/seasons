import pygame
from pygame import Color
from typing import Dict, Callable, List, Optional
from game_constants import TARGET_COLORS, TargetType

class TrailRenderer:
    def __init__(self, get_ticks_func=None, get_rainbow_color_func=None):
        self.get_ticks = get_ticks_func or (lambda: pygame.time.get_ticks())
        self.get_rainbow_color = get_rainbow_color_func

    def draw_trail_with_easing(self, positions: Dict[int, float], fade_duration: float, ease_func, 
                               color_func: Callable[[float], Color], display_func: Callable[[int, Color], None]) -> List[int]:
        """Draw a trail with temporal easing. Returns list of positions to remove."""
        current_time_s: float = self.get_ticks() / 1000.0
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

    def get_target_trail_color(self, pos: int = None, brightness: float = 1.0, lit_colors: Dict[int, Color] = None, button_handler = None, target_type: TargetType = None) -> Color:
        """Get color for target trail with brightness.
        
        This method can be called in two ways:
        1. With pos, brightness, lit_colors, and button_handler (original way)
        2. With brightness and target_type (new way for more flexibility)
        """
        base_color: Color = None
        
        # Handle the case where target_type is directly provided
        if target_type is not None:
            base_color = TARGET_COLORS[target_type]
        # Handle the original case with position and button handler
        elif pos is not None and lit_colors is not None and button_handler is not None:
            base_color = lit_colors[pos]
            if button_handler.is_in_valid_window(pos):
                pos_target_type: Optional[TargetType] = button_handler.get_target_type(pos)
                if pos_target_type:
                    base_color = TARGET_COLORS[pos_target_type]
        else:
            # Default to white if no color source is provided
            base_color = Color(255, 255, 255)
            
        return Color(
            int(base_color[0] * brightness),
            int(base_color[1] * brightness),
            int(base_color[2] * brightness),
            base_color[3] if len(base_color) > 3 else 255
        )

