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
from gpiozero import Button  # type: ignore

from get_key import get_key
from button_handler import ButtonHandler
from led_position import LEDPosition
from wled_manager import WLEDManager
from display_manager import DisplayManager
from audio_manager import AudioManager
from trail_state_manager import TrailStateManager
from trail_visualization import TrailVisualizer
from fifth_line_target import FifthLineTarget

from game_constants import *

import logging

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='LED rhythm game')
    parser.add_argument('--leds', type=int, default=80,
                      help='Number of LEDs in the strip (default: 80)')
    
    # Display mode options
    display_group = parser.add_argument_group('Display options')    
    display_group.add_argument('--disable-sacn', action='store_true',
                      help='Disable sACN for LED control')

    # Debug options
    debug_group = parser.add_argument_group('Debug options')
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
    one_loop=False,
    disable_wled=False,
    auto_score=False,
    trails=0,
    use_sacn=True
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
target_window_size = int(number_of_leds * TARGET_WINDOW_PERCENT)

# Time conversion constants
MS_PER_SEC = 1000.0  # Convert seconds to milliseconds

# Check if we're on Raspberry Pi
IS_RASPBERRY_PI = platform.system() == "Linux" and os.uname().machine.startswith("aarch64")

quit_app = False

class GameState:
    """Manages game state and timing."""
    
    def __init__(self) -> None:
        self.next_loop: int = 1
        self.loop_count: int = 0
        self.button_handler = ButtonHandler(
            number_of_leds=number_of_leds,
            target_window_size=target_window_size,
            auto_score=args.auto_score
        )
        self.beat_start_time_ms: int = 0
        
        # Create a single session for all HTTP requests with better DNS settings
        connector = aiohttp.TCPConnector(use_dns_cache=True, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=5.0, connect=3.0)
        self.http_session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        # Component managers
        self.audio_manager = AudioManager("music/Rise Up 4.mp3")
        self.start_ticks_ms: int = pygame.time.get_ticks()
        self.wled_manager = WLEDManager(not args.disable_wled, QUAD_IP, self.http_session, WLED_SETTINGS, number_of_leds)
        
        # Trail state manager (replaces individual trail state variables)
        self.trail_state_manager = TrailStateManager(get_rainbow_color_func=get_rainbow_color)
        self.current_led_position: Optional[int] = None  # Track current LED position
        
        # Track miss timestamps for fade effect
        self.miss_timestamps: Dict[Tuple[int, TargetType], Tuple[float, float]] = {}  # (position, target_type) -> (timestamp, initial_intensity)
        
        # Fifth line target manager
        self.fifth_line_target = FifthLineTarget()

        # Initialize GPIO button if on Raspberry Pi
        self.fifth_line_button: Optional[Button] = None
        if IS_RASPBERRY_PI:
            self.fifth_line_button = Button(22)  # GPIO 22 for fifth line hit

    async def update_timing(self, current_time_ms: int) -> Tuple[int, float]:
        """Calculate current timing values."""
        beat_in_phrase, beat_float = self.audio_manager.calculate_beat_timing(
            current_time_ms, self.start_ticks_ms
        )
            
        if beat_in_phrase == 0:
            self.beat_start_time_ms = current_time_ms
        
        return beat_in_phrase, beat_float
    
    def handle_music_loop(self, stable_score: int, current_time_ms: int) -> None:
        """Handle music looping and position updates."""
        print(f"beat_start_time_ms: {self.beat_start_time_ms}, current_time_ms: {current_time_ms}")
        target_time_s: float = self.audio_manager.get_target_music_time(
            stable_score,
            self.beat_start_time_ms,
            current_time_ms
        )
        current_music_pos_s: float = self.audio_manager.get_current_music_position()
        print(f"target_time_s: {target_time_s}, current_music_pos_s: {current_music_pos_s}")
        if self.audio_manager.should_sync_music(current_music_pos_s, target_time_s, 0.4):
            print(f"SYNCING difference {abs(current_music_pos_s - target_time_s)}")
            self.audio_manager.play_music(start_pos_s=target_time_s)

        self.start_ticks_ms = current_time_ms - target_time_s * MS_PER_SEC

    def handle_misses(self, misses: List[TargetType], max_distance: int, display: DisplayManager) -> None:
        """Handle visualization of missed targets with fade out effect.
        
        Args:
            misses: List of target types that were missed
            display: Display manager instance to draw on
        """
        current_time = pygame.time.get_ticks() / 1000.0  # Convert to seconds
        
        # Add new misses
        for target_miss in misses:
            error_pos = self.button_handler.target_positions[target_miss]
            for offset in range(-max_distance, max_distance + 1):
                pos = error_pos + offset

                # Calculate distance-based intensity using quadratic ease out
                distance = abs(offset) / max_distance
                initial_intensity = 1.0 - (distance ** 2)  # Quadratic ease out
                faded_color = Color(
                    int(TARGET_COLORS[target_miss].r * initial_intensity),
                    int(TARGET_COLORS[target_miss].g * initial_intensity),
                    int(TARGET_COLORS[target_miss].b * initial_intensity)
                )
                display.set_target_trail_pixel(pos, faded_color, 1.0)

    def handle_hits(self, hits: List[TargetType], led_position: int, hit_trail_visualizer: 'TrailVisualizer', beat_float: float, display: DisplayManager) -> None:
        """Handle successful hits and update score.
        
        Args:
            hits: List of target types that were hit
            led_position: Current LED position
            hit_trail_visualizer: Visualizer for hit trails
            beat_float: Current beat position as float
            display: Display manager instance to draw on
        """
        for target_hit in hits:
            if led_position > self.button_handler.number_of_leds / 2:
                led_position -= self.button_handler.number_of_leds
            
            # Light up LEDs within the target window
            target_color = TARGET_COLORS[target_hit]
            target_pos = self.button_handler.target_positions[target_hit]
            window_start, window_end = self.button_handler.get_window_boundaries(target_pos)
            
            if window_start > window_end:
                window_end += self.button_handler.number_of_leds
                
            for i in range(window_start, window_end + 1):
                display.set_target_trail_pixel(i % self.button_handler.number_of_leds, target_color, 1.0, 1)
    
            hit_trail_visualizer.add_hit(target_hit)

    async def exit_game(self) -> None:
        """Exit the game gracefully.
        
        This method handles cleanup and final WLED commands before exiting.
        """
        print("sleeping to finish wled commands")
        await asyncio.sleep(3)
        print("Cleanup done, Exiting game")

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

def get_effective_window_size(phrase: int) -> int:
    """Calculate the effective window size based on the current phrase.
    
    Args:
        phrase: Current phrase number (0-based)
        
    Returns:
        The window size to use for scoring
    """
    return target_window_size // 2 if phrase > 8 else target_window_size

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
        led_pin=LED_PIN,
        led_freq_hz=LED_FREQ_HZ,
        led_dma=LED_DMA,
        led_invert=LED_INVERT,
        led_brightness=LED_BRIGHTNESS,
        led_channel=LED_CHANNEL,
        use_sacn=not args.disable_sacn
    )
    
    game_state: GameState = GameState()
    hit_trail_visualizer = TrailVisualizer(
        display,
        number_of_leds
    )
    
    logger.info("Showing main trail")
    logger.info(f"Created hit trail with {len(hit_trail_visualizer.hit_colors)} colors")
    
    try:
        game_state.audio_manager.play_music(start_pos_s=0.0)
        
        # Variables for tracking if we've completed one full loop in debug mode
        previous_led_position = -1
        was_in_valid_window = False  # Track previous fifth line valid window state

        # Handle key press mapping
        key_mapping = {
            "r": TargetType.RED,
            "g": TargetType.GREEN,
            "b": TargetType.BLUE,
            "y": TargetType.YELLOW,
            " ": None  # Space bar for fifth line
        }

        last_beat = -1
        ending_phrase = 1 if args.one_loop else 18
        stable_score = 0
        current_phrase = 0
        while True:
            display.clear()
            current_time_ms: int = pygame.time.get_ticks()
    
            beat_in_phrase: int
            beat_float: float
            beat_in_phrase, beat_float = await game_state.update_timing(current_time_ms)
            fractional_beat: float = beat_float % 1
            
            # Check if space bar or GPIO button was pressed when fifth line was in valid window
            fifth_line_pressed = args.auto_score
            for key, keydown in get_key():
                if key == " " and keydown:
                    fifth_line_pressed = True
                elif key == "quit":
                    display.cleanup()  # Clean up display before exiting
                    return
            
            # Check GPIO button if on Raspberry Pi
            if game_state.fifth_line_button and game_state.fifth_line_button.is_pressed:
                fifth_line_pressed = True
                
            if fifth_line_pressed:
                game_state.fifth_line_target.register_hit()

            # Update fifth line and check for penalties
            game_state.fifth_line_target.update(display, beat_float)
            game_state.fifth_line_target.get_debug_str()  # Use the new debug method
            if game_state.fifth_line_target.check_penalties():
                print("Applying penalty - missed fifth line hit")
                hit_trail_visualizer.clear_all_hits()

            if last_beat != int(beat_float):
                last_beat = int(beat_float)
                print(f"beat_in_phrase: {beat_in_phrase}, beat_float: {beat_float}")
                
                await game_state.wled_manager.update_wled(stable_score)

                game_state.button_handler.set_window_size(get_effective_window_size(stable_score))

                if stable_score >= ending_phrase:
                    display.cleanup()  # Clean up display before exiting
                    await game_state.exit_game()
                    return
    
                # Sync music on phrase boundaries
                if beat_in_phrase == 0:
                    current_phrase = int(stable_score)
                    print(f"current_phrase: {current_phrase}")
                    game_state.handle_music_loop(int(stable_score), current_time_ms)
 
                # Start fifth line animation on measure boundaries
                if beat_in_phrase in (0, 4):  # Check for both start and middle of phrase
                    game_state.fifth_line_target.maybe_start_fifth_line(current_phrase * 2 + (1 if beat_in_phrase == 4 else 0))

            led_position: int = LEDPosition.calculate_position(beat_in_phrase, fractional_beat, number_of_leds)
            
            if not game_state.button_handler.is_in_valid_window(led_position):
                missed_target = game_state.button_handler.missed_target()
                if missed_target:
                    hit_trail_visualizer.remove_hit(missed_target)
            
            game_state.button_handler.reset_flags(led_position)
            
            hits, misses = game_state.button_handler.handle_keypress(led_position)
            
            game_state.handle_hits(hits, led_position, hit_trail_visualizer, beat_float, display)
            game_state.handle_misses(misses, 8, display)
            
            # Update stable_score only when outside a scoring window
            if not game_state.button_handler.is_in_valid_window(led_position):
                stable_score = int(hit_trail_visualizer.get_score())
            
            if led_position != game_state.current_led_position:
                game_state.current_led_position = led_position
                # Store the timestamp and base white color for the new position
                game_state.trail_state_manager.update_position(led_position, current_time_ms / MS_PER_SEC)
            
            # Draw LEDs at the start and end of each target window
            for target_type, target_pos in game_state.button_handler.target_positions.items():
                window_start, window_end = game_state.button_handler.get_window_boundaries(target_pos)
                display.set_target_trail_pixel(window_start, TARGET_COLORS[target_type], -1)
                display.set_target_trail_pixel(window_end, TARGET_COLORS[target_type], -1)
            
            display.set_target_trail_pixel(led_position, Color(255, 255, 255), 0.8)
            
            hit_trail_visualizer.draw_trail(led_position)
            
            if not IS_RASPBERRY_PI:
                display.draw_score_lines(hit_trail_visualizer.get_score())

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
