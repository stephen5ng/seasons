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
        """Initialize the simple hit trail.
        
        Args:
            fade_duration_ms: Duration in milliseconds for the fade-out effect
        """
        super().__init__(16000)
        self.hit_position: Optional[Tuple[int, Color]] = None  # (position, color)        
        self.number_of_hits_by_color: Dict[Color, int] = {}
        self.hits_by_color: Dict[Color, List[int]] = {}
    def add_hit(self, position: int, color: Color) -> None:
        """Implementation of add_hit for subclasses.
        
        Args:
            position: The LED position to light up
            color: The color to display at this position
        """
        # Store a copy of the color to avoid any reference issues
        stored_color = Color(color.r, color.g, color.b, color.a if hasattr(color, 'a') else 255)
        
        color_hash = (stored_color.r, stored_color.g, stored_color.b)
        self.number_of_hits_by_color[color_hash] = self.number_of_hits_by_color.get(color_hash, 0) + 1
        new_position = position + self.number_of_hits_by_color[color_hash]
        self.active_hits[new_position] = (stored_color, pygame.time.get_ticks())
        
        if color_hash not in self.hits_by_color:
            self.hits_by_color = {}
            self.hits_by_color[color_hash] = []
        self.hits_by_color[color_hash].append(new_position)
        
    def remove_hit(self, color: Color) -> None:
        """Remove a hit of the specified target type from the hit trail.
        
        Args:
            color: Color of the hit to remove
        """
        color_hash = (color.r, color.g, color.b)
        if color_hash in self.number_of_hits_by_color:
            self.number_of_hits_by_color[color_hash] -= 1
        if color_hash in self.hits_by_color and self.hits_by_color[color_hash]:
            position = self.hits_by_color[color_hash].pop(0)
            
            if position in self.active_hits:
                del self.active_hits[position]

    def draw(self, display_func) -> None:
        """Draw the simple hit trail.
        
        Args:
            display_func: Function to call to display a pixel
        """
        self._display(display_func) 