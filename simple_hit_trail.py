"""Simple hit trail implementation for the rhythm game.

This module provides a simplified hit trail visualization where each hit
simply lights up the closest LED, rather than creating a trailing effect.
"""
import pygame
from typing import Dict, Tuple, Optional, List
from pygame import Color
from game_constants import TargetType
from hit_trail_base import HitTrailBase

class SimpleHitTrail(HitTrailBase):
    """A simple hit trail implementation that lights up a single LED position."""
    
    def __init__(self) -> None:
        """Initialize the simple hit trail."""
        super().__init__(90000000000)
        self.hit_position: Optional[Tuple[int, TargetType]] = None  # (position, target_type)        
        self.number_of_hits_by_type: Dict[TargetType, int] = {}
        self.hits_by_type: Dict[TargetType, List[int]] = {}
        self.total_hits: int = 0

    def add_hit(self, position: int, target_type: TargetType) -> None:
        """Implementation of add_hit for subclasses.
        
        Args:
            position: The LED position to light up
            target_type: The type of target that was hit
        """
        self.total_hits += 1
        self.number_of_hits_by_type[target_type] = self.number_of_hits_by_type.get(target_type, 0) + 1
        new_position = position + self.number_of_hits_by_type[target_type]
        self.active_hits[new_position] = (target_type, pygame.time.get_ticks())
        
        if target_type not in self.hits_by_type:
            self.hits_by_type[target_type] = []
        self.hits_by_type[target_type].append(new_position)
        print(f"total_hits: {self.total_hits}")
    def remove_hit(self, target_type: TargetType) -> None:
        """Remove a hit of the specified target type from the hit trail.
        
        Args:
            target_type: Type of the hit to remove
        """
        self.total_hits -= 1
        if target_type in self.number_of_hits_by_type:
            self.number_of_hits_by_type[target_type] -= 1
        if target_type in self.hits_by_type and self.hits_by_type[target_type]:
            position = self.hits_by_type[target_type].pop()
            
            if position in self.active_hits:
                del self.active_hits[position]

    def draw(self, display_func) -> None:
        """Draw the simple hit trail.
        
        Args:
            display_func: Function to call to display a pixel
        """
        if self.total_hits > 40:
            self.rotate_speed = -0.01
        elif self.total_hits > 20:
            self.rotate_speed = 0.01
        else:
            self.rotate_speed = 0.0
        # elif self.total_hits > 40:
        #     self.rotate_speed = 0.1
            
        self._display(display_func) 