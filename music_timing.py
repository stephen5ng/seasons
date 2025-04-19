"""Music timing and synchronization utilities."""
from typing import Tuple, Optional

class MusicTiming:
    """Handles music timing calculations and synchronization."""
    
    @staticmethod
    def calculate_beat_timing(
        current_time_ms: int, 
        start_time_ms: int, 
        beat_per_ms: float, 
        beats_per_measure: int
    ) -> Tuple[int, int, float, float]:
        """Calculate current beat timing values.
        
        Args:
            current_time_ms: Current time in milliseconds
            start_time_ms: Start time in milliseconds
            beat_per_ms: Beats per millisecond constant
            beats_per_measure: Number of beats in a measure
            
        Returns:
            Tuple of (beat, beat_in_measure, beat_float, fractional_beat)
        """
        duration_ms: int = current_time_ms - start_time_ms
        beat_float: float = duration_ms * beat_per_ms
        beat: int = int(beat_float)
        beat_in_measure: int = beat % beats_per_measure
        fractional_beat: float = beat_float % 1
        
        return beat, beat_in_measure, beat_float, fractional_beat
    
    @staticmethod
    def calculate_target_music_time(
        score: float, 
        measure_start_ms: int, 
        current_time_ms: int,
        seconds_per_measure: float
    ) -> float:
        """Calculate target music position in seconds based on score and timing.
        
        Args:
            score: Current game score
            measure_start_ms: Start time of current measure in milliseconds
            current_time_ms: Current time in milliseconds
            seconds_per_measure: Seconds per measure constant
            
        Returns:
            Target music position in seconds
        """
        measure_offset_s: float = (current_time_ms - measure_start_ms) / 1000.0
        return int(score) * seconds_per_measure + measure_offset_s
    
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
