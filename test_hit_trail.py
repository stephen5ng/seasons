import unittest
from pygame import Color
from hit_trail import HitTrail

class HitTrailTest(unittest.TestCase):
    def test_calculate_total_space(self):
        """Test calculation of total space needed for hit trail."""
        # Empty trail with spacing of 10
        colors = []
        spacing = 10
        total_space = HitTrail.calculate_total_space(colors, spacing)
        self.assertEqual(total_space, 10)  # (0+1) * 10 = 10
        
        # Trail with 3 colors and spacing of 8
        colors = [Color(255, 0, 0), Color(0, 255, 0), Color(0, 0, 255)]
        spacing = 8
        total_space = HitTrail.calculate_total_space(colors, spacing)
        self.assertEqual(total_space, 32)  # (3+1) * 8 = 32
    
    def test_should_adjust_spacing(self):
        """Test determination of whether spacing needs adjustment."""
        # Trail needs 40 units but only 30 available
        colors = [Color(255, 0, 0), Color(0, 255, 0), Color(0, 0, 255)]
        spacing = 10
        max_leds = 30
        self.assertTrue(HitTrail.should_adjust_spacing(colors, spacing, max_leds))
        
        # Trail needs 20 units with 30 available
        colors = [Color(255, 0, 0)]
        spacing = 10
        max_leds = 30
        self.assertFalse(HitTrail.should_adjust_spacing(colors, spacing, max_leds))
    
    def test_get_new_spacing(self):
        """Test calculation of new spacing."""
        # Current spacing above minimum
        current_spacing = 16
        new_spacing = HitTrail.get_new_spacing(current_spacing)
        self.assertEqual(new_spacing, 8)  # 16/2 = 8
        
        # Current spacing at minimum
        current_spacing = 4
        new_spacing = HitTrail.get_new_spacing(current_spacing)
        self.assertEqual(new_spacing, 0)  # Signal to clear trail
        
        # Current spacing below minimum
        current_spacing = 3
        new_spacing = HitTrail.get_new_spacing(current_spacing)
        self.assertEqual(new_spacing, 0)  # Signal to clear trail
        
        # Custom minimum
        current_spacing = 6
        new_spacing = HitTrail.get_new_spacing(current_spacing, min_spacing=5)
        self.assertEqual(new_spacing, 3)  # 6/2 = 3
    
    def test_add_hit_color(self):
        """Test adding a color to the hit trail."""
        # Add to empty trail
        colors = []
        new_color = Color(255, 0, 0)
        new_colors = HitTrail.add_hit_color(colors, new_color)
        self.assertEqual(len(new_colors), 1)
        self.assertEqual(new_colors[0], new_color)
        
        # Add to existing trail
        colors = [Color(0, 255, 0), Color(0, 0, 255)]
        new_color = Color(255, 0, 0)
        new_colors = HitTrail.add_hit_color(colors, new_color)
        self.assertEqual(len(new_colors), 3)
        self.assertEqual(new_colors[0], new_color)  # New color at beginning
        self.assertEqual(new_colors[1], Color(0, 255, 0))  # Original colors preserved
        self.assertEqual(new_colors[2], Color(0, 0, 255))
    
    def test_limit_trail_length(self):
        """Test limiting trail length."""
        # Trail within limit
        colors = [Color(255, 0, 0), Color(0, 255, 0)]
        max_length = 3
        limited_colors = HitTrail.limit_trail_length(colors, max_length)
        self.assertEqual(len(limited_colors), 2)  # No change
        
        # Trail exceeding limit
        colors = [Color(255, 0, 0), Color(0, 255, 0), Color(0, 0, 255), Color(255, 255, 0)]
        max_length = 2
        limited_colors = HitTrail.limit_trail_length(colors, max_length)
        self.assertEqual(len(limited_colors), 2)  # Truncated to 2
        self.assertEqual(limited_colors[0], Color(255, 0, 0))  # First two colors preserved
        self.assertEqual(limited_colors[1], Color(0, 255, 0))
    
    def test_calculate_trail_positions(self):
        """Test calculation of trail positions."""
        # Simple trail with integer spacing
        led_position = 10
        colors = [Color(255, 0, 0), Color(0, 255, 0)]
        spacing = 2
        number_of_leds = 20
        positions = HitTrail.calculate_trail_positions(led_position, colors, spacing, number_of_leds)
        self.assertEqual(len(positions), 2)
        self.assertEqual(positions[8], Color(255, 0, 0))  # 10 - (1*2) = 8
        self.assertEqual(positions[6], Color(0, 255, 0))  # 10 - (2*2) = 6
        
        # Trail with wrapping
        led_position = 1
        colors = [Color(255, 0, 0), Color(0, 255, 0)]
        spacing = 3
        number_of_leds = 10
        positions = HitTrail.calculate_trail_positions(led_position, colors, spacing, number_of_leds)
        self.assertEqual(len(positions), 2)
        self.assertEqual(positions[8], Color(255, 0, 0))  # (1 - (1*3)) % 10 = 8
        self.assertEqual(positions[5], Color(0, 255, 0))  # (1 - (2*3)) % 10 = 5

if __name__ == '__main__':
    unittest.main()
