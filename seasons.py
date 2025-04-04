#!/usr/bin/env python

import asyncio
import math
import os
import platform
from typing import List, Optional, Tuple

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
MIN_CYAN = 128  # Minimum cyan value for LED color
MAX_CYAN = 255  # Maximum cyan value for LED color

# Fade effect constants
MIN_FADE_FACTOR = 0.95   # Minimum fade factor (fastest fade)
MAX_FADE_FACTOR = 0.98   # Maximum fade factor (slowest fade)
FADE_SCORE_SCALE = 10.0  # Score at which fade factor reaches maximum
TRAIL_LENGTH = 8  # Number of previous positions to remember

# Score display constants
HIGH_SCORE_THRESHOLD = 5  # Score threshold for exciting effects
COLOR_CYCLE_SPEED = 2000  # Time in ms for one complete color cycle
SCORE_LINE_COLOR = Color("green")
SCORE_LINE_SPACING = 2  # Pixels between score lines
SCORE_LINE_HEIGHT = 1  # Height of each score line

# MQTT settings
MQTT_SERVER = os.environ.get("MQTT_SERVER", "localhost")

# Create easing functions once
CYAN_EASE = easing_functions.ExponentialEaseInOut(start=0, end=1, duration=1)

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

class GameState:
    """Manages game state and timing."""
    
    def __init__(self) -> None:
        self.start_ticks = pygame.time.get_ticks()
        self.last_beat_in_measure = 0
        self.score = 0
        self.next_loop = 1
        self.loop_count = 0
        self.button_handler = ButtonPressHandler()
        self.led_trail = LEDTrail(TRAIL_LENGTH)
        self.beat_start_time = 0
    
    def update_timing(self) -> Tuple[int, int, float, float]:
        """Calculate current timing values."""
        duration_ms = pygame.time.get_ticks() - self.start_ticks
        beat_float = duration_ms * BEAT_PER_MS
        beat = int(beat_float)
        beat_in_measure = beat % BEATS_PER_MEASURE
        fractional_beat = beat_float % 1
        
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
                start_time = self.score * SECONDS_PER_MEASURE + measure_offset
                pygame.mixer.music.play(start=start_time)

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

def draw_score_lines(screen: pygame.Surface, score: float, current_time: int) -> None:
    """Draw horizontal lines representing the score."""
    num_lines = int(score)
    for i in range(num_lines):
        y = SCREEN_HEIGHT - 1 - (i * (SCORE_LINE_HEIGHT + SCORE_LINE_SPACING))
        if y >= 0:  # Only draw if we haven't gone off the top of the screen
            line_color = get_rainbow_color(current_time, i) if score > HIGH_SCORE_THRESHOLD else SCORE_LINE_COLOR
            pygame.draw.line(screen, line_color, (0, y), (SCREEN_WIDTH - 1, y))

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
    display_surface = pygame.display.set_mode(
        (SCREEN_WIDTH * SCALING_FACTOR, SCREEN_HEIGHT * SCALING_FACTOR))
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), flags=pygame.SRCALPHA)
    screen = screen.convert_alpha()
    
    # Initialize game state
    game_state = GameState()
    
    # Initialize music
    pygame.mixer.music.load("music/Rise Up.mp3")
    pygame.mixer.music.play(start=0)

    while True:
        screen.fill((0, 0, 0))

        # Update timing and music
        beat, beat_in_measure, beat_float, fractional_beat = game_state.update_timing()
        game_state.handle_music_loop(beat_in_measure)

        # Calculate beat position
        percent_of_measure = (fractional_beat / BEATS_PER_MEASURE) + (beat_in_measure / BEATS_PER_MEASURE)
        beat_position = int(percent_of_measure * NUMBER_OF_LEDS)
        
        # Handle loop counting
        if percent_of_measure < 0.5:
            if game_state.loop_count != game_state.next_loop:
                game_state.loop_count = game_state.next_loop
        elif game_state.next_loop == game_state.loop_count:
            game_state.next_loop = game_state.loop_count + 1
                
        # Handle scoring and penalties
        if not game_state.button_handler.is_in_valid_window(beat_position):
            new_score = game_state.button_handler.apply_penalty(game_state.score)
            if new_score != game_state.score:
                game_state.score = new_score
        game_state.button_handler.reset_flags(beat_position)
        
        # Update and draw trail
        game_state.led_trail.update(beat_position)
        game_state.led_trail.draw(screen, game_state.score)
        
        # Draw score lines
        current_time = pygame.time.get_ticks()
        draw_score_lines(screen, game_state.score, current_time)
        
        # Draw current beat position
        distance_to_zero = min(beat_position, NUMBER_OF_LEDS - beat_position)
        draw_led(screen, beat_position, get_cyan_color(distance_to_zero))

        # Handle input
        for key, keydown in get_key():
            if keydown:
                game_state.score = game_state.button_handler.handle_keypress(
                    beat_position, game_state.score)
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
