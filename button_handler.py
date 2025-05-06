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
            self.target_window_size = 1
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
    
    def apply_penalty(self, score: float) -> float:
        """Apply penalty if button wasn't pressed in valid window.
        
        Args:
            score: Current score
            
        Returns:
            Updated score after penalty
        """
        if not any(self.button_states.values()) and not self.penalty_applied:
            score = ButtonHandler.calculate_penalty_score(score)
            self.penalty_applied = True
        return score
    
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

    def handle_keypress(self, led_position: int, current_time: int) -> Tuple[Optional[bool], Optional[TargetType]]:
        """Handle keypress and update score if in valid window with correct key.
        
        Args:
            led_position: Current LED position
            current_time: Current time in milliseconds
            
        Returns:
            Tuple of (successful_hit, target_hit) where:
            - successful_hit: True if correct key was pressed, False if wrong key, None if no key
            - target_hit: The target type that was hit, or None if no target
        """
        # Get the current keyboard state
        keys_pressed: Dict[int, bool] = pygame.key.get_pressed()
        
        target_type: Optional[TargetType] = self.get_target_type(led_position)        
        if not target_type:
            return None, target_type

        # Check for key presses outside their windows
        error_result = self._check_for_out_of_window_presses(keys_pressed, led_position)
        if error_result:
            return error_result
        

        # Check for wrong key presses in this window
        error_result = self._check_for_wrong_key_in_window(keys_pressed, target_type, led_position)
        if error_result:
            return error_result

        # Check for correct key press
        keys = ButtonHandler.get_keys_for_target(target_type)
        if (any(keys_pressed[key] for key in keys) or self.auto_score) and not self.button_states[target_type]:
            self.button_states[target_type] = True
            self.penalty_applied = False
            return True, target_type

        return None, target_type

    
    def _check_for_out_of_window_presses(self, keys_pressed: Dict[int, bool], led_position: int) -> Optional[Tuple[bool, TargetType]]:
        """Check for key presses outside their target windows.
        
        Args:
            keys_pressed: Dictionary of key states
            led_position: Current LED position
            
        Returns:
            Error result tuple if an out-of-window press is detected, None otherwise.
            The tuple contains (False, target_type)
        """
        for target_type in TargetType:
            keys = ButtonHandler.get_keys_for_target(target_type)
            if any(keys_pressed[key] for key in keys):
                window_pos = self.get_window_position_for_target(target_type)
                
                # If we're not in this key's window, show error and apply penalty
                if abs(led_position - window_pos) > self.target_window_size:
                    return self._create_error_feedback(target_type)
        return None

    def _check_for_wrong_key_in_window(self, keys_pressed: Dict[int, bool], correct_target: TargetType, 
                                     led_position: int) -> Optional[Tuple[bool, TargetType]]:
        """Check for wrong key presses in a target window.
        
        Args:
            keys_pressed: Dictionary of key states
            correct_target: The correct target type for this window
            led_position: Current LED position
            
        Returns:
            Error result tuple if a wrong key press is detected, None otherwise.
            The tuple contains (False, target_type)
        """
        for wrong_target in TargetType:
            if wrong_target != correct_target:
                wrong_keys = ButtonHandler.get_keys_for_target(wrong_target)
                
                if any(keys_pressed[key] for key in wrong_keys):
                    error_pos = self.get_window_position_for_target(wrong_target)
                    return self._create_error_feedback(wrong_target)
        return None

    def _create_error_feedback(self, target_type: TargetType) -> Tuple[bool, TargetType]:
        """Create error feedback for incorrect key presses.
        
        Args:
            target_type: The target type that was incorrectly pressed
            error_pos: The position where the error occurred
            
        Returns:
            Tuple containing (False, target_type)
        """
        self.error_sound.play()
        return False, target_type
    
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
        # Calculate score after 25% reduction
        reduced_score: float = score * 0.75
        # Make sure it's at least 0.25 less than original score
        reduced_score = min(reduced_score, score - 0.25)
        # Round to nearest 0.25 and ensure score doesn't go below 0
        return max(0, round(reduced_score * 4) / 4)
    
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
        elif target_type == TargetType.BLUE:
            return [pygame.K_b, pygame.K_DOWN]
        elif target_type == TargetType.GREEN:
            return [pygame.K_g, pygame.K_RIGHT]
        else:  # YELLOW
            return [pygame.K_y, pygame.K_LEFT]
