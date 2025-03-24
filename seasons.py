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
MIN_BLUE = 50  # Minimum blue value
MAX_BLUE = 255  # Maximum blue value

# Create easing function once
BLUE_EASE = easing_functions.ExponentialEaseInOut(start=0, end=1, duration=1)

# Global state
quit_app = False

async def trigger_events_from_mqtt(subscribe_client: aiomqtt.Client) -> None:
    """Handle MQTT events for game control."""
    global quit_app
    async for message in subscribe_client.messages:
        if message.topic.matches("password_game/quit"):
            quit_app = True

def draw_led(screen, i, color) -> None:
    """Draw an LED at position i in a circular pattern, starting at 180 degrees."""
    angle = math.pi + (2 * math.pi * i) / NUMBER_OF_LEDS
    x = CIRCLE_CENTER_X + int(CIRCLE_RADIUS * math.cos(angle))
    y = CIRCLE_CENTER_Y + int(CIRCLE_RADIUS * math.sin(angle))
    screen.set_at((x, y), color)
    
def get_blue_color(position: int) -> Color:
    """Calculate blue color intensity based on position relative to zero.
    Creates a smooth symmetric fade in and out effect using easing."""
    if position >= FADE_THRESHOLD:
        return Color(0, 0, MIN_BLUE)  # Dark blue
    
    normalized_pos = position / FADE_THRESHOLD
    intensity = BLUE_EASE(normalized_pos)
    
    blue_value = int(MIN_BLUE + (MAX_BLUE - MIN_BLUE) * (1 - intensity))
    return Color(0, 0, blue_value)

async def run_game() -> None:
    """Main game loop handling display, input, and game logic."""
    global quit_app

    clock = Clock()
    display_surface = pygame.display.set_mode(
        (SCREEN_WIDTH * SCALING_FACTOR, SCREEN_HEIGHT * SCALING_FACTOR))
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), flags=pygame.SRCALPHA)
    screen = screen.convert_alpha()
    
    # Game state
    current_position = 0
    last_direction = 0
    angle = 0
    ease = easing_functions.ExponentialEaseInOut(start=1, end=LAST_LED, duration=1)
    start_ticks = pygame.time.get_ticks()
    last_beat_in_measure = 0
    hit_time = 0  # Track when the last hit occurred
    
    # Initialize music
    pygame.mixer.music.load("music/Rise Up.wav")
    pygame.mixer.music.play()

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
        for i in range(NUMBER_OF_LEDS):
            draw_led(screen, i, Color("black"))
        
        # Calculate and draw beat position
        percent_of_measure = (fractional_beat / BEATS_PER_MEASURE) + (beat_in_measure / BEATS_PER_MEASURE)
        beat_position = int(percent_of_measure * NUMBER_OF_LEDS)
        
        # Check if we should show green LED (within hit duration)
        current_time = pygame.time.get_ticks()
        if current_time - hit_time < HIT_DURATION_MS:
            draw_led(screen, beat_position, Color("green"))
        else:
            distance_to_zero = min(beat_position, NUMBER_OF_LEDS - beat_position)
            print(f"beat_position: {beat_position}, distance_to_zero: {distance_to_zero}")
            draw_led(screen, beat_position, get_blue_color(distance_to_zero))

        # Handle input
        for key, keydown in get_key():
            if keydown:
                if beat_position >= NUMBER_OF_LEDS - 1 or beat_position <= 0:
                    print("hit!")
                    hit_time = current_time
            elif not keydown:
                last_direction = 0
            if key == "quit":
                return

            current_position += last_direction
            current_position = min(current_position, 100)
            current_position = max(current_position, 0)

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
