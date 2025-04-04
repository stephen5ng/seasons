#!/usr/bin/env python

import asyncio
import math
import os
import platform
from typing import Optional

import aiomqtt
import easing_functions
import pygame
from pygame import Color
from pygameasync import Clock

from get_key import get_key
import hub75
import my_inputs

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

# LED display constants
NUMBER_OF_LEDS = 40
HIT_DURATION_MS = 500  # How long to show the green LED after a hit
FADE_THRESHOLD = 5  # Number of LEDs before zero to start fading
MIN_BLUE = 128  # Minimum blue value for LED color
MAX_BLUE = 255  # Maximum blue value for LED color

# Fade effect constants
MIN_FADE_FACTOR = 0.95   # Minimum fade factor (fastest fade)
MAX_FADE_FACTOR = 0.98   # Maximum fade factor (slowest fade)
FADE_SCORE_SCALE = 10.0  # Score at which fade factor reaches maximum

# Score display constants
HIGH_SCORE_THRESHOLD = 5  # Score threshold for exciting effects
COLOR_CYCLE_SPEED = 2000  # Time in ms for one complete color cycle
SCORE_LINE_COLOR = Color("green")
SCORE_LINE_SPACING = 2  # Pixels between score lines
SCORE_LINE_HEIGHT = 1  # Height of each score line

# MQTT settings
MQTT_SERVER = os.environ.get("MQTT_SERVER", "localhost")

# Create easing functions once
BLUE_EASE = easing_functions.ExponentialEaseInOut(start=0, end=1, duration=1)

# Global state
quit_app = False

class ButtonPressHandler:
    """Handles button press logic and scoring."""
    
    def __init__(self) -> None:
        self.button_pressed: bool = False
        self.penalty_applied: bool = False
        self.round_active: bool = False
    
    def is_in_valid_window(self, beat_position: int) -> bool:
        """Check if the current beat position is in a valid window for scoring."""
        return beat_position >= NUMBER_OF_LEDS - 2 or beat_position <= 2
    
    def apply_penalty(self, score: float) -> float:
        """Apply penalty if button wasn't pressed in valid window."""
        if not self.button_pressed and not self.penalty_applied:
            score /= 2
            self.penalty_applied = True
        return score
    
    def reset_flags(self, beat_position: int) -> None:
        """Reset state flags based on beat position."""
        if self.is_in_valid_window(beat_position) and not self.round_active:
            self.button_pressed = False
            self.penalty_applied = False
            self.round_active = True  # Start a new scoring round
        elif not self.is_in_valid_window(beat_position):
            self.round_active = False  # End the current scoring round
    
    def handle_keypress(self, beat_position: int, score: float) -> float:
        """Handle keypress and update score if in valid window."""
        if self.is_in_valid_window(beat_position) and not self.button_pressed:
            score += 1
            self.button_pressed = True
            self.penalty_applied = False
        return score

async def trigger_events_from_mqtt(subscribe_client: aiomqtt.Client) -> None:
    """Handle MQTT events for game control."""
    global quit_app
    async for message in subscribe_client.messages:
        if message.topic.matches("password_game/quit"):
            quit_app = True

def get_led_position(i: int) -> tuple[int, int]:
    """Convert LED index to x,y coordinates in a circular pattern, starting at 12 o'clock."""
    angle = 3 * math.pi / 2 + (2 * math.pi * i) / NUMBER_OF_LEDS
    x = CIRCLE_CENTER_X + int(CIRCLE_RADIUS * math.cos(angle))
    y = CIRCLE_CENTER_Y + int(CIRCLE_RADIUS * math.sin(angle))
    return (x, y)

def draw_led(screen: pygame.Surface, i: int, color: Color) -> None:
    """Draw an LED at position i in a circular pattern."""
    screen.set_at(get_led_position(i), color)

def get_fade_factor(score: float) -> float:
    """Calculate fade factor based on current score.
    As score increases, fade factor increases (slower fade)."""
    normalized_score = min(score / FADE_SCORE_SCALE, 1.0)
    return MIN_FADE_FACTOR + normalized_score * (MAX_FADE_FACTOR - MIN_FADE_FACTOR)

def fade_led(screen: pygame.Surface, i: int, score: float) -> None:
    """Fade the LED at position i by reducing its RGB values by a score-dependent factor."""
    c = screen.get_at(get_led_position(i))
    fade_factor = get_fade_factor(score)
    faded_color = Color(
        int(c[0] * fade_factor),  # Red
        int(c[1] * fade_factor),  # Green
        int(c[2] * fade_factor),  # Blue
        c[3]                      # Alpha (unchanged)
    )
    screen.set_at(get_led_position(i), faded_color)

def get_blue_color(position: int) -> Color:
    """Calculate blue color intensity based on position relative to zero.
    Creates a smooth symmetric fade in and out effect using easing."""
    if position >= FADE_THRESHOLD:
        return Color(0, 0, MIN_BLUE)  # Dark blue
    
    normalized_pos = position / FADE_THRESHOLD
    intensity = BLUE_EASE(normalized_pos)
    blue_value = int(MIN_BLUE + (MAX_BLUE - MIN_BLUE) * (1 - intensity))
    return Color(0, 0, blue_value)

def get_rainbow_color(time_ms: int, line_index: int) -> Color:
    """Generate a rainbow color based on time and line position."""
    # Offset each line's hue by its position for a wave effect
    hue = (time_ms / COLOR_CYCLE_SPEED + line_index * 0.1) % 1.0
    
    # Convert HSV to RGB (simplified conversion)
    if hue < 1/6:  # Red to Yellow
        r = 255
        g = int(255 * (hue * 6))
        b = 0
    elif hue < 2/6:  # Yellow to Green
        r = int(255 * (2 - hue * 6))
        g = 255
        b = 0
    elif hue < 3/6:  # Green to Cyan
        r = 0
        g = 255
        b = int(255 * (hue * 6 - 2))
    elif hue < 4/6:  # Cyan to Blue
        r = 0
        g = int(255 * (4 - hue * 6))
        b = 255
    elif hue < 5/6:  # Blue to Magenta
        r = int(255 * (hue * 6 - 4))
        g = 0
        b = 255
    else:  # Magenta to Red
        r = 255
        g = 0
        b = int(255 * (6 - hue * 6))
    
    return Color(r, g, b)

def draw_score_lines(screen: pygame.Surface, score: float, current_time: int) -> None:
    """Draw horizontal lines from the bottom of the screen to represent the score.
    Each line represents one point. Above HIGH_SCORE_THRESHOLD, lines flash with rainbow colors."""
    num_lines = int(score)
    
    for i in range(num_lines):
        y = SCREEN_HEIGHT - 1 - (i * (SCORE_LINE_HEIGHT + SCORE_LINE_SPACING))
        if y >= 0:  # Only draw if we haven't gone off the top of the screen
            line_color = get_rainbow_color(current_time, i) if score > HIGH_SCORE_THRESHOLD else SCORE_LINE_COLOR
            pygame.draw.line(screen, line_color, (0, y), (SCREEN_WIDTH - 1, y))

async def run_game() -> None:
    """Main game loop handling display, input, and game logic."""
    global quit_app

    # Initialize display
    clock = Clock()
    display_surface = pygame.display.set_mode(
        (SCREEN_WIDTH * SCALING_FACTOR, SCREEN_HEIGHT * SCALING_FACTOR))
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), flags=pygame.SRCALPHA)
    screen = screen.convert_alpha()
    
    # Initialize game state
    start_ticks = pygame.time.get_ticks()
    last_beat_in_measure = 0
    score = 0
    next_loop = 1
    loop_count = 0
    button_press_handler = ButtonPressHandler()

    # Initialize music
    pygame.mixer.music.load("music/Rise Up.mp3")
    pygame.mixer.music.play(start=0)

    while True:
        screen.fill((0, 0, 0))

        # Calculate beat timing
        duration_ms = pygame.time.get_ticks() - start_ticks
        beat_float = duration_ms * BEAT_PER_MS
        beat = int(beat_float)
        beat_in_measure = beat % BEATS_PER_MEASURE
        if beat_in_measure == 0:
            beat_start_time = pygame.time.get_ticks()
        fractional_beat = beat_float % 1

        # Handle music looping
        if beat_in_measure != last_beat_in_measure:
            last_beat_in_measure = beat_in_measure
            if beat_in_measure == 0:
                # Calculate the offset into the current measure
                current_time = pygame.time.get_ticks()
                measure_offset = (current_time - beat_start_time) / 1000.0
                start_time = score * SECONDS_PER_MEASURE + measure_offset
                pygame.mixer.music.play(start=start_time)

        # Calculate beat position
        percent_of_measure = (fractional_beat / BEATS_PER_MEASURE) + (beat_in_measure / BEATS_PER_MEASURE)
        beat_position = int(percent_of_measure * NUMBER_OF_LEDS)
        
        # Handle loop counting
        if percent_of_measure < 0.5:
            if loop_count != next_loop:
                loop_count = next_loop
        elif next_loop == loop_count:
            next_loop = loop_count + 1
                
        # Handle scoring and penalties
        if not button_press_handler.is_in_valid_window(beat_position):
            new_score = button_press_handler.apply_penalty(score)
            if new_score != score:
                score = new_score
        button_press_handler.reset_flags(beat_position)
        
        # Draw game elements
        for i in range(NUMBER_OF_LEDS):
            fade_led(screen, i, score)
        
        # Draw score lines
        current_time = pygame.time.get_ticks()
        draw_score_lines(screen, score, current_time)
        
        # Draw beat indicator
        distance_to_zero = min(beat_position, NUMBER_OF_LEDS - beat_position)
        draw_led(screen, beat_position, get_blue_color(distance_to_zero))

        # Handle input
        for key, keydown in get_key():
            if keydown:
                score = button_press_handler.handle_keypress(beat_position, score)
            if key == "quit":
                return

        # Update display
        hub75.update(screen)
        pygame.transform.scale(screen,
            display_surface.get_rect().size, dest_surface=display_surface)
        pygame.display.update()
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
    if platform.system() != "Darwin":
        my_inputs.get_key()

    hub75.init()
    pygame.init()

    asyncio.run(main())
