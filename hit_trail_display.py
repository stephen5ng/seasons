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
    print_hit_trail_instructions,
    parse_hit_trail_args
)

async def main() -> None:
    """Main entry point."""
    args = parse_hit_trail_args()
    print_hit_trail_instructions()
    
    visualizer = HitTrailVisualizer(**args)
    await visualizer.run()
    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main()) 