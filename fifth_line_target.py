#!/usr/bin/env python3

"""Fifth line target handling for the rhythm game.

This module provides a class to manage the fifth line target mechanics, including
animation, hit detection, and state management.
"""

from enum import Enum, auto
from typing import Optional
import pygame
from pygame import Color
import easing_functions

from game_constants import (
    BEATS_PER_MEASURE,
    FIFTH_LINE_TARGET_BUFFER_MEASURE,
    FIFTH_LINE_TARGET_MEASURES,
    TargetType
)
from display_manager import DisplayManager
WINDOW_SIZE_PERCENT_BEFORE = 0.10
WINDOW_SIZE_PERCENT_AFTER = 0.20
WINDOW_SIZE_LEDS_BEFORE = int(150*WINDOW_SIZE_PERCENT_BEFORE)

class TargetState(Enum):
    """States for the fifth line target.
    
    NO_TARGET: No active target
    PRE_WINDOW: Target exists but not yet in valid window
    IN_WINDOW: Target is in valid hit window
    POST_WINDOW: Target has passed valid window
    """
    NO_TARGET = auto()
    PRE_WINDOW = auto()
    IN_WINDOW = auto()
    POST_WINDOW = auto()

class FifthLineTarget:
    """Manages the fifth line target mechanics and state.
    
    This class handles all aspects of the fifth line target, including:
    - Animation timing and progression
    - Hit detection and validation
    - State management for valid hit windows
    - Visual rendering of the fifth line
    - Penalty handling for missed hits
    
    Attributes:
        target_hit_registered: Whether a hit has been registered for the target
        state: Current state of the target (NO_TARGET, PRE_WINDOW, IN_WINDOW, POST_WINDOW)
    """
    
    @staticmethod
    def should_start_fifth_line(measure: int) -> bool:
        """Check if a fifth line target should be started for the given measure.
        
        Args:
            measure: The current measure number in the song.
            
        Returns:
            bool: True if a fifth line target should be started at this measure.
        """
        target_measure = measure + FIFTH_LINE_TARGET_BUFFER_MEASURE
        return target_measure in FIFTH_LINE_TARGET_MEASURES

    def __init__(self, measure: int) -> None:
        """Initialize the fifth line target state for a specific measure.
                
        Args:
            measure: The current measure number in the song.
        """
        target_measure = measure + FIFTH_LINE_TARGET_BUFFER_MEASURE
        self._target_beat = target_measure * BEATS_PER_MEASURE
        self.target_hit_registered: bool = False
        self.state: TargetState = TargetState.PRE_WINDOW
        self.penalty_applied: bool = False
        self._last_debug_str: str = ""  # Track last debug string
        print(f"Starting fifth line animation for measure {target_measure}")
    
    def _update_state(self, percent_complete: float) -> None:
        """Update the target state based on animation progress.
        
        Args:
            percent_complete: Animation completion percentage (0.0 to 1.5)
        """
        old_state = self.state
        
        if percent_complete < 1.0 - WINDOW_SIZE_PERCENT_BEFORE:
            self.state = TargetState.PRE_WINDOW
        elif percent_complete < 1.0 + WINDOW_SIZE_PERCENT_AFTER:
            self.state = TargetState.IN_WINDOW
        elif percent_complete < 1.5:    
            self.state = TargetState.POST_WINDOW
        else:
            self.state = TargetState.NO_TARGET

        if old_state != self.state:
            print(f"State transition: {old_state.name} -> {self.state.name}")
    
    def check_penalties(self) -> bool:
        """Check if a penalty should be applied.
        
        Returns:
            True if a penalty should be applied (missed hit in valid window)
        """
        if self.state == TargetState.POST_WINDOW and not self.penalty_applied and not self.target_hit_registered:
            print(f"Penalizing for missed fifth line target: {self._target_beat}")
            self.penalty_applied = True
            return True
        return False
    
    def get_fifth_line_color(self, percent_complete: float, was_hit: bool) -> Color:
        """Get the color for the fifth line based on its state and animation progress.
        
        Args:
            percent_complete: Animation completion percentage (0.0 to 1.5)
            was_hit: Whether the fifth line was successfully hit
            
        Returns:
            Color for the fifth line with appropriate brightness
        """
        # Base color selection
        if was_hit:
            base_color = Color(255, 165, 0)  # Orange when hit
        elif self.state == TargetState.IN_WINDOW:
            base_color = Color(255, 165, 0)  # Orange in valid window
        else:
            base_color = Color(255, 255, 255)  # White otherwise
        
        # Apply fade-out for animation completion
        if percent_complete >= 1.0:
            brightness = 1 - min(1.0, (percent_complete - 1.0) * 2)
            if brightness <= 0:
                return Color(0, 0, 0)  # Fully transparent
            return Color(
                int(base_color.r * brightness),
                int(base_color.g * brightness),
                int(base_color.b * brightness)
            )
        
        return base_color
    
    def draw_fifth_line(self, display: DisplayManager, percent_complete: float) -> None:
        """Draw the fifth line with easing animation and color transitions.
        
        Args:
            display: The display manager instance to draw on.
            percent_complete: The completion percentage of the animation (0.0 to 1.5).
        """
        FIFTH_LINE_EASE = easing_functions.QuadEaseInOut(start=0.0, end=1.0, duration=1.0)
        
        # Calculate position with easing, capped at 1.0 for the animation
        eased = FIFTH_LINE_EASE.ease(min(percent_complete, 1.0))
        position = int(eased * (display.led_count - WINDOW_SIZE_LEDS_BEFORE))
        
        # A fifth line can only be considered "hit" if it was hit while in the valid window
        was_hit = self.state == TargetState.IN_WINDOW and self.target_hit_registered
        color = self.get_fifth_line_color(percent_complete, was_hit)
        if color == Color(0, 0, 0):  # Fully transparent
            return

        # start = max(0, position - 20)
        start = position
        end = position + 1
        if percent_complete >= 1.0 - WINDOW_SIZE_PERCENT_BEFORE:
            for i in range(position, display.led_count):
                # duration *= 0.5
                display.set_fifth_line_pixel(i, Color(255, 165, 0) if was_hit else Color(255, 255, 255), 0.5, 0)
        # Redraw the entire fifth line if it was hit
        if was_hit:
            start = 0
        duration = 0.5
        
        for i in range(start, end):
            # duration *= 0.5
            display.set_fifth_line_pixel(i, color, duration, 0)
        
        display.set_fifth_line_pixel(display.led_count - 1, Color(255, 165, 0), 1.0, 0)
        display.set_fifth_line_pixel(display.led_count - WINDOW_SIZE_LEDS_BEFORE, Color(255, 165, 0), 1.0, 0)

    @staticmethod
    def handle_fifth_line_miss(display: DisplayManager) -> None:
        """Handle fifth line miss by lighting up the last 12 lights.
        
        This is a static method that can be called even when there are no active targets,
        ensuring that misses are always visually indicated.
        
        Args:
            display: The display manager instance to draw on.
        """
        for i in range(12):
            display.set_fifth_line_pixel(display.led_count - 1 - i, Color(255, 165, 0), 0.2, 0)
    
    def update(self, display: DisplayManager, beat_float: float) -> None:
        """Update and draw the fifth line animation if one is active.
        
        Args:
            display: The display manager instance to draw on.
            beat_float: The current beat position as float.
        """
        if self.state == TargetState.NO_TARGET:
            return        
        
        progress = 1.0 - (self._target_beat - beat_float) / (FIFTH_LINE_TARGET_BUFFER_MEASURE*BEATS_PER_MEASURE)
        self._update_state(progress)
        if self.state == TargetState.NO_TARGET:  # Animation complete
            print(f"-------------Animation complete for target_beat: {self._target_beat}")
        elif progress >= 0:  # Animation active
            self.draw_fifth_line(display, progress)
    
    def register_hit(self) -> bool:
        """Register a hit for the current fifth line target if in valid window.
        
        Returns:
            bool: True if the hit was registered, False if not in valid window.
        """
        if self.state == TargetState.IN_WINDOW:
            # print(f"Registering hit for fifth line target: {self._target_beat}")
            self.target_hit_registered = True
            return True
        return False

    def get_debug_str(self) -> str:
        """Get the debug string for the current state.
        
        Returns:
            A string describing the current state of the fifth line target
        """
        debug_str = f" fifth line state: {self.state.name}, hit registered: {self.target_hit_registered}, target beat: {self._target_beat}"
        if debug_str != self._last_debug_str:
            self._last_debug_str = debug_str
            print(debug_str)
        return debug_str

    def is_in_valid_window(self) -> bool:
        """Check if the target is currently in the valid hit window.
        
        Returns:
            True if the target is in the valid window for hits
        """
        return self.state == TargetState.IN_WINDOW 