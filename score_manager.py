"""Score management utilities for the rhythm game."""

from typing import List, Optional, Tuple, Dict, Any
from pygame import Color

from game_constants import TargetType, TARGET_COLORS, INITIAL_HIT_SPACING
from hit_trail import HitTrail
from score_effects import ScoreEffects


class ScoreManager:
    """Manages score tracking, calculation, and related effects.
    
    This class handles all score-related functionality including:
    - Score tracking and updates
    - Score flash effects
    - Hit trail management based on score
    """
    
    def __init__(self, initial_score: float = 0.0) -> None:
        """Initialize the score manager.
        
        Args:
            initial_score: Starting score value
        """
        self.score: float = initial_score
        self.previous_score: float = 0.0
        self.score_flash_start_beat: Optional[float] = None
        self.last_hit_target: str = "none"
        self.hit_colors: List[Color] = []
        self.hit_spacing: int = INITIAL_HIT_SPACING
        self.hit_trail_cleared: bool = False
    
    def update_score(self, new_score: float, target_type: str, beat_float: float, led_count: int) -> None:
        """Update score and trigger flash effect if score increased.
        
        Args:
            new_score: New score value
            target_type: Type of target hit (e.g., "red", "blue", "none")
            beat_float: Current beat position as a float
            led_count: Total number of LEDs
        """
        if new_score > self.score:
            self._handle_score_increase(new_score, target_type, beat_float, led_count)
        
        # Always update trail length based on new score
        max_trail_length: int = int(new_score * 4)
        self.hit_colors = HitTrail.limit_trail_length(self.hit_colors, max_trail_length)
                
        self.previous_score = self.score
        self.score = new_score
    
    def _handle_score_increase(self, new_score: float, target_type: str, beat_float: float, led_count: int) -> None:
        """Handle logic when score increases.
        
        Args:
            new_score: New score value
            target_type: Type of target hit
            beat_float: Current beat position
            led_count: Total number of LEDs
        """
        self.score_flash_start_beat = beat_float
        self.last_hit_target = target_type
        
        # Check if adding a new hit would exceed circle size
        if HitTrail.should_adjust_spacing(self.hit_colors, self.hit_spacing, led_count):
            new_spacing = HitTrail.get_new_spacing(self.hit_spacing)
            if new_spacing == 0:  # Signal to clear trail
                # Clear hit trail if we've hit minimum spacing
                self.hit_colors = []
                self.hit_spacing = INITIAL_HIT_SPACING  # Reset to initial spacing
                self.hit_trail_cleared = True  # Mark that hit trail has been cleared
                print("*********** Hit trail cleared, resetting spacing")
                return  # Skip adding hit color when trail is cleared
            else:
                self.hit_spacing = new_spacing
                print(f"*********** Hit spacing: {self.hit_spacing}")
        
        # Add hit color to beginning of trail
        try:
            target_enum: TargetType = TargetType[target_type.upper()]
            self.hit_colors = HitTrail.add_hit_color(self.hit_colors, TARGET_COLORS[target_enum])
            print(f"Hit colors: {len(self.hit_colors)}")
        except KeyError:
            pass  # Ignore invalid target types
    
    def get_score_flash_intensity(self, beat_float: float) -> float:
        """Calculate the intensity of the score flash effect based on musical beats.
        
        Args:
            beat_float: Current beat position as a float
            
        Returns:
            Flash intensity value between 0.0 and 1.0
        """
        return ScoreEffects.get_flash_intensity(beat_float, self.score_flash_start_beat)
    
    @staticmethod
    def calculate_score_penalty(score: float) -> float:
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
    def get_score_line_color(base_color: Color, flash_intensity: float, flash_type: str) -> Color:
        """Get the color for score lines during flash effect.
        
        Args:
            base_color: Base color for score lines
            flash_intensity: Intensity of flash effect (0.0 to 1.0)
            flash_type: Type of flash effect (e.g., "red", "blue")
            
        Returns:
            Modified color for score lines
        """
        return ScoreEffects.get_score_line_color(base_color, flash_intensity, flash_type)
    
    @staticmethod
    def calculate_trail_positions(led_position: int, hit_colors: List[Color], 
                                 hit_spacing: int, led_count: int) -> Dict[int, Color]:
        """Calculate positions and colors for the hit trail.
        
        Args:
            led_position: Current LED position
            hit_colors: List of colors for the hit trail
            hit_spacing: Spacing between hit trail elements
            led_count: Total number of LEDs
            
        Returns:
            Dictionary mapping positions to colors
        """
        return HitTrail.calculate_trail_positions(led_position, hit_colors, hit_spacing, led_count)
