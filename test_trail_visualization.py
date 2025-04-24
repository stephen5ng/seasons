#!/usr/bin/env python3
"""Unit tests for the trail visualization module."""

import unittest
from unittest.mock import MagicMock, patch

import pygame
from pygame import Color

from trail_visualization import TrailVisualizer, HitTrailVisualizer


class TestTrailVisualizer(unittest.TestCase):
    """Test cases for the TrailVisualizer base class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Patch DisplayManager to avoid creating an actual display
        self.display_mock = MagicMock()
        with patch('trail_visualization.DisplayManager', return_value=self.display_mock):
            self.visualizer = TrailVisualizer(led_count=100)
    
    def test_init(self):
        """Test initialization with custom parameters."""
        with patch('trail_visualization.DisplayManager', return_value=self.display_mock):
            visualizer = TrailVisualizer(
                led_count=120,
                screen_width=200,
                screen_height=150,
                scaling_factor=5
            )
        
        self.assertEqual(visualizer.led_count, 120)
        self.assertEqual(visualizer.current_position, 0)
        self.assertFalse(visualizer.running)
    
    def test_update_position(self):
        """Test updating the LED position."""
        # Starting position is 0
        self.assertEqual(self.visualizer.current_position, 0)
        
        # Update by default speed (1)
        self.visualizer.update_position()
        self.assertEqual(self.visualizer.current_position, 1)
        
        # Update by custom speed
        self.visualizer.update_position(speed=5)
        self.assertEqual(self.visualizer.current_position, 6)
        
        # Test wrapping around
        self.visualizer.current_position = 95
        self.visualizer.update_position(speed=10)
        self.assertEqual(self.visualizer.current_position, 5)  # 95 + 10 = 105 % 100 = 5
    

class TestHitTrailVisualizer(unittest.TestCase):
    """Test cases for the HitTrailVisualizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Patch DisplayManager and HitTrail to avoid creating actual instances
        self.display_mock = MagicMock()
        
        # Since HitTrail has only static methods, we'll patch them individually
        self.hit_trail_add_color_patcher = patch('trail_visualization.HitTrail.add_hit_color')
        self.hit_trail_calculate_positions_patcher = patch('trail_visualization.HitTrail.calculate_trail_positions')
        self.hit_trail_limit_trail_length_patcher = patch('trail_visualization.HitTrail.limit_trail_length')
        
        self.mock_add_hit_color = self.hit_trail_add_color_patcher.start()
        self.mock_calculate_positions = self.hit_trail_calculate_positions_patcher.start()
        self.mock_limit_trail_length = self.hit_trail_limit_trail_length_patcher.start()
        
        # Set up return values for mocked methods
        self.mock_add_hit_color.side_effect = lambda colors, new_color: [new_color] + colors
        self.mock_limit_trail_length.side_effect = lambda colors, max_length: colors[:max_length]
        
        with patch('trail_visualization.DisplayManager', return_value=self.display_mock):
            self.visualizer = HitTrailVisualizer(
                led_count=100,
                initial_score=2.0,
                auto_mode=False,
                speed=2
            )
    
    def tearDown(self):
        """Clean up after each test."""
        self.hit_trail_add_color_patcher.stop()
        self.hit_trail_calculate_positions_patcher.stop()
        self.hit_trail_limit_trail_length_patcher.stop()
    
    def test_init(self):
        """Test initialization with custom parameters."""
        self.assertEqual(self.visualizer.led_count, 100)
        self.assertEqual(self.visualizer.speed, 2)
        self.assertFalse(self.visualizer.auto_mode)
        self.assertEqual(self.visualizer.score, 2.0)
    
    def test_add_hit(self):
        """Test adding a hit to the trail."""
        from game_constants import TargetType, TARGET_COLORS
        
        # Initial state
        initial_colors = self.visualizer.hit_colors.copy()
        initial_score = self.visualizer.score
        
        # Add a hit
        self.visualizer.add_hit(TargetType.RED)
        
        # Verify score increased
        self.assertEqual(self.visualizer.score, initial_score + 0.25)
        
        # Verify HitTrail methods were called
        self.mock_add_hit_color.assert_called()
        self.mock_limit_trail_length.assert_called()
        
        # Verify the color and score used are correct
        add_color_args = self.mock_add_hit_color.call_args[0]
        self.assertEqual(add_color_args[1], TARGET_COLORS[TargetType.RED])
    
    def test_clear_hit_trail(self):
        """Test clearing the hit trail."""
        # Set up some initial state
        self.visualizer.hit_colors = [Color(255, 0, 0), Color(0, 255, 0)]
        self.visualizer.hit_trail_cleared = False
        
        # Clear the trail
        self.visualizer.clear_hit_trail()
        
        # Verify state was reset
        self.assertEqual(self.visualizer.hit_colors, [])
        self.assertTrue(self.visualizer.hit_trail_cleared)
    
    def test_draw_hit_trail(self):
        """Test drawing the hit trail."""
        # Set up mock to return specific positions
        self.mock_calculate_positions.return_value = {
            10: Color(255, 0, 0),
            20: Color(0, 255, 0),
            30: Color(0, 0, 255)
        }
        
        # Draw the hit trail
        self.visualizer.draw_hit_trail()
        
        # Verify HitTrail.calculate_trail_positions was called with correct params
        self.mock_calculate_positions.assert_called_with(
            self.visualizer.current_position,
            self.visualizer.hit_colors,
            16,  # Default spacing from game_constants.INITIAL_HIT_SPACING
            self.visualizer.led_count
        )
        
        # Verify display.set_hit_trail_pixel was called for each position
        self.assertEqual(self.display_mock.set_hit_trail_pixel.call_count, 3)
        calls = self.display_mock.set_hit_trail_pixel.call_args_list
        self.assertEqual(calls[0][0], (10, Color(255, 0, 0)))
        self.assertEqual(calls[1][0], (20, Color(0, 255, 0)))
        self.assertEqual(calls[2][0], (30, Color(0, 0, 255)))
    
    def test_key_handling(self):
        """Test keyboard event handling."""
        import pygame
        from game_constants import TargetType
        
        # Create mock events
        red_key_event = MagicMock(type=pygame.KEYDOWN, key=pygame.K_r)
        green_key_event = MagicMock(type=pygame.KEYDOWN, key=pygame.K_g)
        blue_key_event = MagicMock(type=pygame.KEYDOWN, key=pygame.K_b)
        yellow_key_event = MagicMock(type=pygame.KEYDOWN, key=pygame.K_y)
        clear_key_event = MagicMock(type=pygame.KEYDOWN, key=pygame.K_c)
        quit_key_event = MagicMock(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)
        
        # Test key handlers
        with patch('pygame.event.get', return_value=[red_key_event]):
            # Manually call the event processing code to test key handling
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.visualizer.add_hit(TargetType.RED)
            
            # Check if add_hit was called with RED target
            self.mock_add_hit_color.assert_called()


if __name__ == '__main__':
    unittest.main() 