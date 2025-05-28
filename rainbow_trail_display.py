"""Rainbow trail display implementation for the rhythm game.

This module provides a rainbow display visualization that lights up
all LEDs in a rainbow pattern during autopilot mode.
"""
from pygame import Color, time
from display_manager import DisplayManager
import random
from typing import List

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
        self.last_update_ms = 0
        self.UPDATE_INTERVAL_MS = 200  # Update every 200ms
        
        # Calculate number of color swaths needed
        self.num_swaths = (led_count + PIXELS_PER_SWATH - 1) // PIXELS_PER_SWATH
        
        # Initialize array with random game colors for each swath
        self.colors: List[Color] = []
        last_color = None
        for _ in range(self.num_swaths):
            # Get available colors (all except the last used color)
            available_colors = [c for c in RAINBOW_COLORS if c != last_color]
            color = random.choice(available_colors)
            self.colors.append(color)
            last_color = color

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
        """Update the display state by rotating colors once per second."""
        current_time_ms = time.get_ticks()
        if current_time_ms - self.last_update_ms >= self.UPDATE_INTERVAL_MS:
            # Rotate colors array by 1 position, ensuring no adjacent duplicates
            if self.colors[0] != self.colors[-1]:  # Safe to rotate if ends are different
                self.colors = self.colors[1:] + self.colors[:1]
            else:
                # If rotation would create adjacent duplicates, swap last color
                available_colors = [c for c in RAINBOW_COLORS if c != self.colors[0] and c != self.colors[-2]]
                self.colors[-1] = random.choice(available_colors)
                self.colors = self.colors[1:] + self.colors[:1]
            self.last_update_ms = current_time_ms
        
        # Always display current color array in 4-pixel swaths
        for swath_idx in range(self.num_swaths):
            color = self.colors[swath_idx]
            # Set all 4 pixels in this swath to the same color
            for pixel in range(PIXELS_PER_SWATH):
                led_idx = swath_idx * PIXELS_PER_SWATH + pixel
                if led_idx < self.led_count:  # Don't exceed LED strip length
                    self.display.set_hit_trail_pixel(led_idx, color, 0.5) 