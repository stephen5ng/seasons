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
    
    def __init__(self, error_sound: Optional[pygame.mixer.Sound] = None,
                number_of_leds: int = 80, target_window_size: int = 4,
                auto_score: bool = False) -> None:
        """Initialize the button handler.
        
        Args:
            error_sound: Sound to play when an error occurs
            number_of_leds: Number of LEDs in the strip (default: 80)
            target_window_size: Size of target windows (default: 4)
            auto_score: When True, automatically scores on every round
        """
        self.button_states: Dict[str, bool] = {
            "r": False,
            "b": False,
            "g": False,
            "y": False
        }
        self.penalty_applied: bool = False
        self.round_active: bool = False
        self.error_sound: Optional[pygame.mixer.Sound] = error_sound
        self.auto_score: bool = auto_score
        
        # Store LED configuration
        self.number_of_leds = number_of_leds
        self.target_window_size = target_window_size
        
        # Calculate target positions using percentages
        self.red_target_pos = 0
        self.blue_target_pos = int(number_of_leds * 0.5)   # 6 o'clock (50%)
        self.green_target_pos = int(number_of_leds * 0.25) # 3 o'clock (25%)
        self.yellow_target_pos = int(number_of_leds * 0.75) # 9 o'clock (75%)
    
    def is_in_valid_window(self, led_position: int) -> bool:
        """Check if the current LED position is in a valid window for scoring.
        
        Args:
            led_position: Current LED position
            
        Returns:
            True if the position is in a valid scoring window
        """
        return ButtonHandler.is_position_in_valid_window(led_position, self.number_of_leds, self.target_window_size, 
                                                       self.blue_target_pos, self.green_target_pos, self.yellow_target_pos)
    
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
            self.button_states = {k: False for k in self.button_states}
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
        return ButtonHandler.get_target_type_for_position(position, self.number_of_leds, self.target_window_size, 
                                                        self.blue_target_pos, self.green_target_pos, self.yellow_target_pos)

    def handle_keypress(self, led_position: int, score: float, current_time: int) -> Tuple[float, str, Optional[Tuple[int, Color]]]:
        """Handle keypress and update score if in valid window with correct key.
        
        Args:
            led_position: Current LED position
            score: Current score
            current_time: Current time in milliseconds
            
        Returns:
            Tuple of (updated_score, target_hit, error_feedback) where error_feedback is
            (error_position, error_color) if an error occurred, None otherwise
        """
        # Get the current keyboard state
        keys_pressed: Dict[int, bool] = pygame.key.get_pressed()
        
        # Check for key presses outside their windows
        error_result = self._check_for_out_of_window_presses(keys_pressed, led_position, score)
        if error_result:
            return error_result
        
        # Check for correct key presses in the target window
        target_type: Optional[TargetType] = self.get_target_type(led_position)
        if target_type:
            # Check for wrong key presses in this window
            error_result = self._check_for_wrong_key_in_window(keys_pressed, target_type, led_position, score)
            if error_result:
                return error_result
                
            # Check for correct key press
            keys = ButtonHandler.get_keys_for_target(target_type)
            if (any(keys_pressed[key] for key in keys) or self.auto_score) and not self.button_states[target_type.name[0].lower()]:
                self.button_states[target_type.name[0].lower()] = True
                self.penalty_applied = False
                return score + 0.25, target_type.name.lower(), None
        
        return score, "none", None
    
    def _check_for_out_of_window_presses(self, keys_pressed: Dict[int, bool], led_position: int, score: float) -> Optional[Tuple[float, str, Tuple[int, Color]]]:
        """Check for key presses outside their target windows.
        
        Args:
            keys_pressed: Dictionary of key states
            led_position: Current LED position
            score: Current score
            
        Returns:
            Error result tuple if an out-of-window press is detected, None otherwise
        """
        for target_type in TargetType:
            keys = ButtonHandler.get_keys_for_target(target_type)
            if any(keys_pressed[key] for key in keys):
                window_pos = self.get_window_position_for_target(target_type)
                
                # If we're not in this key's window, show error and apply penalty
                if abs(led_position - window_pos) > self.target_window_size:
                    if self.error_sound:
                        self.error_sound.play()
                    error_color: Color = TARGET_COLORS[target_type]
                    return max(0, score - 0.25), "none", (window_pos, error_color)
        return None
    
    def _check_for_wrong_key_in_window(self, keys_pressed: Dict[int, bool], correct_target: TargetType, 
                                       led_position: int, score: float) -> Optional[Tuple[float, str, Tuple[int, Color]]]:
        """Check for wrong key presses in a target window.
        
        Args:
            keys_pressed: Dictionary of key states
            correct_target: The correct target type for this window
            led_position: Current LED position
            score: Current score
            
        Returns:
            Error result tuple if a wrong key press is detected, None otherwise
        """
        for wrong_target in TargetType:
            if wrong_target != correct_target:
                wrong_keys = ButtonHandler.get_keys_for_target(wrong_target)
                
                if any(keys_pressed[key] for key in wrong_keys):
                    if self.error_sound:
                        self.error_sound.play()
                    error_pos = self.get_window_position_for_target(wrong_target)
                    error_color: Color = TARGET_COLORS[wrong_target]
                    return max(0, score - 0.25), "none", (error_pos, error_color)
        return None
    
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
    def is_position_in_valid_window(led_position: int, led_count: int, window_size: int,
                                   mid_pos: float, right_pos: float, left_pos: float) -> bool:
        """Check if the LED position is in a valid scoring window.
        
        Args:
            led_position: Position to check
            led_count: Total number of LEDs
            window_size: Size of the target window
            mid_pos: Middle target position
            right_pos: Right target position
            left_pos: Left target position
            
        Returns:
            True if the position is in a valid window
        """
        return (led_position >= led_count - window_size or 
                led_position <= window_size or
                abs(led_position - mid_pos) <= window_size or
                abs(led_position - right_pos) <= window_size or
                abs(led_position - left_pos) <= window_size)
    
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
        
        # Get fixed target positions by percentage
        red_percent = 0.0      # 12 o'clock (0%)
        green_percent = 0.25   # 3 o'clock (25%)
        blue_percent = 0.5     # 6 o'clock (50%)
        yellow_percent = 0.75  # 9 o'clock (75%)
        
        # Calculate window size as percentage
        window_percent = window_size / led_count
        
        # Check if position is near a target, with wrapping for the red target
        if (position_percent <= window_percent or 
            position_percent >= (1.0 - window_percent)):
            return TargetType.RED
        elif abs(position_percent - blue_percent) <= window_percent:
            return TargetType.BLUE
        elif abs(position_percent - green_percent) <= window_percent:
            return TargetType.GREEN
        elif abs(position_percent - yellow_percent) <= window_percent:
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

# For backward compatibility
ButtonPressHandler = ButtonHandler