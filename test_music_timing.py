import unittest
from music_timing import MusicTiming

class MusicTimingTest(unittest.TestCase):
    def test_calculate_beat_timing(self):
        """Test beat timing calculation."""
        # 1000ms after start, with 1 beat per 250ms (4 beats per second)
        beat, beat_in_measure, beat_float, fractional_beat = MusicTiming.calculate_beat_timing(
            current_time_ms=1000,
            start_time_ms=0,
            beat_per_ms=1/250,
            beats_per_measure=4
        )
        
        self.assertEqual(beat, 4)  # 1000ms / 250ms = 4 beats
        self.assertEqual(beat_in_measure, 0)  # 4 % 4 = 0 (start of a measure)
        self.assertEqual(beat_float, 4.0)
        self.assertEqual(fractional_beat, 0.0)
        
        # 1125ms after start (4.5 beats)
        beat, beat_in_measure, beat_float, fractional_beat = MusicTiming.calculate_beat_timing(
            current_time_ms=1125,
            start_time_ms=0,
            beat_per_ms=1/250,
            beats_per_measure=4
        )
        
        self.assertEqual(beat, 4)  # int(4.5) = 4
        self.assertEqual(beat_in_measure, 0)  # 4 % 4 = 0
        self.assertEqual(beat_float, 4.5)
        self.assertEqual(fractional_beat, 0.5)
    
    def test_calculate_target_music_time(self):
        """Test target music time calculation."""
        # Score 2, 500ms into measure, 3s per measure
        target_time = MusicTiming.calculate_target_music_time(
            score=2,
            measure_start_ms=1000,
            current_time_ms=1500,
            seconds_per_measure=3
        )
        
        # Expected: 2 measures (2*3s) + 0.5s offset = 6.5s
        self.assertEqual(target_time, 6.5)
        
        # Score 0, 250ms into measure, 3s per measure
        target_time = MusicTiming.calculate_target_music_time(
            score=0.75,  # Should use int(0.75) = 0
            measure_start_ms=2000,
            current_time_ms=2250,
            seconds_per_measure=3
        )
        
        # Expected: 0 measures (0*3s) + 0.25s offset = 0.25s
        self.assertEqual(target_time, 0.25)
    
    def test_should_sync_music(self):
        """Test music sync decision."""
        # Positions within threshold
        self.assertFalse(MusicTiming.should_sync_music(10.1, 10.2, 0.2))
        
        # Positions at threshold
        self.assertFalse(MusicTiming.should_sync_music(10.0, 10.2, 0.2))
        
        # Positions beyond threshold
        self.assertTrue(MusicTiming.should_sync_music(10.0, 10.21, 0.2))
        self.assertTrue(MusicTiming.should_sync_music(10.3, 10.0, 0.2))
        
        # Custom threshold
        self.assertFalse(MusicTiming.should_sync_music(10.0, 10.3, 0.5))
        self.assertTrue(MusicTiming.should_sync_music(10.0, 10.6, 0.5))
    
    def test_calculate_target_beats(self):
        """Test target beat calculation."""
        # 5 seconds at 4 beats per second (1 beat per 250ms)
        target_beats = MusicTiming.calculate_target_beats(
            target_time_s=5.0,
            beat_per_ms=1/250
        )
        
        self.assertEqual(target_beats, 20)  # 5s * 4 beats/s = 20 beats
        
        # 2.5 seconds at 2 beats per second (1 beat per 500ms)
        target_beats = MusicTiming.calculate_target_beats(
            target_time_s=2.5,
            beat_per_ms=1/500
        )
        
        self.assertEqual(target_beats, 5)  # 2.5s * 2 beats/s = 5 beats

if __name__ == '__main__':
    unittest.main()
