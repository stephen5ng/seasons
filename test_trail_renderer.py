import unittest
from unittest.mock import Mock
import pygame
from pygame import Color
from trail_renderer import TrailRenderer
from game_constants import TARGET_COLORS, TargetType

class TrailRendererTest(unittest.TestCase):
    def setUp(self):
        # Use a fixed time for deterministic tests
        self.fixed_time = 123456
        self.mock_ticks = Mock(return_value=self.fixed_time)
        self.mock_rainbow = Mock(return_value=Color(100, 150, 200, 255))
        self.trail_renderer = TrailRenderer(get_ticks_func=self.mock_ticks, get_rainbow_color_func=self.mock_rainbow)

    def test_get_target_trail_color_basic(self):
        lit_colors = {5: Color(200, 100, 50, 255)}
        class DummyButtonHandler:
            def is_in_valid_window(self, pos): return False
            def get_target_type(self, pos): return None
        color = self.trail_renderer.get_target_trail_color(5, 0.5, lit_colors, DummyButtonHandler())
        self.assertEqual(color, Color(100, 50, 25, 255))

    def test_get_target_trail_color_with_target(self):
        lit_colors = {7: Color(20, 40, 60, 255)}
        class DummyButtonHandler:
            def is_in_valid_window(self, pos): return True
            def get_target_type(self, pos): return TargetType.RED
        color = self.trail_renderer.get_target_trail_color(7, 0.25, lit_colors, DummyButtonHandler())
        expected = Color(int(TARGET_COLORS[TargetType.RED][0]*0.25), 0, 0, 255)
        self.assertEqual(color, expected)

    def test_draw_trail_with_easing(self):
        positions = {3: 120.0, 5: 122.0}
        fade_duration = 5.0
        class DummyEase:
            def ease(self, elapsed): return 1.0 - min(elapsed / fade_duration, 1.0)
        displayed = []
        def color_func(brightness, pos): return Color(int(255 * brightness), 0, 0, 255)
        def display_func(pos, color): displayed.append((pos, color))
        # Simulate current_time_s = 125.1 (so elapsed for 3 is 5.1 > fade_duration)
        self.trail_renderer.get_ticks = Mock(return_value=125100)
        positions_to_remove = self.trail_renderer.draw_trail_with_easing(
            positions, fade_duration, DummyEase(), color_func, display_func)
        # 3: elapsed = 5.1, should be removed; 5: elapsed = 3.1, should be drawn
        expected_brightness = 1.0 - (3.1 / 5.0)
        expected_color = Color(int(255 * expected_brightness), 0, 0, 255)
        self.assertIn((5, expected_color), displayed)
        self.assertIn(3, positions_to_remove)
        self.assertNotIn(5, positions_to_remove)

if __name__ == '__main__':
    pygame.init()
    unittest.main()
