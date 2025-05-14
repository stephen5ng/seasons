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
        # Patch DisplayManager to avoid creating actual instances
        self.display_mock = MagicMock()
        
        with patch('trail_visualization.DisplayManager', return_value=self.display_mock):
            self.visualizer = HitTrailVisualizer(
                led_count=100,
                initial_score=2.0,
                auto_mode=False,
                speed=2
            )
    
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
        initial_score = self.visualizer.score
        
        # Add a hit
        self.visualizer.add_hit(TargetType.RED)
        
        # Verify score increased
        self.assertEqual(self.visualizer.score, initial_score + 0.25)
    
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
        # Draw the hit trail
        self.visualizer.draw_hit_trail()
        
        # Verify display.set_hit_trail_pixel was called
        self.display_mock.set_hit_trail_pixel.assert_called()


if __name__ == '__main__':
    unittest.main() 