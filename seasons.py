#!/usr/bin/env python

import asyncio
import math
import os
import platform
import sys
import argparse
from typing import List, Optional, Tuple, Union

import aiomqtt
import aiohttp
import easing_functions
import pygame
from pygame import Color, K_r, K_b
from pygameasync import Clock

from get_key import get_key
import my_inputs

# Constants
SPB = 3.69230769  # Seconds per beat
SPB = 1.84615385
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
NUMBER_OF_LEDS = args.leds

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
ALWAYS_SCORE = False  # When True, automatically scores on every round

# LED display constants
TARGET_WINDOW_SIZE = NUMBER_OF_LEDS // 20  # Window size proportional to number of LEDs
MID_TARGET_POS = NUMBER_OF_LEDS/2  # Position of the middle target
RIGHT_TARGET_POS = NUMBER_OF_LEDS/4  # Position of the 90 degree target
LEFT_TARGET_POS = 3*NUMBER_OF_LEDS/4  # Position of the 270 degree target
TRAIL_FADE_DURATION_S = 0.8  # Time for trail to fade out
TRAIL_EASE = easing_functions.CircularEaseOut(start=1.0, end=0.0, duration=TRAIL_FADE_DURATION_S)

# Score display constants
HIGH_SCORE_THRESHOLD = 5  # Score threshold for exciting effects
COLOR_CYCLE_TIME_MS = 2000  # Time in ms for one complete color cycle
SCORE_LINE_COLOR = Color("green")
SCORE_LINE_SPACING = 0.5  # Pixels between score lines
SCORE_LINE_HEIGHT = 0.5  # Height of each score line
SCORE_FLASH_DURATION_MS = 1000  # How long the score flash lasts
SCORE_LINE_ANIMATION_TIME_MS = 100  # ms per line animation (slowed down from 50ms)

# Create easing functions once
SCORE_FLASH_EASE = easing_functions.ExponentialEaseOut(start=0, end=1, duration=1)  # Smooth animation for score flashes

# Global state
quit_app = False

class ButtonPressHandler:
    """Handles button press logic and scoring."""
    
    def __init__(self) -> None:
        self.button_states = {
            "r": False,
            "b": False,
            "g": False,
            "y": False
        }
        self.penalty_applied: bool = False
        self.round_active: bool = False
    
    def is_in_valid_window(self, led_position: int) -> bool:
        """Check if the current LED position is in a valid window for scoring."""
        return_value = (led_position >= NUMBER_OF_LEDS - TARGET_WINDOW_SIZE or 
                led_position <= TARGET_WINDOW_SIZE or
                abs(led_position - MID_TARGET_POS) <= TARGET_WINDOW_SIZE or
                abs(led_position - RIGHT_TARGET_POS) <= TARGET_WINDOW_SIZE or
                abs(led_position - LEFT_TARGET_POS) <= TARGET_WINDOW_SIZE)
        return return_value
    
    def apply_penalty(self, score: float) -> float:
        """Apply penalty if button wasn't pressed in valid window."""
        if not any(self.button_states.values()) and not self.penalty_applied:
            # Calculate score after 25% reduction
            reduced_score = score * 0.75
            # Make sure it's at least 0.25 less than original score
            reduced_score = min(reduced_score, score - 0.25)
            # Round to nearest 0.25 and ensure score doesn't go below 0
            score = max(0, round(reduced_score * 4) / 4)
            self.penalty_applied = True
        return score
    
    def reset_flags(self, led_position: int) -> None:
        """Reset state flags based on LED position."""
        if self.is_in_valid_window(led_position) and not self.round_active:
            self.button_states = {k: False for k in self.button_states}
            self.penalty_applied = False
            self.round_active = True  # Start a new scoring round
        elif not self.is_in_valid_window(led_position):
            self.round_active = False  # End the current scoring round
    
    def _check_and_score(self, button_key: str, key: int, keys_pressed: List[bool], score: float, color: str) -> Optional[Tuple[float, str]]:
        """Helper method to check button press and update score if valid."""
        if (keys_pressed[key] or ALWAYS_SCORE) and not self.button_states[button_key]:
            self.button_states[button_key] = True
            self.penalty_applied = False
            return score + 0.25, color
        return None

    def handle_keypress(self, led_position: int, score: float, current_time: int) -> Tuple[float, str]:
        """Handle keypress and update score if in valid window with correct key."""
        if not self.is_in_valid_window(led_position):
            return score, "none"
            
        keys_pressed = pygame.key.get_pressed()
        
        # Check each target window and corresponding button
        if led_position <= 2 or led_position >= NUMBER_OF_LEDS - 2:  # Red target
            result = self._check_and_score("r", pygame.K_r, keys_pressed, score, "red")
            if result:
                return result
        elif abs(led_position - MID_TARGET_POS) <= 2:  # Blue target
            result = self._check_and_score("b", pygame.K_b, keys_pressed, score, "blue")
            if result:
                return result
        elif abs(led_position - RIGHT_TARGET_POS) <= 2:  # Green target
            result = self._check_and_score("g", pygame.K_g, keys_pressed, score, "green")
            if result:
                return result
        elif abs(led_position - LEFT_TARGET_POS) <= 2:  # Yellow target
            result = self._check_and_score("y", pygame.K_y, keys_pressed, score, "yellow")
            if result:
                return result
        
        return score, "none"

class GameState:
    """Manages game state and timing."""
    
    def __init__(self) -> None:
        self.start_ticks_ms = pygame.time.get_ticks()
        self.last_beat_in_measure = 0
        self.score = 0
        self.previous_score = 0  # Track previous score to detect changes
        self.score_flash_start_beat: Optional[float] = None  # When the score last changed (in beats)
        self.last_hit_target = "none"  # Track which target was hit: "red", "blue", or "none"
        self.next_loop = 1
        self.loop_count = 0
        self.button_handler = ButtonPressHandler()
        self.trail_length = 0 
        self.beat_start_time_ms = 0
        self.last_music_start_time_s = 0.0  # Track when we last started playing music
        self.last_music_start_pos_s = 0.0   # Track from what position we started playing
        self.total_beats = 0  # Track total beats in song
        self.last_beat = -1  # Track last beat for increment
        self.last_wled_measure = -1
        self.last_wled_score = -1
        self.http_session = aiohttp.ClientSession()  # Create a single session for all HTTP requests
        self.current_http_task: Optional[asyncio.Task] = None
        self.current_led_position = None  # Track current LED position
        
        # Trail state
        self.lit_positions = {}  # Maps LED position to timestamp when it was lit
        self.lit_colors = {}    # Maps LED position to base color when it was lit
        
        # Hit trail state
        self.hit_colors = []  # List of colors for successful hits
        self.hit_spacing = 8  # Current spacing between hit trail LEDs
        self.in_scoring_window = False  # Whether currently in a scoring window
    
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
        url = f"http://{WLED_IP}/win&{wled_command}&S2={2+int(self.score*6)}"
        
        # Don't send multiple requests at once.
        if self.current_http_task and not self.current_http_task.done():
            return
       
        # Start new request
        self.current_http_task = asyncio.create_task(self._send_wled_command_inner(url))

    async def update_timing(self) -> Tuple[int, int, float, float]:
        """Calculate current timing values."""
        duration_ms = pygame.time.get_ticks() - self.start_ticks_ms
        beat_float = duration_ms * BEAT_PER_MS
        beat = int(beat_float)
        beat_in_measure = beat % BEATS_PER_MEASURE
        fractional_beat = beat_float % 1
        
        # Update total beats when we cross a beat boundary
        if beat > self.last_beat:
            self.total_beats += 1
            self.last_beat = beat
            print(f"Total beats in song: {self.total_beats}")
            
            # Check WLED_SETTINGS for current beat
            wled_measure = self.total_beats//BEATS_PER_MEASURE
            if self.score != self.last_wled_score or self.last_wled_measure != wled_measure:
                if self.last_wled_measure != wled_measure:
                    print(f"NEW MEASURE {wled_measure}")
                    if wled_measure in WLED_SETTINGS:
                        self.last_wled_measure = wled_measure
                wled_command = WLED_SETTINGS[self.last_wled_measure]
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
        
        current_time_ms = pygame.time.get_ticks()
        measure_offset_s = (current_time_ms - self.beat_start_time_ms) / 1000.0
        target_time_s = int(self.score) * SECONDS_PER_MEASURE_S + measure_offset_s
        
        # Get current music position in seconds, accounting for start position
        current_music_pos_s = self.last_music_start_pos_s + (pygame.mixer.music.get_pos() / 1000.0)
        
        print(f"Current music position: {current_music_pos_s}, Score: {self.score}")
        print(f"Target time: {target_time_s}")

        if abs(current_music_pos_s - target_time_s) > 0.2:
            print(f"difference {abs(current_music_pos_s - target_time_s)}")
            print(f"Starting music at {target_time_s} seconds")
            self.last_music_start_pos_s = target_time_s
            # Update total beats based on new target time
            target_beats = int(target_time_s * (1000 * BEAT_PER_MS))
            self.total_beats = target_beats
            self.last_beat = target_beats - 1
            pygame.mixer.music.play(start=target_time_s)

    def update_score(self, new_score: float, target_type: str, beat_float: float) -> None:
        """Update score and trigger flash effect if score increased."""
        if new_score > self.score:
            self.score_flash_start_beat = beat_float
            self.last_hit_target = target_type
            
            # Check if adding a new hit would exceed circle size
            total_space_needed = (len(self.hit_colors) + 1) * self.hit_spacing
            if total_space_needed >= NUMBER_OF_LEDS:
                self.hit_spacing = self.hit_spacing / 2
            
            # Add hit color to beginning of trail
            # TODO: replace with map
            if target_type == "red":
                self.hit_colors.insert(0, Color(255, 0, 0))
            elif target_type == "blue":
                self.hit_colors.insert(0, Color(0, 0, 255))
            elif target_type == "green":
                self.hit_colors.insert(0, Color(0, 255, 0))
            elif target_type == "yellow":
                self.hit_colors.insert(0, Color(255, 255, 0))
        
        # Always update trail length based on new score
        max_trail_length = int(new_score * 4)
        if len(self.hit_colors) > max_trail_length:
            self.hit_colors = self.hit_colors[:max_trail_length]
                
        self.previous_score = self.score
        self.score = new_score
    
    def get_score_flash_intensity(self, beat_float: float) -> float:
        """Calculate the intensity of the score flash effect based on musical beats."""
        if self.score_flash_start_beat is None:
            return 0.0
        
        beats_since_flash = beat_float - self.score_flash_start_beat
        if beats_since_flash >= 2.0:  # Flash lasts for 2 beats
            return 0.0
        
        return 1.0 - (beats_since_flash / 2.0)

    def calculate_led_position(self, beat_in_measure: int, fractional_beat: float) -> int:
        """Calculate the current LED position based on beat timing."""
        percent_of_measure = (fractional_beat / BEATS_PER_MEASURE) + (beat_in_measure / BEATS_PER_MEASURE)
        return int(percent_of_measure * NUMBER_OF_LEDS)
    
    def update_loop_count(self, percent_of_measure: float) -> None:
        """Update the loop count based on measure progress."""
        if percent_of_measure < 0.5:
            if self.loop_count != self.next_loop:
                self.loop_count = self.next_loop
        elif self.next_loop == self.loop_count:
            self.next_loop = self.loop_count + 1

    def reset_flags(self, led_position: int) -> None:
        """Reset state flags based on LED position."""
        was_in_window = self.in_scoring_window
        self.in_scoring_window = self.button_handler.is_in_valid_window(led_position)
        
        # Reset button state when entering new window
        if not was_in_window and self.in_scoring_window:
            self.button_handler.button_states = {k: False for k in self.button_handler.button_states}
            self.button_handler.penalty_applied = False
            self.button_handler.round_active = True
        elif was_in_window and not self.in_scoring_window:
            self.button_handler.round_active = False

def get_led_position_at_radius(i: int, radius: int) -> Tuple[int, int]:
    """Convert LED index to x,y coordinates in a circular pattern at given radius, starting at 12 o'clock."""
    angle = 3 * math.pi / 2 + (2 * math.pi * i) / NUMBER_OF_LEDS
    x = CIRCLE_CENTER_X + int(radius * math.cos(angle))
    y = CIRCLE_CENTER_Y + int(radius * math.sin(angle))
    return (x, y)

def get_led_position(i: int) -> Tuple[int, int]:
    """Convert LED index to x,y coordinates in a circular pattern, starting at 12 o'clock."""
    return get_led_position_at_radius(i, CIRCLE_RADIUS)

def get_led_position_inner(i: int) -> Tuple[int, int]:
    """Convert LED index to x,y coordinates in a circular pattern, starting at 12 o'clock."""
    return get_led_position_at_radius(i, CIRCLE_RADIUS - 2)

def get_led_position_outer(i: int) -> Tuple[int, int]:
    """Convert LED index to x,y coordinates in a circular pattern, starting at 12 o'clock."""
    return get_led_position_at_radius(i, CIRCLE_RADIUS + 2)

def get_rainbow_color(time_ms: int, line_index: int) -> Color:
    """Generate a rainbow color based on time and line position."""
    hue = (time_ms / COLOR_CYCLE_TIME_MS + line_index * 0.1) % 1.0
    
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
    num_lines = int(score*2)
    current_line = num_lines  # Default to all lines unlit
    
    if flash_intensity > 0:
        # Calculate which line should be lit based on time since flash started
        time_since_flash = SCORE_FLASH_DURATION_MS * (1 - flash_intensity)
        current_line = int(time_since_flash / SCORE_LINE_ANIMATION_TIME_MS)
        # Ensure we start from the top (line 0) and move downward
        current_line = min(current_line, num_lines - 1)
    
    for i in range(num_lines):
        y = SCREEN_HEIGHT - 1 - ((num_lines - 1 - i) * (SCORE_LINE_HEIGHT + SCORE_LINE_SPACING))
        if y >= 0:  # Only draw if we haven't gone off the top of the screen
            # Only use rainbow effect when not flashing
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
    
    def __init__(self):
        if IS_RASPBERRY_PI:
            self.strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
            self.strip.begin()
            self.pygame_surface = None
            self.display_surface = None
        else:
            self.strip = None
            self.display_surface = pygame.display.set_mode((SCREEN_WIDTH * SCALING_FACTOR, SCREEN_HEIGHT * SCALING_FACTOR))
            self.pygame_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    
    def clear(self):
        """Clear the display."""
        if IS_RASPBERRY_PI:
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, 0)
        else:
            self.pygame_surface.fill((0, 0, 0))
    
    def set_pixel(self, pos: int, color: Color):
        """Set pixel color at position."""
        if IS_RASPBERRY_PI:
            # Convert Pygame color to WS281x color (RGB order)
            ws_color = LEDColor(color.r, color.g, color.b)
            self.strip.setPixelColor(pos, ws_color)
        else:
            x, y = get_led_position(pos)
            self.pygame_surface.set_at((x, y), color)
    
    def set_outer_pixel(self, pos: int, color: Color):
        """Set pixel color at position in outer circle."""
        if not IS_RASPBERRY_PI:
            x, y = get_led_position_outer(pos)
            self.pygame_surface.set_at((x, y), color)
    
    def update(self):
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
    clock = Clock()
    display = LEDDisplay()
    
    # Initialize game state
    game_state = GameState()
    
    try:
        # Initialize music
        pygame.mixer.music.load("music/Rise Up 3.mp3")
        pygame.mixer.music.play(start=0)

        while True:
            display.clear()

            # Update timing and music
            beat, beat_in_measure, beat_float, fractional_beat = await game_state.update_timing()
            game_state.handle_music_loop(beat_in_measure)

            current_time_ms = pygame.time.get_ticks()
            current_time_s = current_time_ms / 1000.0
            
            # Calculate LED position and update loop count
            led_position = game_state.calculate_led_position(beat_in_measure, fractional_beat)
            game_state.update_loop_count(led_position / NUMBER_OF_LEDS)

            # Handle scoring and penalties
            if not game_state.button_handler.is_in_valid_window(led_position):
                new_score = game_state.button_handler.apply_penalty(game_state.score)
                if new_score != game_state.score:
                    print(f"New score: {new_score}, target hit: none")
                    game_state.update_score(new_score, "none", beat_float)
            game_state.reset_flags(led_position)
            
            # Check for scoring (both manual and auto)
            new_score, target_hit = game_state.button_handler.handle_keypress(
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
            
            # Draw trail using temporal easing
            positions_to_remove = []
            for pos, lit_time in game_state.lit_positions.items():
                elapsed_s = current_time_s - lit_time
                if elapsed_s > TRAIL_FADE_DURATION_S:
                    positions_to_remove.append(pos)
                else:
                    brightness = TRAIL_EASE.ease(elapsed_s)
                    base_color = game_state.lit_colors[pos]
                    
                    # Check if in target window and apply target color
                    if game_state.button_handler.is_in_valid_window(pos):
                        
                        # TODO: refactor to remove duplicated logic in is_in_valid_window.
                        # Check which target window we're in
                        near_end_target = pos <= TARGET_WINDOW_SIZE or pos >= NUMBER_OF_LEDS - TARGET_WINDOW_SIZE
                        near_middle_target = abs(pos - MID_TARGET_POS) <= TARGET_WINDOW_SIZE
                        near_right_target = abs(pos - RIGHT_TARGET_POS) <= TARGET_WINDOW_SIZE
                        near_left_target = abs(pos - LEFT_TARGET_POS) <= TARGET_WINDOW_SIZE
                        
                        if near_end_target:
                            base_color = Color(255, 0, 0)  # Red
                        elif near_middle_target:
                            base_color = Color(0, 0, 255)  # Blue
                        elif near_right_target:
                            base_color = Color(0, 255, 0)  # Green
                        elif near_left_target:
                            base_color = Color(255, 255, 0)  # Yellow
                    
                    faded_color = Color(
                        int(base_color[0] * brightness),
                        int(base_color[1] * brightness),
                        int(base_color[2] * brightness),
                        base_color[3]
                    )
                    display.set_pixel(pos, faded_color)
            
            # Clean up old trail positions
            for pos in positions_to_remove:
                del game_state.lit_positions[pos]
                del game_state.lit_colors[pos]
            
            # Draw hit trail in outer circle
            for i, color in enumerate(game_state.hit_colors):
                trail_pos = int((led_position - (i + 1) * game_state.hit_spacing) % NUMBER_OF_LEDS)
                display.set_outer_pixel(trail_pos, color)
            
            # Draw score lines with flash effect (only in Pygame mode)
            if not IS_RASPBERRY_PI:
                flash_intensity = game_state.get_score_flash_intensity(beat_float)
                draw_score_lines(display.pygame_surface, game_state.score, current_time_ms, flash_intensity, game_state.last_hit_target)
            
            # Draw current LED in white
            base_color = Color(255, 255, 255)
            # Apply target colors if in scoring window
            if game_state.button_handler.is_in_valid_window(led_position):
                # TODO: refactor to remove duplicated logic in is_in_valid_window.
                # Check which target window we're in
                near_end_target = led_position <= 2 or led_position >= NUMBER_OF_LEDS - 2
                near_middle_target = abs(led_position - MID_TARGET_POS) <= 2
                near_right_target = abs(led_position - RIGHT_TARGET_POS) <= 2
                near_left_target = abs(led_position - LEFT_TARGET_POS) <= 2
                
                if near_end_target:
                    base_color = Color(255, 0, 0)  # Red
                elif near_middle_target:
                    base_color = Color(0, 0, 255)  # Blue
                elif near_right_target:
                    base_color = Color(0, 255, 0)  # Green
                elif near_left_target:
                    base_color = Color(255, 255, 0)  # Yellow
            
            display.set_pixel(led_position, base_color)

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
