import unittest
import pygame
import math
from unittest.mock import MagicMock, patch
from pygame import Color, Surface
from display_manager import DisplayManager

class DisplayManagerTest(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Initialize pygame for testing
        pygame.init()
        
        # Mock IS_RASPBERRY_PI to always be False for tests
        self.is_raspberry_pi_patcher = patch('display_manager.IS_RASPBERRY_PI', False)
        self.is_raspberry_pi_patcher.start()
        
        # Create display manager with test dimensions
        self.screen_width = 100
        self.screen_height = 100
        self.scaling_factor = 2
        self.led_count = 60
        self.display_manager = DisplayManager(
            screen_width=self.screen_width,
            screen_height=self.screen_height,
            scaling_factor=self.scaling_factor,
            led_count=self.led_count,
            led_pin=18,
            led_freq_hz=800000,
            led_dma=10,
            led_invert=False,
            led_brightness=255,
            led_channel=0
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.is_raspberry_pi_patcher.stop()
        pygame.quit()
    
    def test_init(self):
        """Test initialization of display manager."""
        self.assertEqual(self.display_manager.screen_width, self.screen_width)
        self.assertEqual(self.display_manager.screen_height, self.screen_height)
        self.assertEqual(self.display_manager.scaling_factor, self.scaling_factor)
        self.assertIsNotNone(self.display_manager.pygame_surface)
        self.assertEqual(self.display_manager.pygame_surface.get_width(), self.screen_width)
        self.assertEqual(self.display_manager.pygame_surface.get_height(), self.screen_height)
        self.assertIsNotNone(self.display_manager.display_surface)
        self.assertEqual(self.display_manager.display_surface.get_width(), self.screen_width * self.scaling_factor)
        self.assertEqual(self.display_manager.display_surface.get_height(), self.screen_height * self.scaling_factor)
    
    def test_clear(self):
        """Test clearing the display."""
        # Set some pixels
        test_color = Color(255, 0, 0)
        center_x = 50
        center_y = 50
        radius = 10
        led_count = 60
        pos = 5
        
        # Calculate expected position
        expected_x, expected_y = self.display_manager._get_ring_position(
            pos, center_x, center_y, radius, led_count
        )
        
        # Set pixel and verify it was set
        self.display_manager.set_target_pixel(pos, test_color, center_x, center_y, radius, led_count)
        self.assertEqual(self.display_manager.pygame_surface.get_at((expected_x, expected_y)), test_color)
        
        # Clear the display
        self.display_manager.clear()
        self.assertEqual(self.display_manager.pygame_surface.get_at((expected_x, expected_y)), Color(0, 0, 0))
    
    def test_set_target_pixel(self):
        """Test setting a pixel in the target ring."""
        # Set a pixel in the target ring
        center_x = 50
        center_y = 50
        radius = 10
        led_count = 60
        test_color = Color(0, 255, 0)
        
        # Set pixel at position 0 (should be at the top of the circle)
        self.display_manager.set_target_pixel(0, test_color, center_x, center_y, radius, led_count)
        
        # Calculate expected position
        expected_x, expected_y = self.display_manager._get_ring_position(
            0, center_x, center_y, radius, led_count
        )
        
        # Check that the pixel was set at the expected position
        self.assertEqual(self.display_manager.pygame_surface.get_at((expected_x, expected_y)), test_color)
    
    def test_get_ring_position(self):
        """Test calculation of ring positions."""
        center_x = 50
        center_y = 50
        radius = 10
        led_count = 60
        
        # Test position at 0 (top of circle)
        x, y = DisplayManager._get_ring_position(0, center_x, center_y, radius, led_count)
        self.assertEqual(x, center_x)
        self.assertEqual(y, center_y - radius)
        
        # Test position at 1/4 of the way around (right side)
        x, y = DisplayManager._get_ring_position(led_count // 4, center_x, center_y, radius, led_count)
        self.assertAlmostEqual(x, center_x + radius, delta=1)
        self.assertAlmostEqual(y, center_y, delta=1)
        
        # Test position at 1/2 of the way around (bottom)
        x, y = DisplayManager._get_ring_position(led_count // 2, center_x, center_y, radius, led_count)
        self.assertAlmostEqual(x, center_x, delta=1)
        self.assertAlmostEqual(y, center_y + radius, delta=1)
        
        # Test position at 3/4 of the way around (left side)
        x, y = DisplayManager._get_ring_position(3 * led_count // 4, center_x, center_y, radius, led_count)
        self.assertAlmostEqual(x, center_x - radius, delta=1)
        self.assertAlmostEqual(y, center_y, delta=1)
    
    @patch('pygame.draw.line')
    def test_draw_score_lines(self, mock_draw_line):
        """Test drawing score lines."""
        # Mock functions
        get_rainbow_color = MagicMock(return_value=Color(255, 0, 0))
        get_score_line_color = MagicMock(return_value=Color(0, 255, 0))
        
        # Call draw_score_lines with test parameters
        self.display_manager.draw_score_lines(
            score=2.5,
            current_time=1000,
            flash_intensity=0.5,
            flash_type="red",
            score_line_color=Color(0, 0, 255),
            high_score_threshold=5.0,
            score_flash_duration_ms=1000,
            score_line_animation_time_ms=100,
            score_line_height=0.5,
            score_line_spacing=0.5,
            get_rainbow_color_func=get_rainbow_color,
            get_score_line_color_func=get_score_line_color
        )
        
        # Verify that pygame.draw.line was called the expected number of times
        # For score 2.5, there should be 5 lines (int(2.5 * 2))
        self.assertEqual(mock_draw_line.call_count, 5)

if __name__ == '__main__':
    unittest.main() 