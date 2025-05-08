"""Audio management utilities for the rhythm game."""

import pygame
from typing import Optional, Tuple, Dict, Any

from music_timing import MusicTiming
from game_constants import *


class AudioManager:
    """Manages audio playback, synchronization, and timing.
    
    This class handles all audio-related functionality including:
    - Music loading and playback
    - Music synchronization with game timing
    - Sound effect management
    """
    
    def __init__(self, music_file: Optional[str] = None) -> None:
        """Initialize the audio manager.
        
        Args:
            music_file: Path to the music file to load
        """
        self.last_music_start_time_s: float = 0.0  # Track when we last started playing music
        self.last_music_start_pos_s: float = 0.0   # Track from what position we started playing
        self.music_file: Optional[str] = music_file
        self.sound_effects: Dict[str, pygame.mixer.Sound] = {}
        
        # Load music if provided
        if music_file:
            self.load_music(music_file)
    
    def load_music(self, music_file: str) -> None:
        """Load a music file for playback.
        
        Args:
            music_file: Path to the music file to load
        """
        self.music_file = music_file
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
    
    def handle_music_loop(self, score: float, beat_start_time_ms: int, 
                         current_time_ms: int, seconds_per_measure_s: float) -> None:
        """Handle music looping and synchronization.
        
        Args:
            score: Current game score
            beat_start_time_ms: Time when the current beat started
            current_time_ms: Current time in milliseconds
            seconds_per_measure_s: Duration of one measure in seconds
        """
        # Calculate target music time based on score and timing
        target_time_s: float = MusicTiming.calculate_target_music_time(
            score, beat_start_time_ms, current_time_ms, seconds_per_measure_s
        )
        
        # Get current music position in seconds
        current_music_pos_s: float = self.get_current_music_position()
        
        # Check if we need to synchronize music
        if self._should_sync_music(current_music_pos_s, target_time_s):
            self._sync_music(target_time_s)
    
    def _should_sync_music(self, current_pos_s: float, target_pos_s: float) -> bool:
        """Determine if music needs to be synchronized.
        
        Args:
            current_pos_s: Current music position in seconds
            target_pos_s: Target music position in seconds
            
        Returns:
            True if music should be synchronized
        """
        return MusicTiming.should_sync_music(current_pos_s, target_pos_s)
        
    def should_sync_music(self, current_pos_s: float, target_pos_s: float) -> bool:
        """Public method to determine if music needs to be synchronized.
        
        Args:
            current_pos_s: Current music position in seconds
            target_pos_s: Target music position in seconds
            
        Returns:
            True if music should be synchronized
        """
        return self._should_sync_music(current_pos_s, target_pos_s)
        
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
        
    @staticmethod
    def calculate_target_beats(target_time_s: float, beat_per_ms: float) -> int:
        """Calculate target beats based on target time.
        
        Args:
            target_time_s: Target time in seconds
            beat_per_ms: Beats per millisecond
            
        Returns:
            Target beats
        """
        return MusicTiming.calculate_target_beats(target_time_s, beat_per_ms)
    
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
