from typing import Dict, List, Optional, Tuple
import pygame
from pygame import Color

# Import constants needed by ButtonPressHandler
from game_constants import NUMBER_OF_LEDS, TARGET_WINDOW_SIZE, MID_TARGET_POS, RIGHT_TARGET_POS, LEFT_TARGET_POS, TARGET_COLORS, TargetType

# Game settings
ALWAYS_SCORE = True  # When True, automatically scores on every round

class ButtonPressHandler:
    """Handles button press logic and scoring."""
    
    def __init__(self, error_sound: pygame.mixer.Sound) -> None:
        self.button_states: Dict[str, bool] = {
            "r": False,
            "b": False,
            "g": False,
            "y": False
        }
        self.penalty_applied: bool = False
        self.round_active: bool = False
        self.error_sound: pygame.mixer.Sound = error_sound
    
    def is_in_valid_window(self, led_position: int) -> bool:
        """Check if the current LED position is in a valid window for scoring."""
        return_value: bool = (led_position >= NUMBER_OF_LEDS - TARGET_WINDOW_SIZE or 
                led_position <= TARGET_WINDOW_SIZE or
                abs(led_position - MID_TARGET_POS) <= TARGET_WINDOW_SIZE or
                abs(led_position - RIGHT_TARGET_POS) <= TARGET_WINDOW_SIZE or
                abs(led_position - LEFT_TARGET_POS) <= TARGET_WINDOW_SIZE)
        return return_value
    
    def apply_penalty(self, score: float) -> float:
        """Apply penalty if button wasn't pressed in valid window."""
        if not any(self.button_states.values()) and not self.penalty_applied:
            # Calculate score after 25% reduction
            reduced_score: float = score * 0.75
            # Make sure it's at least 0.25 less than original score
            reduced_score = min(reduced_score, score - 0.25)
            # Round to nearest 0.25 and ensure score doesn't go below 0
            score = max(0, round(reduced_score * 4) / 4)
            self.penalty_applied = True
        return score
    
    def reset_flags(self, led_position: int) -> None:
        """Reset state flags based on LED position."""
        if self.is_in_valid_window(led_position) and not self.round_active:
            self.button_states = {k: False for k in self.button_states}
            self.penalty_applied = False
            self.round_active = True  # Start a new scoring round
        elif not self.is_in_valid_window(led_position):
            self.round_active = False  # End the current scoring round
    
    def get_target_type(self, position: int) -> Optional[TargetType]:
        """Determine which target window the position is in, if any."""
        if position <= TARGET_WINDOW_SIZE or position >= NUMBER_OF_LEDS - TARGET_WINDOW_SIZE:
            return TargetType.RED
        elif abs(position - MID_TARGET_POS) <= TARGET_WINDOW_SIZE:
            return TargetType.BLUE
        elif abs(position - RIGHT_TARGET_POS) <= TARGET_WINDOW_SIZE:
            return TargetType.GREEN
        elif abs(position - LEFT_TARGET_POS) <= TARGET_WINDOW_SIZE:
            return TargetType.YELLOW
        return None

    def handle_keypress(self, led_position: int, score: float, current_time: int) -> Tuple[float, str, Optional[Tuple[int, Color]]]:
        """Handle keypress and update score if in valid window with correct key.
        Returns (score, target_type, (error_position, error_color)) where error_position is the center of the target window 
        and error_color is the color of the wrong key that was pressed."""
        keys_pressed: Dict[int, bool] = pygame.key.get_pressed()
        # Check both letter keys and arrow keys
        any_key_pressed: bool = any(keys_pressed[key] for key in [pygame.K_r, pygame.K_b, pygame.K_g, pygame.K_y, 
                                                          pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT])
        
        # Check for any key press outside its window
        for target_type in TargetType:
            # Check both letter and arrow keys for this target
            keys: List[int]
            if target_type == TargetType.RED:
                keys = [pygame.K_r, pygame.K_UP]
            elif target_type == TargetType.BLUE:
                keys = [pygame.K_b, pygame.K_DOWN]
            elif target_type == TargetType.GREEN:
                keys = [pygame.K_g, pygame.K_RIGHT]
            else:  # YELLOW
                keys = [pygame.K_y, pygame.K_LEFT]
            
            if any(keys_pressed[key] for key in keys):
                # Get the center position of this key's window
                window_pos: int
                if target_type == TargetType.RED:
                    window_pos = 0
                elif target_type == TargetType.BLUE:
                    window_pos = int(MID_TARGET_POS)
                elif target_type == TargetType.GREEN:
                    window_pos = int(RIGHT_TARGET_POS)
                else:  # YELLOW
                    window_pos = int(LEFT_TARGET_POS)
                
                # If we're not in this key's window, show error and apply penalty
                if abs(led_position - window_pos) > TARGET_WINDOW_SIZE:
                    self.error_sound.play()
                    error_color: Color = TARGET_COLORS[target_type]
                    return max(0, score - 0.25), "none", (window_pos, error_color)
        
        # If we get here, either no keys were pressed or we're in a valid window
        target_type: Optional[TargetType] = self.get_target_type(led_position)
        
        if target_type:
            # Check both letter and arrow keys for this target
            keys: List[int]
            if target_type == TargetType.RED:
                keys = [pygame.K_r, pygame.K_UP]
            elif target_type == TargetType.BLUE:
                keys = [pygame.K_b, pygame.K_DOWN]
            elif target_type == TargetType.GREEN:
                keys = [pygame.K_g, pygame.K_RIGHT]
            else:  # YELLOW
                keys = [pygame.K_y, pygame.K_LEFT]
            
            # Check if wrong button was pressed in this window
            for wrong_target in TargetType:
                if wrong_target != target_type:
                    wrong_keys: List[int]
                    if wrong_target == TargetType.RED:
                        wrong_keys = [pygame.K_r, pygame.K_UP]
                    elif wrong_target == TargetType.BLUE:
                        wrong_keys = [pygame.K_b, pygame.K_DOWN]
                    elif wrong_target == TargetType.GREEN:
                        wrong_keys = [pygame.K_g, pygame.K_RIGHT]
                    else:  # YELLOW
                        wrong_keys = [pygame.K_y, pygame.K_LEFT]
                    
                    if any(keys_pressed[key] for key in wrong_keys):
                        self.error_sound.play()
                        # Get the center position of the wrong key's window
                        error_pos: int
                        if wrong_target == TargetType.RED:
                            error_pos = 0
                        elif wrong_target == TargetType.BLUE:
                            error_pos = int(MID_TARGET_POS)
                        elif wrong_target == TargetType.GREEN:
                            error_pos = int(RIGHT_TARGET_POS)
                        else:  # YELLOW
                            error_pos = int(LEFT_TARGET_POS)
                        error_color: Color = TARGET_COLORS[wrong_target]
                        return max(0, score - 0.25), "none", (error_pos, error_color)
            
            if (any(keys_pressed[key] for key in keys) or ALWAYS_SCORE) and not self.button_states[target_type.name[0].lower()]:
                self.button_states[target_type.name[0].lower()] = True
                self.penalty_applied = False
                return score + 0.25, target_type.name.lower(), None
        
        return score, "none", None 