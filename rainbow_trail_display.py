"""Rainbow trail display implementation for the rhythm game.

This module provides a rainbow display visualization that lights up
all LEDs in a rainbow pattern during autopilot mode.
"""
from pygame import Color, time
from display_manager import DisplayManager
import random
from typing import List, Dict, Optional

# Define available colors
RAINBOW_COLORS = [
    Color(255, 0, 0),    # Red
    Color(0, 255, 0),    # Green
    Color(0, 0, 255),    # Blue
    Color(255, 255, 0),  # Yellow
    Color(255, 165, 0)   # Orange
]

PIXELS_PER_SWATH = 4

class RainbowTrailDisplay:
    """A display implementation that shows all LEDs in rotating game colors."""
    
    def __init__(self, display: DisplayManager, led_count: int) -> None:
        """Initialize the rainbow trail display.
        
        Args:
            display: DisplayManager instance for controlling the LED display
            led_count: Number of LEDs in the strip
        """
        self.display = display
        self.led_count = led_count
        self.last_update_ms = time.get_ticks()
        self.current_offset = 0
        
        # Define rainbow colors
        self.colors = [
            Color(255, 0, 0),      # Red
            Color(0, 255, 0),      # Green
            Color(0, 0, 255),      # Blue
            Color(255, 255, 0),    # Yellow
            Color(255, 165, 0),    # Orange
        ]
        
        # Each color gets 4 pixels
        self.pixels_per_color = 4
        
    def get_current_colors(self) -> List[Color]:
        """Get the current color sequence.
        
        Returns:
            List of colors in current sequence
        """
        # Create the full sequence of colors with each color repeated for pixels_per_color
        color_sequence = []
        for color in self.colors:
            color_sequence.extend([color] * self.pixels_per_color)
        return color_sequence

    def set_pixel(self, position: int, color: Color, duration: float) -> None:
        """Set a pixel in the display.
        
        In rainbow mode, we ignore the provided color and position since colors
        are managed by the rotating color array.
        
        Args:
            position: Position to set (ignored)
            color: Color to set (ignored)
            duration: Duration for the pixel (used as is)
        """
        pass

    def clear(self) -> None:
        """Clear the display."""
        pass

    def update(self) -> None:
        """Update the rainbow trail display.
        
        This rotates the colors every 200ms to create an animated effect.
        """
        current_time_ms = time.get_ticks()
        if current_time_ms - self.last_update_ms >= 200:  # Update every 200ms
            self.current_offset = (self.current_offset + 1) % len(self.colors)
            self.last_update_ms = current_time_ms
            
        # Get the current sequence of colors
        colors = self.get_current_colors()
        total_pattern_length = len(colors)
        
        # Update both hit trail and target trail pixels
        for i in range(self.led_count):
            # Calculate color index with offset and wrap around
            color_idx = (i + self.current_offset * self.pixels_per_color) % total_pattern_length
            color = colors[color_idx]
            
            # Update both trails with the same rainbow pattern
            self.display.set_hit_trail_pixel(i, color, 1.0)  # Layer 0 for hit trail
            self.display.set_target_trail_pixel(i, color, 1.0, 0)  # Layer 0 for target trail 