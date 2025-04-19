"""Unit tests for the ButtonHandler class."""

import unittest
from unittest.mock import MagicMock, patch
import pygame
from pygame import Color

from button_handler import ButtonHandler
from game_constants import TargetType, TARGET_COLORS

class TestButtonHandler(unittest.TestCase):
    """Test cases for the ButtonHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_sound = MagicMock()
        self.button_handler = ButtonHandler(self.error_sound)
        
        # Mock constants for testing
        self.led_count = 80
        self.window_size = 4
        self.mid_pos = 40
        self.right_pos = 20
        self.left_pos = 60
    
    def test_is_position_in_valid_window(self):
        """Test the is_position_in_valid_window static method."""
        # Test positions in each window
        self.assertTrue(ButtonHandler.is_position_in_valid_window(
            0, self.led_count, self.window_size, self.mid_pos, self.right_pos, self.left_pos))
        self.assertTrue(ButtonHandler.is_position_in_valid_window(
            self.led_count - 1, self.led_count, self.window_size, self.mid_pos, self.right_pos, self.left_pos))
        self.assertTrue(ButtonHandler.is_position_in_valid_window(
            self.mid_pos, self.led_count, self.window_size, self.mid_pos, self.right_pos, self.left_pos))
        self.assertTrue(ButtonHandler.is_position_in_valid_window(
            self.right_pos, self.led_count, self.window_size, self.mid_pos, self.right_pos, self.left_pos))
        self.assertTrue(ButtonHandler.is_position_in_valid_window(
            self.left_pos, self.led_count, self.window_size, self.mid_pos, self.right_pos, self.left_pos))
        
        # Test positions at window edges
        self.assertTrue(ButtonHandler.is_position_in_valid_window(
            self.window_size, self.led_count, self.window_size, self.mid_pos, self.right_pos, self.left_pos))
        self.assertTrue(ButtonHandler.is_position_in_valid_window(
            self.mid_pos + self.window_size, self.led_count, self.window_size, self.mid_pos, self.right_pos, self.left_pos))
        
        # Test positions outside windows
        self.assertFalse(ButtonHandler.is_position_in_valid_window(
            10, self.led_count, self.window_size, self.mid_pos, self.right_pos, self.left_pos))
        self.assertFalse(ButtonHandler.is_position_in_valid_window(
            30, self.led_count, self.window_size, self.mid_pos, self.right_pos, self.left_pos))
        self.assertFalse(ButtonHandler.is_position_in_valid_window(
            50, self.led_count, self.window_size, self.mid_pos, self.right_pos, self.left_pos))
    
    def test_calculate_penalty_score(self):
        """Test the calculate_penalty_score static method."""
        # Test with different score values
        self.assertEqual(ButtonHandler.calculate_penalty_score(1.0), 0.75)
        self.assertEqual(ButtonHandler.calculate_penalty_score(2.0), 1.5)
        self.assertEqual(ButtonHandler.calculate_penalty_score(0.25), 0.0)
        
        # Test with fractional scores
        self.assertEqual(ButtonHandler.calculate_penalty_score(1.75), 1.25)
        self.assertEqual(ButtonHandler.calculate_penalty_score(0.5), 0.25)
    
    def test_get_target_type_for_position(self):
        """Test the get_target_type_for_position static method."""
        # Test positions in each target window
        self.assertEqual(
            ButtonHandler.get_target_type_for_position(0, self.led_count, self.window_size, 
                                                      self.mid_pos, self.right_pos, self.left_pos),
            TargetType.RED
        )
        self.assertEqual(
            ButtonHandler.get_target_type_for_position(self.led_count - 1, self.led_count, self.window_size, 
                                                      self.mid_pos, self.right_pos, self.left_pos),
            TargetType.RED
        )
        self.assertEqual(
            ButtonHandler.get_target_type_for_position(self.mid_pos, self.led_count, self.window_size, 
                                                      self.mid_pos, self.right_pos, self.left_pos),
            TargetType.BLUE
        )
        self.assertEqual(
            ButtonHandler.get_target_type_for_position(self.right_pos, self.led_count, self.window_size, 
                                                      self.mid_pos, self.right_pos, self.left_pos),
            TargetType.GREEN
        )
        self.assertEqual(
            ButtonHandler.get_target_type_for_position(self.left_pos, self.led_count, self.window_size, 
                                                      self.mid_pos, self.right_pos, self.left_pos),
            TargetType.YELLOW
        )
        
        # Test position outside any window
        self.assertIsNone(
            ButtonHandler.get_target_type_for_position(30, self.led_count, self.window_size, 
                                                     self.mid_pos, self.right_pos, self.left_pos)
        )
    
    def test_get_keys_for_target(self):
        """Test the get_keys_for_target static method."""
        # Test keys for each target type
        self.assertEqual(ButtonHandler.get_keys_for_target(TargetType.RED), [pygame.K_r, pygame.K_UP])
        self.assertEqual(ButtonHandler.get_keys_for_target(TargetType.BLUE), [pygame.K_b, pygame.K_DOWN])
        self.assertEqual(ButtonHandler.get_keys_for_target(TargetType.GREEN), [pygame.K_g, pygame.K_RIGHT])
        self.assertEqual(ButtonHandler.get_keys_for_target(TargetType.YELLOW), [pygame.K_y, pygame.K_LEFT])
    
    def test_get_window_position_for_target(self):
        """Test the get_window_position_for_target static method."""
        # Test window positions for each target type
        with patch('button_handler.MID_TARGET_POS', self.mid_pos), \
             patch('button_handler.RIGHT_TARGET_POS', self.right_pos), \
             patch('button_handler.LEFT_TARGET_POS', self.left_pos):
            self.assertEqual(ButtonHandler.get_window_position_for_target(TargetType.RED), 0)
            self.assertEqual(ButtonHandler.get_window_position_for_target(TargetType.BLUE), int(self.mid_pos))
            self.assertEqual(ButtonHandler.get_window_position_for_target(TargetType.GREEN), int(self.right_pos))
            self.assertEqual(ButtonHandler.get_window_position_for_target(TargetType.YELLOW), int(self.left_pos))
    
    @patch('pygame.key.get_pressed')
    def test_handle_keypress_correct_key(self, mock_get_pressed):
        """Test handle_keypress with correct key press."""
        # Mock key press for red target
        keys_dict = {pygame.K_r: True}
        mock_get_pressed.return_value = MagicMock(__getitem__=lambda _, key: keys_dict.get(key, False))
        
        # Test with position in red target window
        with patch.object(self.button_handler, 'get_target_type', return_value=TargetType.RED):
            score, target_hit, error_feedback = self.button_handler.handle_keypress(0, 1.0, 1000)
            self.assertEqual(score, 1.25)
            self.assertEqual(target_hit, "red")
            self.assertIsNone(error_feedback)
    
    @patch('pygame.key.get_pressed')
    def test_handle_keypress_wrong_key(self, mock_get_pressed):
        """Test handle_keypress with wrong key press."""
        # Mock key press for blue target when in red window
        keys_dict = {pygame.K_b: True}
        mock_get_pressed.return_value = MagicMock(__getitem__=lambda _, key: keys_dict.get(key, False))
        
        # Test with position in red target window
        with patch.object(self.button_handler, 'get_target_type', return_value=TargetType.RED):
            score, target_hit, error_feedback = self.button_handler.handle_keypress(0, 1.0, 1000)
            self.assertEqual(score, 0.75)
            self.assertEqual(target_hit, "none")
            self.assertIsNotNone(error_feedback)
            self.assertEqual(error_feedback[0], ButtonHandler.get_window_position_for_target(TargetType.BLUE))
    
    @patch('pygame.key.get_pressed')
    def test_handle_keypress_out_of_window(self, mock_get_pressed):
        """Test handle_keypress with key press outside its window."""
        # Mock key press for red target
        keys_dict = {pygame.K_r: True}
        mock_get_pressed.return_value = MagicMock(__getitem__=lambda _, key: keys_dict.get(key, False))
        
        # Test with position not in red target window
        with patch.object(self.button_handler, '_check_for_out_of_window_presses', 
                         return_value=(0.75, "none", (0, TARGET_COLORS[TargetType.RED]))):
            score, target_hit, error_feedback = self.button_handler.handle_keypress(30, 1.0, 1000)
            self.assertEqual(score, 0.75)
            self.assertEqual(target_hit, "none")
            self.assertIsNotNone(error_feedback)
    
    def test_reset_flags(self):
        """Test reset_flags method."""
        # Set initial state
        self.button_handler.button_states = {"r": True, "b": True, "g": True, "y": True}
        self.button_handler.penalty_applied = True
        self.button_handler.round_active = False
        
        # Test entering a valid window
        with patch.object(self.button_handler, 'is_in_valid_window', return_value=True):
            self.button_handler.reset_flags(0)
            self.assertEqual(self.button_handler.button_states, {"r": False, "b": False, "g": False, "y": False})
            self.assertFalse(self.button_handler.penalty_applied)
            self.assertTrue(self.button_handler.round_active)
        
        # Test leaving a valid window
        with patch.object(self.button_handler, 'is_in_valid_window', return_value=False):
            self.button_handler.reset_flags(30)
            self.assertFalse(self.button_handler.round_active)

if __name__ == '__main__':
    unittest.main()
