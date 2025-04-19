"""WLED controller utilities."""
import asyncio
import aiohttp
from typing import Dict, Optional, Any, Callable

class WLEDController:
    """Handles WLED device communication and command management."""
    
    def __init__(self, ip_address: str, http_session: aiohttp.ClientSession):
        """Initialize the WLED controller.
        
        Args:
            ip_address: IP address of the WLED device
            http_session: Aiohttp session for making HTTP requests
        """
        self.ip_address = ip_address
        self.http_session = http_session
        self.current_http_task: Optional[asyncio.Task] = None
    
    @staticmethod
    def build_command_url(ip_address: str, command: str, score_param: int) -> str:
        """Build the full URL for a WLED command.
        
        Args:
            ip_address: IP address of the WLED device
            command: WLED command string (without base URL)
            score_param: Score parameter to include in the command
            
        Returns:
            Complete URL for the WLED command
        """
        return f"http://{ip_address}/win&{command}&S2={score_param}"
    
    @staticmethod
    def calculate_score_param(score: float, base: int = 2, multiplier: int = 6) -> int:
        """Calculate the score parameter for WLED commands.
        
        Args:
            score: Current game score
            base: Base value for the score parameter
            multiplier: Multiplier for the score
            
        Returns:
            Calculated score parameter
        """
        return base + int(score * multiplier)
    
    async def _send_command_inner(self, url: str) -> bool:
        """Internal method to send WLED command.
        
        Args:
            url: Complete URL for the WLED command
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        try:
            async with self.http_session.get(url, timeout=1.0) as response:
                if response.status != 200:
                    print(f"Error: HTTP {response.status} for {url}")
                    return False
                await response.text()
                return True
        except asyncio.TimeoutError:
            print(f"Error: Timeout connecting to WLED at {url}")
            return False
        except aiohttp.ClientError as e:
            print(f"Error: Failed to connect to WLED: {e}")
            return False
        except Exception as e:
            print(f"Error: Unexpected error connecting to WLED: {e}")
            return False
    
    async def send_command(self, command: str, score: float) -> bool:
        """Send a command to the WLED device, canceling any outstanding request.
        
        Args:
            command: WLED command string (without base URL)
            score: Current game score
            
        Returns:
            True if a new command was sent, False if skipped or failed
        """
        # Don't send multiple requests at once
        if self.current_http_task and not self.current_http_task.done():
            return False
        
        # Build the URL with score parameter
        score_param = self.calculate_score_param(score)
        url = self.build_command_url(self.ip_address, command, score_param)
        
        # Start new request
        self.current_http_task = asyncio.create_task(self._send_command_inner(url))
        return True
    
    @staticmethod
    def get_command_for_measure(measure: int, command_settings: Dict[int, str]) -> Optional[str]:
        """Get the appropriate WLED command for the current measure.
        
        Args:
            measure: Current measure number
            command_settings: Dictionary mapping measures to commands
            
        Returns:
            Command string if found for the measure, None otherwise
        """
        return command_settings.get(measure)
