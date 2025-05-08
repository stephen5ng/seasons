"""Music timing and synchronization utilities."""
from typing import Tuple, Optional
from game_constants import *

class MusicTiming:
    """Handles music timing calculations and synchronization."""
    
    @staticmethod
    def calculate_beat_timing(
        current_time_ms: int, 
        start_time_ms: int
    ) -> Tuple[int, int, float, float]:
        """Calculate current beat timing values.
        
        Args:
            current_time_ms: Current time in milliseconds
            start_time_ms: Start time in milliseconds
            
        Returns:
            Tuple of (beat, beat_in_phrase, beat_float, fractional_beat)
        """
        duration_ms: int = current_time_ms - start_time_ms
        beat_float: float = duration_ms * BEAT_PER_MS
        beat_in_phrase: int = int(beat_float) % BEATS_PER_PHRASE
        fractional_beat: float = beat_float % 1
        
        return beat_in_phrase, beat_float, fractional_beat
    
    @staticmethod
    def should_sync_music(current_pos_s: float, target_pos_s: float, threshold: float = 0.2) -> bool:
        """Determine if music should be synchronized based on position difference.
        
        Args:
            current_pos_s: Current music position in seconds
            target_pos_s: Target music position in seconds
            threshold: Maximum allowed difference before sync is needed
            
        Returns:
            True if music should be synchronized, False otherwise
        """
        return abs(current_pos_s - target_pos_s) > threshold
    
    @staticmethod
    def calculate_target_beats(target_time_s: float, beat_per_ms: float) -> int:
        """Calculate target beat count based on target time.
        
        Args:
            target_time_s: Target time in seconds
            beat_per_ms: Beats per millisecond constant
            
        Returns:
            Target beat count
        """
        return int(target_time_s * (1000 * beat_per_ms))
