import unittest
import asyncio
import pygame
from seasons import (
    GameState, ButtonPressHandler, TargetType, TARGET_COLORS,
    NUMBER_OF_LEDS, TARGET_WINDOW_SIZE, MID_TARGET_POS,
    RIGHT_TARGET_POS, LEFT_TARGET_POS
)

class TestButtonPressHandler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.error_sound = pygame.mixer.Sound("music/error.mp3")
        self.handler = ButtonPressHandler(self.error_sound)

    def test_is_in_valid_window(self):
        # Test positions within each target window
        self.assertTrue(self.handler.is_in_valid_window(0))  # Red target
        self.assertTrue(self.handler.is_in_valid_window(TARGET_WINDOW_SIZE - 1))  # Red target
        self.assertTrue(self.handler.is_in_valid_window(int(MID_TARGET_POS)))  # Blue target
        self.assertTrue(self.handler.is_in_valid_window(int(RIGHT_TARGET_POS)))  # Green target
        self.assertTrue(self.handler.is_in_valid_window(int(LEFT_TARGET_POS)))  # Yellow target
        
        # Test positions outside target windows
        self.assertFalse(self.handler.is_in_valid_window(TARGET_WINDOW_SIZE + 1))
        self.assertFalse(self.handler.is_in_valid_window(int(MID_TARGET_POS) + TARGET_WINDOW_SIZE + 1))

    def test_get_target_type(self):
        # Test each target type
        self.assertEqual(self.handler.get_target_type(0), TargetType.RED)
        self.assertEqual(self.handler.get_target_type(int(MID_TARGET_POS)), TargetType.BLUE)
        self.assertEqual(self.handler.get_target_type(int(RIGHT_TARGET_POS)), TargetType.GREEN)
        self.assertEqual(self.handler.get_target_type(int(LEFT_TARGET_POS)), TargetType.YELLOW)
        
        # Test positions outside target windows
        self.assertIsNone(self.handler.get_target_type(TARGET_WINDOW_SIZE + 1))

    def test_apply_penalty(self):
        # Test penalty application
        score = 4.0
        new_score = self.handler.apply_penalty(score)
        self.assertLess(new_score, score)
        self.assertGreaterEqual(new_score, 0)

class TestGameState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.game_state = self.loop.run_until_complete(self._create_game_state())

    def tearDown(self):
        self.loop.run_until_complete(self.game_state.http_session.close())
        self.loop.close()

    async def _create_game_state(self):
        return GameState()

    def test_update_score(self):
        # Test score increase
        initial_score = self.game_state.score
        self.game_state.update_score(initial_score + 0.25, "red", 0.0)
        self.assertEqual(self.game_state.score, initial_score + 0.25)
        
        # Test hit trail clearing
        self.game_state.hit_colors = [TARGET_COLORS[TargetType.RED]] * 100
        self.game_state.hit_spacing = 4
        self.game_state.update_score(self.game_state.score + 0.25, "red", 0.0)
        # The hit trail should be cleared and a new hit added
        self.assertEqual(len(self.game_state.hit_colors), 1)  # Should have one hit after clearing
        self.assertEqual(self.game_state.hit_spacing, 16)  # Should reset to initial spacing

    def test_calculate_led_position(self):
        # Test LED position calculation
        position = self.game_state.calculate_led_position(0, 0.0)
        self.assertEqual(position, 0)
        
        position = self.game_state.calculate_led_position(4, 0.5)
        self.assertGreater(position, 0)
        self.assertLess(position, NUMBER_OF_LEDS)

    def test_get_score_flash_intensity(self):
        # Test flash intensity calculation
        self.game_state.score_flash_start_beat = 0.0
        intensity = self.game_state.get_score_flash_intensity(0.0)
        self.assertEqual(intensity, 1.0)
        
        intensity = self.game_state.get_score_flash_intensity(2.0)
        self.assertEqual(intensity, 0.0)

if __name__ == '__main__':
    unittest.main() 