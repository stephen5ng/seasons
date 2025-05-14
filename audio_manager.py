"""Audio management utilities for the rhythm game."""

import pygame
from typing import Optional, Tuple, Dict, Any

from game_constants import *


class AudioManager:
    """Manages audio playback, synchronization, and timing.
    
    This class handles all audio-related functionality including:
    - Music loading and playback
    - Music synchronization with game timing
    - Sound effect management
    - Beat timing calculations
    """
    
    def __init__(self, music_file: str) -> None:
        """Initialize the audio manager.
        
        Args:
            music_file: Path to the music file to load
        """
        self.last_music_start_time_s: float = 0.0  # Track when we last started playing music
        self.last_music_start_pos_s: float = 0.0   # Track from what position we started playing
        self.sound_effects: Dict[str, pygame.mixer.Sound] = {}
        pygame.mixer.music.load(music_file)
        
    def play_music(self, start_pos_s: float = 0.0) -> None:
        """Play the loaded music from the specified position.
        
        Args:
            start_pos_s: Position in seconds to start playback from
        """
        self.last_music_start_time_s = pygame.time.get_ticks() / 1000.0
        self.last_music_start_pos_s = start_pos_s
        pygame.mixer.music.play(start=start_pos_s)
    
    def get_current_music_position(self) -> float:
        """Get the current music playback position in seconds.
        
        Returns:
            Current position in seconds
        """
        return self.last_music_start_pos_s + (pygame.mixer.music.get_pos() / 1000.0)
    
    def calculate_beat_timing(self, current_time_ms: int, start_time_ms: int) -> Tuple[int, float, float]:
        """Calculate current beat timing values.
        
        Args:
            current_time_ms: Current time in milliseconds
            start_time_ms: Start time in milliseconds
            
        Returns:
            Tuple of (beat_in_phrase, beat_float, fractional_beat)
        """
        duration_ms: int = current_time_ms - start_time_ms
        beat_float: float = duration_ms * BEAT_PER_MS
        beat_in_phrase: int = int(beat_float) % BEATS_PER_PHRASE
        fractional_beat: float = beat_float % 1
        
        return beat_in_phrase, beat_float, fractional_beat
    
    def should_sync_music(self, current_pos_s: float, target_pos_s: float, threshold: float = 0.2) -> bool:
        """Determine if music should be synchronized based on position difference.
        
        Args:
            current_pos_s: Current music position in seconds
            target_pos_s: Target music position in seconds
            threshold: Maximum allowed difference before sync is needed
            
        Returns:
            True if music should be synchronized, False otherwise
        """
        return abs(current_pos_s - target_pos_s) > threshold
    
    def calculate_target_beats(self, target_time_s: float) -> int:
        """Calculate target beat count based on target time.
        
        Args:
            target_time_s: Target time in seconds
            
        Returns:
            Target beat count
        """
        return int(target_time_s * (1000 * BEAT_PER_MS))
    
    def get_target_music_time(self, score: float, beat_start_time_ms: int, 
                             current_time_ms: int) -> float:
        """Calculate target music time based on score and timing.
        
        Args:
            score: Current game score
            beat_start_time_ms: Time when the current beat started
            current_time_ms: Current time in milliseconds
            
        Returns:
            Target music time in seconds
        """
        measure_offset_s: float = (current_time_ms - beat_start_time_ms) / 1000.0
        return int(score) * SECONDS_PER_MEASURE_S + measure_offset_s
    
    def _sync_music(self, target_pos_s: float) -> None:
        """Synchronize music to the target position.
        
        Args:
            target_pos_s: Target position in seconds
        """
        print(f"Starting music at {target_pos_s} seconds")
        self.last_music_start_pos_s = target_pos_s
        self.last_music_start_time_s = pygame.time.get_ticks() / 1000.0
        pygame.mixer.music.play(start=target_pos_s)
    
    def load_sound_effect(self, name: str, sound_file: str) -> None:
        """Load a sound effect for later playback.
        
        Args:
            name: Name to identify the sound effect
            sound_file: Path to the sound effect file
        """
        self.sound_effects[name] = pygame.mixer.Sound(sound_file)
    
    def play_sound_effect(self, name: str) -> None:
        """Play a previously loaded sound effect.
        
        Args:
            name: Name of the sound effect to play
        """
        if name in self.sound_effects:
            self.sound_effects[name].play()
    
    @staticmethod
    def set_volume(volume: float) -> None:
        """Set the music volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        pygame.mixer.music.set_volume(volume)
    
    @staticmethod
    def pause_music() -> None:
        """Pause music playback."""
        pygame.mixer.music.pause()
    
    @staticmethod
    def unpause_music() -> None:
        """Resume music playback."""
        pygame.mixer.music.unpause()
    
    @staticmethod
    def stop_music() -> None:
        """Stop music playback."""
        pygame.mixer.music.stop()
