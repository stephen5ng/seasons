"""
Trail Visualization - Common utilities for visualizing LED trails

This module provides shared functionality for visualizing different types of LED trails
including hit trails and main trails. It's used by the main game (seasons.py).
"""

from pygame import Color
from typing import List

import game_constants
from display_manager import DisplayManager
from simple_hit_trail import SimpleHitTrail

class TrailVisualizer:
    """Base class for trail visualization.
    
    This class provides functionality for visualizing LED trails using the SimpleHitTrail strategy.
    """
    
    def __init__(self, 
                 display: DisplayManager,
                 led_count: int) -> None:
        """Initialize the trail visualizer.
        
        Args:
            display: DisplayManager instance for controlling the LED display
            led_count: Number of LEDs in the strip
        """
        self.led_count = led_count
        self.display = display
        self.simple_hit_trail = SimpleHitTrail()
    
    def get_score(self) -> float:
        """Get the current score from the hit trail.
        
        Returns:
            Current score value
        """
        return self.simple_hit_trail.get_score()
    
    def draw_trail(self, led_position: int) -> None:
        """Draw the hit trail at the given LED position.
        
        Args:
            led_position: Current LED position to draw at
        """
        self.simple_hit_trail.draw(lambda pos, color: self.display.set_hit_trail_pixel(pos, color, -1))
    
    @property
    def hit_colors(self) -> List[Color]:
        """Get the current hit colors.
        
        Returns:
            List of colors in the hit trail
        """
        if self.simple_hit_trail.hit_position:
            _, color, _ = self.simple_hit_trail.hit_position
            return [color]
        return []
    
    def remove_hit(self, target_type: game_constants.TargetType) -> None:
        """Remove a hit of the specified target type from the hit trail.
        
        This method removes the hit from the trail and clears the LED by drawing black
        at that position.
        
        Args:
            target_type: Type of target to remove
        """
        # Get the position before removing the hit
        if target_type in self.simple_hit_trail.hits_by_type and self.simple_hit_trail.hits_by_type[target_type]:
            position = self.simple_hit_trail.hits_by_type[target_type][-1]
            # Clear the LED by drawing black permanently
            self.display.set_hit_trail_pixel(position, Color(0, 0, 0), -1)
        
        # Remove the hit from the trail
        self.simple_hit_trail.remove_hit(target_type)
    
    def add_hit(self, target_type: game_constants.TargetType) -> None:
        """Add a hit of the specified target type to the hit trail.
        
        Args:
            target_type: Type of target to add
        """
        # Calculate target position based on target type
        if target_type == game_constants.TargetType.RED:
            target_pos = 0  # 12 o'clock
        elif target_type == game_constants.TargetType.GREEN:
            target_pos = int(self.led_count * 0.25)  # 3 o'clock
        elif target_type == game_constants.TargetType.BLUE:
            target_pos = int(self.led_count * 0.5)  # 6 o'clock
        else:  # YELLOW
            target_pos = int(self.led_count * 0.75)  # 9 o'clock
            
        # Add the hit at the target position
        self.simple_hit_trail.add_hit(target_pos, target_type)
        