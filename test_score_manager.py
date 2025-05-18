"""Unit tests for the ScoreManager class."""

import pytest
from pygame import Color

from score_manager import ScoreManager
from game_constants import TargetType, TARGET_COLORS, INITIAL_HIT_SPACING

def test_calculate_score():
    """Test score calculation from total hits."""
    # Test with different hit counts
    assert ScoreManager.calculate_score(0) == 0.0
    assert ScoreManager.calculate_score(4) == 1.0
    assert ScoreManager.calculate_score(8) == 2.0
    assert ScoreManager.calculate_score(12) == 3.0

def test_calculate_score_penalty():
    """Test score penalty calculation."""
    # Test with different score values
    assert ScoreManager.calculate_score_penalty(1.0) == 0.75
    assert ScoreManager.calculate_score_penalty(2.0) == 1.5
    assert ScoreManager.calculate_score_penalty(0.25) == 0.0
    
    # Test with fractional scores
    assert ScoreManager.calculate_score_penalty(1.75) == 1.25
    assert ScoreManager.calculate_score_penalty(0.5) == 0.25

def test_get_score_line_color():
    """Test score line color calculation."""
    base_color = Color(255, 255, 255)
    
    # Test with no flash
    assert ScoreManager.get_score_line_color(base_color, 0.0, "red") == base_color
    
    # Test with red flash
    red_flash = ScoreManager.get_score_line_color(base_color, 1.0, "red")
    assert red_flash.r == 255
    assert red_flash.g < 255
    assert red_flash.b < 255
    
    # Test with blue flash
    blue_flash = ScoreManager.get_score_line_color(base_color, 1.0, "blue")
    assert blue_flash.r < 255
    assert blue_flash.g < 255
    assert blue_flash.b == 255
    
    # Test with green flash
    green_flash = ScoreManager.get_score_line_color(base_color, 1.0, "green")
    assert green_flash.r < 255
    assert green_flash.g == 255
    assert green_flash.b < 255
    
    # Test with yellow flash
    yellow_flash = ScoreManager.get_score_line_color(base_color, 1.0, "yellow")
    assert yellow_flash.r == 255
    assert yellow_flash.g == 255
    assert yellow_flash.b < 255
