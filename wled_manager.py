"""WLED management for the rhythm game."""
import asyncio
import aiohttp
from typing import Optional, Dict

from wled_controller import WLEDController

class WLEDManager:
    """Manages WLED communication and state tracking.
    
    This class encapsulates all WLED-related functionality, including tracking the last
    sent measure and score, and determining when to send new commands.
    """
    
    def __init__(self, enabled: bool, ip_address: str, http_session: aiohttp.ClientSession, command_settings: Dict[int, str], number_of_leds: int) -> None:
        """Initialize the WLED manager.
        
        Args:
            enabled: Whether WLED is enabled
            ip_address: IP address of the WLED device
            http_session: Shared HTTP session for making requests
            command_settings: Dictionary mapping measures to WLED commands
            number_of_leds: Number of LEDs in the strip
        """
        self.enabled = enabled
        self.wled_controller = WLEDController(ip_address, http_session)
        self.command_settings = command_settings
        self.last_wled_base_command: str = ""
        self.last_wled_command: str = ""
        self.number_of_leds = number_of_leds

    def merge_dicts_with_seg(self, d1, d2, n, current_phrase):
        seg1 = d1.get("seg", [])
        seg2 = d2.get("seg", [])
        
        s1 = seg1[0] if seg1 else {}
        s2 = seg2[0] if seg2 else {}
        
        base_seg = {**s1, **s2}
        seg_list = [{**base_seg,
                     "start": i * 150,
                     "stop": i*150 + min(150, current_phrase*8),
                     "id": i
                     } for i in range(n)]

        return {
            **d1,
            **d2,
            "seg": seg_list
        }        

    async def update_wled(self, current_phrase) -> None:
        """Update WLED device based on current measure and score.
        
        Checks if the measure or score has changed significantly enough to warrant
        sending a new command to the WLED device.
        
        Args:
            current_measure: Current measure number
        """
        if not self.enabled:
            return

        wled_base_command = self.command_settings.get(current_phrase)
        if wled_base_command and wled_base_command != self.last_wled_base_command:
            self.last_wled_base_command = wled_base_command
        
        json_base = {
                 "seg": [{
                 }]
                }
        
        wled_command = self.merge_dicts_with_seg(self.last_wled_base_command, json_base, 3, current_phrase)
        if wled_command != self.last_wled_command:
            print(f"wled_command: {wled_command}")
            self.last_wled_command = wled_command
            await self.wled_controller.send_json(wled_command)
