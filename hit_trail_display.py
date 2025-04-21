#!/usr/bin/env python3
"""
Hit Trail Display - Standalone program to visualize hit trails

This program shows only the hit trail visualization from the rhythm game,
allowing you to see how the hit trail looks with different settings.
"""

import asyncio
import argparse
import pygame
from pygame import Color
from typing import List, Dict, Optional, Tuple

from game_constants import (
    TARGET_COLORS, TargetType, SCREEN_WIDTH, SCREEN_HEIGHT, SCALING_FACTOR,
    CIRCLE_CENTER_X, CIRCLE_CENTER_Y, HIT_TRAIL_RADIUS, INITIAL_HIT_SPACING
)
import game_constants  # For updating NUMBER_OF_LEDS
from hit_trail import HitTrail
from display_manager import DisplayManager
from score_manager import ScoreManager
from get_key import get_key

class HitTrailDemo:
    """Demonstration of hit trail visualization."""
    
    def __init__(self, led_count: int = 80, initial_score: float = 0.0, 
                 auto_mode: bool = False, speed: int = 1, 
                 hit_spacing: int = INITIAL_HIT_SPACING) -> None:
        """Initialize the hit trail demo.
        
        Args:
            led_count: Number of LEDs in the strip
            initial_score: Starting score value
            auto_mode: When True, automatically adds hits on a timer
            speed: Speed of LED movement (1-10)
            hit_spacing: Initial spacing between hit trail elements
        """
        self.led_count = led_count
        self.score_manager = ScoreManager(initial_score)
        self.display = DisplayManager(
            screen_width=SCREEN_WIDTH,
            screen_height=SCREEN_HEIGHT,
            scaling_factor=SCALING_FACTOR,
            led_count=led_count
        )
        self.led_position = 0
        self.auto_mode = auto_mode
        self.auto_timer = 0
        self.speed = max(1, min(10, speed))  # Clamp between 1 and 10
        
        # Override initial hit spacing
        self.score_manager.hit_spacing = hit_spacing
        
        self.target_types = [
            TargetType.RED, 
            TargetType.GREEN, 
            TargetType.BLUE, 
            TargetType.YELLOW
        ]
        self.next_target = 0
        
        # Initialize hit trail colors based on starting score
        hit_colors_count = int(initial_score * 4)  # 4 colors per score point
        for i in range(min(hit_colors_count, 40)):  # Max 40 colors
            if i % 4 == 0:
                self.score_manager.hit_colors.append(TARGET_COLORS[TargetType.RED])
            elif i % 4 == 1:
                self.score_manager.hit_colors.append(TARGET_COLORS[TargetType.GREEN])
            elif i % 4 == 2:
                self.score_manager.hit_colors.append(TARGET_COLORS[TargetType.BLUE])
            else:
                self.score_manager.hit_colors.append(TARGET_COLORS[TargetType.YELLOW])
                
        print(f"Created hit trail with {len(self.score_manager.hit_colors)} colors")
    
    async def run(self) -> None:
        """Run the hit trail demo."""
        pygame.init()
        clock = pygame.time.Clock()
        running = True
        
        while running:
            self.display.clear()
            current_time = pygame.time.get_ticks()
            
            # Handle key events
            for key, keydown in get_key():
                if key == "quit":
                    running = False
                    break
                
                # Manual hit trail control
                if not self.auto_mode and keydown:
                    if key == "r" or key == "up":
                        self._add_hit(TargetType.RED)
                    elif key == "g" or key == "right":
                        self._add_hit(TargetType.GREEN)  
                    elif key == "b" or key == "down":
                        self._add_hit(TargetType.BLUE)
                    elif key == "y" or key == "left":
                        self._add_hit(TargetType.YELLOW)
                    elif key == "c":
                        # Clear the hit trail
                        self.score_manager.hit_colors = []
                        self.score_manager.hit_spacing = INITIAL_HIT_SPACING
                        self.score_manager.hit_trail_cleared = True
                        print("Hit trail cleared manually")
                    
            # Automatic hit trail generation
            if self.auto_mode:
                self.auto_timer += 1
                if self.auto_timer >= 30:  # Add hit every 30 frames
                    self.auto_timer = 0
                    self._add_hit(self.target_types[self.next_target])
                    self.next_target = (self.next_target + 1) % len(self.target_types)
            
            # Update LED position
            self.led_position = (self.led_position + self.speed) % self.led_count
            
            # Draw hit trail
            trail_positions = ScoreManager.calculate_trail_positions(
                self.led_position, self.score_manager.hit_colors, 
                self.score_manager.hit_spacing, self.led_count
            )
            for pos, color in trail_positions.items():
                self.display.set_hit_trail_pixel(pos, color)
                        
            # Update display
            self.display.update()
            await asyncio.sleep(0.03)  # Roughly 30 FPS
    
    def _add_hit(self, target_type: TargetType) -> None:
        """Add a hit of the specified target type to the hit trail.
        
        Args:
            target_type: Type of target to add
        """
        # Update score (0.25 points per hit)
        new_score = self.score_manager.score + 0.25
        
        # Use score_manager to update the hit trail
        self.score_manager.update_score(
            new_score, 
            target_type.name.lower(), 
            0.0,  # Beat float (not important for this demo)
            self.led_count
        )
        
        print(f"Added {target_type.name} hit, score: {self.score_manager.score}, "
              f"trail length: {len(self.score_manager.hit_colors)}")

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Hit Trail Display Demo')
    parser.add_argument('--leds', type=int, default=80,
                      help='Number of LEDs in the strip (default: 80)')
    parser.add_argument('--score', type=float, default=0.0,
                      help='Initial score value')
    parser.add_argument('--auto', action='store_true',
                      help='Automatically add hits on a timer')
    parser.add_argument('--speed', type=int, default=1,
                      help='Speed of LED movement (1-10, default: 1)')
    parser.add_argument('--spacing', type=int, default=INITIAL_HIT_SPACING,
                      help=f'Initial spacing between hit trail elements (default: {INITIAL_HIT_SPACING})')
    return parser.parse_args()

def print_instructions() -> None:
    """Print usage instructions for the hit trail demo."""
    print("\nHit Trail Display Demo")
    print("=====================\n")
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
    print("  --spacing N  - Set initial hit spacing\n")

async def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    # Update NUMBER_OF_LEDS in game_constants
    game_constants.NUMBER_OF_LEDS = args.leds
    
    print_instructions()
    
    demo = HitTrailDemo(
        led_count=args.leds,
        initial_score=args.score,
        auto_mode=args.auto,
        speed=args.speed,
        hit_spacing=args.spacing
    )
    await demo.run()
    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main()) 