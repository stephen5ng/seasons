"""Button handling utilities for the rhythm game."""

from typing import Dict, List, Optional, Tuple, Callable, Any
import pygame
from pygame import Color

# Import only the enum and colors, but not the position constants
from game_constants import TARGET_COLORS, TargetType

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
    INTERESTING_KEYS = [pygame.K_r, pygame.K_b, pygame.K_g, pygame.K_y,
                        pygame.K_UP, pygame.K_DOWN, pygame.K_RIGHT, pygame.K_LEFT]
    def __init__(self, error_sound: pygame.mixer.Sound,
                number_of_leds: int = 80, target_window_size: int = 4,
                auto_score: bool = False) -> None:
        """Initialize the button handler.
        
        Args:
            error_sound: Sound to play when an error occurs
            number_of_leds: Number of LEDs in the strip (default: 80)
            target_window_size: Size of target windows (default: 4)
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
        if auto_score:
            self.target_window_size = 0
        # Store LED configuration
        self.number_of_leds = number_of_leds
        self.target_window_size = target_window_size
        
        # Calculate target positions using percentages
        self.red_target_pos = 0
        self.blue_target_pos = int(number_of_leds * self.BLUE_TARGET_PERCENT)
        self.green_target_pos = int(number_of_leds * self.GREEN_TARGET_PERCENT)
        self.yellow_target_pos = int(number_of_leds * self.YELLOW_TARGET_PERCENT)
    
        self.last_target_type = TargetType.RED
        
    def is_in_valid_window(self, led_position: int) -> bool:
        """Check if the current LED position is in a valid window for scoring.
        
        Args:
            led_position: Current LED position
            
        Returns:
            True if the position is in a valid scoring window
        """
        return self.get_target_type(led_position) is not None
    
    def missed_target(self) -> bool:
        """Apply penalty if button wasn't pressed in valid window.
        
        Args:
            score: Current score
            
        Returns:
            Updated score after penalty
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
        target_type = ButtonHandler.get_target_type_for_position(
            position,
            self.number_of_leds,
            self.target_window_size,
            self.blue_target_pos,
            self.green_target_pos,
            self.yellow_target_pos
        )
        if target_type:
            self.last_target_type = target_type
        return target_type

    def handle_keypress(self, led_position: int) -> Tuple[Optional[bool], Optional[TargetType]]:
        """Handle keypress and update score if in valid window with correct key.
        
        Args:
            led_position: Current LED position
            
        Returns:
            Tuple of (successful_hit, target_hit) where:
            - successful_hit: True if correct key was pressed, False otherwise
            - target_hit: The target type that was hit, or None if no target
        """
        target_type: Optional[TargetType] = self.get_target_type(led_position)        
        
        all_pressed_keys = pygame.key.get_pressed()
        keys_pressed = []
        for key in ButtonHandler.INTERESTING_KEYS:
            if all_pressed_keys[key]:
                keys_pressed.append(key)
        
        target_keys = ButtonHandler.get_keys_for_target(target_type)
        # print(f"target_keys: {target_keys}")
        good_key_pressed = False
        for key_pressed in keys_pressed:
            # print(key_pressed)
            if key_pressed in target_keys:
                if not self.button_states[target_type]:
                    self.button_states[target_type] = True
                    self.penalty_applied = False
                    good_key_pressed = True
                    # print(f"good key: {key_pressed}")
            else:
                # print(f"wrong key: {key_pressed}")
                # print(f"looking for: {target_keys} for target: {target_type}")
                self.error_sound.play()

        if good_key_pressed:
            return True, target_type
        return None, None
    
    def get_window_position_for_target(self, target_type: TargetType) -> int:
        """Get the center position of a target window.
        
        Args:
            target_type: Target type to get position for
            
        Returns:
            Center position of the target window
        """
        if target_type == TargetType.RED:
            return self.red_target_pos
        elif target_type == TargetType.BLUE:
            return self.blue_target_pos
        elif target_type == TargetType.GREEN:
            return self.green_target_pos
        else:  # YELLOW
            return self.yellow_target_pos
    
    @staticmethod
    def calculate_penalty_score(score: float) -> float:
        """Calculate score after applying a penalty.
        
        Args:
            score: Current score
            
        Returns:
            Score after penalty
        """
        return max(0, score - 0.25)
    
    @staticmethod
    def get_target_type_for_position(position: int, led_count: int, window_size: int,
                                    mid_pos: float, right_pos: float, left_pos: float) -> Optional[TargetType]:
        """Determine which target window the position is in, if any.
        
        Args:
            position: LED position to check
            led_count: Total number of LEDs
            window_size: Size of the target window
            mid_pos: Middle target position
            right_pos: Right target position
            left_pos: Left target position
            
        Returns:
            TargetType if position is in a target window, None otherwise
        """
        # Convert position to percentage around the ring (0-1)
        position_percent = position / led_count
        
        # Calculate window size as percentage
        window_percent = window_size / led_count
        
        # Check if position is near a target, with wrapping for the red target
        if (position_percent <= window_percent or 
            position_percent >= (1.0 - window_percent)):
            return TargetType.RED
        elif abs(position_percent - ButtonHandler.BLUE_TARGET_PERCENT) <= window_percent:
            return TargetType.BLUE
        elif abs(position_percent - ButtonHandler.GREEN_TARGET_PERCENT) <= window_percent:
            return TargetType.GREEN
        elif abs(position_percent - ButtonHandler.YELLOW_TARGET_PERCENT) <= window_percent:
            return TargetType.YELLOW
        return None
    
    @staticmethod
    def get_keys_for_target(target_type: TargetType) -> List[int]:
        """Get the keyboard keys associated with a target type.
        
        Args:
            target_type: Target type to get keys for
            
        Returns:
            List of key codes for the target
        """
        if target_type == TargetType.RED:
            return [pygame.K_r, pygame.K_UP]
        if target_type == TargetType.BLUE:
            return [pygame.K_b, pygame.K_DOWN]
        if target_type == TargetType.GREEN:
            return [pygame.K_g, pygame.K_RIGHT]
        if target_type == TargetType.YELLOW:
            return [pygame.K_y, pygame.K_LEFT]
        
        return []
        
