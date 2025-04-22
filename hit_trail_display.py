#!/usr/bin/env python3
"""
Hit Trail Display - Standalone program to visualize hit trails

This program shows only the hit trail visualization from the rhythm game,
allowing you to see how the hit trail looks with different settings.
"""

import asyncio
import pygame
from trail_visualization import (
    HitTrailVisualizer,
    SimpleTrailVisualizer,
    print_hit_trail_instructions,
    parse_hit_trail_args
)

async def main() -> None:
    """Main entry point."""
    args = parse_hit_trail_args()
    print_hit_trail_instructions()
    
    # Choose visualizer based on strategy
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
    
    await visualizer.run()
    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main()) 