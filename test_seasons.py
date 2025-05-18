"""Unit tests for the seasons game."""

import pytest
from unittest.mock import MagicMock, patch
from pygame import Color

from seasons import GameState, get_rainbow_color, get_score_line_color
from game_constants import TargetType, TARGET_COLORS
from trail_visualization import TrailVisualizer

class TestGameState:
    """Test cases for the GameState class."""
    
    @pytest.fixture
    def game_state(self):
        """Create a GameState instance for testing."""
        with patch('seasons.WLEDManager'), \
             patch('seasons.AudioManager'), \
             patch('seasons.ButtonHandler'), \
             patch('seasons.TrailStateManager'):
            return GameState()
    
    @pytest.fixture
    def hit_trail_visualizer(self):
        """Create a mock TrailVisualizer for testing."""
        visualizer = MagicMock(spec=TrailVisualizer)
        visualizer.simple_hit_trail.total_hits = 0
        visualizer.get_score.return_value = 0.0
        return visualizer
    
    def test_handle_hits(self, game_state, hit_trail_visualizer):
        """Test handling successful hits."""
        display = MagicMock()
        
        # Test with no hits
        game_state.handle_hits([], 0, hit_trail_visualizer, 0.0, display)
        hit_trail_visualizer.add_hit.assert_not_called()
        
        # Test with hits
        hit_trail_visualizer.simple_hit_trail.total_hits = 0
        game_state.handle_hits([TargetType.RED], 0, hit_trail_visualizer, 1.0, display)
        hit_trail_visualizer.add_hit.assert_called_once_with(TargetType.RED)

def test_get_rainbow_color():
    """Test rainbow color generation."""
    # Test red to yellow transition
    color = get_rainbow_color(0, 0)
    assert color.r == 255
    assert color.g == 0
    assert color.b == 0
    
    # Test yellow to green transition
    color = get_rainbow_color(COLOR_CYCLE_TIME_MS / 6, 0)
    assert color.r < 255
    assert color.g == 255
    assert color.b == 0
    
    # Test green to cyan transition
    color = get_rainbow_color(COLOR_CYCLE_TIME_MS / 3, 0)
    assert color.r == 0
    assert color.g == 255
    assert color.b > 0
    
    # Test cyan to blue transition
    color = get_rainbow_color(COLOR_CYCLE_TIME_MS / 2, 0)
    assert color.r == 0
    assert color.g < 255
    assert color.b == 255
    
    # Test blue to magenta transition
    color = get_rainbow_color(2 * COLOR_CYCLE_TIME_MS / 3, 0)
    assert color.r > 0
    assert color.g == 0
    assert color.b == 255
    
    # Test magenta to red transition
    color = get_rainbow_color(5 * COLOR_CYCLE_TIME_MS / 6, 0)
    assert color.r == 255
    assert color.g == 0
    assert color.b > 0

def test_get_score_line_color():
    """Test score line color calculation."""
    base_color = Color(255, 255, 255)
    
    # Test with no flash
    assert get_score_line_color(base_color, 0.0, "red") == base_color
    
    # Test with red flash
    red_flash = get_score_line_color(base_color, 1.0, "red")
    assert red_flash.r == 255
    assert red_flash.g < 255
    assert red_flash.b < 255
    
    # Test with blue flash
    blue_flash = get_score_line_color(base_color, 1.0, "blue")
    assert blue_flash.r < 255
    assert blue_flash.g < 255
    assert blue_flash.b == 255
    
    # Test with green flash
    green_flash = get_score_line_color(base_color, 1.0, "green")
    assert green_flash.r < 255
    assert green_flash.g == 255
    assert green_flash.b < 255
    
    # Test with yellow flash
    yellow_flash = get_score_line_color(base_color, 1.0, "yellow")
    assert yellow_flash.r == 255
    assert yellow_flash.g == 255
    assert yellow_flash.b < 255 