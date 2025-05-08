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
    TrailVisualizer
)

from game_constants import *

import logging

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='LED rhythm game')
    parser.add_argument('--leds', type=int, default=80,
                      help='Number of LEDs in the strip (default: 80)')
    
    # Display mode options
    display_group = parser.add_argument_group('Display options')    

    # Debug options
    debug_group = parser.add_argument_group('Debug options')
    debug_group.add_argument('--score', type=float, default=0.0,
                      help='Set initial score value for debug modes')
    debug_group.add_argument('--one-loop', action='store_true',
                      help='Run for one loop and exit')
    debug_group.add_argument('--disable-wled', action='store_true',
                      help='Disable all WLED light commands')
    debug_group.add_argument('--auto-score', action='store_true',
                      help='Automatically score points when in valid windows')
    
    args = parser.parse_args()
    
    return args

# Define default values to use when the script is imported (not run directly)
default_args = argparse.Namespace(
    leds=80,
    hit_trail_strategy='normal',
    score=0.0,
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

# Set number_of_leds from command line arguments
number_of_leds = args.leds

# Calculate target_window_size based on the number of LEDs
target_window_size = number_of_leds // 20

# Check if we're on Raspberry Pi
IS_RASPBERRY_PI = platform.system() == "Linux" and os.uname().machine.startswith("aarch64")

if IS_RASPBERRY_PI:
    from rpi_ws281x import PixelStrip, Color as LEDColor
# LED strip configuration:
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
            number_of_leds=number_of_leds,
            target_window_size=target_window_size,
            auto_score=args.auto_score
        )
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
        beat, beat_in_phrase, beat_float, fractional_beat = MusicTiming.calculate_beat_timing(
            current_time_ms, self.start_ticks_ms
        )

        # Update total beats when we cross a beat boundary
        if beat > self.last_beat:
            self.total_beats += 1
            self.last_beat = beat
            # print(f"Total beats in song: {self.total_beats}")
            
            if not args.disable_wled:
                wled_measure: int = self.total_beats // BEATS_PER_PHRASE
                await self.wled_manager.update_wled(wled_measure, self.score_manager.score)
            
        if beat_in_phrase == 0:
            self.beat_start_time_ms = pygame.time.get_ticks()
        
        return beat, beat_in_phrase, beat_float, fractional_beat
    
    def handle_music_loop(self, beat_in_measure: int) -> None:
        """Handle music looping and position updates."""
        if beat_in_measure == self.last_beat_in_measure:
            return
        self.last_beat_in_measure = beat_in_measure
        
        if beat_in_measure != 0:
            return
            
        self.beat_start_time_ms = pygame.time.get_ticks()
        current_time_ms: int = pygame.time.get_ticks()
            
        # Calculate target music time
        target_time_s: float = self.audio_manager.get_target_music_time(
            self.score_manager.score,
            self.beat_start_time_ms,
            current_time_ms
        )
        
        # Get current music position for logging
        current_music_pos_s: float = self.audio_manager.get_current_music_position()
        print(f"Current music position: {current_music_pos_s}, Score: {self.score_manager.score}")
        print(f"Target time: {target_time_s}")

        if self.audio_manager.should_sync_music(current_music_pos_s, target_time_s):
            print(f"difference {abs(current_music_pos_s - target_time_s)}")
            
            # Update total beats based on new target time
            target_beats: int = self.audio_manager.calculate_target_beats(target_time_s, BEAT_PER_MS)
            self.total_beats = target_beats
            self.last_beat = target_beats - 1
            
            self.audio_manager.play_music(start_pos_s=target_time_s)

    def update_score(self, new_score: float, target_type: str, beat_float: float) -> None:
        """Update score and trigger flash effect if score increased."""
        self.score_manager.update_score(new_score, target_type, beat_float)
    
    def get_score_flash_intensity(self, beat_float: float) -> float:
        """Calculate the intensity of the score flash effect based on musical beats."""
        return self.score_manager.get_score_flash_intensity(beat_float)

    def calculate_led_position(self, beat_in_phrase: int, fractional_beat: float) -> int:
        """Calculate the current LED position based on beat timing."""
        return LEDPosition.calculate_position(beat_in_phrase, fractional_beat, number_of_leds)

def get_target_ring_position(i: int, radius: int) -> Tuple[int, int]:
    """Convert LED index to x,y coordinates in a circular pattern at given radius, starting at 12 o'clock."""
    x, y = LEDPosition.get_ring_position(i, radius, number_of_leds)
    return (CIRCLE_CENTER_X + x, CIRCLE_CENTER_Y + y)

def get_hit_trail_position(i: int) -> Tuple[int, int]:
    """Convert LED index to x,y coordinates in the hit trail ring, starting at 12 o'clock."""
    return get_target_ring_position(i, HIT_TRAIL_RADIUS)

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
    """Get the color for score lines during flash effect."""
    return ScoreManager.get_score_line_color(base_color, flash_intensity, flash_type)

def draw_fifth_line(display: DisplayManager, percent_complete: float) -> None:
    """Draw the fifth line with easing animation and color transitions.
    
    Args:
        display: The display manager instance to draw on.
        percent_complete: The completion percentage of the animation (0.0 to 1.5).
    """
    FIFTH_LINE_EASE = easing_functions.QuadEaseInOut(start=0.0, end=1.0, duration=1.0)
    
    fifth_color = Color(128, 128, 128)
    CENTER_X = SCREEN_WIDTH // 2
    eased_percent_complete = FIFTH_LINE_EASE(min(percent_complete, 1.0))
    position_x = int(CENTER_X * eased_percent_complete)
    if percent_complete > 0.9:
        fifth_color = Color(255, 0, 0)
    if percent_complete > 1.0:
        # Fade from 100% to 0% between 1.0 and 1.5
        fade_amount = min(1.0, (percent_complete - 1.0) * 2)  # Reaches 1.0 at 150%
        fifth_color.r = int(fifth_color.r * (1.0 - fade_amount))
        fifth_color.g = int(fifth_color.g * (1.0 - fade_amount))
        fifth_color.b = int(fifth_color.b * (1.0 - fade_amount))
    pygame.draw.circle(display.pygame_surface, fifth_color, (position_x, 96), 4, 1)

def draw_fifth_lines(display: DisplayManager, measure: float) -> None:
    """Draw the fifth line animation based on the current measure.
    
    Args:
        display: The display manager instance to draw on.
        measure: The current measure number in the song.
    """
    TARGET_MEASURES = [9, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35]
    TARGET_BUFFER = 1
    for target in TARGET_MEASURES:
        if measure > target - TARGET_BUFFER and measure <= target + TARGET_BUFFER/2:
            # print(f"draw_fifth_lines measure: {measure}")
            percent_complete = (measure - (target - TARGET_BUFFER)) / TARGET_BUFFER
            draw_fifth_line(display, percent_complete)
            break

async def run_game() -> None:
    """Main game loop handling display, input, and game logic."""
    # Configure file logging for hit trail behavior
    logging.basicConfig(filename='hit_trail.log', filemode='w', level=logging.INFO, format='%(asctime)s %(message)s')
    logger = logging.getLogger('hit_trail')
    global quit_app

    # Initialize display and clock
    pygame.init()
    clock: Clock = Clock()
    display = DisplayManager(
        screen_width=SCREEN_WIDTH,
        screen_height=SCREEN_HEIGHT,
        scaling_factor=SCALING_FACTOR,
        led_count=number_of_leds,
        led_pin=LED_PIN,  # Default GPIO pin
        led_freq_hz=LED_FREQ_HZ,  # Default frequency
        led_dma=LED_DMA,  # Default DMA channel
        led_invert=LED_INVERT,  # Default invert setting
        led_brightness=LED_BRIGHTNESS,  # Default brightness
        led_channel=LED_CHANNEL  # Default channel
    )
    
    game_state: GameState = GameState()
    hit_trail_visualizer = TrailVisualizer.create_visualizer(
        led_count=number_of_leds,
        auto_mode=args.auto_score,
        speed=1
    )
    
    hit_trail_visualizer.display = display

    if args.score > 0:
        logger.info(f"Setting initial score to {args.score}")
        game_state.score_manager.score = args.score
        hit_trail_visualizer.score = args.score  # Let each visualizer handle the score
    
    logger.info("Showing main trail")
        
    # Set up hit colors based on score (simulate multiple hits)
    hit_trail_visualizer.score = game_state.score  # Let the visualizer handle color mapping
    logger.info(f"Created hit trail with {len(hit_trail_visualizer.hit_colors)} colors")
    
    try:
        # Initialize music
        game_state.audio_manager.load_music("music/Rise Up 4.mp3")
        game_state.audio_manager.play_music(start_pos_s=0.0)

        # Variables for tracking if we've completed one full loop in debug mode
        previous_led_position = -1

        # Handle key press mapping
        key_mapping = {
            "r": TargetType.RED,
            "g": TargetType.GREEN,
            "b": TargetType.BLUE,
            "y": TargetType.YELLOW
        }

        last_beat = -1
        target_hit: Optional[TargetType] = None
        ending_phrase = 1 if args.one_loop else 18
        phrase = 0
        beat_score_offset = 0
        while True:
            display.clear()

            beat_in_phrase: int
            beat_float: float
            fractional_beat: float
            beat, beat_in_phrase, beat_float, fractional_beat = await game_state.update_timing()
            phrase = max(0, int(game_state.score_manager.score - 0.25 + beat_score_offset))
            # print(f"beat: {beat}, beat_in_measure: {beat_in_measure}, beat_float: {beat_float}, fractional_beat: {fractional_beat}")
            measure = 1 + (beat_float / 4)

            if last_beat != beat:
                beat_score_offset = 0
                last_beat = beat
                if beat % BEATS_PER_PHRASE == 0:
                    print(f"phrase: {phrase}, beat_in_phrase: {beat_in_phrase}, measure: {measure}, beat: {beat}")
                if phrase >= ending_phrase:
                    return
            game_state.handle_music_loop(beat_in_phrase)
 
            # print(f"score: {game_state.score_manager.score}, score*2: {game_state.score_manager.score*2}, measure: {measure}")
            if not IS_RASPBERRY_PI:
                score_based_measure = 1+phrase*2 + (beat_in_phrase + fractional_beat)/BEATS_PER_MEASURE
                draw_fifth_lines(display, score_based_measure)
                # print(f"phrase: {phrase}, measure: {measure}, beat_in_phrase: {beat_in_phrase}, fractional_beat: {fractional_beat}, score: {game_state.score_manager.score + beat_score_offset}, score_based_measure: {score_based_measure}")
    
            current_time_ms: int = pygame.time.get_ticks()
            
            led_position: int = game_state.calculate_led_position(beat_in_phrase, fractional_beat)
            
            if not game_state.button_handler.is_in_valid_window(led_position):
                missed_target = game_state.button_handler.missed_target()
                if missed_target:
                    new_score = max(0, game_state.score_manager.score - 0.25)
                    print(f"PENALTY New score: {new_score}, target hit: {target_hit}")

                    # TODO: remove second argument after refactoring normal trail.
                    game_state.update_score(new_score, None, beat_float)
                    hit_trail_visualizer.remove_hit(missed_target)
            
            game_state.reset_flags(led_position)
            
            successful_hit, target_hit = game_state.button_handler.handle_keypress(
                led_position)
            # print(f"successful_hit: {successful_hit}, target_hit: {target_hit}")

            if successful_hit is not None and target_hit is not None:
                new_score = game_state.score_manager.score + 0.25 if successful_hit else 0
                new_led_position = led_position
                if led_position > number_of_leds / 2:
                    new_led_position = led_position - number_of_leds
                if new_led_position < game_state.button_handler.get_window_position_for_target(target_hit):
                    beat_score_offset = -0.25
                    print(f"beat_score_offset: {beat_score_offset}")
                print(f"target_hit: {target_hit}")
                    
                if new_score > game_state.score:
                    hit_trail_visualizer.add_hit(target_hit)
            
                game_state.update_score(new_score, target_hit, beat_float)
            
            # Update trail state when LED position changes
            if led_position != game_state.current_led_position:
                game_state.current_led_position = led_position
                # Store the timestamp and base white color for the new position
                game_state.trail_state_manager.update_position(led_position, current_time_ms / 1000.0)
            
            game_state.trail_state_manager.draw_main_trail(
                TRAIL_FADE_DURATION_S,
                TRAIL_EASE,
                game_state.button_handler,
                lambda pos, color: display.set_pixel(pos, color)
            )
                        
            hit_trail_visualizer.sync_with_game_state(game_state, led_position)
            
            if not IS_RASPBERRY_PI:
                flash_intensity: float = game_state.get_score_flash_intensity(beat_float)
                display.draw_score_lines(
                    score=game_state.score_manager.score,
                    current_time=current_time_ms,
                    flash_intensity=flash_intensity,
                    flash_type=target_hit,
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
            if successful_hit is False:
                print(f"successful_hit: {successful_hit}, target_type: {target_hit}")
                error_pos = game_state.button_handler.get_window_position_for_target(target_hit)
                error_color = TARGET_COLORS[target_hit]
                display.set_pixel(error_pos, error_color)  # Use the color of the wrong key that was pressed

            if not IS_RASPBERRY_PI:
                for key, keydown in get_key():
                    if key == "quit":
                        return
                
            display.update()
            await clock.tick(60)
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
