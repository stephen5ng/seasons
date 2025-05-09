"""Game constants for the rhythm game."""

from enum import Enum, auto
from pygame import Color
import easing_functions

# Global game constants
NUMBER_OF_LEDS = 80  # Default number of LEDs - will be overridden by command line

# Target constants - will be calculated at runtime based on actual LED count
TARGET_WINDOW_PERCENT = 0.05

# Target positions as fixed percentages (clock positions)
RED_TARGET_PERCENT = 0.0    # 12 o'clock (0%)
GREEN_TARGET_PERCENT = 0.25 # 3 o'clock (25%)
BLUE_TARGET_PERCENT = 0.5   # 6 o'clock (50%)
YELLOW_TARGET_PERCENT = 0.75 # 9 o'clock (75%)

# Display constants
SCALING_FACTOR = 4
SCREEN_WIDTH = 192
SCREEN_HEIGHT = 192
CIRCLE_RADIUS = int(SCREEN_WIDTH * 0.3)  # 30% of screen width
CIRCLE_CENTER_X = SCREEN_WIDTH // 2
CIRCLE_CENTER_Y = SCREEN_HEIGHT // 2

# Sound settings
ERROR_SOUND = "music/error.mp3"  # Path to error sound effect

# Hit trail settings
INITIAL_HIT_SPACING = 16  # Initial spacing between hit trail LEDs
HIT_TRAIL_RADIUS = CIRCLE_RADIUS - 4  # Radius for hit trail (inner circle)
TARGET_TRAIL_RADIUS = CIRCLE_RADIUS + 4  # Radius for target trail (outer circle)

# Game timing constants
BEATS_PER_MEASURE = 4
BEATS_PER_PHRASE = 8
BEAT_PER_MS = 13.0 / 6000.0
SECONDS_PER_MEASURE_S = 3.7

# Trail settings
TRAIL_FADE_DURATION_S = 0.8  # Time for trail to fade out
TRAIL_EASE = easing_functions.CircularEaseOut(start=1.0, end=0.0, duration=TRAIL_FADE_DURATION_S)

# Score display constants
HIGH_SCORE_THRESHOLD = 5  # Score threshold for exciting effects
COLOR_CYCLE_TIME_MS = 2000  # Time in ms for one complete color cycle
SCORE_LINE_COLOR = Color("green")
SCORE_LINE_SPACING = 0.5  # Pixels between score lines
SCORE_LINE_HEIGHT = 0.5  # Height of each score line
SCORE_FLASH_DURATION_MS = 1000  # How long the score flash lasts
SCORE_LINE_ANIMATION_TIME_MS = 500  # How long the score line animation lasts

# WLED settings
WLED_IP = "192.168.0.121"
WLED_SETTINGS = {
    0: "FX=2&FP=67&SX=32",  # BREATHE / BLINK RED 
    4: "FX=54&FP=57&SX=48",  # CHASE 3 / CANDY
    8: "FX=19&FP=10&SX=255",  # DISSOLVE RND / FOREST
    12: "FX=66&FP=41&SX=128",  # FIRE 2012 / MAGRED
    16: "FX=9&FP=20&SX=128",  # RAINBOW / PASTEL
    20: "FX=92&FP=45&SX=192",  # SINELON / CLOUD
    24: "FX=13&FP=27&SX=96",  # SUNSET / SHERBET
    32: "FX=3&FP=43&SX=128",  # WIPE / YELBLU
    35: "FX=34&FP=19&SX=32",  # COLORFUL / TEMPERATURE
    38: "FX=108&FP=9&SX=128",  # SINE / OCEAN
    45: "FX=173&FP=34&SX=128",  # TARTAN / TERTIARY
    48: "FX=34&FP=19&SX=32",  # BREATHE / SPLASH
}

# Target type enum
class TargetType(Enum):
    RED = auto()
    BLUE = auto()
    GREEN = auto()
    YELLOW = auto()

# Target colors
TARGET_COLORS = {
    TargetType.RED: Color(255, 0, 0),
    TargetType.BLUE: Color(0, 0, 255),
    TargetType.GREEN: Color(0, 255, 0),
    TargetType.YELLOW: Color(255, 255, 0)
}
