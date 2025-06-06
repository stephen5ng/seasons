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
from simple_hit_trail import SimpleHitTrail, DefaultTrailDisplay
from rainbow_trail_display import RainbowTrailDisplay
from fifth_line_target import FifthLineTarget, TargetState

from game_constants import *

import logging

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='LED rhythm game')
    parser.add_argument('--leds', type=int, default=NUMBER_OF_LEDS,
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

# Time conversion constants
MS_PER_SEC = 1000.0  # Convert seconds to milliseconds

# Check if we're on Raspberry Pi
IS_RASPBERRY_PI = platform.system() == "Linux" and os.uname().machine.startswith("aarch64")

quit_app = False

class GameState:
    """Manages game state and timing."""
    
    def __init__(self) -> None:
        # Store LED configuration
        self.number_of_leds = args.leds
        
        self.next_loop: int = 1
        self.loop_count: int = 0
        self.button_handler = ButtonHandler(
            number_of_leds=self.number_of_leds,
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
        self.wled_manager = WLEDManager(not args.disable_wled, QUAD_HOSTNAME, self.http_session, number_of_leds=self.number_of_leds//2)
        
        # Trail state manager (replaces individual trail state variables)
        self.trail_state_manager = TrailStateManager()
        self.current_led_position: Optional[int] = None  # Track current LED position
        
        # Track miss timestamps for fade effect
        self.miss_timestamps: Dict[Tuple[int, TargetType], Tuple[float, float]] = {}  # (position, target_type) -> (timestamp, initial_intensity)
        
        # Fifth line target array
        self.fifth_line_targets: List[FifthLineTarget] = []

        # Initialize GPIO button if on Raspberry Pi
        self.fifth_line_button: Optional[Button] = None
        self.fifth_line_pressed: bool = False
        if IS_RASPBERRY_PI:
            self.fifth_line_button = Button(22)  # GPIO 22 for fifth line hit
            self.fifth_line_button.when_pressed = lambda: setattr(self, 'fifth_line_pressed', True)
            
        # Music and timing state
        self.music_started: bool = False
        self.last_hit_time: int = 0
        
        # Display objects will be set after DisplayManager is created
        self.display: Optional[DisplayManager] = None
        self.default_display: Optional[DefaultTrailDisplay] = None
        self.rainbow_display: Optional[RainbowTrailDisplay] = None
        self.hit_trail: Optional[SimpleHitTrail] = None

    def initialize_displays(self, display: DisplayManager) -> None:
        """Initialize display objects after DisplayManager is created.
        
        Args:
            display: The display manager instance
        """
        self.display = display
        self.default_display = DefaultTrailDisplay(display, self.number_of_leds)
        self.rainbow_display = RainbowTrailDisplay(display, self.number_of_leds)
        self.hit_trail = SimpleHitTrail(display, self.number_of_leds, trail_display=self.default_display)

    def stop_music_and_reset(self) -> None:
        """Stop music and reset game state."""
        if self.hit_trail is None or self.default_display is None:
            raise RuntimeError("Display objects not initialized")
            
        pygame.mixer.music.stop()
        self.hit_trail.trail_display = self.default_display
        self.hit_trail.reset()
        self.music_started = False
        self.last_hit_time = 0

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
                display.set_target_trail_pixel(pos, faded_color, 0.5, 0)

    def handle_hits(self, hits: List[TargetType], hit_trail: 'SimpleHitTrail', display: DisplayManager, add_hit: bool = True) -> None:
        """Handle successful hits and update score.
        
        Args:
            hits: List of target types that were hit
            hit_trail: Hit trail instance
            display: Display manager instance to draw on
            add_hit: Whether to add the hit to the hit trail
        """
        for target_hit in hits:
            # Light up LEDs within the target window
            target_color = TARGET_COLORS[target_hit]
            target_pos = self.button_handler.target_positions[target_hit]
            window_start, window_end = self.button_handler.get_window_boundaries(target_pos, hit_trail.hits_by_type, target_hit)
            
            if window_start > window_end:
                window_end += self.button_handler.number_of_leds
                
            for i in range(window_start, window_end + 1):
                display.set_target_trail_pixel(i % self.button_handler.number_of_leds, target_color, 1.0, 1)
    
            if add_hit:
                hit_trail.add_hit(target_hit)

    async def exit_game(self) -> None:
        """Exit the game gracefully.
        
        This method handles cleanup and final WLED commands before exiting.
        """
        print("sleeping to finish wled commands")
        await asyncio.sleep(3)
        print("Cleanup done, Exiting game")

def get_target_ring_position(i: int, radius: int, number_of_leds: int) -> Tuple[int, int]:
    """Convert LED index to x,y coordinates in a circular pattern at given radius, starting at 12 o'clock."""
    x, y = LEDPosition.get_ring_position(i, radius, number_of_leds)
    return (CIRCLE_CENTER_X + x, CIRCLE_CENTER_Y + y)

def get_hit_trail_position(i: int, number_of_leds: int) -> Tuple[int, int]:
    """Convert LED index to x,y coordinates in the hit trail ring, starting at 12 o'clock."""
    return get_target_ring_position(i, HIT_TRAIL_RADIUS, number_of_leds)

async def run_game() -> None:
    """Main game loop handling display, input, and game logic."""
    # Configure file logging for hit trail behavior
    logging.basicConfig(filename='hit_trail.log', filemode='w', level=logging.INFO, format='%(asctime)s %(message)s')
    logger = logging.getLogger('hit_trail')
    global quit_app

    # Initialize display and clock
    pygame.init()
    clock: Clock = Clock()
    
    game_state: GameState = GameState()
    
    display = DisplayManager(
        screen_width=SCREEN_WIDTH,
        screen_height=SCREEN_HEIGHT,
        scaling_factor=SCALING_FACTOR,
        led_count=game_state.number_of_leds,
        led_pin=LED_PIN,
        led_freq_hz=LED_FREQ_HZ,
        led_dma=LED_DMA,
        led_invert=LED_INVERT,
        led_brightness=LED_BRIGHTNESS,
        led_channel=LED_CHANNEL,
        use_sacn=not args.disable_sacn
    )
    
    # Initialize display objects in game state
    game_state.initialize_displays(display)

    logger.info("Showing main trail")
    logger.info(f"Created hit trail with {game_state.hit_trail.total_hits} total hits")
    
    try:
        # Handle key press mapping
        key_mapping = {
            "r": TargetType.RED,
            "g": TargetType.GREEN,
            "b": TargetType.BLUE,
            "y": TargetType.YELLOW,
            " ": None  # Space bar for fifth line
        }

        last_beat = -1
        stable_score = 0
        current_phrase = 0
        while True:
            display.clear()
            current_time_ms: int = pygame.time.get_ticks()
    
            beat_in_phrase: int
            beat_float: float
            beat_in_phrase, beat_float = await game_state.update_timing(current_time_ms)
            fractional_beat: float = beat_float % 1
            
            # Check for fifth line press (space bar or GPIO button)
            fifth_line_pressed = game_state.fifth_line_pressed
            game_state.fifth_line_pressed = False  # Reset GPIO flag
            
            for key, keydown in get_key():
                if key == " " and keydown:
                    fifth_line_pressed = True
                elif key == "quit":
                    display.cleanup()  # Clean up display before exiting
                    return

            valid_targets = [t for t in game_state.fifth_line_targets if t.is_in_valid_window()]
            if valid_targets and (fifth_line_pressed or args.auto_score):
                for target in valid_targets:
                    target.register_hit()
            elif fifth_line_pressed:
                FifthLineTarget.handle_fifth_line_miss(display)

            # Update all fifth line targets and remove completed ones
            for target in game_state.fifth_line_targets[:]:  # Create copy of list for safe removal
                target.update(display, beat_float)
                # Check for penalties
                if current_phrase < AUTOPILOT_PHRASE and target.check_penalties():
                    # Remove half of all hits as penalty for missing fifth line target
                    game_state.hit_trail.remove_half_hits()
                    print("----------------Score penalty: Missed fifth line target")
                if target.state == TargetState.NO_TARGET:
                    game_state.fifth_line_targets.remove(target)

            if last_beat != int(beat_float):
                last_beat = int(beat_float)
                print(f"beat_in_phrase: {beat_in_phrase}, beat_float: {beat_float}")
                
                # print(f"Updating WLED {stable_score}, hit_trail.get_score(): {hit_trail.get_score()}")
                await game_state.wled_manager.update_wled(int(stable_score*2))

                print(f"music_started: {game_state.music_started}, args.auto_score: {args.auto_score}")
                if beat_in_phrase == 0:
                    if game_state.music_started:
                        if current_time_ms - game_state.last_hit_time > 30000:
                            game_state.stop_music_and_reset()
                        else:
                            current_phrase = int(stable_score)
                            print(f"--> current_phrase: {current_phrase}")
                            if current_phrase < AUTOPILOT_PHRASE:
                                game_state.handle_music_loop(int(stable_score), current_time_ms)
                            else:
                                game_state.hit_trail.trail_display = game_state.rainbow_display
                    elif game_state.last_hit_time > 0 or args.auto_score:
                        game_state.audio_manager.play_music(start_pos_s=0.0)
                        game_state.start_ticks_ms = current_time_ms
                        game_state.music_started = True
                        print("Starting music on phrase boundary")

                # Start fifth line animation on measure boundaries
                if beat_in_phrase in (0, 4):  # Check for both start and middle of phrase
                    measure = current_phrase * 2 + (1 if beat_in_phrase == 4 else 0)
                    if FifthLineTarget.should_start_fifth_line(measure):
                        game_state.fifth_line_targets.append(FifthLineTarget(measure))

            led_position: int = LEDPosition.calculate_position(beat_in_phrase, fractional_beat, game_state.number_of_leds)
            
            game_state.button_handler.reset_flags(led_position)
            
            hits, misses = game_state.button_handler.handle_keypress(led_position)
            
            game_state.handle_hits(hits, game_state.hit_trail, display, game_state.music_started)
            game_state.handle_misses(misses, 8, display)
            
            if hits or misses or fifth_line_pressed:
                game_state.last_hit_time = current_time_ms
            
            # Update stable_score only when outside a scoring window
            if not game_state.button_handler.is_in_valid_window(led_position):
                if game_state.music_started and not pygame.mixer.music.get_busy():
                    game_state.stop_music_and_reset()
                stable_score = game_state.hit_trail.get_score()
                
            if led_position != game_state.current_led_position:
                game_state.current_led_position = led_position
                # Store the timestamp and base white color for the new position
                game_state.trail_state_manager.update_position(led_position, current_time_ms / MS_PER_SEC)
            
            # Update display state
            game_state.hit_trail.trail_display.update()
            
            # Draw LEDs at the start and end of each target window
            for target_type, target_pos in game_state.button_handler.target_positions.items():
                window_start, window_end = game_state.button_handler.get_window_boundaries(target_pos, game_state.hit_trail.hits_by_type, target_type)
                display.set_target_trail_pixel(window_start, TARGET_COLORS[target_type], 0.5, 0)
                display.set_target_trail_pixel(window_end, TARGET_COLORS[target_type], 0.5, 0)

            display.set_target_trail_pixel(led_position, Color(255, 255, 255), 0.3, 0)
            display.draw_score_lines(game_state.hit_trail.get_score())
                        
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
