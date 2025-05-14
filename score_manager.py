"""Score management utilities for the rhythm game."""

from typing import List, Optional, Tuple, Dict, Any
from pygame import Color

from game_constants import TargetType, TARGET_COLORS, INITIAL_HIT_SPACING
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
        self.score_flash_start_beat: Optional[float] = None
    
    def update_score(self, new_score: float, beat_float: float) -> None:
        """Update score and trigger flash effect if score increased.
        
        Args:
            new_score: New score value
            beat_float: Current beat position as a float
        """
        # print(f"new_score: {new_score}, self.score: {self.score}")
        if new_score > self.score:
            self._handle_score_increase(beat_float)
                        
        self.score = new_score
    
    def _handle_score_increase(self, beat_float: float) -> None:
        """Handle logic when score increases.
        
        Args:
            beat_float: Current beat position
        """
        self.score_flash_start_beat = beat_float
    
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
