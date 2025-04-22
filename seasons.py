#!/usr/bin/env python3

import asyncio
import os
import platform
import argparse
import sys
from typing import List, Optional, Tuple, Dict

import aiohttp
import pygame
from pygame import Color
from pygameasync import Clock

from get_key import get_key
from button_handler import ButtonHandler
from led_position import LEDPosition
from music_timing import MusicTiming
from wled_manager import WLEDManager
from display_manager import DisplayManager
from score_manager import ScoreManager
from audio_manager import AudioManager
from trail_state_manager import TrailStateManager
from trail_visualization import (
    HitTrailVisualizer,
    SimpleTrailVisualizer,
    print_hit_trail_instructions,
    parse_hit_trail_args
)
from simple_hit_trail import SimpleHitTrail

# Import game constants - import specific constants first
from game_constants import (
    WLED_IP, WLED_SETTINGS, SCALING_FACTOR, SCREEN_WIDTH, SCREEN_HEIGHT, 
    CIRCLE_CENTER_X, CIRCLE_CENTER_Y, BEATS_PER_MEASURE, 
    BEAT_PER_MS, SECONDS_PER_MEASURE_S, ERROR_SOUND, HIT_TRAIL_RADIUS,
    BONUS_TRAIL_RADIUS, TRAIL_FADE_DURATION_S, TRAIL_EASE,
    BONUS_TRAIL_FADE_DURATION_S, BONUS_TRAIL_EASE, HIGH_SCORE_THRESHOLD,
    SCORE_FLASH_DURATION_MS, SCORE_LINE_ANIMATION_TIME_MS, SCORE_LINE_HEIGHT,
    SCORE_LINE_SPACING, SCORE_LINE_COLOR, TargetType, TARGET_COLORS
)

# Import remaining constants
import game_constants
from game_constants import *

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='LED rhythm game')
    parser.add_argument('--leds', type=int, default=80,
                      help='Number of LEDs in the strip (default: 80)')
    
    # Display mode options
    display_group = parser.add_argument_group('Display options')
    display_group.add_argument('--show-bonus-trails', action='store_true',
                      help='Display bonus trails')
    display_group.add_argument('--show-main-trail', action='store_true',
                      help='Display main trail')
    display_group.add_argument('--show-hit-trail', action='store_true',
                      help='Display hit trail')
    display_group.add_argument('--hit-trail-strategy', type=str, choices=['normal', 'simple'], default='normal',
                      help='Strategy for hit trail visualization (normal=traditional trail, simple=single LED fade)')
    
    # Debug options
    debug_group = parser.add_argument_group('Debug options')
    debug_group.add_argument('--score', type=float, default=0.0,
                      help='Set initial score value for debug modes')
    debug_group.add_argument('--max-bonus-trails', type=int, default=5,
                      help='Maximum number of bonus trails to create (default: 5)')
    debug_group.add_argument('--one-loop', action='store_true',
                      help='Run for one loop and exit')
    debug_group.add_argument('--disable-wled', action='store_true',
                      help='Disable all WLED light commands')
    debug_group.add_argument('--auto-score', action='store_true',
                      help='Automatically score points when in valid windows')
    
    # Positional shortcut
    parser.add_argument('trails', type=int, nargs='?', default=0,
                      help='Number of bonus trails to display (shortcut for --show-bonus-trails --max-bonus-trails N)')
    
    args = parser.parse_args()
    
    # Handle the positional argument for bonus trails
    if args.trails > 0:
        args.show_bonus_trails = True
        args.max_bonus_trails = args.trails
        print(f"Debug mode: Showing {args.trails} bonus trails")
    
    # If no display modes specified, enable all by default
    if not args.show_bonus_trails and not args.show_main_trail and not args.show_hit_trail:
        args.show_bonus_trails = True
        args.show_main_trail = True
        args.show_hit_trail = True
    
    return args

# Define default values to use when the script is imported (not run directly)
default_args = argparse.Namespace(
    leds=80,
    show_bonus_trails=True,
    show_main_trail=True,
    show_hit_trail=True,
    hit_trail_strategy='normal',
    score=0.0,
    max_bonus_trails=5,
    one_loop=False,
    disable_wled=False,
    auto_score=False,
    trails=0
)

# Only parse arguments when the script is run directly
if __name__ == "__main__":
    args = parse_args()
else:
    # Use default values when the script is imported
    args = default_args

# Update shared constants in game_constants for runtime values
game_constants.NUMBER_OF_LEDS = args.leds

# Update dependent constants
game_constants.TARGET_WINDOW_SIZE = game_constants.NUMBER_OF_LEDS // 20

# Calculate target positions based on percentages
MID_TARGET_POS = int(game_constants.NUMBER_OF_LEDS * game_constants.BLUE_TARGET_PERCENT)
RIGHT_TARGET_POS = int(game_constants.NUMBER_OF_LEDS * game_constants.GREEN_TARGET_PERCENT)
LEFT_TARGET_POS = int(game_constants.NUMBER_OF_LEDS * game_constants.YELLOW_TARGET_PERCENT)

# For convenience, reference frequently used constants directly
NUMBER_OF_LEDS = game_constants.NUMBER_OF_LEDS
TARGET_WINDOW_SIZE = game_constants.TARGET_WINDOW_SIZE

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

# Global state
quit_app = False


class GameState:
    """Manages game state and timing."""
    
    def __init__(self) -> None:
        self.start_ticks_ms: int = pygame.time.get_ticks()
        self.last_beat_in_measure: int = 0
        self.next_loop: int = 1
        self.loop_count: int = 0
        self.error_sound: pygame.mixer.Sound = pygame.mixer.Sound(ERROR_SOUND)
        self.button_handler = ButtonHandler(
            self.error_sound,
            number_of_leds=NUMBER_OF_LEDS,
            target_window_size=TARGET_WINDOW_SIZE,
            auto_score=args.auto_score
        )
        self.trail_length: int = 0 
        self.beat_start_time_ms: int = 0
        self.total_beats: int = 0  # Track total beats in song
        self.last_beat: int = -1  # Track last beat for increment
        self.http_session = aiohttp.ClientSession()  # Create a single session for all HTTP requests
        
        # Component managers
        self.score_manager = ScoreManager()
        self.audio_manager = AudioManager()
        self.audio_manager.load_sound_effect("error", ERROR_SOUND)
        self.wled_manager = WLEDManager(WLED_IP, self.http_session, WLED_SETTINGS)
        
        # Trail state manager (replaces individual trail state variables)
        self.trail_state_manager = TrailStateManager(get_rainbow_color_func=get_rainbow_color)
        self.current_led_position: Optional[int] = None  # Track current LED position
        
    @property
    def score(self) -> float:
        """Get the current score."""
        return self.score_manager.score
        
    @property
    def previous_score(self) -> float:
        """Get the previous score."""
        return self.score_manager.previous_score
        
    @property
    def hit_colors(self) -> List[Color]:
        """Get the hit colors list."""
        return self.score_manager.hit_colors
        
    @property
    def hit_spacing(self) -> int:
        """Get the current hit spacing."""
        return self.score_manager.hit_spacing
        
    @property
    def hit_trail_cleared(self) -> bool:
        """Check if the hit trail has been cleared."""
        return self.score_manager.hit_trail_cleared
        
    @property
    def last_hit_target(self) -> str:
        """Get the last hit target."""
        return self.score_manager.last_hit_target
        
    def reset_flags(self, led_position: int) -> None:
        """Reset state flags based on LED position."""
        # Track if we're in a scoring window
        was_in_window: bool = self.button_handler.round_active
        
        # Let the button handler reset its flags
        self.button_handler.reset_flags(led_position)
        
        # Update our local tracking of scoring window
        is_in_window: bool = self.button_handler.round_active
        
        # If we just entered a scoring window, print debug info
        if is_in_window and not was_in_window:
            print(f"Entered scoring window at position {led_position}")

    async def update_timing(self) -> Tuple[int, int, float, float]:
        """Calculate current timing values."""
        current_time_ms: int = pygame.time.get_ticks()
        beat, beat_in_measure, beat_float, fractional_beat = MusicTiming.calculate_beat_timing(
            current_time_ms, self.start_ticks_ms, BEAT_PER_MS, BEATS_PER_MEASURE
        )
        
        # Update total beats when we cross a beat boundary
        if beat > self.last_beat:
            self.total_beats += 1
            self.last_beat = beat
            print(f"Total beats in song: {self.total_beats}")
            
            # Update WLED based on current measure and score
            # Skip if WLED is disabled
            if not args.disable_wled:
                wled_measure: int = self.total_beats // BEATS_PER_MEASURE
                await self.wled_manager.update_wled(wled_measure, self.score_manager.score)
            
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
            
        self.beat_start_time_ms = pygame.time.get_ticks()
        current_time_ms: int = pygame.time.get_ticks()
        
        # Skip music handling if in debug mode with a score set
        if args.score > 0:
            return
            
        # Calculate target music time
        target_time_s: float = self.audio_manager.get_target_music_time(
            self.score_manager.score,
            self.beat_start_time_ms,
            current_time_ms,
            SECONDS_PER_MEASURE_S
        )
        
        # Get current music position for logging
        current_music_pos_s: float = self.audio_manager.get_current_music_position()
        print(f"Current music position: {current_music_pos_s}, Score: {self.score_manager.score}")
        print(f"Target time: {target_time_s}")

        # Check if we need to synchronize music
        if self.audio_manager.should_sync_music(current_music_pos_s, target_time_s):
            print(f"difference {abs(current_music_pos_s - target_time_s)}")
            
            # Update total beats based on new target time
            target_beats: int = self.audio_manager.calculate_target_beats(target_time_s, BEAT_PER_MS)
            self.total_beats = target_beats
            self.last_beat = target_beats - 1
            
            # Play music from the target position
            self.audio_manager.play_music(start_pos_s=target_time_s)

    def update_score(self, new_score: float, target_type: str, beat_float: float) -> None:
        """Update score and trigger flash effect if score increased."""
        self.score_manager.update_score(new_score, target_type, beat_float, NUMBER_OF_LEDS)
    
    def get_score_flash_intensity(self, beat_float: float) -> float:
        """Calculate the intensity of the score flash effect based on musical beats."""
        return self.score_manager.get_score_flash_intensity(beat_float)

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
    from game_constants import COLOR_CYCLE_TIME_MS
    
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
    """Get the color for score lines during flash effect."""
    return ScoreManager.get_score_line_color(base_color, flash_intensity, flash_type)



async def run_game() -> None:
    """Main game loop handling display, input, and game logic."""
    global quit_app

    # Initialize display and clock
    pygame.init()
    clock: Clock = Clock()
    display = DisplayManager(
        screen_width=SCREEN_WIDTH,
        screen_height=SCREEN_HEIGHT,
        scaling_factor=SCALING_FACTOR,
        led_count=game_constants.NUMBER_OF_LEDS,
        led_pin=18,  # Default GPIO pin
        led_freq_hz=800000,  # Default frequency
        led_dma=10,  # Default DMA channel
        led_invert=False,  # Default invert setting
        led_brightness=255,  # Default brightness
        led_channel=0  # Default channel
    )
    
    # Initialize game state
    game_state: GameState = GameState()
    
    # Initialize hit trail visualization based on strategy
    use_simple_hit_trail = args.hit_trail_strategy == 'simple'
    
    if use_simple_hit_trail:
        # For simple strategy, use SimpleTrailVisualizer
        hit_trail_visualizer = SimpleTrailVisualizer(
            led_count=game_constants.NUMBER_OF_LEDS,
            auto_mode=False,  # No auto mode in main game
            speed=1,  # Speed is controlled by the game
            fade_duration_ms=500  # 500ms fade duration
        )
    else:
        # For normal strategy, use HitTrailVisualizer
        hit_trail_visualizer = HitTrailVisualizer(
            led_count=game_constants.NUMBER_OF_LEDS,
            initial_score=args.score,
            auto_mode=False,  # No auto mode in main game
            speed=1,  # Speed is controlled by the game
            hit_spacing=game_constants.INITIAL_HIT_SPACING
        )
    
    hit_trail_visualizer.display = display
    
    # Debug display modes
    show_main_trail = args.show_main_trail
    show_hit_trail = args.show_hit_trail
    show_bonus_trails = args.show_bonus_trails
    run_one_loop = args.one_loop
    
    # Set initial score for debug modes
    if args.score > 0:
        print(f"Setting initial score to {args.score}")
        game_state.score_manager.score = args.score
        if not use_simple_hit_trail:
            hit_trail_visualizer.score = args.score  # Only set score for normal strategy
    
    # Debug setup for different display modes
    if show_main_trail:
        print(f"Showing main trail")
    if show_hit_trail:
        print(f"Showing hit trail using {args.hit_trail_strategy} strategy")
        
        # Set up hit colors based on score (simulate multiple hits) - only for normal strategy
        if not use_simple_hit_trail:
            # Add different colors based on the score level
            hit_colors_count = int(game_state.score * 4)  # 4 colors per score point
            for i in range(min(hit_colors_count, 40)):  # Max 40 colors
                if i % 4 == 0:
                    hit_trail_visualizer.hit_colors.append(TARGET_COLORS[TargetType.RED])
                elif i % 4 == 1:
                    hit_trail_visualizer.hit_colors.append(TARGET_COLORS[TargetType.GREEN])
                elif i % 4 == 2:
                    hit_trail_visualizer.hit_colors.append(TARGET_COLORS[TargetType.BLUE])
                else:
                    hit_trail_visualizer.hit_colors.append(TARGET_COLORS[TargetType.YELLOW])
                    
            print(f"Created hit trail with {len(hit_trail_visualizer.hit_colors)} colors")
    if show_bonus_trails:
        print(f"Showing bonus trails")
    
    try:
        # Initialize music
        game_state.audio_manager.load_music("music/Rise Up 3.mp3")
        game_state.audio_manager.play_music(start_pos_s=0.0)

        # Variables for tracking if we've completed one full loop in debug mode
        debug_loop_started = True  # Start tracking immediately
        previous_led_position = -1

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

            # For debug mode, track when we've completed one loop
            if run_one_loop:
                # Initialize the first position
                if previous_led_position == -1:
                    previous_led_position = led_position
                    print(f"Debug: Started tracking at position {led_position}")
                
                # If we've gone from a high position to a low position, we've completed a loop
                elif previous_led_position > 70 and led_position < 10:
                    print(f"Debug: Completed one full loop, exiting.")
                    return
                
                previous_led_position = led_position
            
            # Handle scoring and penalties
            if not game_state.button_handler.is_in_valid_window(led_position):
                new_score: float = game_state.button_handler.apply_penalty(game_state.score_manager.score)
                if new_score != game_state.score_manager.score:
                    print(f"New score: {new_score}, target hit: none")
                    game_state.update_score(new_score, "none", beat_float)
            
            # Always reset flags
            game_state.reset_flags(led_position)
            
            # Check for scoring (both manual and auto)
            new_score: float
            target_hit: str
            error_feedback: Optional[Tuple[int, Color]] = None
            new_score, target_hit, error_feedback = game_state.button_handler.handle_keypress(
                led_position, game_state.score_manager.score, current_time_ms)
            if new_score != game_state.score:
                print(f"New score: {new_score}, target hit: {target_hit}")
                game_state.update_score(new_score, target_hit, beat_float)
                
                # If the score increased and we're showing hit trail, update the hit trail
                if new_score > game_state.score and show_hit_trail:
                    try:
                        if target_hit != "none":
                            target_enum = TargetType[target_hit.upper()]
                            
                            # Update the appropriate hit trail strategy
                            if use_simple_hit_trail:
                                # For simple strategy, just add the hit at the current position
                                hit_trail_visualizer.add_hit(target_enum)
                            else:
                                # For normal strategy, update the visualizer
                                hit_trail_visualizer.score = new_score
                                hit_trail_visualizer.add_hit(target_enum)
                    except KeyError:
                        pass  # Ignore invalid target types
                        
            # Handle hit trail cleared state synchronization (only for normal strategy)
            if not use_simple_hit_trail and game_state.hit_trail_cleared and show_hit_trail:
                hit_trail_visualizer.hit_trail_cleared = True
            
            # Update trail state when LED position changes
            if led_position != game_state.current_led_position:
                game_state.current_led_position = led_position
                # Store the timestamp and base white color for the new position
                game_state.trail_state_manager.update_position(led_position, current_time_s)
            
            # Draw target trail
            if show_main_trail:
                game_state.trail_state_manager.draw_main_trail(
                    TRAIL_FADE_DURATION_S,
                    TRAIL_EASE,
                    game_state.button_handler,
                    lambda pos, color: display.set_pixel(pos, color)
                )
            
            # Draw bonus trail if hit trail has been cleared
            if game_state.hit_trail_cleared and show_bonus_trails:
                game_state.trail_state_manager.draw_bonus_trail(
                    BONUS_TRAIL_FADE_DURATION_S,
                    BONUS_TRAIL_EASE,
                    lambda pos, color: display.set_bonus_trail_pixel(pos, color)
                )
                # Reset hit_trail_cleared flag after drawing the bonus trail
                game_state.score_manager.hit_trail_cleared = False
                print("Reset hit_trail_cleared flag")
            
            # Draw hit trail in outer circle using the selected strategy
            if show_hit_trail:
                if use_simple_hit_trail:
                    # For simple strategy, just update position and draw
                    hit_trail_visualizer.current_position = led_position
                    hit_trail_visualizer.draw_hit_trail()
                else:
                    # For normal strategy, use the visualizer
                    # Make sure hit_trail_visualizer has the same hit trail colors as game_state
                    if hit_trail_visualizer.hit_colors != game_state.hit_colors:
                        hit_trail_visualizer.hit_colors = game_state.hit_colors.copy()
                        hit_trail_visualizer.hit_spacing = game_state.hit_spacing
                    
                    # Update visualizer position and draw hit trail
                    hit_trail_visualizer.current_position = led_position
                    hit_trail_visualizer.draw_hit_trail()
            
            # Draw score lines with flash effect (only in Pygame mode)
            if not IS_RASPBERRY_PI:
                flash_intensity: float = game_state.get_score_flash_intensity(beat_float)
                display.draw_score_lines(
                    score=game_state.score_manager.score,
                    current_time=current_time_ms,
                    flash_intensity=flash_intensity,
                    flash_type=game_state.last_hit_target,
                    score_line_color=SCORE_LINE_COLOR,
                    high_score_threshold=HIGH_SCORE_THRESHOLD,
                    score_flash_duration_ms=SCORE_FLASH_DURATION_MS,
                    score_line_animation_time_ms=SCORE_LINE_ANIMATION_TIME_MS,
                    score_line_height=SCORE_LINE_HEIGHT,
                    score_line_spacing=SCORE_LINE_SPACING,
                    get_rainbow_color_func=get_rainbow_color,
                    get_score_line_color_func=get_score_line_color
                )
            
            # Draw current LED in white (unless hit-trail-only mode)
            if show_main_trail:
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
                
                # If using simple hit trail strategy, allow direct key presses to light up LEDs
                if use_simple_hit_trail and show_hit_trail and keydown:
                    if key == "r" or key == "up":
                        hit_trail_visualizer.add_hit(TargetType.RED)
                    elif key == "g" or key == "right":
                        hit_trail_visualizer.add_hit(TargetType.GREEN) 
                    elif key == "b" or key == "down":
                        hit_trail_visualizer.add_hit(TargetType.BLUE)
                    elif key == "y" or key == "left":
                        hit_trail_visualizer.add_hit(TargetType.YELLOW)

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
