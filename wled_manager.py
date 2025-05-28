"""WLED management for the rhythm game."""
import asyncio
import aiohttp
import socket
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, Union

from wled_controller import WLEDController
from game_constants import NUMBER_OF_VICTORY_LEDS

# Configure logging
logger = logging.getLogger(__name__)

WLED_BASE = {
    "bri": 255,
    "seg": [
        {
            "id": 0,
            "grp": 1,
            "on": True,
            "bri": 255,
            "set": 0,
            "n": "segment0",
            "ix": 128,
            "sel": True,
            "si": 0,
        },
        {
            "id": 1,
            "grp": 1,
            "on": True,
            "bri": 255,
            "set": 0,
            "n": "segment1",
            "ix": 128,
            "sel": True,
            "o3": False,
            "si": 0,
        },
        {
            "id": 2,
            "grp": 1,
            "on": True,
            "bri": 255,
            "set": 0,
            "n": "segment2",
            "ix": 128,
            "sel": True,
            "o3": False,
            "si": 0,
        },
        {
            "id": 3,
            "grp": 1,
            "on": True,
            "bri": 255,
            "set": 0,
            "n": "segment3",
            "ix": 128,
            "sel": True,
            "o3": False,
            "si": 0,
        },
    ],
}

def resolve_mdns_hostname(hostname: str) -> str:
    """Resolve an mDNS hostname to an IP address.
    
    Args:
        hostname: The mDNS hostname to resolve
        
    Returns:
        The resolved IP address
        
    Raises:
        socket.gaierror: If hostname resolution fails
    """
    try:
        # Try to resolve the hostname
        logger.info(f"Resolving WLED hostname {hostname}...")
        ip_address = socket.gethostbyname(hostname)
        logger.info(f"Resolved WLED {hostname} to {ip_address}")
        return ip_address
    except socket.gaierror as e:
        logger.error(f"Failed to resolve WLED {hostname}: {e}")
        raise

class WLEDManager:
    """Manages WLED communication and state tracking.
    
    This class encapsulates all WLED-related functionality, including tracking the last
    sent measure and score, and determining when to send new commands.
    """
    
    def __init__(self, enabled: bool, hostname: str, http_session: aiohttp.ClientSession, number_of_leds: int) -> None:
        """Initialize the WLED manager.
        
        Args:
            enabled: Whether WLED is enabled
            hostname: Hostname or IP address of the WLED device
            http_session: Shared HTTP session for making requests
            number_of_leds: Number of LEDs in the strip
        """
        self.enabled = enabled
        self.wled_config = self._load_wled_config()
        
        # Resolve hostname if it looks like a DNS name
        if self.enabled and not hostname.replace(".", "").isdigit():  # Simple check for IP vs hostname
            try:
                ip_address = resolve_mdns_hostname(hostname)
            except socket.gaierror:
                logger.error(f"Could not resolve {hostname}, falling back to hostname")
                ip_address = hostname
        else:
            ip_address = hostname
            
        self.wled_controller = WLEDController(ip_address, http_session)
        self.last_wled_base_command: str = ""
        self.last_wled_command: str = ""
        self.number_of_leds = number_of_leds

    def _load_wled_config(self) -> Dict[int, Dict[str, Any]]:
        """Load WLED configuration from wled.json file and transform into a measure-keyed dictionary.
        
        Returns:
            Dict containing the WLED configuration, where keys are measure numbers and values
            are the corresponding segment configurations.
            
        Raises:
            FileNotFoundError: If wled.json doesn't exist
            json.JSONDecodeError: If wled.json is invalid
            KeyError: If a config entry is missing required fields
        """
        try:
            config_path = Path("wled.json")
            with open(config_path, "r") as f:
                config_array = json.load(f)
            
            # Transform array into measure-keyed dictionary
            config_dict = {}
            config_names = {}
            current_measure = 0
            for entry in config_array:
                try:
                    config_dict[current_measure] = entry["seg"]
                    measure = int(entry["measure"])  # Convert measure to int for consistency
                    config_names[current_measure] = entry.get("name", "")  # Store the name for this measure
                    current_measure += measure
                except (KeyError, ValueError) as e:
                    logger.error(f"Invalid config entry {entry}: {e}")
                    continue
                    
            logger.info(f"Successfully loaded WLED configuration from wled.json with {len(config_dict)} measures")
            self.config_names = config_names
            return config_dict
        except FileNotFoundError:
            logger.warning("wled.json not found, using default configuration")
            self.config_names = {}
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse wled.json: {e}")
            self.config_names = {}
            return {}

    def merge_dicts_with_seg(self, d1, d2, n, number_of_leds):
        seg1 = d1.get("seg", [])
        seg2 = d2.get("seg", [])
        
        s1 = seg1[0] if seg1 else {}
        s2 = seg2[0] if seg2 else {}
        
        base_seg = {**s1, **s2}
        seg_list = [{**base_seg,
                     "start": i * NUMBER_OF_VICTORY_LEDS,
                     "stop": i*NUMBER_OF_VICTORY_LEDS + min(NUMBER_OF_VICTORY_LEDS, number_of_leds),
                     "n": f"segment_{i}",
                     "id": i
                     } for i in range(n)]

        return {
            **d1,
            **d2,
            "seg": seg_list
        }        

    async def update_wled(self, current_measure: int) -> None:
        """Update WLED device based on current measure and score.
        
        Checks if the measure or score has changed significantly enough to warrant
        sending a new command to the WLED device.
        
        Args:
            current_measure: Current measure number. If -1, WLED will be turned off.
        """
        if not self.enabled:
            return
        print(f"WLED current measure: {current_measure}")
        # print(f"WLED config: {self.wled_config[current_phrase*8]}")
        wled_base_command = {"on": current_measure >= 1, "seg": self.wled_config.get(current_measure, [])}
        # print(f"WLED base command: {wled_base_command}")
        if wled_base_command and wled_base_command != self.last_wled_base_command:
            self.last_wled_base_command = wled_base_command
            # print(f"WLED config keys: {self.wled_config.keys()}")
            
        number_of_leds = self.number_of_leds // 4
        if current_measure > 30:
            number_of_leds = number_of_leds * 4
        elif current_measure > 16:
            number_of_leds = number_of_leds * 2
        wled_command = self.merge_dicts_with_seg(self.last_wled_base_command, WLED_BASE, 4, number_of_leds)
        if wled_command != self.last_wled_command:
            logger.debug(f"Sending WLED command: {wled_command} {number_of_leds}")
            self.last_wled_command = wled_command
            await self.wled_controller.send_json(wled_command)
