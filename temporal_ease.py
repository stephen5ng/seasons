from rpi_ws281x import PixelStrip, Color
from easing_functions import QuadEaseOut
import colorsys
import time

# --- Configuration ---
LED_COUNT = 60
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

TRAIL_FADE_DURATION_S = 1.5     # Time to fade out
MOVE_INTERVAL_S = 0.04          # Time between head movements
HUE_STEP = 3                  # Degrees hue changes per move

# --- Setup ---
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                   LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# --- State ---
lit_time_s = [None] * LED_COUNT
lit_hue = [None] * LED_COUNT

ease = QuadEaseOut(start=1.0, end=0.0, duration=TRAIL_FADE_DURATION_S)

head = 0
hue = 0
last_move_time_s = time.time()

while True:
    now_s = time.time()

    # Move head and light up
    if now_s - last_move_time_s >= MOVE_INTERVAL_S:
        lit_time_s[head] = now_s
        lit_hue[head] = hue
        head = (head + 1) % LED_COUNT
        hue = (hue + HUE_STEP) % 360
        last_move_time_s = now_s

    # Update LED colors
    for i in range(LED_COUNT):
        if lit_time_s[i] is None:
            strip.setPixelColor(i, Color(0, 0, 0))
            continue

        elapsed_s = now_s - lit_time_s[i]
        if elapsed_s > TRAIL_FADE_DURATION_S:
            lit_time_s[i] = None
            lit_hue[i] = None
            strip.setPixelColor(i, Color(0, 0, 0))
        else:
            brightness = ease.ease(elapsed_s)
            h = (lit_hue[i] % 360) / 360.0
            s = 1.0
            v = brightness
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            strip.setPixelColor(i, Color(int(r * 255), int(g * 255), int(b * 255)))

    strip.show()
    time.sleep(0.01)
