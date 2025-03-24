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

# Global state
quit_app = False

async def trigger_events_from_mqtt(subscribe_client: aiomqtt.Client) -> None:
    """Handle MQTT events for game control."""
    global quit_app
    async for message in subscribe_client.messages:
        if message.topic.matches("password_game/quit"):
            quit_app = True

def draw_led(screen, i, color) -> None:
    """Draw an LED at position i in a circular pattern."""
    angle = (2 * math.pi * i) / NUMBER_OF_LEDS
    x = CIRCLE_CENTER_X + int(CIRCLE_RADIUS * math.cos(angle))
    y = CIRCLE_CENTER_Y + int(CIRCLE_RADIUS * math.sin(angle))
    screen.set_at((x, y), color)
    
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
            draw_led(screen, i, Color("red"))
        
        # Calculate and draw beat position
        percent_of_measure = (fractional_beat / BEATS_PER_MEASURE) + (beat_in_measure / BEATS_PER_MEASURE)
        beat_position = int(percent_of_measure * NUMBER_OF_LEDS)
        draw_led(screen, beat_position, Color("blue"))

        # Handle input
        for key, keydown in get_key():
            if keydown:
                if beat_position >= NUMBER_OF_LEDS - 1 or beat_position <= 0:
                    print("hit!")
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
