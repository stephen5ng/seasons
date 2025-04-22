#!/usr/bin/env python3
"""
Trail Visualization - Common utilities for visualizing LED trails

This module provides shared functionality for visualizing different types of LED trails
including hit trails, main trails, and bonus trails. It's used by both the main
game (seasons.py) and the standalone hit trail viewer (hit_trail_display.py).
"""

import asyncio
import pygame
from pygame import Color
from typing import List, Dict, Optional, Tuple, Callable, Any

import game_constants
from hit_trail import HitTrail
from display_manager import DisplayManager
from get_key import get_key
from simple_hit_trail import SimpleHitTrail  # Import the SimpleHitTrail class


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
        
        # Update global constants
        game_constants.NUMBER_OF_LEDS = led_count
        
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
    
    async def run(self) -> None:
        """Run the visualization loop.
        
        This method should be overridden by subclasses to implement specific visualization.
        """
        raise NotImplementedError("Subclasses must implement run()")
    
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


class HitTrailVisualizer(TrailVisualizer):
    """Specialized visualizer for hit trails."""
    
    def __init__(self, 
                 led_count: int = 80, 
                 initial_score: float = 0.0,
                 auto_mode: bool = False, 
                 speed: int = 1,
                 hit_spacing: int = game_constants.INITIAL_HIT_SPACING) -> None:
        """Initialize the hit trail visualizer.
        
        Args:
            led_count: Number of LEDs in the strip
            initial_score: Starting score value
            auto_mode: When True, automatically adds hits on a timer
            speed: Speed of LED movement (1-10)
            hit_spacing: Initial spacing between hit trail elements
        """
        super().__init__(led_count)
        
        # Manage hit trail state directly
        self.score = initial_score
        self.hit_colors: List[Color] = []
        self.hit_spacing = hit_spacing
        self.hit_trail_cleared = False
        
        # Hit trail specific settings
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
        
        # Initialize hit trail colors based on starting score
        self._init_hit_trail_colors(initial_score)
    
    def _init_hit_trail_colors(self, initial_score: float) -> None:
        """Initialize hit trail colors based on the starting score.
        
        Args:
            initial_score: Starting score value
        """
        hit_colors_count = int(initial_score * 4)  # 4 colors per score point
        for i in range(min(hit_colors_count, 40)):  # Max 40 colors
            if i % 4 == 0:
                self.hit_colors.append(game_constants.TARGET_COLORS[game_constants.TargetType.RED])
            elif i % 4 == 1:
                self.hit_colors.append(game_constants.TARGET_COLORS[game_constants.TargetType.GREEN])
            elif i % 4 == 2:
                self.hit_colors.append(game_constants.TARGET_COLORS[game_constants.TargetType.BLUE])
            else:
                self.hit_colors.append(game_constants.TARGET_COLORS[game_constants.TargetType.YELLOW])
                
        print(f"Created hit trail with {len(self.hit_colors)} colors")
    
    async def run(self) -> None:
        """Run the hit trail visualization loop."""
        pygame.init()
        self.running = True
        
        while self.running:
            self.display.clear()
            
            # Process pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        self.running = False
                    elif not self.auto_mode:
                        if event.key in (pygame.K_r, pygame.K_UP):
                            self.add_hit(game_constants.TargetType.RED)
                        elif event.key in (pygame.K_g, pygame.K_RIGHT):
                            self.add_hit(game_constants.TargetType.GREEN)
                        elif event.key in (pygame.K_b, pygame.K_DOWN):
                            self.add_hit(game_constants.TargetType.BLUE)
                        elif event.key in (pygame.K_y, pygame.K_LEFT):
                            self.add_hit(game_constants.TargetType.YELLOW)
                        elif event.key == pygame.K_c:
                            self.clear_hit_trail()
            
            # Handle automatic hit generation
            if self.auto_mode:
                self.auto_timer += 1
                if self.auto_timer >= 30:  # Add hit every 30 frames
                    self.auto_timer = 0
                    self.add_hit(self.target_types[self.next_target])
                    self.next_target = (self.next_target + 1) % len(self.target_types)
            
            # Update position
            self.update_position(self.speed)
            
            # Draw hit trail
            self.draw_hit_trail()
            
            # Update display
            self.display.update()
            await self.tick(30)
    
    def add_hit(self, target_type: game_constants.TargetType) -> None:
        """Add a hit of the specified target type to the hit trail.
        
        Args:
            target_type: Type of target to add
        """
        # Update score (0.25 points per hit)
        self.score += 0.25
        
        # Check if we need to adjust spacing
        if HitTrail.should_adjust_spacing(self.hit_colors, self.hit_spacing, self.led_count):
            new_spacing = HitTrail.get_new_spacing(self.hit_spacing)
            if new_spacing == 0:  # Signal to clear trail
                # Clear hit trail if we've hit minimum spacing
                self.hit_colors = []
                self.hit_spacing = game_constants.INITIAL_HIT_SPACING  # Reset to initial spacing
                self.hit_trail_cleared = True  # Mark that hit trail has been cleared
                print("*********** Hit trail cleared, resetting spacing")
                return  # Skip adding hit color when trail is cleared
            else:
                self.hit_spacing = new_spacing
                print(f"*********** Hit spacing: {self.hit_spacing}")
        
        # Add hit color to beginning of trail
        self.hit_colors = HitTrail.add_hit_color(
            self.hit_colors, 
            game_constants.TARGET_COLORS[target_type]
        )
        
        # Limit trail length based on score
        max_trail_length = int(self.score * 4)
        self.hit_colors = HitTrail.limit_trail_length(self.hit_colors, max_trail_length)
        
        print(f"Added {target_type.name} hit, score: {self.score}, "
              f"trail length: {len(self.hit_colors)}")
    
    def clear_hit_trail(self) -> None:
        """Clear the hit trail."""
        self.hit_colors = []
        self.hit_spacing = game_constants.INITIAL_HIT_SPACING
        self.hit_trail_cleared = True
        print("Hit trail cleared manually")
    
    def draw_hit_trail(self) -> None:
        """Draw the hit trail on the display."""
        trail_positions = HitTrail.calculate_trail_positions(
            self.current_position, 
            self.hit_colors,
            self.hit_spacing, 
            self.led_count
        )
        for pos, color in trail_positions.items():
            self.display.set_hit_trail_pixel(pos, color)


def print_hit_trail_instructions() -> None:
    """Print usage instructions for the hit trail visualizer."""
    print("\nHit Trail Visualizer")
    print("===================\n")
    print("Controls:")
    print("  R / UP     - Add RED hit")
    print("  G / RIGHT  - Add GREEN hit")
    print("  B / DOWN   - Add BLUE hit")
    print("  Y / LEFT   - Add YELLOW hit")
    print("  C          - Clear trail")
    print("  ESC / Q    - Quit")
    print("\nOptions:")
    print("  --leds N     - Set number of LEDs (default: 80)")
    print("  --score N    - Set initial score (default: 0.0)")
    print("  --auto       - Automatically add hits")
    print("  --speed N    - Set movement speed (1-10, default: 1)")
    print("  --spacing N  - Set initial hit spacing")
    print("  --strategy S - Hit trail strategy (normal or simple)")


# Utility functions for command-line usage
def parse_hit_trail_args() -> Dict[str, Any]:
    """Parse command line arguments for the hit trail visualizer."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hit Trail Visualizer')
    parser.add_argument('--leds', type=int, default=80,
                      help='Number of LEDs in the strip (default: 80)')
    parser.add_argument('--score', type=float, default=0.0,
                      help='Initial score (default: 0.0)')
    parser.add_argument('--auto', action='store_true',
                      help='Automatically add hits')
    parser.add_argument('--speed', type=int, default=1,
                      help='Speed of LED movement (1-10, default: 1)')
    parser.add_argument('--spacing', type=int, default=game_constants.INITIAL_HIT_SPACING,
                      help=f'Initial spacing between hit trail elements (default: {game_constants.INITIAL_HIT_SPACING})')
    parser.add_argument('--strategy', type=str, choices=['normal', 'simple'], default='normal',
                      help='Hit trail visualization strategy (normal=traditional trail, simple=single LED fade)')
    parser.add_argument('--fade-duration', type=int, default=500,
                      help='Fade duration in ms for simple strategy (default: 500)')
    
    args = parser.parse_args()
    return {
        'led_count': args.leds,
        'initial_score': args.score,
        'auto_mode': args.auto,
        'speed': args.speed,
        'hit_spacing': args.spacing,
        'strategy': args.strategy,
        'fade_duration': args.fade_duration
    }


class SimpleTrailVisualizer(TrailVisualizer):
    """Visualizer using the SimpleHitTrail strategy."""
    
    def __init__(self, 
                 led_count: int = 80, 
                 auto_mode: bool = False, 
                 speed: int = 1,
                 fade_duration_ms: int = 500) -> None:
        """Initialize the simple hit trail visualizer.
        
        Args:
            led_count: Number of LEDs in the strip
            auto_mode: When True, automatically adds hits on a timer
            speed: Speed of LED movement (1-10)
            fade_duration_ms: Duration in milliseconds for the fade-out effect
        """
        super().__init__(led_count)
        
        # Simple hit trail implementation
        self.simple_hit_trail = SimpleHitTrail(fade_duration_ms=fade_duration_ms)
        
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
    
    async def run(self) -> None:
        """Run the simple hit trail visualization loop."""
        pygame.init()
        self.running = True
        
        while self.running:
            self.display.clear()
            
            # Process pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        self.running = False
                    elif not self.auto_mode:
                        if event.key in (pygame.K_r, pygame.K_UP):
                            self.add_hit(game_constants.TargetType.RED)
                        elif event.key in (pygame.K_g, pygame.K_RIGHT):
                            self.add_hit(game_constants.TargetType.GREEN)
                        elif event.key in (pygame.K_b, pygame.K_DOWN):
                            self.add_hit(game_constants.TargetType.BLUE)
                        elif event.key in (pygame.K_y, pygame.K_LEFT):
                            self.add_hit(game_constants.TargetType.YELLOW)
                        elif event.key == pygame.K_c:
                            self.clear_hit_trail()
            
            # Handle automatic hit generation
            if self.auto_mode:
                self.auto_timer += 1
                if self.auto_timer >= 30:  # Add hit every 30 frames
                    self.auto_timer = 0
                    self.add_hit(self.target_types[self.next_target])
                    self.next_target = (self.next_target + 1) % len(self.target_types)
            
            # Update position
            self.update_position(self.speed)
            
            # Draw simple hit trail
            self.simple_hit_trail.draw(lambda pos, color: self.display.set_hit_trail_pixel(pos, color))
            
            # Indicate current position with a dim white pixel
            self.display.set_pixel(self.current_position, Color(128, 128, 128))
            
            # Update display
            self.display.update()
            await self.tick(30)
    
    def add_hit(self, target_type: game_constants.TargetType) -> None:
        """Add a hit of the specified target type to the hit trail.
        
        Args:
            target_type: Type of target to add
        """
        # Add the hit at the current position
        self.simple_hit_trail.add_hit(
            self.current_position, 
            game_constants.TARGET_COLORS[target_type]
        )
        print(f"Added {target_type.name} hit at position {self.current_position}")
    
    def clear_hit_trail(self) -> None:
        """Clear the hit trail."""
        # Reset the simple hit trail by creating a new instance
        self.simple_hit_trail = SimpleHitTrail(fade_duration_ms=self.simple_hit_trail.fade_duration_ms)
        print("Hit trail cleared manually")


async def main() -> None:
    """Initialize and run the hit trail visualizer."""
    print_hit_trail_instructions()
    
    # Parse command line arguments
    args = parse_hit_trail_args()
    
    # Initialize visualizer based on strategy
    if args['strategy'] == 'simple':
        print(f"Using SIMPLE hit trail strategy with {args['fade_duration']}ms fade duration")
        visualizer = SimpleTrailVisualizer(
            led_count=args['led_count'],
            auto_mode=args['auto_mode'],
            speed=args['speed'],
            fade_duration_ms=args['fade_duration']
        )
    else:
        print(f"Using NORMAL hit trail strategy with {args['hit_spacing']} hit spacing")
        visualizer = HitTrailVisualizer(
            led_count=args['led_count'],
            initial_score=args['initial_score'],
            auto_mode=args['auto_mode'],
            speed=args['speed'],
            hit_spacing=args['hit_spacing']
        )
    
    # Run visualization loop
    await visualizer.run()
    
    # Clean up
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main()) 