"""WLED management for the rhythm game."""
import aiohttp
from typing import Optional, Dict

from wled_controller import WLEDController

class WLEDManager:
    """Manages WLED communication and state tracking.
    
    This class encapsulates all WLED-related functionality, including tracking the last
    sent measure and score, and determining when to send new commands.
    """
    
    def __init__(self, enabled: bool, ip_address: str, http_session: aiohttp.ClientSession, command_settings: Dict[int, str]) -> None:
        """Initialize the WLED manager.
        
        Args:
            enabled: Whether WLED is enabled
            ip_address: IP address of the WLED device
            http_session: Shared HTTP session for making requests
            command_settings: Dictionary mapping measures to WLED commands
        """
        self.enabled = enabled
        self.wled_controller = WLEDController(ip_address, http_session)
        self.command_settings = command_settings
        self.last_wled_command: str = ""
        
    async def update_wled(self, current_phrase) -> None:
        """Update WLED device based on current measure and score.
        
        Checks if the measure or score has changed significantly enough to warrant
        sending a new command to the WLED device.
        
        Args:
            current_measure: Current measure number
        """
        if not self.enabled:
            return

        wled_command = self.command_settings.get(current_phrase)
        if wled_command != self.last_wled_command:
            print(f"wled_command: {wled_command}")
            self.last_wled_command = wled_command
            await self.wled_controller.send_command(wled_command) 
