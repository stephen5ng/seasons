"""Unit tests for the ScoreManager class."""

import unittest
from unittest.mock import patch, MagicMock
from pygame import Color

from score_manager import ScoreManager
from game_constants import TargetType, TARGET_COLORS, INITIAL_HIT_SPACING

class TestScoreManager(unittest.TestCase):
    """Test cases for the ScoreManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.score_manager = ScoreManager()
        self.led_count = 80
    
    def test_init(self):
        """Test initialization with default values."""
        self.assertEqual(self.score_manager.score, 0.0)
        self.assertEqual(self.score_manager.previous_score, 0.0)
        self.assertIsNone(self.score_manager.score_flash_start_beat)
        self.assertEqual(self.score_manager.last_hit_target, "none")
        self.assertEqual(self.score_manager.hit_colors, [])
        self.assertEqual(self.score_manager.hit_spacing, INITIAL_HIT_SPACING)
        self.assertFalse(self.score_manager.hit_trail_cleared)
        
        # Test initialization with custom score
        custom_score_manager = ScoreManager(2.5)
        self.assertEqual(custom_score_manager.score, 2.5)
    
    def test_update_score_no_increase(self):
        """Test update_score when score doesn't increase."""
        # Set initial state
        self.score_manager.score = 1.0
        self.score_manager.previous_score = 0.5
        
        # Update with same score
        self.score_manager.update_score(1.0, "none", 2.5, self.led_count)
        
        # Check that state is updated correctly
        self.assertEqual(self.score_manager.score, 1.0)
        self.assertEqual(self.score_manager.previous_score, 1.0)
        self.assertIsNone(self.score_manager.score_flash_start_beat)
    
    @patch('score_manager.HitTrail.add_hit_color')
    def test_update_score_with_increase(self, mock_add_hit_color):
        """Test update_score when score increases."""
        # Set up mock
        mock_add_hit_color.return_value = [Color(255, 0, 0)]
        
        # Update with increased score
        self.score_manager.update_score(0.25, TargetType.RED, 2.5, self.led_count)
        
        # Check that state is updated correctly
        self.assertEqual(self.score_manager.score, 0.25)
        self.assertEqual(self.score_manager.previous_score, 0.0)
        self.assertEqual(self.score_manager.score_flash_start_beat, 2.5)
        self.assertEqual(self.score_manager.last_hit_target, TargetType.RED)
        
        # Verify HitTrail.add_hit_color was called
        mock_add_hit_color.assert_called_once()
    
    @patch('score_manager.ScoreEffects.get_flash_intensity')
    def test_get_score_flash_intensity(self, mock_get_flash_intensity):
        """Test get_score_flash_intensity method."""
        # Set up mock
        mock_get_flash_intensity.return_value = 0.75
        
        # Call the method
        intensity = self.score_manager.get_score_flash_intensity(3.5)
        
        # Check result
        self.assertEqual(intensity, 0.75)
        
        # Verify mock was called
        mock_get_flash_intensity.assert_called_once_with(3.5, None)
    
    def test_calculate_score_penalty(self):
        """Test calculate_score_penalty static method."""
        # Test with different score values
        self.assertEqual(ScoreManager.calculate_score_penalty(1.0), 0.75)
        self.assertEqual(ScoreManager.calculate_score_penalty(2.0), 1.5)
        self.assertEqual(ScoreManager.calculate_score_penalty(0.25), 0.0)
        
        # Test with fractional scores
        self.assertEqual(ScoreManager.calculate_score_penalty(1.75), 1.25)
        self.assertEqual(ScoreManager.calculate_score_penalty(0.5), 0.25)
    
    @patch('score_manager.ScoreEffects.get_score_line_color')
    def test_get_score_line_color(self, mock_get_score_line_color):
        """Test get_score_line_color static method."""
        # Set up mock
        base_color = Color(255, 255, 255)
        flash_intensity = 0.8
        flash_type = "red"
        mock_get_score_line_color.return_value = Color(255, 50, 50)
        
        # Call the method
        color = ScoreManager.get_score_line_color(base_color, flash_intensity, flash_type)
        
        # Check result
        self.assertEqual(color, Color(255, 50, 50))
        
        # Verify mock was called
        mock_get_score_line_color.assert_called_once_with(base_color, flash_intensity, flash_type)
    
    @patch('score_manager.HitTrail.calculate_trail_positions')
    def test_calculate_trail_positions(self, mock_calculate_trail_positions):
        """Test calculate_trail_positions static method."""
        # Set up mock
        led_position = 40
        hit_colors = [Color(255, 0, 0), Color(0, 255, 0)]
        hit_spacing = 8
        led_count = 80
        expected_positions = {48: Color(255, 0, 0), 56: Color(0, 255, 0)}
        mock_calculate_trail_positions.return_value = expected_positions
        
        # Call the method
        positions = ScoreManager.calculate_trail_positions(led_position, hit_colors, hit_spacing, led_count)
        
        # Check result
        self.assertEqual(positions, expected_positions)
        
        # Verify mock was called
        mock_calculate_trail_positions.assert_called_once_with(led_position, hit_colors, hit_spacing, led_count)

if __name__ == '__main__':
    unittest.main()
