"""Display management utilities."""
import pygame
import math
from typing import Optional, Tuple, Callable, List, Any
from pygame import Color, Surface
from game_constants import *

# For Raspberry Pi mode
try:
    from rpi_ws281x import PixelStrip, Color as LEDColor
    IS_RASPBERRY_PI = True
except ImportError:
    IS_RASPBERRY_PI = False
    PixelStrip = None
    LEDColor = None

class DisplayManager:
    """Handles LED display output for both Pygame and WS281x."""
    
    def __init__(self, 
                 screen_width: int, 
                 screen_height: int, 
                 scaling_factor: int,
                 led_count: int = 0,
                 led_pin: int = 18,
                 led_freq_hz: int = 800000,
                 led_dma: int = 10,
                 led_invert: bool = False,
                 led_brightness: int = 255,
                 led_channel: int = 0) -> None:
        """Initialize the display manager.
        
        Args:
            screen_width: Width of the screen in pixels
            screen_height: Height of the screen in pixels
            scaling_factor: Scaling factor for the display
            led_count: Number of LEDs in the strip (Raspberry Pi mode)
            led_pin: GPIO pin connected to the pixels (Raspberry Pi mode)
            led_freq_hz: LED signal frequency in Hz (Raspberry Pi mode)
            led_dma: DMA channel to use (Raspberry Pi mode)
            led_invert: True to invert the signal (Raspberry Pi mode)
            led_brightness: Set to 0 for darkest and 255 for brightest (Raspberry Pi mode)
            led_channel: PWM channel to use (Raspberry Pi mode)
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.scaling_factor = scaling_factor
        self.led_count = led_count
        
        if IS_RASPBERRY_PI:
            self.strip: PixelStrip = PixelStrip(
                led_count*2, led_pin, led_freq_hz, led_dma, led_invert, led_brightness, led_channel
            )
            self.strip.begin()
            self.pygame_surface: Optional[Surface] = None
            self.display_surface: Optional[Surface] = None
        else:
            self.strip: Optional[PixelStrip] = None
            self.display_surface: Surface = pygame.display.set_mode(
                (screen_width * scaling_factor, screen_height * scaling_factor)
            )
            self.pygame_surface: Surface = pygame.Surface((screen_width, screen_height))
    
    def clear(self) -> None:
        """Clear the display."""
        if IS_RASPBERRY_PI:
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, 0)
        else:
            self.pygame_surface.fill((0, 0, 0))
    
    def _convert_to_led_color(self, color: Color) -> Optional[Any]:
        """Convert Pygame color to WS281x color.
        
        Args:
            color: Pygame Color object
            
        Returns:
            WS281x Color object or None if not on Raspberry Pi
        """
        return LEDColor(color.r, color.g, color.b) if LEDColor else None

    def set_pixel(self, pos: int, color: Color) -> None:
        """Set pixel color at position in target ring."""
        if IS_RASPBERRY_PI:
            self.strip.setPixelColor(pos, self._convert_to_led_color(color))
        else:
            # Avoid circular import
            import game_constants
            x, y = self._get_ring_position(pos, 
                                         self.screen_width // 2, 
                                         self.screen_height // 2, 
                                         game_constants.TARGET_TRAIL_RADIUS, 
                                         self.led_count)
            self.pygame_surface.set_at((x, y), color)
    
    def set_hit_trail_pixel(self, pos: int, color: Color) -> None:
        """Set pixel color at position in hit trail ring."""
        if IS_RASPBERRY_PI:
            led_pos = pos % self.led_count
            led_pos += self.led_count
            self.strip.setPixelColor(led_pos, self._convert_to_led_color(color))
        else:
            # Avoid circular import
            import game_constants
            x, y = self._get_ring_position(pos, 
                                         self.screen_width // 2, 
                                         self.screen_height // 2, 
                                         game_constants.HIT_TRAIL_RADIUS, 
                                         self.led_count)
            self.pygame_surface.set_at((x, y), color)
            
    # New-style methods
    def set_target_pixel(self, pos: int, color: Color, 
                         center_x: int, center_y: int, radius: int, led_count: int) -> None:
        """Set pixel color at position in target ring.
        
        Args:
            pos: LED position index
            color: Color to set
            center_x: X coordinate of the circle center
            center_y: Y coordinate of the circle center
            radius: Radius of the circle
            led_count: Total number of LEDs in the circle
        """
        if IS_RASPBERRY_PI:
            ws_color = LEDColor(color.r, color.g, color.b) if LEDColor else None
            self.strip.setPixelColor(pos, ws_color)
        else:
            x, y = self._get_ring_position(pos, center_x, center_y, radius, led_count)
            self.pygame_surface.set_at((x, y), color)
    
    def update(self) -> None:
        """Update the display."""
        if IS_RASPBERRY_PI:
            self.strip.show()
        else:
            pygame.transform.scale(
                self.pygame_surface, 
                (self.screen_width * self.scaling_factor, self.screen_height * self.scaling_factor), 
                self.display_surface
            )
            pygame.display.update()
    
    def draw_score_lines(self, score: float) -> None:
        """Draw horizontal lines representing the score with top-to-bottom animation.
        
        Args:
            score: Current score
        """        
        if not self.pygame_surface:
            return
            
        num_lines: int = int(score * 2)
        
        for i in range(num_lines):
            y: int = max(0, self.screen_height - 1 - ((num_lines - 1 - i) * (SCORE_LINE_HEIGHT + SCORE_LINE_SPACING)))
            pygame.draw.line(self.pygame_surface, SCORE_LINE_COLOR, (0, y), (10, y))
    
    @staticmethod
    def _get_ring_position(i: int, center_x: int, center_y: int, 
                          radius: int, led_count: int) -> Tuple[int, int]:
        """Convert LED index to x,y coordinates in a circular pattern.
        
        Args:
            i: LED index
            center_x: X coordinate of the circle center
            center_y: Y coordinate of the circle center
            radius: Radius of the circle
            led_count: Total number of LEDs in the circle
            
        Returns:
            Tuple of (x, y) coordinates
        """
        # print(f"i: {i}, led_count: {led_count}")
        i -= 1
        angle = 2 * math.pi * i / led_count
        # Start at top (12 o'clock) and go clockwise
        x = int(radius * math.sin(angle))
        y = int(-radius * math.cos(angle))
        return (center_x + x, center_y + y)
