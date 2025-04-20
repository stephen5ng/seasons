"""WLED management for the rhythm game."""
import aiohttp
from typing import Optional, Dict

from wled_controller import WLEDController

class WLEDManager:
    """Manages WLED communication and state tracking.
    
    This class encapsulates all WLED-related functionality, including tracking the last
    sent measure and score, and determining when to send new commands.
    """
    
    def __init__(self, ip_address: str, http_session: aiohttp.ClientSession, command_settings: Dict[int, str]) -> None:
        """Initialize the WLED manager.
        
        Args:
            ip_address: IP address of the WLED device
            http_session: Shared HTTP session for making requests
            command_settings: Dictionary mapping measures to WLED commands
        """
        self.wled_controller = WLEDController(ip_address, http_session)
        self.command_settings = command_settings
        self.last_wled_measure: int = -1
        self.last_wled_score: float = -1.0
        
    async def update_wled(self, current_measure: int, score: float) -> None:
        """Update WLED device based on current measure and score.
        
        Checks if the measure or score has changed significantly enough to warrant
        sending a new command to the WLED device.
        
        Args:
            current_measure: Current measure number
            score: Current game score
        """
        # Check if we need to update WLED based on measure or score change
        if score != self.last_wled_score or self.last_wled_measure != current_measure:
            # If measure changed, check for a new command
            if self.last_wled_measure != current_measure:
                print(f"NEW MEASURE {current_measure}")
                wled_command = WLEDController.get_command_for_measure(current_measure, self.command_settings)
                if wled_command:
                    self.last_wled_measure = current_measure
                    await self.send_wled_command(wled_command, score)
                    
            # Always update the last score
            self.last_wled_score = score
            print(f"score {score}")
            
    async def send_wled_command(self, wled_command: str, score: float) -> None:
        """Send a command to the WLED device.
        
        Args:
            wled_command: Command string to send
            score: Current score to include in command
        """
        await self.wled_controller.send_command(wled_command, score) 