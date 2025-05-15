"""Display management utilities."""
import pygame
import math
from typing import Optional, Tuple, Callable, List, Any
from pygame import Color, Surface
from game_constants import *
import game_constants

# For Raspberry Pi mode
try:
    from rpi_ws281x import PixelStrip, Color as LEDColor
    IS_RASPBERRY_PI = True
except ImportError:
    IS_RASPBERRY_PI = False
    PixelStrip = None
    LEDColor = None

LED_OFFSET = 10
class DisplayManager:
    """Handles LED display output for both Pygame and WS281x."""
    
    def __init__(self, 
                 screen_width: int, 
                 screen_height: int, 
                 scaling_factor: int,
                 led_count: int,
                 led_pin: int,
                 led_freq_hz: int,
                 led_dma: int,
                 led_invert: bool,
                 led_brightness: int,
                 led_channel: int) -> None:
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
        # New dict to track active pixels: (pos, trail_type) -> (color, set_time, duration)
        self._active_pixels = {}
        
        # Create setter functions once at initialization
        def create_trail_setter(is_target: bool) -> Callable[[int, Color], None]:
            """Create a setter function for a trail type.
            
            Args:
                is_target: True for target trail, False for hit trail
                
            Returns:
                A function that sets a pixel on the specified trail
            """
            def setter(pos: int, color: Color) -> None:
                rpi_calc = lambda p, lc: (p + LED_OFFSET) % lc if is_target else (p + LED_OFFSET) % lc + lc
                radius = game_constants.TARGET_TRAIL_RADIUS if is_target else game_constants.HIT_TRAIL_RADIUS
                self._set_pixel_on_trail(pos, color, rpi_calc, radius)
            return setter
            
        # Store setters in a list for fast indexing (0=target, 1=hit)
        self._setters = [create_trail_setter(True), create_trail_setter(False)]
        
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

    def _set_pixel_on_trail(self, pos: int, color: Color, rpi_pos_calculator: Callable[[int, int], int], pygame_radius: int) -> None:
        """Activate a pixel on the display at a specific position.
        
        This method only handles the immediate display update.
        
        Args:
            pos: The logical position of the LED.
            color: The Pygame Color for the LED.
            rpi_pos_calculator: A function to calculate the actual LED index for Raspberry Pi.
            pygame_radius: The radius of the trail ring for Pygame display.
        """
        if IS_RASPBERRY_PI:
            actual_led_pos = rpi_pos_calculator(pos, self.led_count)
            self.strip.setPixelColor(actual_led_pos, self._convert_to_led_color(color))
        else:
            x, y = self._get_ring_position(pos, self.screen_width // 2, self.screen_height // 2, pygame_radius, self.led_count)
            self.pygame_surface.set_at((x, y), color)

    def _request_pixel_on_trail(self, pos: int, color: Color, trail_type: str, duration: float) -> None:
        """Request a pixel to be displayed on a trail with fade management.
        
        Args:
            pos: The logical position of the LED.
            color: The Pygame Color for the LED.
            trail_type: A string ('target' or 'hit') indicating the trail.
            duration: Duration (in seconds) for the pixel to remain on. If -1, the pixel remains until overridden.
        """
        now = pygame.time.get_ticks() / 1000.0
        # Store only color, time, and duration - setter can be derived from trail_type
        self._active_pixels[pos, trail_type] = (color, now, duration)
        




    def set_target_trail_pixel(self, pos: int, color: Color, duration: float = -1) -> None:
        """Set pixel color at position in target ring with an optional duration.
        
        Args:
            pos: The logical position of the LED.
            color: The Pygame Color for the LED.
            duration: Duration (in seconds) for the pixel to remain on. If -1, the pixel remains until overridden.
        """
        self._request_pixel_on_trail(pos, color, 'target', duration)
    
    def set_hit_trail_pixel(self, pos: int, color: Color, duration: float = -1) -> None:
        """Set pixel color at position in hit trail ring with an optional duration.
        
        Args:
            pos: The logical position of the LED.
            color: The Pygame Color for the LED.
            duration: Duration (in seconds) for the pixel to remain on. If -1, the pixel remains until overridden.
        """
        self._request_pixel_on_trail(pos, color, 'hit', duration)

    def update(self) -> None:
        """Update the display and fade out pixels if their duration has expired."""
        now = pygame.time.get_ticks() / 1000.0
        to_remove = []
        
        # First pass: update all pixels and collect ones to remove
        for (pos, trail_type), (color, set_time, duration) in self._active_pixels.items():
            elapsed = now - set_time
            trail_idx = 0 if trail_type == 'target' else 1
            setter = self._setters[trail_idx]
            
            if duration != -1 and elapsed >= duration:
                # Fade out: set the pixel to black
                faded_color = Color(0, 0, 0)
                setter(pos, faded_color)
                to_remove.append((pos, trail_type))
                continue
            elif duration > 0:
                # Interpolate for smooth fade out
                fade_ratio = 1 - (elapsed / duration)
                color = Color(
                    int(color.r * fade_ratio),
                    int(color.g * fade_ratio),
                    int(color.b * fade_ratio)
                )
            setter(pos, color)
        
        # Second pass: remove expired pixels
        for key in to_remove:
            del self._active_pixels[key]
            
        # Update the display
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
        angle = 2 * math.pi * i / led_count

        # Start at top (12 o'clock) and go clockwise
        x = int(radius * math.sin(angle))
        y = int(-radius * math.cos(angle))
        return (center_x + x, center_y + y)
