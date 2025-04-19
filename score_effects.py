"""Score visual effects calculations."""
from typing import Optional

class ScoreEffects:
    """Handles score-related visual effects calculations."""
    
    @staticmethod
    def get_flash_intensity(current_beat_float: float, flash_start_beat: Optional[float]) -> float:
        """Calculate the intensity of the score flash effect based on musical beats.
        
        Args:
            current_beat_float: Current beat position as a float
            flash_start_beat: Beat when the flash effect started, or None if no flash
            
        Returns:
            Float between 0.0 and 1.0 representing flash intensity
        """
        if flash_start_beat is None:
            return 0.0
        
        beats_since_flash: float = current_beat_float - flash_start_beat
        if beats_since_flash >= 2.0:  # Flash lasts for 2 beats
            return 0.0
        
        return 1.0 - (beats_since_flash / 2.0)
