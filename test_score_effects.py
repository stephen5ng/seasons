import unittest
from score_effects import ScoreEffects

class ScoreEffectsTest(unittest.TestCase):
    def test_get_flash_intensity_no_flash(self):
        """Test that intensity is 0 when flash_start_beat is None."""
        intensity = ScoreEffects.get_flash_intensity(10.5, None)
        self.assertEqual(intensity, 0.0)
    
    def test_get_flash_intensity_just_started(self):
        """Test intensity right when flash starts."""
        current_beat = 15.0
        flash_start = 15.0
        intensity = ScoreEffects.get_flash_intensity(current_beat, flash_start)
        self.assertEqual(intensity, 1.0)  # Just started, so full intensity
    
    def test_get_flash_intensity_halfway(self):
        """Test intensity halfway through flash duration."""
        current_beat = 16.0
        flash_start = 15.0
        # After 1 beat of a 2-beat effect, intensity should be 0.5
        intensity = ScoreEffects.get_flash_intensity(current_beat, flash_start)
        self.assertEqual(intensity, 0.5)
    
    def test_get_flash_intensity_ended(self):
        """Test intensity after flash has ended."""
        current_beat = 17.5
        flash_start = 15.0
        # After 2.5 beats, the 2-beat effect should be done
        intensity = ScoreEffects.get_flash_intensity(current_beat, flash_start)
        self.assertEqual(intensity, 0.0)
    
    def test_get_flash_intensity_almost_done(self):
        """Test intensity right before flash ends."""
        current_beat = 16.9
        flash_start = 15.0
        # After 1.9 beats of a 2-beat effect, intensity should be 0.05
        intensity = ScoreEffects.get_flash_intensity(current_beat, flash_start)
        self.assertAlmostEqual(intensity, 0.05, places=2)

if __name__ == '__main__':
    unittest.main()
