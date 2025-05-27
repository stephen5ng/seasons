"""sACN (E1.31) display implementation for DMX over Ethernet."""
import logging
import time
import socket
from typing import List, Dict
from pygame import Color
from game_constants import DISPLAY_LED_OFFSET

# For sACN mode
try:
    import sacn
    HAS_SACN = True
except ImportError:
    HAS_SACN = False
    sacn = None

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

LEDS_PER_UNIVERSE = 170  # Maximum LEDs per DMX universe (512 channels / 3 channels per LED)
SACN_DNS_HOSTNAME = "seasons-uno.local"  # LED controller hostname
REFRESH_RATE = 22  # Hz - how often to send updates
MIN_TIME_BETWEEN_UPDATES = 1.0 / REFRESH_RATE  # seconds

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
        logger.info(f"Resolving hostname {hostname}...")
        ip_address = socket.gethostbyname(hostname)
        logger.info(f"Resolved {hostname} to {ip_address}")
        return ip_address
    except socket.gaierror as e:
        logger.error(f"Failed to resolve {hostname}: {e}")
        raise

class SacnDisplay:
    """sACN (E1.31) display implementation for DMX over Ethernet."""
    def __init__(self, led_count: int) -> None:
        """Initialize sACN display.
        
        Args:
            led_count: Number of LEDs in the strip
        """
        self.led_count = led_count
        self.leds_per_strip = led_count//3
        logger.info(f"Initializing sACN display with {led_count} LEDs")
        
        # Calculate number of universes needed (170 LEDs per universe)
        self.num_universes = (led_count + LEDS_PER_UNIVERSE - 1) // LEDS_PER_UNIVERSE
        self.universes = list(range(1, self.num_universes + 1))  # Universes 1 to N
        print(f"Using {self.num_universes} universes: {self.universes}")
        
        # Resolve the LED controller's IP address once at startup
        self.sacn_ip_address = resolve_mdns_hostname(SACN_DNS_HOSTNAME)
        
        # Initialize sACN sender with manual refresh rate
        self.sender = sacn.sACNsender(fps=REFRESH_RATE, sync_universe=self.universes[-1] + 1)
        self.sender.start()
        
        # Track which universes have changed
        self.changed_universes: Dict[int, bool] = {universe: False for universe in self.universes}
        self.last_update_time = 0.0
        
        # Activate all needed universes
        for universe in self.universes:
            self.sender.activate_output(universe)
            self.sender[universe].destination = self.sacn_ip_address
            self.sender[universe].multicast = False  # Set to True if multiple receivers
            # Manually control refresh rate
            self.sender[universe].manual_flush = True
            logger.info(f"Activated universe {universe} -> {self.sacn_ip_address}")
        
        # Initialize DMX data buffer
        self.clear()
        
    def set_pixel(self, pos: int, color: Color, trail_start_offset: int, _: int) -> None:
        """Set a pixel color in the DMX data buffer.
        
        Args:
            pos: LED position (0 to led_count-1)
            color: RGB color
            trail_start_offset: Offset for trail position
            _: Unused parameter (pygame_radius)
        """
        # Use offset on first two strips but not on line 5.
        if trail_start_offset < self.leds_per_strip*2:
            pos = (pos + DISPLAY_LED_OFFSET) % self.leds_per_strip

        pos += trail_start_offset

        # Calculate DMX address (3 channels per LED)
        addr = pos * 3
        
        # Set RGB values in DMX data
        self.dmx_data[addr] = color.r
        self.dmx_data[addr + 1] = color.g
        self.dmx_data[addr + 2] = color.b
        
        # Mark affected universe as changed
        universe = (addr // (LEDS_PER_UNIVERSE * 3)) + 1
        if universe in self.changed_universes:
            self.changed_universes[universe] = True
        
    def set_fifth_line_pixel(self, pos: int, color: Color, trail_start_offset: int) -> None:
        """Set a pixel on the fifth line.
        
        Args:
            pos: LED position (0 to led_count-1)
            color: RGB color
        """
        self.set_pixel(pos, color, trail_start_offset, 0)
        
    def draw_score_lines(self, score: float) -> None:
        """Draw score lines (not supported in sACN)."""
        pass
        
    def clear(self) -> None:
        """Clear all pixels by setting to black."""
        total_channels = self.led_count * 3  # 3 channels per LED
        self.dmx_data = [0] * total_channels     
        # Mark all universes as changed when clearing
        for universe in self.universes:
            self.changed_universes[universe] = True
           
    def show(self) -> None:
        """Send only changed universes of DMX data, respecting rate limiting."""
        current_time = time.time()
        time_since_last_update = current_time - self.last_update_time
        
        # Rate limit updates
        if time_since_last_update < MIN_TIME_BETWEEN_UPDATES:
            return
            
        any_changes = False
        for universe in self.universes:
            if not self.changed_universes[universe]:
                continue
                
            # Calculate start and end indices for this universe
            start_idx = (universe - 1) * LEDS_PER_UNIVERSE * 3
            end_idx = min(start_idx + (LEDS_PER_UNIVERSE * 3), len(self.dmx_data))
            
            # Get the slice of DMX data for this universe
            universe_data = self.dmx_data[start_idx:end_idx]
            
            any_changes = True
            # Pad to 512 bytes if needed
            if len(universe_data) < 512:
                universe_data = list(universe_data) + [0] * (512 - len(universe_data))
            
            # Queue the universe update
            self.sender[universe].dmx_data = tuple(universe_data)
        
        # If any universes changed, send a sync to update all changed universes at once
        if any_changes:
            self.sender.flush()
            self.last_update_time = current_time
            
        # Reset change tracking
        self.changed_universes = {universe: False for universe in self.universes}
        
    def cleanup(self) -> None:
        """Clean up sACN resources by stopping the sender."""
        self.sender.stop()
