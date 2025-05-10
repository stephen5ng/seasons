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
    def build_command_url(ip_address: str, command: str) -> str:
        """Build the full URL for a WLED command.
        
        Args:
            ip_address: IP address of the WLED device
            command: WLED command string (without base URL)
            
        Returns:
            Complete URL for the WLED command
        """
        return f"http://{ip_address}/win&{command}"
    
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
    
    async def send_command(self, command: str) -> bool:
        """Send a command to the WLED device, canceling any outstanding request.
        
        Args:
            command: WLED command string (without base URL)
            
        Returns:
            True if a new command was sent, False if skipped or failed
        """
        # Don't send multiple requests at once
        if self.current_http_task and not self.current_http_task.done():
            return False
        
        url = self.build_command_url(self.ip_address, command)
        
        self.current_http_task = asyncio.create_task(self._send_command_inner(url))
        return True

