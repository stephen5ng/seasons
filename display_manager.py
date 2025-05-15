"""Display management utilities."""
import pygame
import math
import numpy as np
import sys
from enum import Enum, auto
from typing import Optional, Tuple, Callable, List, Any, Dict
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

class TrailType(Enum):
    """Enum for trail types.
    
    The auto() values will be 0 for TARGET and 1 for HIT, making them perfect for array indexing.
    """
    TARGET = 0  # Explicitly set to 0 for array indexing
    HIT = 1     # Explicitly set to 1 for array indexing

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
        
        # Map trail types to their properties
        self._trail_properties: Dict[TrailType, Dict[str, Any]] = {
            TrailType.TARGET: {
                'rpi_calc': lambda p, lc: (p + LED_OFFSET) % lc,
                'radius': game_constants.TARGET_TRAIL_RADIUS,
                'setter': lambda pos, color: self._set_pixel_on_trail(
                    pos, color,
                    lambda p, lc: (p + LED_OFFSET) % lc,
                    game_constants.TARGET_TRAIL_RADIUS
                )
            },
            TrailType.HIT: {
                'rpi_calc': lambda p, lc: (p + LED_OFFSET) % lc + lc,
                'radius': game_constants.HIT_TRAIL_RADIUS,
                'setter': lambda pos, color: self._set_pixel_on_trail(
                    pos, color,
                    lambda p, lc: (p + LED_OFFSET) % lc + lc,
                    game_constants.HIT_TRAIL_RADIUS
                )
            }
        }
        
        # Numpy arrays to track active pixels in parallel
        # Shape: (2, led_count, 3) for colors, (2, led_count, 2) for timing
        # First dimension: trail_type (0 for target, 1 for hit)
        # Second dimension: pos (0 to led_count-1)
        # Third dimension: [r,g,b] for colors, [set_time, duration] for timing
        self._active_colors_np = np.zeros((2, led_count, 3), dtype=np.uint8)
        self._active_times_np = np.full((2, led_count, 2), [-1.0, -1.0], dtype=np.float32)  # Initialize with -1 for both set_time and duration
        
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

    def _request_pixel_on_trail(self, pos: int, color: Color, trail_type: TrailType, duration: float) -> None:
        """Request a pixel to be displayed on a trail with fade management.
        
        Args:
            pos: The logical position of the LED.
            color: The Pygame Color for the LED.
            trail_type: The type of trail (TARGET or HIT).
            duration: Duration (in seconds) for the pixel to remain on. If -1, the pixel remains until overridden.
                    Must be either -1 (permanent) or > 0 (fading).
        """
        if duration != -1 and duration <= 0:
            raise ValueError("Duration must be either -1 (permanent) or > 0 (fading)")
            
        now = pygame.time.get_ticks() / 1000.0
        
        # Update numpy arrays using enum value directly as index
        trail_idx = trail_type.value
        self._active_colors_np[trail_idx, pos] = [color.r, color.g, color.b]
        self._active_times_np[trail_idx, pos] = [now, duration]

    def set_target_trail_pixel(self, pos: int, color: Color, duration: float = -1) -> None:
        """Set pixel color at position in target ring with an optional duration.
        
        Args:
            pos: The logical position of the LED.
            color: The Pygame Color for the LED.
            duration: Duration (in seconds) for the pixel to remain on. If -1, the pixel remains until overridden.
        """
        self._request_pixel_on_trail(pos, color, TrailType.TARGET, duration)
    
    def set_hit_trail_pixel(self, pos: int, color: Color, duration: float = -1) -> None:
        """Set pixel color at position in hit trail ring with an optional duration.
        
        Args:
            pos: The logical position of the LED.
            color: The Pygame Color for the LED.
            duration: Duration (in seconds) for the pixel to remain on. If -1, the pixel remains until overridden.
        """
        self._request_pixel_on_trail(pos, color, TrailType.HIT, duration)

    def _calculate_faded_colors(self, now: float) -> np.ndarray:
        """Calculate faded colors for all pixels based on their durations and elapsed time.
        
        Args:
            now: Current time in seconds
            
        Returns:
            Array of faded colors with shape (2, led_count, 3)
        """
        # Get set_times and durations for all pixels
        set_times = self._active_times_np[:, :, 0]  # Shape: (2, led_count)
        durations = self._active_times_np[:, :, 1]  # Shape: (2, led_count)
        elapsed = now - set_times  # Shape: (2, led_count)
        
        # Create masks for different pixel states
        # Shape: (2, led_count, 1) for broadcasting with colors
        is_fading = (durations > 0)[..., None]  # Pixels that should fade
        is_expired = (is_fading & (elapsed >= durations)[..., None])  # Fading pixels that have expired
        is_permanent = (durations == -1)[..., None]  # Permanent pixels
        
        # Calculate fade ratios for fading pixels (1.0 to 0.0)
        # Shape: (2, led_count, 1)
        fade_ratios = np.where(
            is_fading,
            1.0 - np.clip(elapsed / durations, 0, 1)[..., None],
            1.0
        )
        
        # Calculate final colors:
        # - Expired pixels become black (0)
        # - Fading pixels are multiplied by fade ratio
        # - Permanent pixels keep original color
        return np.where(
            is_expired,
            0,  # Expired pixels become black
            np.where(
                is_permanent,
                self._active_colors_np,  # Permanent pixels keep original color
                (self._active_colors_np * fade_ratios).astype(np.uint8)  # Fading pixels
            )
        )

    def _update_display(self, faded_colors: np.ndarray) -> None:
        """Update the display with faded colors.
        
        Args:
            faded_colors: Array of faded colors with shape (2, led_count, 3)
        """
        # Update display using numpy implementation
        for trail_type in TrailType:
            trail_idx = trail_type.value
            setter = self._trail_properties[trail_type]['setter']
            
            # Find positions with non-zero colors
            non_zero_mask = np.any(faded_colors[trail_idx] != 0, axis=1)
            non_zero_positions = np.where(non_zero_mask)[0]
            
            # Update only non-zero pixels
            for pos in non_zero_positions:
                color = Color(*faded_colors[trail_idx, pos])
                setter(pos, color)
        
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

    def update(self) -> None:
        """Update the display and fade out pixels if their duration has expired."""
        now = pygame.time.get_ticks() / 1000.0
        faded_colors = self._calculate_faded_colors(now)
        self._update_display(faded_colors)
    
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
