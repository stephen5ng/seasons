import my_inputs
import platform
import pygame
import sys

shifted = {
   "`": "~",
   "1": "!",
   "2": "@",
   "3": "#",
   "4": "$",
   "5": "%",
   "6": "^",
   "7": "&",
   "8": "*",
   "9": "(",
   "0": ")",
   "-": "_",
   "=": "+",
   "[": "{",
   "]": "}",
   "\\": "|",
   ",": "<",
   ".": ">",
   "/": "?"
}

NAMES_TO_KEYS = {
    "SPACE": " ",
    "GRAVE": "`",
    "LEFTBRACE": "{",
    "RIGHTBRACE": "}",
    "SEMICOLON": ";",
    "APOSTROPHE": "'",
    "COMMA": ",",
    "DOT": ".",
    "SLASH": "/",
    "ESC": "escape"
}

is_shifted = False
def get_key():
    global is_shifted

    def handle_shift(is_shifted, key):
        if key.isalpha():
            return key.upper() if is_shifted else key.lower()

        if is_shifted and key in shifted.keys():
            return shifted[key]

        return key

    if platform.system() != "Darwin":
        events = my_inputs.get_key()
        if not events:
            return
        for event in events:
            if event.ev_type == "Key":
                key = event.code[4:]
                if key in NAMES_TO_KEYS.keys():
                    key = NAMES_TO_KEYS[key]

                if "SHIFT" in key:
                    is_shifted = False if event.state == 0 else True
                elif event.state:
                    if len(key) == 1:
                        yield handle_shift(is_shifted, key)
                    else:
                        yield key.lower()
        return

    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
            is_shifted = 0 != pygame.key.get_mods() & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT)
            key = pygame.key.name(event.key)
            if key.upper() in NAMES_TO_KEYS.keys():
                key = NAMES_TO_KEYS[key.upper()]
            if len(key) == 1:
                # print(f"shifted: {is_shifted} K: {key} alpha: {key.isalpha()}")
                yield handle_shift(is_shifted, key), event.type == pygame.KEYDOWN
            else:
                yield key, event.type == pygame.KEYDOWN
        elif event.type == pygame.QUIT:
            yield "quit", True
