import unittest
import math
from led_position import LEDPosition

class LEDPositionTest(unittest.TestCase):
    def test_calculate_position_start_of_measure(self):
        """Test position at the start of a measure."""
        # At beat 0 with no fractional part (start of measure)
        position = LEDPosition.calculate_position(
            beat_in_measure=0, 
            fractional_beat=0.0, 
            beats_per_measure=4, 
            number_of_leds=80
        )
        self.assertEqual(position, 0)
    
    def test_calculate_position_middle_of_measure(self):
        """Test position in the middle of a measure."""
        # At beat 2 with no fractional part (halfway through a 4-beat measure)
        position = LEDPosition.calculate_position(
            beat_in_measure=2, 
            fractional_beat=0.0, 
            beats_per_measure=4, 
            number_of_leds=80
        )
        self.assertEqual(position, 40)  # 80 * (2/4) = 40
    
    def test_calculate_position_fractional(self):
        """Test position with fractional beat."""
        # At beat 1 with 0.5 fractional part (37.5% through a 4-beat measure)
        position = LEDPosition.calculate_position(
            beat_in_measure=1, 
            fractional_beat=0.5, 
            beats_per_measure=4, 
            number_of_leds=80
        )
        self.assertEqual(position, 30)  # 80 * (1/4 + 0.5/4) = 80 * 0.375 = 30
    
    def test_calculate_position_end_of_measure(self):
        """Test position at the end of a measure."""
        # At beat 3 with 0.999 fractional part (almost at the end of a 4-beat measure)
        position = LEDPosition.calculate_position(
            beat_in_measure=3, 
            fractional_beat=0.999, 
            beats_per_measure=4, 
            number_of_leds=80
        )
        self.assertEqual(position, 79)  # Almost 80, but should be 79 (0-indexed)
    
    def test_get_ring_position_top(self):
        """Test ring position at the top (12 o'clock)."""
        # Position 0 should be at the top (12 o'clock)
        x, y = LEDPosition.get_ring_position(
            led_index=0, 
            radius=100, 
            number_of_leds=80
        )
        self.assertEqual(x, 0)
        self.assertAlmostEqual(y, -100, delta=1)  # Allow for rounding
    
    def test_get_ring_position_right(self):
        """Test ring position at the right (3 o'clock)."""
        # Position 20 (1/4 of 80) should be at the right (3 o'clock)
        x, y = LEDPosition.get_ring_position(
            led_index=20, 
            radius=100, 
            number_of_leds=80
        )
        self.assertAlmostEqual(x, 100, delta=1)  # Allow for rounding
        self.assertAlmostEqual(y, 0, delta=1)  # Allow for rounding

if __name__ == '__main__':
    unittest.main()
