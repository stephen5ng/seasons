"""Display manager for the rhythm game."""
import pygame
import math
import numpy as np
from enum import Enum, auto
from typing import Tuple, Protocol, Optional, Dict, List
from pygame import Color
from game_constants import *
import game_constants
from sacn_display import SacnDisplay

import logging

# For Raspberry Pi mode
try:
    from rpi_ws281x import PixelStrip, Color as LEDColor
    IS_RASPBERRY_PI = True
except ImportError:
    IS_RASPBERRY_PI = False
    PixelStrip = None
    LEDColor = None

# For sACN mode
try:
    import sacn
except ImportError:
    sacn = None

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TrailType(Enum):
    """Types of trails that can be drawn."""
    TARGET = 0
    HIT = 1
    FIFTH_LINE = 2

class Display(Protocol):
    """Protocol for display implementations."""
    def set_pixel(self, pos: int, color: Color, trail_start_offset: int, pygame_radius: int) -> None: ...
    def set_fifth_line_pixel(self, pos: int, color: Color) -> None: ...
    def draw_score_lines(self, score: float) -> None: ...
    def clear(self) -> None: ...
    def show(self) -> None: ...

class RaspberryPiDisplay:
    """Raspberry Pi LED strip display implementation."""
    def __init__(self, led_count: int, led_pin: int, led_freq_hz: int, led_dma: int, 
                 led_invert: bool, led_brightness: int, led_channel: int) -> None:
        self.led_count = led_count
        self.strip = PixelStrip(
            led_count*2 if USE_SEPARATE_FIFTH_LINE_STRIP else led_count*3,
            led_pin, led_freq_hz, led_dma, led_invert, led_brightness, 0
        )
        if USE_SEPARATE_FIFTH_LINE_STRIP:
            self.fifth_line_strip = PixelStrip(
                led_count, 13, led_freq_hz, 5, led_invert, led_brightness, 1
            )
        self.strip.begin()
        if USE_SEPARATE_FIFTH_LINE_STRIP:
            self.fifth_line_strip.begin()

    def _convert_to_led_color(self, color: Color) -> LEDColor:
        """Convert Pygame color to WS281x color.
        
        Args:
            color: Pygame Color object
            
        Returns:
            WS281x Color object
        """
        return LEDColor(color.r, color.g, color.b)

    def set_pixel(self, pos: int, color: Color, trail_start_offset: int, _: int) -> None:
        """Set a pixel on the LED strip.
        
        Args:
            pos: The logical position of the LED
            color: The color to set
            trail_start_offset: Offset for LED position calculation
            _: Unused parameter (pygame_radius)
        """
        actual_led_pos = int((pos + DISPLAY_LED_OFFSET) % self.led_count + trail_start_offset)
        self.strip.setPixelColor(actual_led_pos, self._convert_to_led_color(color))

    def set_fifth_line_pixel(self, pos: int, color: Color, trail_start_offset: int) -> None:
        """Set a pixel on the fifth line strip."""
        if USE_SEPARATE_FIFTH_LINE_STRIP:
            self.fifth_line_strip.setPixelColor(pos, self._convert_to_led_color(color))
        else:
            self.set_pixel(pos, color, trail_start_offset)

    def draw_score_lines(self, score: float) -> None:
        """Draw score lines on the display."""
        # No-op for Raspberry Pi as it doesn't have a display for score lines
        pass

    def clear(self) -> None:
        """Clear all pixels using slice assignment."""
        self.strip[:] = 0
        if USE_SEPARATE_FIFTH_LINE_STRIP:
            self.fifth_line_strip[:] = 0

    def show(self) -> None:
        """Update the display."""
        self.strip.show()
        if USE_SEPARATE_FIFTH_LINE_STRIP:
            self.fifth_line_strip.show()

class PygameDisplay:
    """Pygame display implementation."""
    def __init__(self, screen_width: int, screen_height: int, scaling_factor: int, led_count: int) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.scaling_factor = scaling_factor
        self.led_count = led_count
        self.display_surface = pygame.display.set_mode(
            (screen_width * scaling_factor, screen_height * scaling_factor)
        )
        self.pygame_surface = pygame.Surface((screen_width, screen_height))

    def set_pixel(self, pos: int, color: Color, _: int, pygame_radius: int) -> None:
        """Set a pixel on the pygame surface.
        
        Args:
            pos: The logical position of the LED
            color: The color to set
            _: Unused parameter (trail_start_offset)
            pygame_radius: Radius to use for pygame display
        """
        x, y = self._get_ring_position(pos, self.screen_width // 2, self.screen_height // 2, 
                                     pygame_radius, self.led_count)
        self.pygame_surface.set_at((x, y), color)

    def set_fifth_line_pixel(self, pos: int, color: Color, trail_start_offset: int) -> None:
        """Set a pixel on the fifth line."""
        position_x = int((pos / (self.led_count - 1)) * (self.screen_width // 2))
        pygame.draw.circle(self.pygame_surface, color, (position_x, 96), 1, 1)

    def draw_score_lines(self, score: float) -> None:
        """Draw horizontal lines representing the score with top-to-bottom animation."""
        num_lines: int = int(score * 2)
        for i in range(num_lines):
            y: int = max(0, self.screen_height - 1 - ((num_lines - 1 - i) * (SCORE_LINE_HEIGHT + SCORE_LINE_SPACING)))
            pygame.draw.line(self.pygame_surface, SCORE_LINE_COLOR, (0, y), (10, y))

    def clear(self) -> None:
        """Clear the display."""
        self.pygame_surface.fill((0, 0, 0))

    def show(self) -> None:
        """Update the display."""
        pygame.transform.scale(
            self.pygame_surface, 
            (self.screen_width * self.scaling_factor, self.screen_height * self.scaling_factor), 
            self.display_surface
        )
        pygame.display.update()

    @staticmethod
    def _get_ring_position(i: int, center_x: int, center_y: int, 
                          radius: int, led_count: int) -> Tuple[int, int]:
        """Convert LED index to x,y coordinates in a circular pattern."""
        angle = 2 * math.pi * i / led_count
        x = int(radius * math.sin(angle))
        y = int(-radius * math.cos(angle))
        return (center_x + x, center_y + y)

class PygameAndSacnDisplay:
    """Display implementation that combines both Pygame and sACN displays.
    
    This class delegates all display operations to both a Pygame display and an sACN display,
    allowing for simultaneous visualization on screen and LED strips.
    """
    
    def __init__(self, screen_width: int, screen_height: int, scaling_factor: int, led_count: int) -> None:
        """Initialize the combined display.
        
        Args:
            screen_width: Width of pygame display
            screen_height: Height of pygame display
            scaling_factor: Scaling factor for pygame display
            led_count: Number of LEDs in strip
        """
        self.pygame_display = PygameDisplay(screen_width, screen_height, scaling_factor, led_count)
        self.sacn_display = SacnDisplay(led_count * 3)  # Target, hit, fifth line
        
    def set_pixel(self, pos: int, color: Color, trail_start_offset: int, pygame_radius: int) -> None:
        """Set a pixel on both displays.
        
        Args:
            pos: Position of the pixel
            color: Color to set
            trail_start_offset: Offset for the trail
            pygame_radius: Radius to use for pygame display
        """
        self.pygame_display.set_pixel(pos, color, trail_start_offset, pygame_radius)
        self.sacn_display.set_pixel(pos, color, trail_start_offset, pygame_radius)
        
    def set_fifth_line_pixel(self, pos: int, color: Color, trail_start_offset: int) -> None:
        """Set a pixel on the fifth line for both displays.
        
        Args:
            pos: Position of the pixel
            color: Color to set
            trail_start_offset: Offset for the trail
        """
        self.pygame_display.set_fifth_line_pixel(pos, color, trail_start_offset)
        self.sacn_display.set_fifth_line_pixel(pos, color, trail_start_offset)
        
    def draw_score_lines(self, score: float) -> None:
        """Draw score lines on the pygame display.
        
        Args:
            score: Score value to display
        """
        self.pygame_display.draw_score_lines(score)
        # sACN display doesn't support score lines
        
    def clear(self) -> None:
        """Clear both displays."""
        self.pygame_display.clear()
        self.sacn_display.clear()
        
    def show(self) -> None:
        """Update both displays."""
        self.pygame_display.show()
        self.sacn_display.show()

    def cleanup(self) -> None:
        """Clean up display resources."""
        self.sacn_display.cleanup()

class DisplayManager:
    """Handles LED display output for Pygame, WS281x, and sACN."""
    
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
                 led_channel: int,
                 use_sacn: bool = False) -> None:
        """Initialize the display manager.
        
        Args:
            screen_width: Width of pygame display
            screen_height: Height of pygame display
            scaling_factor: Scaling factor for pygame display
            led_count: Number of LEDs in strip
            led_pin: GPIO pin for WS281x
            led_freq_hz: WS281x frequency
            led_dma: WS281x DMA channel
            led_invert: WS281x invert signal
            led_brightness: WS281x brightness
            led_channel: WS281x PWM channel
            use_sacn: Whether to use sACN for LED control
        """
        self.led_count = led_count
        
        if IS_RASPBERRY_PI:
            if use_sacn:
                self.display = SacnDisplay(led_count*3) # Target, hit, fifth line
            else:
                self.display = RaspberryPiDisplay(
                    led_count, led_pin, led_freq_hz, led_dma, led_invert, led_brightness, led_channel
                )
        else:
            if use_sacn:
                self.display: Display = PygameAndSacnDisplay(screen_width, screen_height, scaling_factor, led_count)
            else:
                self.display = PygameDisplay(screen_width, screen_height, scaling_factor, led_count)

        self._trail_properties: Dict[TrailType, Dict[str, Any]] = {
            TrailType.TARGET: {
                'setter': lambda pos, color: self._set_pixel_on_trail(
                    pos, color,
                    0,
                    game_constants.TARGET_TRAIL_RADIUS
                )
            },
            TrailType.HIT: {
                'setter': lambda pos, color: self._set_pixel_on_trail(
                    pos, color,
                    self.led_count,
                    game_constants.HIT_TRAIL_RADIUS
                )
            },
            TrailType.FIFTH_LINE: {
                'setter': lambda pos, color: self._set_pixel_on_fifth_line(
                    pos, 
                    color, 
                    0 if USE_SEPARATE_FIFTH_LINE_STRIP else self.led_count * 2
                )
            }
        }
        
        # Numpy arrays to track active pixels in parallel
        # Shape: (num_trails, 2, led_count, 3) for colors, (num_trails, 2, led_count, 2) for timing
        # First dimension: trail_type (0 for target, 1 for hit, 2 for fifth)
        # Second dimension: layer
        # Third dimension: pos (0 to led_count-1)
        # Fourth dimension: [r,g,b] for colors, [set_time, duration] for timing
        num_trails = len(TrailType)
        self._active_colors_np = np.zeros((num_trails, 2, led_count, 3), dtype=np.uint8)
        self._active_times_np = np.full((num_trails, 2, led_count, 2), [-1.0, -1.0], dtype=np.float32)

    def clear(self) -> None:
        """Clear the display by delegating to the display implementation."""
        self.display.clear()

    def _set_pixel_on_trail(self, pos: int, color: Color, trail_start_offset: int, pygame_radius: int) -> None:
        """Activate a pixel on the display at a specific position."""
        self.display.set_pixel(pos, color, trail_start_offset, pygame_radius)

    def _set_pixel_on_fifth_line(self, pos: int, color: Color, trail_start_offset: int) -> None:
        """Set a pixel on the fifth line strip."""
        self.display.set_fifth_line_pixel(pos, color, trail_start_offset)

    def update(self) -> None:
        """Update the display and fade out pixels if their duration has expired."""
        now = pygame.time.get_ticks() / 1000.0
        faded_colors = self._calculate_faded_colors(now)
        self._update_display(faded_colors)
        self.display.show()

    def _calculate_faded_colors(self, now: float) -> np.ndarray:
        """Calculate faded colors for all pixels based on their durations and elapsed time.
        
        Args:
            now: Current time in seconds
            
        Returns:
            Array of faded colors with shape (num_trails, led_count, 3) after averaging layers
        """
        # Get set_times and durations for all pixels
        set_times = self._active_times_np[:, :, :, 0]  # Shape: (num_trails, 2, led_count)
        durations = self._active_times_np[:, :, :, 1]  # Shape: (num_trails, 2, led_count)
        elapsed = now - set_times  # Shape: (num_trails, 2, led_count)
        
        # Create masks for different pixel states
        # Shape: (num_trails, 2, led_count, 1) for broadcasting with colors
        is_fading = (durations > 0)[..., None]  # Pixels that should fade
        is_expired = (is_fading & (elapsed >= durations)[..., None])  # Fading pixels that have expired
        is_permanent = (durations == -1)[..., None]  # Permanent pixels
        
        # Calculate fade ratios for fading pixels (1.0 to 0.0)
        # Shape: (num_trails, 2, led_count, 1)
        # Handle edge cases:
        # 1. Avoid division by zero by masking where durations > 0
        # 2. Ensure elapsed times are non-negative
        # 3. Prevent overflow by clipping large values
        safe_durations = np.where(durations > 0, durations, 1.0)  # Replace 0/negative with 1.0 to avoid div by zero
        safe_elapsed = np.maximum(elapsed, 0)  # Ensure non-negative
        fade_ratios = np.where(
            is_fading,
            1.0 - np.clip(safe_elapsed / safe_durations, 0, 1)[..., None],
            1.0
        )
        
        # Calculate colors for each layer:
        # - Expired pixels become black (0)
        # - Fading pixels are multiplied by fade ratio
        # - Permanent pixels keep original color
        layer_colors = np.where(
            is_expired,
            0,  # Expired pixels become black
            np.where(
                is_permanent,
                self._active_colors_np,  # Permanent pixels keep original color
                (self._active_colors_np * fade_ratios).astype(np.uint8)  # Fading pixels
            )
        )  # Shape: (num_trails, 2, led_count, 3)
        
        # Average the two layers using integer arithmetic
        # Add layers and right shift by 1 (divide by 2)
        averaged = ((layer_colors[:, 0].astype(np.uint16) + layer_colors[:, 1].astype(np.uint16)) >> 1).astype(np.uint8)
        
        return averaged  # Shape: (num_trails, led_count, 3)

    def _update_display(self, faded_colors: np.ndarray) -> None:
        """Update the display with faded colors.
        
        Args:
            faded_colors: Array of faded colors with shape (num_trails, led_count, 3) after averaging
        """
        # logger.debug("Updating display with faded colors")
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
                # logger.debug(f"Set pixel {pos} to RGB({color.r}, {color.g}, {color.b})")
        
        # Note: show() is called by update() after this method returns

    def draw_score_lines(self, score: float) -> None:
        """Draw horizontal lines representing the score with top-to-bottom animation."""
        self.display.draw_score_lines(score)

    def _request_pixel_on_trail(self, pos: int, color: Color, trail_type: TrailType, duration: float, layer: int) -> None:
        """Request a pixel to be displayed on a trail with fade management.
        
        Args:
            pos: The logical position of the LED.
            color: The Pygame Color for the LED.
            trail_type: The type of trail (TARGET, HIT, or FIFTH_LINE).
            duration: Duration (in seconds) for the pixel to remain on. If -1, the pixel remains until overridden.
                    Must be either -1 (permanent) or > 0 (fading).
            layer: The layer to set the pixel on.
        """
        if duration != -1 and duration <= 0:
            raise ValueError("Duration must be either -1 (permanent) or > 0 (fading)")
            
        now = pygame.time.get_ticks() / 1000.0
        
        # Handle positions that wrap around the LED strip
        pos = pos % self.led_count
            
        # Update numpy arrays using enum value directly as index
        trail_idx = trail_type.value
        self._active_colors_np[trail_idx, layer, pos] = [color.r, color.g, color.b]
        self._active_times_np[trail_idx, layer, pos] = [now, duration]

    def set_target_trail_pixel(self, pos: int, color: Color, duration: float, layer: int) -> None:
        """Set pixel color at position in target ring with an optional duration.
        
        Args:
            pos: The logical position of the LED.
            color: The Pygame Color for the LED.
            duration: Duration (in seconds) for the pixel to remain on. If -1, the pixel remains until overridden.
            layer: The layer to set the pixel on.
        """
        self._request_pixel_on_trail(pos, color, TrailType.TARGET, duration, layer)
    
    def set_hit_trail_pixel(self, pos: int, color: Color, duration: float) -> None:
        """Set pixel color at position in hit trail ring with specified duration.
        
        Args:
            pos: The logical position of the LED.
            color: The Pygame Color for the LED.
            duration: Duration (in seconds) for the pixel to remain on. If -1, the pixel remains until overridden.
        """
        self._request_pixel_on_trail(pos, color, TrailType.HIT, duration, 0)

    def set_fifth_line_pixel(self, pos: int, color: Color, duration: float, layer: int) -> None:
        """Set pixel color for the fifth line LED chain with optional duration.
        
        Args:
            pos: Position in the fifth line chain (0 to led_count-1)
            color: The Pygame Color for the LED
            duration: Duration (in seconds) for the pixel to remain on. If -1, the pixel remains until overridden.
            layer: The layer to set the pixel on.
        """
        if pos < 0 or pos >= self.led_count:
            raise ValueError(f"Position must be between 0 and {self.led_count-1}")
        self._request_pixel_on_trail(pos, color, TrailType.FIFTH_LINE, duration, layer)

    def cleanup(self) -> None:
        """Clean up display resources."""
        if hasattr(self.display, 'cleanup'):
            self.display.cleanup()
