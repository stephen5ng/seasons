"""Hit trail management utilities."""
from typing import List, Dict, Optional
from pygame import Color

class HitTrail:
    """Handles hit trail management and calculations."""
    
    @staticmethod
    def calculate_total_space(colors: List[Color], spacing: float) -> float:
        """Calculate total space needed for hit trail.
        
        Args:
            colors: List of colors in the hit trail
            spacing: Current spacing between hit trail elements
            
        Returns:
            Total space needed for the hit trail
        """
        return (len(colors) + 1) * spacing
    
    @staticmethod
    def should_adjust_spacing(colors: List[Color], spacing: float, max_leds: int) -> bool:
        """Determine if spacing needs to be adjusted based on available space.
        
        Args:
            colors: List of colors in the hit trail
            spacing: Current spacing between hit trail elements
            max_leds: Maximum number of LEDs available
            
        Returns:
            True if spacing needs adjustment, False otherwise
        """
        total_space: float = HitTrail.calculate_total_space(colors, spacing)
        return total_space >= max_leds
    
    @staticmethod
    def get_new_spacing(current_spacing: float, min_spacing: float = 4.0) -> float:
        """Calculate new spacing when adjustment is needed.
        
        Args:
            current_spacing: Current spacing between hit trail elements
            min_spacing: Minimum allowed spacing before trail is cleared
            
        Returns:
            New spacing value
        """
        if current_spacing <= min_spacing:
            return 0  # Signal that trail should be cleared
        return max(current_spacing / 2, 1)
    
    @staticmethod
    def add_hit_color(colors: List[Color], target_color: Color) -> List[Color]:
        """Add a new color to the beginning of the hit trail.
        
        Args:
            colors: Current list of colors in the hit trail
            target_color: Color to add for the new hit
            
        Returns:
            Updated list of colors with new color at the beginning
        """
        new_colors = colors.copy()
        new_colors.insert(0, target_color)
        return new_colors
    
    @staticmethod
    def limit_trail_length(colors: List[Color], max_length: int) -> List[Color]:
        """Limit the trail length based on maximum allowed length.
        
        Args:
            colors: Current list of colors in the hit trail
            max_length: Maximum allowed length for the trail
            
        Returns:
            Updated list of colors limited to max_length
        """
        if len(colors) > max_length:
            return colors[:max_length]
        return colors
    
    @staticmethod
    def calculate_trail_positions(led_position: int, colors: List[Color], 
                                spacing: float, number_of_leds: int) -> Dict[int, Color]:
        """Calculate positions for all elements in the hit trail.
        
        Args:
            led_position: Current LED position
            colors: List of colors in the hit trail
            spacing: Spacing between hit trail elements
            number_of_leds: Total number of LEDs in the strip
            
        Returns:
            Dictionary mapping LED positions to colors
        """
        positions: Dict[int, Color] = {}
        for i, color in enumerate(colors):
            trail_pos: int = int((led_position - (i + 1) * spacing) % number_of_leds)
            positions[trail_pos] = color
        return positions
