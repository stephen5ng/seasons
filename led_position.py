"""LED position calculation utilities."""
from typing import Tuple
from game_constants import *
class LEDPosition:
    """Handles LED position calculations based on musical timing."""
    
    @staticmethod
    def calculate_position(beat_in_phrase: int, fractional_beat: float, 
                          number_of_leds: int) -> int:
        """Calculate the current LED position based on beat timing.
        
        Args:
            beat_in_phrase: Current beat within the phrase (0-indexed)
            fractional_beat: Fractional part of the current beat (0.0-0.99)
            number_of_leds: Total number of LEDs in the strip
            
        Returns:
            Integer position of the active LED (0 to number_of_leds-1)
        """
        percent_of_phrase: float = (fractional_beat / BEATS_PER_PHRASE) + (beat_in_phrase / BEATS_PER_PHRASE)
        return int(percent_of_phrase * number_of_leds)
    
    @staticmethod
    def get_ring_position(led_index: int, radius: int, number_of_leds: int) -> Tuple[int, int]:
        """Convert LED index to x,y coordinates in a circular pattern.
        
        Args:
            led_index: Index of the LED in the strip (0 to number_of_leds-1)
            radius: Radius of the circular pattern in pixels
            number_of_leds: Total number of LEDs in the strip
            
        Returns:
            Tuple of (x, y) coordinates, with (0,0) at the center
        """
        import math
        angle: float = 3 * math.pi / 2 + (2 * math.pi * led_index) / number_of_leds
        x: int = int(radius * math.cos(angle))
        y: int = int(radius * math.sin(angle))
        return (x, y)
