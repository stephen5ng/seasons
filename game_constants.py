import easing_functions
from enum import Enum, auto
from pygame import Color

# Debug settings
ALWAYS_SCORE = True  # When True, automatically scores on every round

# Sound settings
ERROR_SOUND = "music/error.mp3"  # Path to error sound effect

# Hit trail settings
INITIAL_HIT_SPACING = 16  # Initial spacing between hit trail LEDs
HIT_TRAIL_RADIUS = 30 - 4  # CIRCLE_RADIUS - 4 (default; override if needed)
TARGET_TRAIL_RADIUS = 30 + 4  # CIRCLE_RADIUS + 4 (default; override if needed)
BONUS_TRAIL_RADIUS = 30 - 6  # HIT_TRAIL_RADIUS - 2 (default; override if needed)
BONUS_TRAIL_COLOR = Color(255, 165, 0)  # Orange color for bonus trail

class TargetType(Enum):
    RED = auto()
    BLUE = auto()
    GREEN = auto()
    YELLOW = auto()

# LED display constants (set these after parsing args in seasons.py)
NUMBER_OF_LEDS = 80  # Default; should be overwritten by seasons.py
TARGET_WINDOW_SIZE = NUMBER_OF_LEDS // 20
MID_TARGET_POS = NUMBER_OF_LEDS/2
RIGHT_TARGET_POS = NUMBER_OF_LEDS/4
LEFT_TARGET_POS = 3*NUMBER_OF_LEDS/4

TRAIL_FADE_DURATION_S = 0.8
TRAIL_EASE = easing_functions.CircularEaseOut(start=1.0, end=0.0, duration=TRAIL_FADE_DURATION_S)
BONUS_TRAIL_FADE_DURATION_S = 0.2
BONUS_TRAIL_EASE = easing_functions.CircularEaseOut(start=1.0, end=0.0, duration=BONUS_TRAIL_FADE_DURATION_S)

# Target colors
TARGET_COLORS = {
    TargetType.RED: Color(255, 0, 0),
    TargetType.BLUE: Color(0, 0, 255),
    TargetType.GREEN: Color(0, 255, 0),
    TargetType.YELLOW: Color(255, 255, 0)
}

# Score display constants
HIGH_SCORE_THRESHOLD = 5
COLOR_CYCLE_TIME_MS = 2000
SCORE_LINE_COLOR = Color("green")
SCORE_LINE_SPACING = 0.5
SCORE_LINE_HEIGHT = 0.5
SCORE_FLASH_DURATION_MS = 1000
SCORE_LINE_ANIMATION_TIME_MS = 100

SCORE_FLASH_EASE = easing_functions.ExponentialEaseOut(start=0, end=1, duration=1)
