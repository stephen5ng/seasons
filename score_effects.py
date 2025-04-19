"""Score visual effects calculations."""
from typing import Optional, Tuple
from pygame import Color

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
    
    @staticmethod
    def get_score_line_color(base_color: Color, flash_intensity: float, flash_type: str) -> Color:
        """Create a flash effect for score lines based on which target was hit.
        
        Args:
            base_color: Base color for score lines
            flash_intensity: Intensity of flash effect (0.0 to 1.0)
            flash_type: Type of flash effect (e.g., "red", "blue")
            
        Returns:
            Modified color for score lines
        """
        if flash_intensity <= 0:
            return base_color
            
        # Create different flash colors based on target type
        r: int = base_color.r
        g: int = base_color.g
        b: int = base_color.b
        
        if flash_type == "red":
            r = min(255, int(r + (255 - r) * flash_intensity))
        elif flash_type == "blue":
            b = min(255, int(b + (255 - b) * flash_intensity))
        elif flash_type == "green":
            g = min(255, int(g + (255 - g) * flash_intensity))
        elif flash_type == "yellow":
            r = min(255, int(r + (255 - r) * flash_intensity))
            g = min(255, int(g + (255 - g) * flash_intensity))
            
        return Color(r, g, b)
