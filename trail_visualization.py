#!/usr/bin/env python3
"""
Trail Visualization - Common utilities for visualizing LED trails

This module provides shared functionality for visualizing different types of LED trails
including hit trails and main trails. It's used by both the main
game (seasons.py) and the standalone hit trail viewer (hit_trail_display.py).
"""

import asyncio
import pygame
from pygame import Color
from typing import List, Dict, Any, TYPE_CHECKING

import game_constants
from hit_trail import HitTrail
from display_manager import DisplayManager
from get_key import get_key
from simple_hit_trail import SimpleHitTrail

if TYPE_CHECKING:
    from seasons import GameState


class TrailVisualizer:
    """Base class for trail visualization.
    
    This class provides common functionality for visualizing different types of LED trails.
    It can be extended to create specialized visualizers for different trail types.
    """
    
    def __init__(self, 
                 led_count: int = 80, 
                 screen_width: int = game_constants.SCREEN_WIDTH,
                 screen_height: int = game_constants.SCREEN_HEIGHT,
                 scaling_factor: int = game_constants.SCALING_FACTOR) -> None:
        """Initialize the trail visualizer.
        
        Args:
            led_count: Number of LEDs in the strip
            screen_width: Width of the visualization screen
            screen_height: Height of the visualization screen
            scaling_factor: Scaling factor for the display
        """
        self.led_count = led_count
                
        # Initialize display
        self.display = DisplayManager(
            screen_width=screen_width,
            screen_height=screen_height,
            scaling_factor=scaling_factor,
            led_count=led_count
        )
        
        # Common state
        self.current_position = 0
        self.running = False
        
        # Optional state with defaults
        self.auto_mode = False
        self.auto_timer = 0
        self.speed = 1
        self.target_types = [
            game_constants.TargetType.RED,
            game_constants.TargetType.GREEN,
            game_constants.TargetType.BLUE,
            game_constants.TargetType.YELLOW
        ]
        self.next_target = 0
    
    def sync_with_game_state(self, game_state: 'GameState', led_position: int) -> None:
        """Synchronize the visualizer's state with the game state.
        
        Args:
            game_state: The current game state
            led_position: Current LED position
        """
        self.current_position = led_position        
        self.draw_hit_trail()
    
    @classmethod
    def create_visualizer(cls, 
                         led_count: int,
                         auto_mode: bool,
                         speed: int) -> 'TrailVisualizer':
        """Create a trail visualizer based on the specified strategy.
        
        Args:
            strategy: The visualization strategy to use ('normal' or 'simple')
            led_count: Number of LEDs in the strip
            initial_score: Starting score value
            auto_mode: When True, automatically adds hits on a timer
            speed: Speed of LED movement (1-10)
            hit_spacing: Initial spacing between hit trail elements
            fade_duration_ms: Duration in milliseconds for the fade-out effect
            
        Returns:
            A TrailVisualizer instance configured with the specified strategy
        """
        return SimpleTrailVisualizer(
            led_count=led_count,
            auto_mode=auto_mode,
            speed=speed
        )
    
    def _handle_keydown(self, key: int) -> None:
        """Handle keydown events.
        
        Args:
            key: The key that was pressed
        """
        if not self.auto_mode:
            if key in (pygame.K_r, pygame.K_UP):
                self.add_hit(game_constants.TargetType.RED)
            elif key in (pygame.K_g, pygame.K_RIGHT):
                self.add_hit(game_constants.TargetType.GREEN)
            elif key in (pygame.K_b, pygame.K_DOWN):
                self.add_hit(game_constants.TargetType.BLUE)
            elif key in (pygame.K_y, pygame.K_LEFT):
                self.add_hit(game_constants.TargetType.YELLOW)
            elif key == pygame.K_c:
                self.clear_hit_trail()
    
    def update_position(self, speed: int = 1) -> None:
        """Update the current LED position.
        
        Args:
            speed: Speed of movement (number of positions to move per frame)
        """
        self.current_position = (self.current_position + speed) % self.led_count
    
    def handle_quit_events(self) -> bool:
        """Handle quit events.
        
        Returns:
            True if the application should continue running, False if it should quit
        """
        for key, keydown in get_key():
            if key == "quit":
                return False
        return True
    
    async def tick(self, fps: int = 30) -> None:
        """Wait for the next frame.
        
        Args:
            fps: Target frames per second
        """
        await asyncio.sleep(1.0 / fps)
    
    def draw_hit_trail(self) -> None:
        """Draw the hit trail on the display.
        
        This method should be implemented by subclasses to draw their specific hit trail visualization.
        """
        raise NotImplementedError("Subclasses must implement draw_hit_trail()")

    def remove_hit(self, target_type: game_constants.TargetType) -> None:
        """Remove a hit of the specified target type from the hit trail.
        
        Args:
            target_type: Type of target to remove
        """
        pass

    @property
    def hit_colors(self) -> List[Color]:
        """Get the current hit colors.
        
        Returns:
            List of colors in the hit trail
        """
        return []

class SimpleTrailVisualizer(TrailVisualizer):
    """Visualizer using the SimpleHitTrail strategy."""
    
    def __init__(self, 
                 led_count: int = 80, 
                 auto_mode: bool = False, 
                 speed: int = 1) -> None:
        """Initialize the simple hit trail visualizer.
        
        Args:
            led_count: Number of LEDs in the strip
            auto_mode: When True, automatically adds hits on a timer
            speed: Speed of LED movement (1-10)
        """
        super().__init__(led_count)
        
        # Simple hit trail implementation
        self.simple_hit_trail = SimpleHitTrail()
        
        # Settings
        self.auto_mode = auto_mode
        self.auto_timer = 0
        self.speed = max(1, min(10, speed))  # Clamp between 1 and 10
        self.target_types = [
            game_constants.TargetType.RED,
            game_constants.TargetType.GREEN,
            game_constants.TargetType.BLUE,
            game_constants.TargetType.YELLOW
        ]
        self.next_target = 0
        
        # Track score
        self._score = 0.0
        
        print(f"SimpleTrailVisualizer initialized with auto_mode={auto_mode}")
    
    @property
    def score(self) -> float:
        """Get the current score."""
        return self._score
    
    @score.setter
    def score(self, value: float) -> None:
        """Set the current score."""
        self._score = value
    
    @property
    def hit_colors(self) -> List[Color]:
        """Get the current hit colors.
        
        Returns:
            List of colors in the hit trail
        """
        if self.simple_hit_trail.hit_position:
            _, color, _ = self.simple_hit_trail.hit_position
            return [color]
        return []
    
    def remove_hit(self, target_type: game_constants.TargetType) -> None:
        """Remove a hit of the specified target type from the hit trail.
        
        Args:
            target_type: Type of target to remove
        """
        self.simple_hit_trail.remove_hit(target_type)
    
    def add_hit(self, target_type: game_constants.TargetType) -> None:
        """Add a hit of the specified target type to the hit trail.
        
        Args:
            target_type: Type of target to add
        """
        # Calculate target position based on target type
        if target_type == game_constants.TargetType.RED:
            target_pos = 0  # 12 o'clock
        elif target_type == game_constants.TargetType.GREEN:
            target_pos = int(self.led_count * 0.25)  # 3 o'clock
        elif target_type == game_constants.TargetType.BLUE:
            target_pos = int(self.led_count * 0.5)  # 6 o'clock
        else:  # YELLOW
            target_pos = int(self.led_count * 0.75)  # 9 o'clock
            
        # Add the hit at the target position
        self.simple_hit_trail.add_hit(target_pos, target_type)

        # Update score
        self._score += 0.25
    
    def clear_hit_trail(self) -> None:
        """Clear the hit trail."""
        self.simple_hit_trail = SimpleHitTrail(fade_duration_ms=500)  # Use same default as in __init__
        
    def draw_hit_trail(self) -> None:
        """Draw the simple hit trail on the display."""
        # Draw the simple hit trail using the SimpleHitTrail implementation
        self.simple_hit_trail.draw(lambda pos, color: self.display.set_hit_trail_pixel(pos, color))
        