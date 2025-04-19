#!/usr/bin/env python3

import asyncio
import math
import os
import platform
import sys
import argparse
from typing import List, Optional, Tuple, Union, Dict, Callable
from enum import Enum, auto

import aiomqtt
import aiohttp
import easing_functions
import pygame
from pygame import Color, K_r, K_b
from pygameasync import Clock

from get_key import get_key
import my_inputs
from button_handler import ButtonPressHandler
from trail_renderer import TrailRenderer
from score_effects import ScoreEffects
from led_position import LEDPosition

# Constants
SPB = 1.84615385  # Seconds per beat
WLED_IP = "192.168.0.121"
WLED_SETTINGS = {
    0: "FX=2&FP=67&SX=32",  # BREATHE / BLINK RED 
    4: "FX=54&FP=57&SX=48",  # CHASE 3 / CANDY
    8: "FX=19&FP=10&SX=255",  # DISSOLVE RND / FOREST
    12: "FX=66&FP=41&SX=128",  # FIRE 2012 / MAGRED
    16: "FX=9&FP=20&SX=128",  # RAINBOW / PASTEL
    20: "FX=92&FP=45&SX=192",  # SINELON / CLOUD
    24: "FX=13&FP=27&SX=96",  # SUNSET / SHERBET
    32: "FX=3&FP=43&SX=128",  # WIPE / YELBLU
    35: "FX=34&FP=19&SX=32",  # COLORFUL / TEMPERATURE
    38: "FX=108&FP=9&SX=128",  # SINE / OCEAN
    45: "FX=173&FP=34&SX=128",  # TARTAN / TERTIARY
    48: "FX=34&FP=19&SX=32",  # BREATHE / SPLASH
}

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='LED rhythm game')
    parser.add_argument('--leds', type=int, default=80,
                      help='Number of LEDs in the strip (default: 80)')
    return parser.parse_args()

args = parse_args()

# Update shared constants in game_constants for runtime values
import game_constants

game_constants.NUMBER_OF_LEDS = args.leds
# Update dependent constants
# (If you want to update more, add them here)
game_constants.TARGET_WINDOW_SIZE = game_constants.NUMBER_OF_LEDS // 20
game_constants.MID_TARGET_POS = game_constants.NUMBER_OF_LEDS / 2
game_constants.RIGHT_TARGET_POS = game_constants.NUMBER_OF_LEDS / 4
game_constants.LEFT_TARGET_POS = 3 * game_constants.NUMBER_OF_LEDS / 4
NUMBER_OF_LEDS = game_constants.NUMBER_OF_LEDS
TARGET_WINDOW_SIZE = game_constants.TARGET_WINDOW_SIZE
MID_TARGET_POS = game_constants.MID_TARGET_POS
RIGHT_TARGET_POS = game_constants.RIGHT_TARGET_POS
LEFT_TARGET_POS = game_constants.LEFT_TARGET_POS

# Check if we're on Raspberry Pi
IS_RASPBERRY_PI = platform.system() == "Linux" and os.uname().machine.startswith("aarch64")

if IS_RASPBERRY_PI:
    from rpi_ws281x import PixelStrip, Color as LEDColor
    # LED strip configuration:
    LED_COUNT = NUMBER_OF_LEDS  # Number of LED pixels
    LED_PIN = 18  # GPIO pin connected to the pixels (must support PWM)
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 10  # DMA channel to use for generating signal
    LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
    LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
    LED_CHANNEL = 0  # PWM channel

# no music at the start?

# Display constants
SCALING_FACTOR = 9
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 96
CIRCLE_RADIUS = 30
CIRCLE_CENTER_X = SCREEN_WIDTH // 2
CIRCLE_CENTER_Y = SCREEN_HEIGHT // 2

# Game timing constants
BEATS_PER_MEASURE = 8
BEAT_PER_MS = 13.0 / 6000.0
SECONDS_PER_MEASURE_S = 3.7

# Debug settings
from game_constants import *

# Global state
quit_app = False


class GameState:
    """Manages game state and timing."""
    
    def __init__(self) -> None:
        self.start_ticks_ms: int = pygame.time.get_ticks()
        self.last_beat_in_measure: int = 0
        self.score: float = 0
        self.previous_score: float = 0  # Track previous score to detect changes
        self.score_flash_start_beat: Optional[float] = None  # When the score last changed (in beats)
        self.last_hit_target: str = "none"  # Track which target was hit: "red", "blue", or "none"
        self.next_loop: int = 1
        self.loop_count: int = 0
        self.error_sound: pygame.mixer.Sound = pygame.mixer.Sound(ERROR_SOUND)
        self.button_handler = ButtonPressHandler(self.error_sound)
        self.trail_length: int = 0 
        self.beat_start_time_ms: int = 0
        self.last_music_start_time_s: float = 0.0  # Track when we last started playing music
        self.last_music_start_pos_s: float = 0.0   # Track from what position we started playing
        self.total_beats: int = 0  # Track total beats in song
        self.last_beat: int = -1  # Track last beat for increment
        self.last_wled_measure: int = -1
        self.last_wled_score: int = -1
        self.http_session: aiohttp.ClientSession = aiohttp.ClientSession()  # Create a single session for all HTTP requests
        self.current_http_task: Optional[asyncio.Task] = None
        self.current_led_position: Optional[int] = None  # Track current LED position
        
        # Trail state
        self.lit_positions: Dict[int, float] = {}  # Maps LED position to timestamp when it was lit
        self.lit_colors: Dict[int, Color] = {}    # Maps LED position to base color when it was lit
        
        # Hit trail state
        self.hit_colors: List[Color] = []  # List of colors for successful hits
        self.hit_spacing: int = INITIAL_HIT_SPACING  # Current spacing between hit trail LEDs
        self.in_scoring_window: bool = False  # Whether currently in a scoring window
        self.hit_trail_cleared: bool = False  # Track if hit trail has been cleared at least once
        
        # Bonus trail state
        self.bonus_trail_positions: Dict[int, float] = {}  # Maps LED position to timestamp when it was lit

        # Trail renderer (extracts trail/color logic)
        self.trail_renderer = TrailRenderer(get_rainbow_color_func=get_rainbow_color)


    async def _send_wled_command_inner(self, url: str) -> None:
        """Internal method to send WLED command."""
        try:
            async with self.http_session.get(url, timeout=1.0) as response:
                if response.status != 200:
                    print(f"Error: HTTP {response.status} for {url}")
                await response.text()
        except asyncio.TimeoutError:
            print(f"Error: Timeout connecting to WLED at {url}")
        except aiohttp.ClientError as e:
            print(f"Error: Failed to connect to WLED: {e}")
        except Exception as e:
            print(f"Error: Unexpected error connecting to WLED: {e}")

    async def send_wled_command(self, wled_command: str) -> None:
        """Send a command to the WLED device, canceling any outstanding request."""
        url: str = f"http://{WLED_IP}/win&{wled_command}&S2={2+int(self.score*6)}"
        
        # Don't send multiple requests at once.
        if self.current_http_task and not self.current_http_task.done():
            return
       
        # Start new request
        self.current_http_task = asyncio.create_task(self._send_wled_command_inner(url))

    async def update_timing(self) -> Tuple[int, int, float, float]:
        """Calculate current timing values."""
        duration_ms: int = pygame.time.get_ticks() - self.start_ticks_ms
        beat_float: float = duration_ms * BEAT_PER_MS
        beat: int = int(beat_float)
        beat_in_measure: int = beat % BEATS_PER_MEASURE
        fractional_beat: float = beat_float % 1
        
        # Update total beats when we cross a beat boundary
        if beat > self.last_beat:
            self.total_beats += 1
            self.last_beat = beat
            print(f"Total beats in song: {self.total_beats}")
            
            # Check WLED_SETTINGS for current beat
            wled_measure: int = self.total_beats//BEATS_PER_MEASURE
            if self.score != self.last_wled_score or self.last_wled_measure != wled_measure:
                if self.last_wled_measure != wled_measure:
                    print(f"NEW MEASURE {wled_measure}")
                    if wled_measure in WLED_SETTINGS:
                        self.last_wled_measure = wled_measure
                wled_command: str = WLED_SETTINGS[self.last_wled_measure]
                await self.send_wled_command(wled_command)
                self.last_wled_score = self.score
                print(f"score {self.score}")
            
        if beat_in_measure == 0:
            self.beat_start_time_ms = pygame.time.get_ticks()
        
        return beat, beat_in_measure, beat_float, fractional_beat
    
    def handle_music_loop(self, beat_in_measure: int) -> None:
        """Handle music looping and position updates."""
        if beat_in_measure == self.last_beat_in_measure:
            return
        self.last_beat_in_measure = beat_in_measure
        
        if beat_in_measure != 0:
            return
        
        current_time_ms: int = pygame.time.get_ticks()
        measure_offset_s: float = (current_time_ms - self.beat_start_time_ms) / 1000.0
        target_time_s: float = int(self.score) * SECONDS_PER_MEASURE_S + measure_offset_s
        
        # Get current music position in seconds, accounting for start position
        current_music_pos_s: float = self.last_music_start_pos_s + (pygame.mixer.music.get_pos() / 1000.0)
        
        print(f"Current music position: {current_music_pos_s}, Score: {self.score}")
        print(f"Target time: {target_time_s}")

        if abs(current_music_pos_s - target_time_s) > 0.2:
            print(f"difference {abs(current_music_pos_s - target_time_s)}")
            print(f"Starting music at {target_time_s} seconds")
            self.last_music_start_pos_s = target_time_s
            # Update total beats based on new target time
            target_beats: int = int(target_time_s * (1000 * BEAT_PER_MS))
            self.total_beats = target_beats
            self.last_beat = target_beats - 1
            pygame.mixer.music.play(start=target_time_s)

    def update_score(self, new_score: float, target_type: str, beat_float: float) -> None:
        """Update score and trigger flash effect if score increased."""
        if new_score > self.score:
            self.score_flash_start_beat = beat_float
            self.last_hit_target = target_type
            
            # Check if adding a new hit would exceed circle size
            total_space_needed: int = (len(self.hit_colors) + 1) * self.hit_spacing
            if total_space_needed >= NUMBER_OF_LEDS:
                if self.hit_spacing <= 4:
                    # Clear hit trail if we've hit minimum spacing
                    self.hit_colors = []
                    self.hit_spacing = INITIAL_HIT_SPACING  # Reset to initial spacing
                    self.hit_trail_cleared = True  # Mark that hit trail has been cleared
                    print("*********** Hit trail cleared, resetting spacing")
                else:
                    self.hit_spacing = max(self.hit_spacing / 2, 1)
                    print(f"*********** Hit spacing: {self.hit_spacing}")
            
            # Add hit color to beginning of trail
            try:
                target_enum: TargetType = TargetType[target_type.upper()]
                self.hit_colors.insert(0, TARGET_COLORS[target_enum])
                print(f"Hit colors: {len(self.hit_colors)}")
            except KeyError:
                pass  # Ignore invalid target types
        
        # Always update trail length based on new score
        max_trail_length: int = int(new_score * 4)
        if len(self.hit_colors) > max_trail_length:
            self.hit_colors = self.hit_colors[:max_trail_length]
                
        self.previous_score = self.score
        self.score = new_score
    
    def get_score_flash_intensity(self, beat_float: float) -> float:
        """Calculate the intensity of the score flash effect based on musical beats."""
        return ScoreEffects.get_flash_intensity(beat_float, self.score_flash_start_beat)

    def calculate_led_position(self, beat_in_measure: int, fractional_beat: float) -> int:
        """Calculate the current LED position based on beat timing."""
        return LEDPosition.calculate_position(beat_in_measure, fractional_beat, BEATS_PER_MEASURE, NUMBER_OF_LEDS)
    
    def update_loop_count(self, percent_of_measure: float) -> None:
        """Update the loop count based on measure progress."""
        if percent_of_measure < 0.5:
            if self.loop_count != self.next_loop:
                self.loop_count = self.next_loop
        elif self.next_loop == self.loop_count:
            self.next_loop = self.loop_count + 1

    def reset_flags(self, led_position: int) -> None:
        """Reset state flags based on LED position."""
        was_in_window: bool = self.in_scoring_window
        self.in_scoring_window = self.button_handler.is_in_valid_window(led_position)
        
        # Reset button state when entering new window
        if not was_in_window and self.in_scoring_window:
            self.button_handler.button_states = {k: False for k in self.button_handler.button_states}
            self.button_handler.penalty_applied = False
            self.button_handler.round_active = True
        elif was_in_window and not self.in_scoring_window:
            self.button_handler.round_active = False

def get_target_ring_position(i: int, radius: int) -> Tuple[int, int]:
    """Convert LED index to x,y coordinates in a circular pattern at given radius, starting at 12 o'clock."""
    x, y = LEDPosition.get_ring_position(i, radius, NUMBER_OF_LEDS)
    return (CIRCLE_CENTER_X + x, CIRCLE_CENTER_Y + y)

def get_hit_trail_position(i: int) -> Tuple[int, int]:
    """Convert LED index to x,y coordinates in the hit trail ring, starting at 12 o'clock."""
    return get_target_ring_position(i, HIT_TRAIL_RADIUS)

def get_bonus_trail_position(i: int) -> Tuple[int, int]:
    """Convert LED index to x,y coordinates in the bonus trail ring, starting at 12 o'clock."""
    return get_target_ring_position(i, BONUS_TRAIL_RADIUS)

def get_rainbow_color(time_ms: int, line_index: int) -> Color:
    """Generate a rainbow color based on time and line position."""
    hue: float = (time_ms / COLOR_CYCLE_TIME_MS + line_index * 0.1) % 1.0
    
    if hue < 1/6:  # Red to Yellow
        return Color(255, int(255 * (hue * 6)), 0)
    elif hue < 2/6:  # Yellow to Green
        return Color(int(255 * (2 - hue * 6)), 255, 0)
    elif hue < 3/6:  # Green to Cyan
        return Color(0, 255, int(255 * (hue * 6 - 2)))
    elif hue < 4/6:  # Cyan to Blue
        return Color(0, int(255 * (4 - hue * 6)), 255)
    elif hue < 5/6:  # Blue to Magenta
        return Color(int(255 * (hue * 6 - 4)), 0, 255)
    else:  # Magenta to Red
        return Color(255, 0, int(255 * (6 - hue * 6)))

def get_score_line_color(base_color: Color, flash_intensity: float, flash_type: str) -> Color:
    """Create a flash effect for score lines based on which target was hit."""
    if flash_type == "blue":
        return Color(
            int(base_color[0] * (1 - flash_intensity)),
            int(base_color[1] * (1 - flash_intensity)),
            min(255, int(255 * flash_intensity + base_color[2] * (1 - flash_intensity))),
            base_color[3]
        )
    else:  # Default to red flash
        return Color(
            min(255, int(255 * flash_intensity + base_color[0] * (1 - flash_intensity))),
            int(base_color[1] * (1 - flash_intensity)),
            int(base_color[2] * (1 - flash_intensity)),
            base_color[3]
        )

def draw_score_lines(screen: pygame.Surface, score: float, current_time: int, flash_intensity: float, flash_type: str) -> None:
    """Draw horizontal lines representing the score with top-to-bottom animation."""
    num_lines: int = int(score*2)
    current_line: int = num_lines  # Default to all lines unlit
    
    if flash_intensity > 0:
        # Calculate which line should be lit based on time since flash started
        time_since_flash: float = SCORE_FLASH_DURATION_MS * (1 - flash_intensity)
        current_line = int(time_since_flash / SCORE_LINE_ANIMATION_TIME_MS)
        # Ensure we start from the top (line 0) and move downward
        current_line = min(current_line, num_lines - 1)
    
    for i in range(num_lines):
        y: int = SCREEN_HEIGHT - 1 - ((num_lines - 1 - i) * (SCORE_LINE_HEIGHT + SCORE_LINE_SPACING))
        if y >= 0:  # Only draw if we haven't gone off the top of the screen
            # Only use rainbow effect when not flashing
            base_color: Color
            line_color: Color
            if flash_intensity > 0 and i <= current_line:
                # During flash animation, use base green color for flash effect
                base_color = SCORE_LINE_COLOR
                line_color = get_score_line_color(base_color, flash_intensity, flash_type)
            elif flash_intensity == 0:
                # When not flashing, use rainbow effect for high scores
                base_color = get_rainbow_color(current_time, i) if score > HIGH_SCORE_THRESHOLD else SCORE_LINE_COLOR
                line_color = base_color
                
            pygame.draw.line(screen, line_color, (0, y), (10, y))

class LEDDisplay:
    """Handles LED display output for both Pygame and WS281x."""
    
    def __init__(self) -> None:
        if IS_RASPBERRY_PI:
            self.strip: PixelStrip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
            self.strip.begin()
            self.pygame_surface: Optional[pygame.Surface] = None
            self.display_surface: Optional[pygame.Surface] = None
        else:
            self.strip: Optional[PixelStrip] = None
            self.display_surface: pygame.Surface = pygame.display.set_mode((SCREEN_WIDTH * SCALING_FACTOR, SCREEN_HEIGHT * SCALING_FACTOR))
            self.pygame_surface: pygame.Surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    
    def clear(self) -> None:
        """Clear the display."""
        if IS_RASPBERRY_PI:
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, 0)
        else:
            self.pygame_surface.fill((0, 0, 0))
    
    def set_pixel(self, pos: int, color: Color) -> None:
        """Set pixel color at position in target ring."""
        if IS_RASPBERRY_PI:
            # Convert Pygame color to WS281x color (RGB order)
            ws_color: LEDColor = LEDColor(color.r, color.g, color.b)
            self.strip.setPixelColor(pos, ws_color)
        else:
            x: int
            y: int
            x, y = get_target_ring_position(pos, TARGET_TRAIL_RADIUS)
            self.pygame_surface.set_at((x, y), color)
    
    def set_hit_trail_pixel(self, pos: int, color: Color) -> None:
        """Set pixel color at position in hit trail ring."""
        if not IS_RASPBERRY_PI:
            x: int
            y: int
            x, y = get_hit_trail_position(pos)
            self.pygame_surface.set_at((x, y), color)
    
    def set_bonus_trail_pixel(self, pos: int, color: Color) -> None:
        """Set pixel color at position in bonus trail ring."""
        if not IS_RASPBERRY_PI:
            x: int
            y: int
            x, y = get_bonus_trail_position(pos)
            self.pygame_surface.set_at((x, y), color)
    
    def update(self) -> None:
        """Update the display."""
        if IS_RASPBERRY_PI:
            self.strip.show()
        else:
            pygame.transform.scale(self.pygame_surface, 
                (SCREEN_WIDTH * SCALING_FACTOR, SCREEN_HEIGHT * SCALING_FACTOR), 
                self.display_surface)
            pygame.display.update()

async def run_game() -> None:
    """Main game loop handling display, input, and game logic."""
    global quit_app

    # Initialize display
    clock: Clock = Clock()
    display: LEDDisplay = LEDDisplay()
    
    # Initialize game state
    game_state: GameState = GameState()
    
    try:
        # Initialize music
        pygame.mixer.music.load("music/Rise Up 3.mp3")
        pygame.mixer.music.play(start=0)

        while True:
            display.clear()

            # Update timing and music
            beat: int
            beat_in_measure: int
            beat_float: float
            fractional_beat: float
            beat, beat_in_measure, beat_float, fractional_beat = await game_state.update_timing()
            game_state.handle_music_loop(beat_in_measure)

            current_time_ms: int = pygame.time.get_ticks()
            current_time_s: float = current_time_ms / 1000.0
            
            # Calculate LED position and update loop count
            led_position: int = game_state.calculate_led_position(beat_in_measure, fractional_beat)
            game_state.update_loop_count(led_position / NUMBER_OF_LEDS)

            # Handle scoring and penalties
            if not game_state.button_handler.is_in_valid_window(led_position):
                new_score: float = game_state.button_handler.apply_penalty(game_state.score)
                if new_score != game_state.score:
                    print(f"New score: {new_score}, target hit: none")
                    game_state.update_score(new_score, "none", beat_float)
            game_state.reset_flags(led_position)
            
            # Check for scoring (both manual and auto)
            new_score: float
            target_hit: str
            error_feedback: Optional[Tuple[int, Color]]
            new_score, target_hit, error_feedback = game_state.button_handler.handle_keypress(
                led_position, game_state.score, current_time_ms)
            if new_score != game_state.score:
                print(f"New score: {new_score}, target hit: {target_hit}")
                game_state.update_score(new_score, target_hit, beat_float)
            
            # Update trail state when LED position changes
            if led_position != game_state.current_led_position:
                game_state.current_led_position = led_position
                # Store the timestamp and base white color for the new position
                game_state.lit_positions[led_position] = current_time_s
                game_state.lit_colors[led_position] = Color(255, 255, 255)  # White
                # Store bonus trail position
                game_state.bonus_trail_positions[led_position] = current_time_s
            
            # Draw target trail
            positions_to_remove: List[int] = game_state.trail_renderer.draw_trail_with_easing(
                game_state.lit_positions,
                TRAIL_FADE_DURATION_S,
                TRAIL_EASE,
                lambda brightness, pos: game_state.trail_renderer.get_target_trail_color(
                    pos, brightness, game_state.lit_colors, game_state.button_handler),
                display.set_pixel
            )
            
            # Clean up old trail positions
            for pos in positions_to_remove:
                del game_state.lit_positions[pos]
                del game_state.lit_colors[pos]
            
            # Draw bonus trail if hit trail has been cleared
            if game_state.hit_trail_cleared:
                bonus_positions_to_remove: List[int] = game_state.trail_renderer.draw_trail_with_easing(
                    game_state.bonus_trail_positions,
                    BONUS_TRAIL_FADE_DURATION_S,
                    BONUS_TRAIL_EASE,
                    lambda brightness, pos: game_state.trail_renderer.get_bonus_trail_color(brightness),
                    lambda p, c: display.set_bonus_trail_pixel((NUMBER_OF_LEDS - p) % NUMBER_OF_LEDS, c)
                )
                
                # Clean up old bonus trail positions
                for pos in bonus_positions_to_remove:
                    del game_state.bonus_trail_positions[pos]
            
            # Draw hit trail in outer circle
            for i, color in enumerate(game_state.hit_colors):
                trail_pos: int = int((led_position - (i + 1) * game_state.hit_spacing) % NUMBER_OF_LEDS)
                display.set_hit_trail_pixel(trail_pos, color)
            
            # Draw score lines with flash effect (only in Pygame mode)
            if not IS_RASPBERRY_PI:
                flash_intensity: float = game_state.get_score_flash_intensity(beat_float)
                draw_score_lines(display.pygame_surface, game_state.score, current_time_ms, flash_intensity, game_state.last_hit_target)
            
            # Draw current LED in white
            base_color: Color = Color(255, 255, 255)
            # Apply target colors if in scoring window
            if game_state.button_handler.is_in_valid_window(led_position):
                target_type: Optional[TargetType] = game_state.button_handler.get_target_type(led_position)
                if target_type:
                    base_color = TARGET_COLORS[target_type]
            
            display.set_pixel(led_position, base_color)

            # Draw error feedback if wrong key was pressed
            if error_feedback is not None:
                error_pos: int
                error_color: Color
                error_pos, error_color = error_feedback
                display.set_pixel(error_pos, error_color)  # Use the color of the wrong key that was pressed

            # Handle input (only for quit)
            for key, keydown in get_key():
                if key == "quit":
                    return

            # Update display
            display.update()
            await clock.tick(30)
    finally:
        # Clean up the HTTP session
        await game_state.http_session.close()

async def main() -> None:
    """Initialize and run the game with MQTT support."""
    await run_game()
    pygame.quit()

if __name__ == "__main__":
    pygame.init()

    asyncio.run(main())
