#!/usr/bin/env python

import asyncio
import math
import os
import platform
import sys
from typing import List, Optional, Tuple, Union

import aiomqtt
import easing_functions
import pygame
from pygame import Color, K_r, K_b
from pygameasync import Clock

from get_key import get_key

# Check if we're on Raspberry Pi
IS_RASPBERRY_PI = platform.system() == "Linux" and os.uname().machine.startswith("arm")

# Check if keyboard is available
try:
    import my_inputs
    my_inputs.get_key()
    HAS_KEYBOARD = True
except (ImportError, my_inputs.UnpluggedError):
    HAS_KEYBOARD = False
    print("No keyboard found, running in auto-score mode")

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
SECONDS_PER_MEASURE = 3.7

# Debug settings
ALWAYS_SCORE = True  # When True, automatically scores on every round

# LED display constants
NUMBER_OF_LEDS = 40
FADE_THRESHOLD = 5  # Number of LEDs before zero to start fading
MIN_CYAN = 128  # Minimum cyan value for LED color
MAX_CYAN = 255  # Maximum cyan value for LED color
RED_WINDOW_SIZE = 4  # How many LEDs before/after target to start showing red
BLUE_WINDOW_SIZE = 4  # How many LEDs before/after mid target to start showing blue
GREEN_WINDOW_SIZE = 4  # How many LEDs before/after 90 degree target to start showing green
YELLOW_WINDOW_SIZE = 4  # How many LEDs before/after 270 degree target to start showing yellow
LED_COLOR_INTENSITY = 0.7  # How much color to add to the LED
BLUE_COLOR_INTENSITY = 1.0  # How much blue to add (brighter than other colors)
GREEN_COLOR_INTENSITY = 1.0  # How much green to add (brighter than other colors)
YELLOW_COLOR_INTENSITY = 1.0  # How much yellow to add (brighter than other colors)
MID_TARGET_POS = NUMBER_OF_LEDS/2  # Position of the middle target
RIGHT_TARGET_POS = NUMBER_OF_LEDS/4  # Position of the 90 degree target
LEFT_TARGET_POS = 3*NUMBER_OF_LEDS/4  # Position of the 270 degree target

# Fade effect constants
MIN_FADE_FACTOR = 0.95   # Minimum fade factor (fastest fade)
MAX_FADE_FACTOR = 0.98   # Maximum fade factor (slowest fade)
FADE_SCORE_SCALE = 10.0  # Score at which fade factor reaches maximum
TRAIL_LENGTH = 8  # Number of previous positions to remember

# Score display constants
HIGH_SCORE_THRESHOLD = 5  # Score threshold for exciting effects
COLOR_CYCLE_SPEED = 2000  # Time in ms for one complete color cycle
SCORE_LINE_COLOR = Color("green")
SCORE_LINE_SPACING = 0.5  # Pixels between score lines
SCORE_LINE_HEIGHT = 0.5  # Height of each score line
SCORE_FLASH_DURATION_MS = 1000  # How long the score flash lasts
SCORE_LINE_ANIMATION_SPEED = 100  # ms per line animation (slowed down from 50ms)

# MQTT settings
MQTT_SERVER = os.environ.get("MQTT_SERVER", "localhost")

# Create easing functions once
CYAN_EASE = easing_functions.ExponentialEaseInOut(start=0, end=1, duration=1)
SCORE_FLASH_EASE = easing_functions.ExponentialEaseOut(start=0, end=1, duration=1)  # Smooth animation for score flashes

# Global state
quit_app = False

class LEDTrail:
    """Manages a trail of LED positions with fading effect."""
    
    def __init__(self, length: int):
        self.positions: List[int] = []
        self.max_length = length
    
    def update(self, new_position: int) -> None:
        """Add new position if different from last and maintain max length."""
        if not self.positions or self.positions[-1] != new_position:
            self.positions.append(new_position)
            if len(self.positions) > self.max_length:
                self.positions.pop(0)
    
    def draw(self, screen: pygame.Surface, score: float) -> None:
        """Draw trail with fading effect based on position age."""
        for i, pos in enumerate(self.positions):
            trail_fade = (i + 1) / len(self.positions)
            distance_to_zero = min(pos, NUMBER_OF_LEDS - pos)
            base_color = get_cyan_color(distance_to_zero)
            fade_factor = get_fade_factor(score) * trail_fade
            
            faded_color = Color(
                int(base_color[0] * fade_factor),
                int(base_color[1] * fade_factor),
                int(base_color[2] * fade_factor),
                base_color[3]
            )
            draw_led(screen, pos, faded_color)

def get_keyboard_input():
    """Get keyboard input if available, otherwise return empty list."""
    if HAS_KEYBOARD:
        return get_key()
    return []

class ButtonPressHandler:
    """Handles button press logic and scoring."""
    
    def __init__(self) -> None:
        self.button_pressed: bool = False
        self.penalty_applied: bool = False
        self.round_active: bool = False
    
    def is_in_valid_window(self, led_position: int) -> bool:
        """Check if the current LED position is in a valid window for scoring."""
        return_value = (led_position >= NUMBER_OF_LEDS - 2 or 
                led_position <= 2 or
                abs(led_position - MID_TARGET_POS) <= 2 or
                abs(led_position - RIGHT_TARGET_POS) <= 2 or
                abs(led_position - LEFT_TARGET_POS) <= 2)
        return return_value
    
    def apply_penalty(self, score: float) -> float:
        """Apply penalty if button wasn't pressed in valid window."""
        if not self.button_pressed and not self.penalty_applied:
            score *= 0.75  # Reduce score by 25% instead of 50%
            self.penalty_applied = True
        return score
    
    def reset_flags(self, led_position: int) -> None:
        """Reset state flags based on LED position."""
        if self.is_in_valid_window(led_position) and not self.round_active:
            self.button_pressed = False
            self.penalty_applied = False
            self.round_active = True  # Start a new scoring round
        elif not self.is_in_valid_window(led_position):
            self.round_active = False  # End the current scoring round
    
    def handle_keypress(self, led_position: int, score: float, current_time: int) -> Tuple[float, str]:
        """Handle keypress and update score if in valid window with correct key."""
        if not self.button_pressed and self.is_in_valid_window(led_position):
            # Check if near end targets (0 or NUMBER_OF_LEDS)
            near_end_target = led_position <= 2 or led_position >= NUMBER_OF_LEDS - 2
            # Check if near middle target
            near_middle_target = abs(led_position - MID_TARGET_POS) <= 2
            # Check if near right target (90 degrees)
            near_right_target = abs(led_position - RIGHT_TARGET_POS) <= 2
            # Check if near left target (270 degrees)
            near_left_target = abs(led_position - LEFT_TARGET_POS) <= 2
            
            # Check for either real key press or auto-score mode
            if HAS_KEYBOARD:
                keys_pressed = pygame.key.get_pressed()
                r_pressed = keys_pressed[pygame.K_r] or ALWAYS_SCORE
                b_pressed = keys_pressed[pygame.K_b] or ALWAYS_SCORE
                g_pressed = keys_pressed[pygame.K_g] or ALWAYS_SCORE
                y_pressed = keys_pressed[pygame.K_y] or ALWAYS_SCORE
            else:
                # In auto-score mode, all targets are hit automatically
                r_pressed = b_pressed = g_pressed = y_pressed = True
            
            if near_end_target and r_pressed:
                score += 0.25
                self.button_pressed = True
                self.penalty_applied = False
                return score, "red"
            elif near_middle_target and b_pressed:
                score += 0.25
                self.button_pressed = True
                self.penalty_applied = False
                return score, "blue"
            elif near_right_target and g_pressed:
                score += 0.25
                self.button_pressed = True
                self.penalty_applied = False
                return score, "green"
            elif near_left_target and y_pressed:
                score += 0.25
                self.button_pressed = True
                self.penalty_applied = False
                return score, "yellow"
        return score, "none"

class GameState:
    """Manages game state and timing."""
    
    def __init__(self) -> None:
        self.start_ticks = pygame.time.get_ticks()
        self.last_beat_in_measure = 0
        self.score = 0
        self.previous_score = 0  # Track previous score to detect changes
        self.score_flash_start_beat: Optional[float] = None  # When the score last changed (in beats)
        self.last_hit_target = "none"  # Track which target was hit: "red", "blue", or "none"
        self.next_loop = 1
        self.loop_count = 0
        self.button_handler = ButtonPressHandler()
        self.led_trail = LEDTrail(TRAIL_LENGTH)
        self.beat_start_time = 0
        self.last_music_start_time = 0.0  # Track when we last started playing music
        self.last_music_start_pos = 0.0   # Track from what position we started playing
        self.total_beats = 0  # Track total beats in song
        self.last_beat = -1  # Track last beat for increment
    
    def update_timing(self) -> Tuple[int, int, float, float]:
        """Calculate current timing values."""
        duration_ms = pygame.time.get_ticks() - self.start_ticks
        beat_float = duration_ms * BEAT_PER_MS
        beat = int(beat_float)
        beat_in_measure = beat % BEATS_PER_MEASURE
        fractional_beat = beat_float % 1
        
        # Update total beats when we cross a beat boundary
        if beat > self.last_beat:
            self.total_beats += 1
            self.last_beat = beat
            print(f"Total beats in song: {self.total_beats}")
        
        if beat_in_measure == 0:
            self.beat_start_time = pygame.time.get_ticks()
        
        return beat, beat_in_measure, beat_float, fractional_beat
    
    def handle_music_loop(self, beat_in_measure: int) -> None:
        """Handle music looping and position updates."""
        if beat_in_measure != self.last_beat_in_measure:
            self.last_beat_in_measure = beat_in_measure
            if beat_in_measure == 0:
                current_time = pygame.time.get_ticks()
                measure_offset = (current_time - self.beat_start_time) / 1000.0
                target_time = int(self.score) * SECONDS_PER_MEASURE + measure_offset
                
                # Get current music position in seconds, accounting for start position
                current_music_pos = self.last_music_start_pos + (pygame.mixer.music.get_pos() / 1000.0)
                
                print(f"Current music position: {current_music_pos}, Score: {self.score}")
                print(f"Target time: {target_time}")
                # Only restart if the difference is more than 0.1 seconds
                if abs(current_music_pos - target_time) > 0.1:
                    print(f"difference {abs(current_music_pos - target_time)}")
                    print(f"Starting music at {target_time} seconds")
                    self.last_music_start_pos = target_time
                    # Update total beats based on new target time
                    target_beats = int(target_time * (1000 * BEAT_PER_MS))
                    self.total_beats = target_beats
                    self.last_beat = target_beats - 1
                    pygame.mixer.music.play(start=target_time)
    
    def update_score(self, new_score: float, current_time: int, target_type: str = "none", beat_float: float = 0) -> None:
        """Update score and trigger flash effect if score increased."""
        if new_score > self.score:
            self.score_flash_start_beat = beat_float
            self.last_hit_target = target_type
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

    def draw_current_led(self, screen: pygame.Surface, led_position: int) -> None:
        """Draw the current LED position with appropriate color."""
        distance_to_zero = min(led_position, NUMBER_OF_LEDS - led_position)
        base_color = get_cyan_color(distance_to_zero)
        led_color = get_led_color(base_color, led_position)
        draw_led(screen, led_position, led_color)

def get_led_position(i: int) -> Tuple[int, int]:
    """Convert LED index to x,y coordinates in a circular pattern, starting at 12 o'clock."""
    angle = 3 * math.pi / 2 + (2 * math.pi * i) / NUMBER_OF_LEDS
    x = CIRCLE_CENTER_X + int(CIRCLE_RADIUS * math.cos(angle))
    y = CIRCLE_CENTER_Y + int(CIRCLE_RADIUS * math.sin(angle))
    return (x, y)

def draw_led(screen: pygame.Surface, i: int, color: Color) -> None:
    """Draw an LED at position i in a circular pattern."""
    screen.set_at(get_led_position(i), color)

def get_fade_factor(score: float) -> float:
    """Calculate fade factor based on current score."""
    normalized_score = min(score / FADE_SCORE_SCALE, 1.0)
    return MIN_FADE_FACTOR + normalized_score * (MAX_FADE_FACTOR - MIN_FADE_FACTOR)

def get_cyan_color(position: int) -> Color:
    """Calculate cyan color intensity based on position relative to zero."""
    if position >= FADE_THRESHOLD:
        return Color(0, MIN_CYAN, MIN_CYAN)
    
    normalized_pos = position / FADE_THRESHOLD
    intensity = CYAN_EASE(normalized_pos)
    cyan_value = int(MIN_CYAN + (MAX_CYAN - MIN_CYAN) * (1 - intensity))
    return Color(0, cyan_value, cyan_value)

def get_window_color(base_color: Color) -> Color:
    """Add a yellow tint to the base color in the valid window."""
    return Color(
        min(255, int(base_color[0] + (255 - base_color[0]) * LED_COLOR_INTENSITY)),
        min(255, int(base_color[1] + (255 - base_color[1]) * LED_COLOR_INTENSITY)),
        min(255, int(base_color[2] + (255 - base_color[2]) * LED_COLOR_INTENSITY)),
        base_color[3]
    )

def get_rainbow_color(time_ms: int, line_index: int) -> Color:
    """Generate a rainbow color based on time and line position."""
    hue = (time_ms / COLOR_CYCLE_SPEED + line_index * 0.1) % 1.0
    
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

def get_led_color(base_color: Color, led_position: int) -> Color:
    """Add color to the LED when near target windows."""
    # Check if we're near either end target window (0 or NUMBER_OF_LEDS)
    distance_to_zero = min(led_position, NUMBER_OF_LEDS - led_position)
    if distance_to_zero <= RED_WINDOW_SIZE:
        # Calculate red intensity based on proximity to target
        color_factor = LED_COLOR_INTENSITY * (1 - distance_to_zero / RED_WINDOW_SIZE)
        return Color(
            min(255, int(255 * color_factor)),  # Red component
            int(base_color[1] * (1 - color_factor)),  # Reduce green
            int(base_color[2] * (1 - color_factor)),  # Reduce blue
            base_color[3]
        )
    
    # Check if we're near the middle target
    distance_to_mid = abs(led_position - MID_TARGET_POS)
    if distance_to_mid <= BLUE_WINDOW_SIZE:
        # Calculate blue intensity based on proximity to middle target
        color_factor = BLUE_COLOR_INTENSITY * (1 - distance_to_mid / BLUE_WINDOW_SIZE)
        return Color(
            0,  # No red
            0,  # No green
            min(255, int(255 * color_factor)),  # Pure blue at full intensity
            base_color[3]
        )
    
    # Check if we're near the right target (90 degrees)
    distance_to_right = abs(led_position - RIGHT_TARGET_POS)
    if distance_to_right <= GREEN_WINDOW_SIZE:
        # Calculate green intensity based on proximity to right target
        color_factor = GREEN_COLOR_INTENSITY * (1 - distance_to_right / GREEN_WINDOW_SIZE)
        return Color(
            0,  # No red
            min(255, int(255 * color_factor)),  # Pure green at full intensity
            0,  # No blue
            base_color[3]
        )
    
    # Check if we're near the left target (270 degrees)
    distance_to_left = abs(led_position - LEFT_TARGET_POS)
    if distance_to_left <= YELLOW_WINDOW_SIZE:
        # Calculate yellow intensity based on proximity to left target
        color_factor = YELLOW_COLOR_INTENSITY * (1 - distance_to_left / YELLOW_WINDOW_SIZE)
        return Color(
            min(255, int(255 * color_factor)),  # Red component
            min(255, int(255 * color_factor)),  # Green component
            0,  # No blue
            base_color[3]
        )
    
    return base_color  # Return normal cyan color when not near targets

def draw_score_lines(screen: pygame.Surface, score: float, current_time: int, flash_intensity: float, flash_type: str) -> None:
    """Draw horizontal lines representing the score with top-to-bottom animation."""
    num_lines = int(score*2)
    current_line = num_lines  # Default to all lines unlit
    
    if flash_intensity > 0:
        # Calculate which line should be lit based on time since flash started
        time_since_flash = SCORE_FLASH_DURATION_MS * (1 - flash_intensity)
        current_line = int(time_since_flash / SCORE_LINE_ANIMATION_SPEED)
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
                
            pygame.draw.line(screen, line_color, (0, y), (SCREEN_WIDTH - 1, y))

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
    
    def update(self):
        """Update the display."""
        if IS_RASPBERRY_PI:
            self.strip.show()
        else:
            pygame.transform.scale(self.pygame_surface, 
                (SCREEN_WIDTH * SCALING_FACTOR, SCREEN_HEIGHT * SCALING_FACTOR), 
                self.display_surface)
            pygame.display.update()

async def trigger_events_from_mqtt(subscribe_client: aiomqtt.Client) -> None:
    """Handle MQTT events for game control."""
    global quit_app
    async for message in subscribe_client.messages:
        if message.topic.matches("password_game/quit"):
            quit_app = True

async def run_game() -> None:
    """Main game loop handling display, input, and game logic."""
    global quit_app

    # Initialize display
    clock = Clock()
    display = LEDDisplay()
    
    # Initialize game state
    game_state = GameState()
    
    # Initialize music
    pygame.mixer.music.load("music/Rise Up 3.mp3")
    pygame.mixer.music.play(start=0)

    while True:
        display.clear()

        # Update timing and music
        beat, beat_in_measure, beat_float, fractional_beat = game_state.update_timing()
        game_state.handle_music_loop(beat_in_measure)

        current_time = pygame.time.get_ticks()
        
        # Calculate LED position and update loop count
        led_position = game_state.calculate_led_position(beat_in_measure, fractional_beat)
        game_state.update_loop_count(led_position / NUMBER_OF_LEDS)
                
        # Handle scoring and penalties
        if not game_state.button_handler.is_in_valid_window(led_position):
            new_score = game_state.button_handler.apply_penalty(game_state.score)
            if new_score != game_state.score:
                game_state.update_score(new_score, current_time, "none", beat_float)
        game_state.button_handler.reset_flags(led_position)
        
        # Check for scoring (both manual and auto)
        new_score, target_hit = game_state.button_handler.handle_keypress(
            led_position, game_state.score, current_time)
        if new_score != game_state.score:
            game_state.update_score(new_score, current_time, target_hit, beat_float)
        
        # Update and draw trail
        game_state.led_trail.update(led_position)
        for pos in game_state.led_trail.positions:
            distance_to_zero = min(pos, NUMBER_OF_LEDS - pos)
            base_color = get_cyan_color(distance_to_zero)
            trail_fade = (game_state.led_trail.positions.index(pos) + 1) / len(game_state.led_trail.positions)
            fade_factor = get_fade_factor(game_state.score) * trail_fade
            faded_color = Color(
                int(base_color[0] * fade_factor),
                int(base_color[1] * fade_factor),
                int(base_color[2] * fade_factor),
                base_color[3]
            )
            display.set_pixel(pos, faded_color)
        
        # Draw score lines with flash effect (only in Pygame mode)
        if not IS_RASPBERRY_PI:
            flash_intensity = game_state.get_score_flash_intensity(beat_float)
            draw_score_lines(display.pygame_surface, game_state.score, current_time, flash_intensity, game_state.last_hit_target)
        
        # Draw current LED
        distance_to_zero = min(led_position, NUMBER_OF_LEDS - led_position)
        base_color = get_cyan_color(distance_to_zero)
        led_color = get_led_color(base_color, led_position)
        display.set_pixel(led_position, led_color)

        # Handle input (only for quit)
        for key, keydown in get_keyboard_input():
            if key == "quit":
                if IS_RASPBERRY_PI:
                    display.clear()
                    display.update()
                return

        # Update display
        display.update()
        await clock.tick(30)

async def main() -> None:
    """Initialize and run the game with MQTT support."""
    async with aiomqtt.Client(MQTT_SERVER) as subscribe_client:
        await subscribe_client.subscribe("#")
        subscribe_task = asyncio.create_task(
            trigger_events_from_mqtt(subscribe_client),
            name="mqtt subscribe handler")

        await run_game()
        subscribe_task.cancel()
        pygame.quit()

if __name__ == "__main__":
    pygame.init()
    asyncio.run(main())
