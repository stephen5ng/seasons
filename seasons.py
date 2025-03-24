#!/usr/bin/env python

import aiomqtt
import asyncio
import easing_functions
from functools import reduce
import math
import os
from PIL import Image, ImageDraw
import platform
import pygame
import pygame.gfxdraw
from pygame import Color
import pygame.freetype
from pyvidplayer2 import Video
import re
import string
import sys
import textrect
from typing import Callable

from pygameasync import Clock
from get_key import get_key
import my_inputs
import hub75

SCALING_FACTOR = 9
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 96

MQTT_SERVER = os.environ.get("MQTT_SERVER", "localhost")

quit_app = False

async def trigger_events_from_mqtt(subscribe_client: aiomqtt.Client):
    global quit_app
    async for message in subscribe_client.messages:
        if message.topic.matches("password_game/quit"):
            quit_app = True

async def run_game():
    global quit_app

    clock = Clock()
    display_surface = pygame.display.set_mode(
       (SCREEN_WIDTH*SCALING_FACTOR, SCREEN_HEIGHT*SCALING_FACTOR))
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), flags=pygame.SRCALPHA)
    screen = screen.convert_alpha()
    current_position = 0
    last_direction = 0
    start_movement = 0
    angle = 0
    last_led = 25
    ease = easing_functions.ExponentialEaseInOut(start=1, end=last_led, duration=1)
    start_ticks = pygame.time.get_ticks()
    pygame.mixer.music.load("music/Rise Up.wav")
    pygame.mixer.music.play()
    beat_per_ms = 13.0/6000.0
    last_beat_in_measure = 0
    measure = 0
    beats_per_measure = 8
    while True:
        duration_ms = pygame.time.get_ticks() - start_ticks
        beat_float = duration_ms * beat_per_ms
        beat = int(beat_float)
        beat_in_measure = beat % beats_per_measure
        fractional_beat = beat_float % 1
        if beat_in_measure != last_beat_in_measure:
            last_beat_in_measure = beat_in_measure
            if beat_in_measure == 0:
                pygame.mixer.music.play()
                print(f"{beat_in_measure} {beat} looping music")
            # print(f"{beat} {beat} {pygame.mixer.music.get_pos()} {duration_ms}")

        pygame.draw.line(screen, Color("orange"), (0, 0), (128, 0))
        for i in range(40):
            pygame.draw.circle(screen, Color("red"), (i*5, 8), 2)
        percent_of_measure = (fractional_beat / beats_per_measure) + (beat_in_measure / beats_per_measure)
        x = int(ease(percent_of_measure))
        x = int(percent_of_measure*last_led)
        # print(f"easing {percent_of_measure} {x}")
        pygame.draw.circle(screen, Color("blue"), (x*5, 8), 2)
        for key, keydown in get_key():
            # print(f"{key}, {keydown} {x}")
            if keydown:
                if x >= 24 or x <= 0:
                    print("hit!")
            elif not keydown:
                last_direction = 0
            if key == "quit":
                return

            current_position += last_direction
            current_position = min(current_position, 100)
            current_position = max(current_position, 0)
        hub75.update(screen)
        pygame.transform.scale(screen,
        display_surface.get_rect().size, dest_surface=display_surface)
        pygame.display.update()
        # await clock.tick(30) 

async def main():
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
