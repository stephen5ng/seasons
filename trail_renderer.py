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

    def get_target_trail_color(self, pos: int, brightness: float, lit_colors: Dict[int, Color], button_handler) -> Color:
        """Get color for target trail with brightness."""
        base_color: Color = lit_colors[pos]
        if button_handler.is_in_valid_window(pos):
            target_type: Optional[TargetType] = button_handler.get_target_type(pos)
            if target_type:
                base_color = TARGET_COLORS[target_type]
        return Color(
            int(base_color[0] * brightness),
            int(base_color[1] * brightness),
            int(base_color[2] * brightness),
            base_color[3]
        )

    def get_bonus_trail_color(self, brightness: float) -> Color:
        """Get color for bonus trail with brightness."""
        if not self.get_rainbow_color:
            raise RuntimeError("get_rainbow_color_func must be provided to TrailRenderer for bonus trail color.")
        current_time_ms: int = self.get_ticks()
        # Use a different offset for bonus trail to create a different rainbow pattern
        rainbow_color: Color = self.get_rainbow_color(current_time_ms, 10)  # Using 10 as offset
        return Color(
            int(rainbow_color[0] * brightness),
            int(rainbow_color[1] * brightness),
            int(rainbow_color[2] * brightness),
            rainbow_color[3]
        )
