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
