#!/usr/bin/env python3
"""Test driver for hit trail visualization."""

import asyncio
import pygame
import game_constants
from trail_visualization import TrailVisualizer, print_hit_trail_instructions

async def run_visualization(visualizer: TrailVisualizer) -> None:
    """Run the visualization loop.
    
    This method handles:
    - Pygame initialization
    - Event handling
    - Auto mode handling
    - Position updates
    - Display updates
    
    Args:
        visualizer: The visualizer instance to run
    """
    pygame.init()
    visualizer.running = True
    
    while visualizer.running:
        visualizer.display.clear()
        
        # Process pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                visualizer.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    visualizer.running = False
                else:
                    visualizer._handle_keydown(event.key)
        
        # Handle automatic hit generation
        if visualizer.auto_mode:
            visualizer.auto_timer += 1
            if visualizer.auto_timer >= 30:  # Add hit every 30 frames
                visualizer.auto_timer = 0
                visualizer.add_hit(visualizer.target_types[visualizer.next_target])
                visualizer.next_target = (visualizer.next_target + 1) % len(visualizer.target_types)
        
        # Update position
        visualizer.update_position(visualizer.speed)
        
        # Draw hit trail
        visualizer.draw_hit_trail()
        
        # Update display
        visualizer.display.update()
        await visualizer.tick(30)

async def main() -> None:
    """Initialize and run the hit trail visualizer."""
    print_hit_trail_instructions()
    
    # Parse command line arguments
    args = parse_hit_trail_args()
    
    # Initialize visualizer based on strategy
    visualizer = TrailVisualizer.create_visualizer(
        strategy=args['strategy'],
        led_count=args['led_count'],
        initial_score=args['initial_score'],
        auto_mode=args['auto_mode'],
        speed=args['speed'],
        hit_spacing=args['hit_spacing'],
        fade_duration_ms=args['fade_duration']
    )
    
    # Run visualization loop
    await run_visualization(visualizer)
    
    # Clean up
    pygame.quit()

def parse_hit_trail_args() -> dict:
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

if __name__ == "__main__":
    asyncio.run(main()) 