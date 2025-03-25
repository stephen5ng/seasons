#!/usr/bin/env python

import asyncio
import os
import platform
from typing import Optional
import math

import aiomqtt
import easing_functions
import pygame
import pygame.gfxdraw
from pygame import Color
from pygameasync import Clock

from get_key import get_key
import hub75
import my_inputs

# Constants
SCALING_FACTOR = 9
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 96
MQTT_SERVER = os.environ.get("MQTT_SERVER", "localhost")
BEATS_PER_MEASURE = 8
BEAT_PER_MS = 13.0 / 6000.0
LAST_LED = 25
NUMBER_OF_LEDS = 40
CIRCLE_RADIUS = 30
CIRCLE_CENTER_X = SCREEN_WIDTH // 2
CIRCLE_CENTER_Y = SCREEN_HEIGHT // 2
HIT_DURATION_MS = 500  # How long to show the green LED after a hit
FADE_THRESHOLD = 5  # Number of LEDs before zero to start fading
MIN_BLUE = 128  # Minimum blue value
MAX_BLUE = 255  # Maximum blue value
FADE_FACTOR = 0.95  # Factor to reduce RGB values by when fading LEDs

# Create easing function once
BLUE_EASE = easing_functions.ExponentialEaseInOut(start=0, end=1, duration=1)

# Global state
quit_app = False
class ButtonPressHandler:
    def __init__(self) -> None:
        self.button_pressed: bool = False
        self.penalty_applied: bool = False
        self.round_active: bool = False
    
    def is_in_valid_window(self, beat_position: int) -> bool:
        return beat_position >= NUMBER_OF_LEDS - 2 or beat_position <= 2
    
    def apply_penalty(self, score: float) -> float:
        if not self.button_pressed and not self.penalty_applied:
            score -= 0.5
            self.penalty_applied = True
        return score
    
    def reset_flags(self, beat_position: int) -> None:
        if self.is_in_valid_window(beat_position) and not self.round_active:
            self.button_pressed = False
            self.penalty_applied = False
            self.round_active = True  # Start a new scoring round
        elif not self.is_in_valid_window(beat_position):
            self.round_active = False  # End the current scoring round
    
    def handle_keypress(self, beat_position: int, score: float) -> float:
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
    """Convert LED index to x,y coordinates in a circular pattern."""
    angle = math.pi + (2 * math.pi * i) / NUMBER_OF_LEDS
    x = CIRCLE_CENTER_X + int(CIRCLE_RADIUS * math.cos(angle))
    y = CIRCLE_CENTER_Y + int(CIRCLE_RADIUS * math.sin(angle))
    return (x, y)

def draw_led(screen, i, color) -> None:
    screen.set_at(get_led_position(i), color)

def fade_led(screen, i) -> None:
    """Fade the LED at position i by reducing its RGB values by FADE_FACTOR."""
    c = screen.get_at(get_led_position(i))
    faded_color = Color(
        int(c[0] * FADE_FACTOR),  # Red
        int(c[1] * FADE_FACTOR),  # Green
        int(c[2] * FADE_FACTOR),  # Blue
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

def draw_vertical_line(screen) -> None:
    """Draw a vertical line on the right side of the screen."""
    for y in range(SCREEN_HEIGHT):
        screen.set_at((SCREEN_WIDTH - 1, y), Color("white"))

def trigger_window(beat_position: int) -> bool:
    """Return True if the beat position is within the trigger window."""
    return beat_position >= NUMBER_OF_LEDS - 2 or beat_position <= 2

async def run_game() -> None:
    """Main game loop handling display, input, and game logic."""
    global quit_app

    clock = Clock()
    display_surface = pygame.display.set_mode(
        (SCREEN_WIDTH * SCALING_FACTOR, SCREEN_HEIGHT * SCALING_FACTOR))
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), flags=pygame.SRCALPHA)
    screen = screen.convert_alpha()
    
    # Game state
    angle = 0
    ease = easing_functions.ExponentialEaseInOut(start=1, end=LAST_LED, duration=1)
    start_ticks = pygame.time.get_ticks()
    last_beat_in_measure = 0
    hit_time = 0  # Track when the last hit occurred
    
    # Initialize music
    pygame.mixer.music.load("music/Rise Up.wav")
    pygame.mixer.music.play()
    score = 0
    next_loop = 1
    loop_count = 0
    triggered = False
    button_press_handler = ButtonPressHandler()
    while True:
        
        # Calculate beat timing
        duration_ms = pygame.time.get_ticks() - start_ticks
        beat_float = duration_ms * BEAT_PER_MS
        beat = int(beat_float)
        beat_in_measure = beat % BEATS_PER_MEASURE
        fractional_beat = beat_float % 1

        # Handle music looping
        if beat_in_measure != last_beat_in_measure:
            last_beat_in_measure = beat_in_measure
            if beat_in_measure == 0:
                pygame.mixer.music.play()

        # Draw game elements
        # Calculate and draw beat position
        percent_of_measure = (fractional_beat / BEATS_PER_MEASURE) + (beat_in_measure / BEATS_PER_MEASURE)
        beat_position = int(percent_of_measure * NUMBER_OF_LEDS)
        
        # Use a latch to count the number of loops
        if percent_of_measure < 0.5:
            if loop_count != next_loop:
                loop_count = next_loop
        elif next_loop == loop_count:
            next_loop = loop_count + 1
                
        if not button_press_handler.is_in_valid_window(beat_position):
            new_score = button_press_handler.apply_penalty(score)
            if new_score != score:
                score = new_score
                print(f"penalty score: {score}")
        button_press_handler.reset_flags(beat_position)
        
        in_trigger_window = trigger_window(beat_position)
        for i in range(NUMBER_OF_LEDS):
            fade_led(screen, i)
        
        # Draw vertical line
        draw_vertical_line(screen)
        
        # Check if we should show green LED (within hit duration)
        current_time = pygame.time.get_ticks()
        if False and current_time - hit_time < HIT_DURATION_MS:
            draw_led(screen, beat_position, Color("green"))
        else:
            distance_to_zero = min(beat_position, NUMBER_OF_LEDS - beat_position)
            draw_led(screen, beat_position, get_blue_color(distance_to_zero))

        # Handle input
        for key, keydown in get_key():
            if keydown:
                score = button_press_handler.handle_keypress(beat_position, score)
                print(f"hit score: {score}")
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
