"""Simple hit trail implementation for the rhythm game.

This module provides a simplified hit trail visualization where each hit
simply lights up the closest LED, rather than creating a trailing effect.
"""
import pygame
from typing import Dict, Tuple, Optional, List, Callable
from pygame import Color
from game_constants import TargetType, TARGET_COLORS
from easing_functions import QuadEaseOut  # type: ignore

class SimpleHitTrail:
    """A simple hit trail implementation that lights up a single LED position."""
    
    def __init__(self, fade_duration_ms: int = 90000000000) -> None:
        """Initialize the simple hit trail.
        
        Args:
            fade_duration_ms: Duration in milliseconds for the fade-out effect
        """
        self.easing = QuadEaseOut(start=1.0, end=0.0, duration=fade_duration_ms)
        self.active_hits: Dict[int, Tuple[TargetType, int]] = {}  # position -> (target_type, start_time)
        self.rotate = 0.0
        self.rotate_speed = 0.0
        self.hit_position: Optional[Tuple[int, TargetType]] = None  # (position, target_type)        
        self.number_of_hits_by_type: Dict[TargetType, int] = {}
        self.hits_by_type: Dict[TargetType, List[int]] = {}
        self.total_hits: int = 0

    def get_score(self) -> float:
        """Calculate current score based on total hits.
        
        Returns:
            Current score value (total_hits / 4.0)
        """
        return self.total_hits / 4.0

    def add_hit(self, position: int, target_type: TargetType) -> None:
        """Add a hit to the trail.
        
        Args:
            position: The LED position to light up
            target_type: The type of target that was hit
        """
        self.total_hits += 1
        new_position = position + self.number_of_hits_by_type.get(target_type, 0)
        self.number_of_hits_by_type[target_type] = self.number_of_hits_by_type.get(target_type, 0) + 1
        self.active_hits[new_position] = (target_type, pygame.time.get_ticks())
        
        if target_type not in self.hits_by_type:
            self.hits_by_type[target_type] = []
        self.hits_by_type[target_type].append(new_position)
        # print(f"total_hits: {self.total_hits}")

    def remove_hit(self, target_type: TargetType) -> None:
        """Remove a hit of the specified target type from the hit trail.
        
        Args:
            target_type: Type of the hit to remove
        """
        if target_type in self.number_of_hits_by_type:
            self.number_of_hits_by_type[target_type] -= 1
        if target_type in self.hits_by_type and self.hits_by_type[target_type]:
            position = self.hits_by_type[target_type].pop()
            
            if position in self.active_hits:
                self.total_hits = max(0, self.total_hits - 1)
                print(f"total_hits: {self.total_hits}")
                del self.active_hits[position]

    def draw(self, display_func: Callable[[int, Color], None]) -> None:
        """Draw the simple hit trail.
        
        Args:
            display_func: Function to call to display a pixel
        """
        if self.total_hits > 60:
            self.rotate_speed = -0.002
        elif self.total_hits > 50:
            self.rotate_speed = 0.002
        elif self.total_hits > 33:
            self.rotate_speed = 0.001
        else:
            self.rotate_speed = 0.0

        current_time = pygame.time.get_ticks()
        positions_to_remove = []
        
        for pos, (target_type, start_time) in self.active_hits.items():
            elapsed_ms = current_time - start_time
            
            if elapsed_ms > self.easing.duration:
                positions_to_remove.append(pos)
                continue
                
            brightness = self.easing(elapsed_ms)
            
            hit_color = TARGET_COLORS[target_type]
            faded_color = Color(
                int(hit_color.r * brightness),
                int(hit_color.g * brightness),
                int(hit_color.b * brightness),
                255  # Always full alpha
            )
            
            self.rotate += self.rotate_speed
            r = int(self.rotate) % 300
            display_func(pos + r, faded_color)
        
        # Remove expired positions
        for pos in positions_to_remove:
            del self.active_hits[pos] 