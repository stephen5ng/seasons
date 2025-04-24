#!/usr/bin/env python3
"""Test script for TrailStateManager."""

import pygame
from pygame import Color
import sys
import time

from trail_state_manager import TrailStateManager
from game_constants import TRAIL_FADE_DURATION_S, TRAIL_EASE

# Mock button handler for testing
class MockButtonHandler:
    def is_in_valid_window(self, pos):
        return pos % 10 == 0
        
    def get_target_type(self, pos):
        from game_constants import TargetType
        if pos % 10 == 0:
            return TargetType.RED
        return None

# Mock rainbow color function
def get_rainbow_color(time_ms, line_index):
    """Simple rainbow color generator for testing."""
    hue = (time_ms / 2000 + line_index * 0.1) % 1.0
    
    if hue < 0.33:
        # Red to Green
        return Color(int(255 * (1 - hue * 3)), int(255 * hue * 3), 0)
    elif hue < 0.66:
        # Green to Blue
        hue = hue - 0.33
        return Color(0, int(255 * (1 - hue * 3)), int(255 * hue * 3))
    else:
        # Blue to Red
        hue = hue - 0.66
        return Color(int(255 * hue * 3), 0, int(255 * (1 - hue * 3)))

def main():
    """Test the TrailStateManager."""
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("TrailStateManager Test")
    
    # Create the trail state manager
    trail_manager = TrailStateManager(get_rainbow_color_func=get_rainbow_color)
    button_handler = MockButtonHandler()
    
    # Test positions
    positions = {}
    start_time = pygame.time.get_ticks() / 1000.0
    
    # Track positions drawn
    display_positions = {}
    
    # Main loop
    clock = pygame.time.Clock()
    running = True
    while running:
        # Clear the screen
        screen.fill((0, 0, 0))
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Update positions
        current_time = pygame.time.get_ticks() / 1000.0
        
        # Add new position every second
        if int(current_time) > int(start_time):
            new_pos = int(current_time) % 100
            trail_manager.update_position(new_pos, current_time)
            start_time = current_time
        
        # Clear display positions
        display_positions.clear()
        
        # Draw main trail
        def display_main(pos, color):
            x = pos * 8
            y = 100
            pygame.draw.circle(screen, color, (x, y), 5)
            display_positions[pos] = color
            
        trail_manager.draw_main_trail(
            TRAIL_FADE_DURATION_S,
            TRAIL_EASE,
            button_handler,
            display_main
        )
        
        # Draw bonus trail
        def display_bonus(pos, color):
            x = pos * 8
            y = 200
            pygame.draw.circle(screen, color, (x, y), 5)
            
        trail_manager.draw_bonus_trail(
            BONUS_TRAIL_FADE_DURATION_S,
            BONUS_TRAIL_EASE,
            display_bonus,
            lambda pos: (100 - pos) % 100
        )
        
        # Draw information
        font = pygame.font.SysFont(None, 24)
        
        text_surface = font.render(f"Active Positions: {len(trail_manager.lit_positions)}", True, (255, 255, 255))
        screen.blit(text_surface, (10, 10))
        
        text_surface = font.render(f"Displayed Positions: {len(display_positions)}", True, (255, 255, 255))
        screen.blit(text_surface, (10, 40))
        
        text_surface = font.render("Press ESC to exit", True, (255, 255, 255))
        screen.blit(text_surface, (10, 70))
        
        # Update display
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
