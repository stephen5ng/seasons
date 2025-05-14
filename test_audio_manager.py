"""Unit tests for the AudioManager class."""

import unittest
from unittest.mock import patch, MagicMock, call
import pygame

from audio_manager import AudioManager
from music_timing import MusicTiming

class TestAudioManager(unittest.TestCase):
    """Test cases for the AudioManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a patch for pygame.mixer.music to avoid actual audio playback
        self.mock_pygame_mixer_music = patch('pygame.mixer.music').start()
        self.mock_pygame_time = patch('pygame.time').start()
        
        # Set up mock return values
        self.mock_pygame_time.get_ticks.return_value = 1000  # 1 second in ms
        self.mock_pygame_mixer_music.get_pos.return_value = 500  # 0.5 seconds in ms
        
        # Create AudioManager instance for testing
        self.audio_manager = AudioManager()
    
    def tearDown(self):
        """Tear down test fixtures."""
        patch.stopall()
    
    def test_init(self):
        """Test initialization with default values."""
        self.assertEqual(self.audio_manager.last_music_start_time_s, 0.0)
        self.assertEqual(self.audio_manager.last_music_start_pos_s, 0.0)
        self.assertIsNone(self.audio_manager.music_file)
        self.assertEqual(self.audio_manager.sound_effects, {})
        
        # Test initialization with music file
        with patch('pygame.mixer.music.load') as mock_load:
            audio_manager = AudioManager("test_music.mp3")
            self.assertEqual(audio_manager.music_file, "test_music.mp3")
            mock_load.assert_called_once_with("test_music.mp3")
    
    def test_load_music(self):
        """Test load_music method."""
        self.audio_manager.load_music("test_music.mp3")
        self.assertEqual(self.audio_manager.music_file, "test_music.mp3")
        self.mock_pygame_mixer_music.load.assert_called_once_with("test_music.mp3")
    
    def test_play_music(self):
        """Test play_music method."""
        self.mock_pygame_time.get_ticks.return_value = 2000  # 2 seconds in ms
        
        self.audio_manager.play_music(1.5)
        
        self.assertEqual(self.audio_manager.last_music_start_time_s, 2.0)
        self.assertEqual(self.audio_manager.last_music_start_pos_s, 1.5)
        self.mock_pygame_mixer_music.play.assert_called_once_with(start=1.5)
    
    def test_get_current_music_position(self):
        """Test get_current_music_position method."""
        self.audio_manager.last_music_start_pos_s = 2.0
        self.mock_pygame_mixer_music.get_pos.return_value = 1500  # 1.5 seconds in ms
        
        position = self.audio_manager.get_current_music_position()
        
        self.assertEqual(position, 3.5)  # 2.0 + 1.5 = 3.5 seconds
    
    @patch('audio_manager.MusicTiming.calculate_target_music_time')
    @patch('audio_manager.MusicTiming.should_sync_music')
    def test_handle_music_loop_no_sync(self, mock_should_sync, mock_calculate_time):
        """Test handle_music_loop when no synchronization is needed."""
        # Set up mocks
        mock_calculate_time.return_value = 5.0
        mock_should_sync.return_value = False
        
        # Call the method
        self.audio_manager.handle_music_loop(2.0, 1000, 3000, 3.7)
        
        # Verify the correct methods were called
        mock_calculate_time.assert_called_once_with(2.0, 1000, 3000, 3.7)
        mock_should_sync.assert_called_once()
        
        # Verify that sync_music was not called
        self.mock_pygame_mixer_music.play.assert_not_called()
    
    @patch('audio_manager.MusicTiming.calculate_target_music_time')
    @patch('audio_manager.MusicTiming.should_sync_music')
    def test_handle_music_loop_with_sync(self, mock_should_sync, mock_calculate_time):
        """Test handle_music_loop when synchronization is needed."""
        # Set up mocks
        mock_calculate_time.return_value = 5.0
        mock_should_sync.return_value = True
        self.mock_pygame_time.get_ticks.return_value = 4000  # 4 seconds in ms
        
        # Call the method
        self.audio_manager.handle_music_loop(2.0, 1000, 3000, 3.7)
        
        # Verify the correct methods were called
        mock_calculate_time.assert_called_once_with(2.0, 1000, 3000, 3.7)
        mock_should_sync.assert_called_once()
        
        # Verify that sync_music was called
        self.mock_pygame_mixer_music.play.assert_called_once_with(start=5.0)
        self.assertEqual(self.audio_manager.last_music_start_pos_s, 5.0)
        self.assertEqual(self.audio_manager.last_music_start_time_s, 4.0)
    
    def test_load_sound_effect(self):
        """Test load_sound_effect method."""
        with patch('pygame.mixer.Sound') as mock_sound:
            mock_sound.return_value = "mock_sound"
            
            self.audio_manager.load_sound_effect("error", "error.wav")
            
            mock_sound.assert_called_once_with("error.wav")
            self.assertEqual(self.audio_manager.sound_effects["error"], "mock_sound")
    
    def test_play_sound_effect(self):
        """Test play_sound_effect method."""
        # Create a mock sound effect
        mock_sound = MagicMock()
        self.audio_manager.sound_effects["error"] = mock_sound
        
        # Call the method
        self.audio_manager.play_sound_effect("error")
        
        # Verify the sound was played
        mock_sound.play.assert_called_once()
        
        # Test with non-existent sound effect
        self.audio_manager.play_sound_effect("non_existent")
        # No exception should be raised

if __name__ == '__main__':
    unittest.main()
