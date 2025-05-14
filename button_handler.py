"""Button handling utilities for the rhythm game."""

from typing import Dict, List, Optional, Tuple, Callable, Any, Set, NamedTuple, Sequence
import pygame
from pygame import Color
import platform
import os

# Import only the enum and colors, but not the position constants
from game_constants import TARGET_COLORS, TargetType
from gpiozero import Button

# Check if we're on Raspberry Pi
IS_RASPBERRY_PI = platform.system() == "Linux" and os.uname().machine.startswith("aarch64")

class ButtonConfig(NamedTuple):
    """Configuration for a GPIO button.
    
    Attributes:
        pin: GPIO pin number
        key: Pygame key code to simulate
        target: Target type this button corresponds to
    """
    pin: int
    key: int
    target: TargetType

class ButtonHandler:
    """Handles button press logic and scoring.
    
    This class provides utilities for detecting button presses, determining if they are
    in the correct window, and updating the score accordingly.
    """
    
    # Target positions as percentages around the ring (0-1)
    RED_TARGET_PERCENT = 0.0      # 12 o'clock
    GREEN_TARGET_PERCENT = 0.25   # 3 o'clock
    BLUE_TARGET_PERCENT = 0.5     # 6 o'clock
    YELLOW_TARGET_PERCENT = 0.75  # 9 o'clock
    
    # GPIO button configuration
    BUTTON_CONFIGS = {
        TargetType.RED: ButtonConfig(17, pygame.K_UP, TargetType.RED),
        TargetType.BLUE: ButtonConfig(23, pygame.K_DOWN, TargetType.BLUE),
        TargetType.GREEN: ButtonConfig(24, pygame.K_RIGHT, TargetType.GREEN),
        TargetType.YELLOW: ButtonConfig(27, pygame.K_LEFT, TargetType.YELLOW)
    }
    
    # Static mapping of keys to target types for fast lookups
    KEY_TO_TARGET = {
        config.key: config.target
        for config in BUTTON_CONFIGS.values()
    }
    
    def __init__(self, error_sound: pygame.mixer.Sound,
                number_of_leds: int, target_window_size: int,
                auto_score: bool) -> None:
        """Initialize the button handler.
        
        Args:
            error_sound: Sound to play when an error occurs
            number_of_leds: Number of LEDs in the strip
            target_window_size: Size of target windows
            auto_score: When True, automatically scores on every round
        """
        self.button_states: Dict[TargetType, bool] = {
            TargetType.RED: False,
            TargetType.BLUE: False,
            TargetType.GREEN: False,
            TargetType.YELLOW: False
        }
        self.penalty_applied: bool = False
        self.round_active: bool = False
        self.error_sound: pygame.mixer.Sound = error_sound
        self.auto_score: bool = auto_score

        # Store LED configuration
        self.number_of_leds = number_of_leds
        self.target_window_size = target_window_size
        
        # Calculate and store target positions
        self.target_positions = {
            TargetType.RED: int(number_of_leds * self.RED_TARGET_PERCENT),
            TargetType.BLUE: int(number_of_leds * self.BLUE_TARGET_PERCENT),
            TargetType.GREEN: int(number_of_leds * self.GREEN_TARGET_PERCENT),
            TargetType.YELLOW: int(number_of_leds * self.YELLOW_TARGET_PERCENT)
        }
    
        self.last_target_type = TargetType.RED
        
        # Initialize GPIO buttons
        self.simulated_keys: Set[int] = set()
        self.gpio_buttons: Dict[int, Button] = {}
        
        # Only initialize GPIO buttons on Raspberry Pi
        if IS_RASPBERRY_PI:
            # Create buttons from configuration
            for target_type, config in self.BUTTON_CONFIGS.items():
                button = Button(config.pin)
                self.gpio_buttons[config.key] = button
    
    def set_window_size(self, window_size: int) -> None:
        """Update the window size for scoring.
        
        Args:
            window_size: New window size to use
        """
        self.target_window_size = window_size

    def is_in_valid_window(self, led_position: int) -> bool:
        """Check if the current LED position is in a valid window for scoring.
        
        Args:
            led_position: Current LED position
            
        Returns:
            True if the position is in a valid scoring window
        """
        return self.get_target_type(led_position) is not None
    
    def missed_target(self) -> Optional[TargetType]:
        """Apply penalty if button wasn't pressed in valid window.
        
        Returns:
            TargetType if a penalty was applied, None otherwise
        """
        if not self.button_states[self.last_target_type] and not self.penalty_applied:
            self.penalty_applied = True
            return self.last_target_type
        return None
    
    def reset_flags(self, led_position: int) -> None:
        """Reset state flags based on LED position.
        
        Args:
            led_position: Current LED position
        """
        if self.is_in_valid_window(led_position) and not self.round_active:
            self.button_states = {target: False for target in TargetType}
            self.penalty_applied = False
            self.round_active = True  # Start a new scoring round
        elif not self.is_in_valid_window(led_position):
            self.round_active = False  # End the current scoring round
    
    def get_target_type(self, position: int) -> Optional[TargetType]:
        """Determine which target window the position is in, if any.
        
        Args:
            position: LED position to check
            
        Returns:
            TargetType if position is in a target window, None otherwise
        """
        target_type = self.get_target_type_for_position(
            position,
            self.number_of_leds,
            self.target_window_size
        )
        if target_type:
            self.last_target_type = target_type
        return target_type

    def handle_keypress(self, led_position: int) -> Tuple[Sequence[TargetType], Sequence[TargetType]]:
        """Handle keypress and return sequences of hits and misses.
        
        Args:
            led_position: Current LED position
            
        Returns:
            Tuple of (hits, misses) where:
            - hits: Sequence of target types that were hit correctly
            - misses: Sequence of target types corresponding to incorrectly pressed keys
        """
        target_type: Optional[TargetType] = self.get_target_type_for_position(led_position, self.number_of_leds,
                                                                              1 if self.auto_score else self.target_window_size)        
        hits: List[TargetType] = []
        misses: List[TargetType] = []
        
        all_pressed_keys = pygame.key.get_pressed()
        keys_pressed = []
        for key in [config.key for config in self.BUTTON_CONFIGS.values()]:
            if all_pressed_keys[key]:
                keys_pressed.append(key)

        for k, v in self.gpio_buttons.items():
            if v.is_pressed:
                keys_pressed.append(k)
                print(f"{v.is_pressed}, {k}")

        if self.simulated_keys:
            print(f"gpio: {self.simulated_keys}")        

        keys_pressed.extend(self.simulated_keys)
            
        target_keys = ButtonHandler.get_keys_for_target(target_type) if target_type else []
        if target_type and self.auto_score:
            keys_pressed = [target_keys[0]]
                
        for key_pressed in keys_pressed:
            key_target = ButtonHandler.KEY_TO_TARGET.get(key_pressed)
            
            # print(f"key_pressed: {key_pressed}, target_keys: {target_keys}")
            if target_type and key_pressed in target_keys:
                if not self.button_states[target_type]:
                    self.button_states[target_type] = True
                    self.penalty_applied = False
                    hits.append(target_type)
            else:
                # self.error_sound.play()
                print(f"key_target: {key_target}")
                if key_target is not None:
                    print(f"miss: {key_target}")
                    misses.append(key_target)

        return hits, misses
    
    def get_target_type_for_position(self, position: int, led_count: int, window_size: int) -> Optional[TargetType]:
        """Determine which target window the position is in, if any.
        
        Args:
            position: LED position to check
            led_count: Total number of LEDs
            window_size: Size of the target window
            
        Returns:
            TargetType if position is in a target window, None otherwise
        """
        for target_type, target_pos in self.target_positions.items():
            if self.mod_distance(position, target_pos, led_count) <= window_size:
                return target_type
        return None
    
    @staticmethod
    def get_keys_for_target(target_type: TargetType) -> List[int]:
        """Get the keyboard keys associated with a target type.
        
        Args:
            target_type: Target type to get keys for
            
        Returns:
            List of key codes for the target
        """
        return [ButtonHandler.BUTTON_CONFIGS[target_type].key]
    
    @staticmethod
    def mod_distance(a, b, mod):
        return min((a - b) % mod, (b - a) % mod)
