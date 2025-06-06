"""Game constants for the rhythm game."""

from enum import Enum, auto
from pygame import Color
import easing_functions

# Global game constants
NUMBER_OF_LEDS: int = 300
NUMBER_OF_VICTORY_LEDS: int = 150

ENDING_PHRASE = 21
AUTOPILOT_PHRASE = 17

# Target constants - will be calculated at runtime based on actual LED count
TARGET_WINDOW_PERCENT = 0.10

FIFTH_LINE_TARGET_MEASURES = [8, 10, 12, 14, 16, 18, 20, 22, 24, 32, 34]
FIFTH_LINE_TARGET_BUFFER_MEASURE = 2

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
DISPLAY_LED_OFFSET = 30  # Offset for LED positions
USE_SEPARATE_FIFTH_LINE_STRIP = False  # Whether to use a separate strip for the fifth line

# Hit trail settings
INITIAL_HIT_SPACING = 16  # Initial spacing between hit trail LEDs
HIT_TRAIL_RADIUS = CIRCLE_RADIUS - 4  # Radius for hit trail (inner circle)
TARGET_TRAIL_RADIUS = CIRCLE_RADIUS + 4  # Radius for target trail (outer circle)

# Game timing constants
BEATS_PER_MEASURE = 4
BEATS_PER_PHRASE = 8
BEAT_PER_MS = 13.0 / 6000.0
SECONDS_PER_PHRASE = 3.692166666

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
QUAD_HOSTNAME = "seasons-quad.local"

# LED strip configuration
LED_PIN = 18  # GPIO pin connected to the pixels (must support PWM)
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10  # DMA channel to use for generating signal
LED_BRIGHTNESS = 128  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0  # PWM channel

# Target type enum
class TargetType(Enum):
    """Enum representing different target types in the game.
    
    The order of declaration determines the cycling order when using next().
    RED -> BLUE -> GREEN -> YELLOW -> RED
    """
    RED = 0
    GREEN = 1
    BLUE = 2
    YELLOW = 3
    
    def next(self) -> 'TargetType':
        """Get the next target type in the cycle.
        
        Returns:
            The next TargetType in the cycle, wrapping back to RED after YELLOW
        """
        # Get list of all target types in order
        types = list(TargetType)
        # Find current index
        current_idx = types.index(self)
        # Return next type, wrapping around to start
        return types[(current_idx + 1) % len(types)]

# Target colors
TARGET_COLORS = {
    TargetType.RED: Color(255, 0, 0),
    TargetType.BLUE: Color(0, 0, 255),
    TargetType.GREEN: Color(0, 255, 0),
    TargetType.YELLOW: Color(255, 255, 0)
}
