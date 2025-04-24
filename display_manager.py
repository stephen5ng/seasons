"""Display management utilities."""
import pygame
import math
from typing import Optional, Tuple, Callable, List
from pygame import Color, Surface

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
        
        if IS_RASPBERRY_PI:
            self.strip: PixelStrip = PixelStrip(
                led_count, led_pin, led_freq_hz, led_dma, led_invert, led_brightness, led_channel
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
    
    # Original-style methods for backward compatibility
    def set_pixel(self, pos: int, color: Color) -> None:
        """Set pixel color at position in target ring."""
        if IS_RASPBERRY_PI:
            # Convert Pygame color to WS281x color (RGB order)
            ws_color: LEDColor = LEDColor(color.r, color.g, color.b)
            self.strip.setPixelColor(pos, ws_color)
        else:
            # Avoid circular import
            import game_constants
            x, y = self._get_ring_position(pos, 
                                         self.screen_width // 2, 
                                         self.screen_height // 2, 
                                         game_constants.TARGET_TRAIL_RADIUS, 
                                         game_constants.NUMBER_OF_LEDS)
            self.pygame_surface.set_at((x, y), color)
    
    def set_hit_trail_pixel(self, pos: int, color: Color) -> None:
        """Set pixel color at position in hit trail ring."""
        if not IS_RASPBERRY_PI:
            # Avoid circular import
            import game_constants
            x, y = self._get_ring_position(pos, 
                                         self.screen_width // 2, 
                                         self.screen_height // 2, 
                                         game_constants.HIT_TRAIL_RADIUS, 
                                         game_constants.NUMBER_OF_LEDS)
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
            # Convert Pygame color to WS281x color (RGB order)
            ws_color: LEDColor = LEDColor(color.r, color.g, color.b)
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
    
    def draw_score_lines(self, score: float, current_time: int, flash_intensity: float, 
                         flash_type: str, score_line_color: Color, high_score_threshold: float,
                         score_flash_duration_ms: int, score_line_animation_time_ms: int,
                         score_line_height: float, score_line_spacing: float,
                         get_rainbow_color_func: Callable[[int, int], Color],
                         get_score_line_color_func: Callable[[Color, float, str], Color]) -> None:
        """Draw horizontal lines representing the score with top-to-bottom animation.
        
        Args:
            score: Current score
            current_time: Current time in milliseconds
            flash_intensity: Intensity of the flash effect (0.0 to 1.0)
            flash_type: Type of flash effect (e.g., "red", "blue")
            score_line_color: Base color for score lines
            high_score_threshold: Threshold for high score rainbow effect
            score_flash_duration_ms: Duration of flash effect in milliseconds
            score_line_animation_time_ms: Time between line animations in milliseconds
            score_line_height: Height of each score line
            score_line_spacing: Spacing between score lines
            get_rainbow_color_func: Function to get rainbow color based on time and index
            get_score_line_color_func: Function to get score line color during flash
        """
        if not self.pygame_surface:
            return
            
        num_lines: int = int(score * 2)
        current_line: int = num_lines  # Default to all lines unlit
        
        if flash_intensity > 0:
            # Calculate which line should be lit based on time since flash started
            time_since_flash: float = score_flash_duration_ms * (1 - flash_intensity)
            current_line = int(time_since_flash / score_line_animation_time_ms)
            # Ensure we start from the top (line 0) and move downward
            current_line = min(current_line, num_lines - 1)
        
        for i in range(num_lines):
            y: int = self.screen_height - 1 - ((num_lines - 1 - i) * (score_line_height + score_line_spacing))
            if y >= 0:  # Only draw if we haven't gone off the top of the screen
                # Only use rainbow effect when not flashing
                base_color: Color
                line_color: Color
                if flash_intensity > 0 and i <= current_line:
                    # During flash animation, use base color for flash effect
                    base_color = score_line_color
                    line_color = get_score_line_color_func(base_color, flash_intensity, flash_type)
                elif flash_intensity == 0:
                    # When not flashing, use rainbow effect for high scores
                    base_color = get_rainbow_color_func(current_time, i) if score > high_score_threshold else score_line_color
                    line_color = base_color
                    
                pygame.draw.line(self.pygame_surface, line_color, (0, y), (10, y))
    
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
        angle = 2 * math.pi * i / led_count
        # Start at top (12 o'clock) and go clockwise
        x = int(radius * math.sin(angle))
        y = int(-radius * math.cos(angle))
        return (center_x + x, center_y + y)
