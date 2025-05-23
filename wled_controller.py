"""WLED controller utilities."""
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional

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
    def build_json_url(ip_address: str) -> str:
        """Build the URL for JSON commands.
        
        Args:
            ip_address: IP address of the WLED device
            
        Returns:
            Complete URL for JSON commands
        """
        return f"http://{ip_address}/json/state"
    
    async def _send_json_inner(self, url: str, json_data: Dict[str, Any]) -> bool:
        """Internal method to send WLED JSON command.
        
        Args:
            url: Complete URL for the JSON command
            json_data: JSON data to send
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        try:
            json_str = json.dumps(json_data)
            
            async with self.http_session.post(url, data=json_str, headers={'Content-Type': 'application/json'}) as response:
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
    
    async def send_json(self, json_data: Dict[str, Any]) -> bool:
        """Send a JSON command to the WLED device.
        
        Args:
            json_data: JSON data to send
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        if self.current_http_task and not self.current_http_task.done():
            return False
        
        url = self.build_json_url(self.ip_address)
        self.current_http_task = asyncio.create_task(self._send_json_inner(url, json_data))
        return True

