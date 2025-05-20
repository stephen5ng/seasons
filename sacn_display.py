"""sACN (E1.31) display implementation for DMX over Ethernet."""
import logging
from typing import List
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
WLED_LEDS_PER_STRIP = 300  # WLED is configured for 300 LEDs per strip
SACN_IP_ADDRESS = "wled-f4afec.local"  # Hardcoded IP address for sACN receiver

class SacnDisplay:
    """sACN (E1.31) display implementation for DMX over Ethernet."""
    def __init__(self, led_count: int) -> None:
        """Initialize sACN display.
        
        Args:
            led_count: Number of LEDs in the strip
        """
        if not HAS_SACN:
            raise ImportError("sacn package is required for sACN support")
            
        self.led_count = led_count
        self.leds_per_strip = led_count//3
        logger.info(f"Initializing sACN display with {led_count} LEDs")
        
        # Calculate number of universes needed (170 LEDs per universe)
        self.num_universes = (led_count + LEDS_PER_UNIVERSE - 1) // LEDS_PER_UNIVERSE
        self.universes = list(range(1, self.num_universes + 1))  # Universes 1 to N
        logger.info(f"Using {self.num_universes} universes: {self.universes}")
        
        self.sender = sacn.sACNsender()
        self.sender.start()
        
        # Activate all needed universes
        for universe in self.universes:
            self.sender.activate_output(universe)
            self.sender[universe].destination = SACN_IP_ADDRESS
            self.sender[universe].multicast = False
            logger.info(f"Activated universe {universe} -> {SACN_IP_ADDRESS}")
        
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
        pos = (pos + DISPLAY_LED_OFFSET) % self.leds_per_strip
        pos += trail_start_offset

        # Calculate DMX address (3 channels per LED)
        addr = pos * 3

        pos += 3*trail_start_offset
        # Set RGB values in DMX data
        self.dmx_data[addr] = color.r
        self.dmx_data[addr + 1] = color.g
        self.dmx_data[addr + 2] = color.b
        
        # logger.debug(f"Set pixel {pos} to RGB({color.r}, {color.g}, {color.b})")
        
    def set_fifth_line_pixel(self, pos: int, color: Color, trail_start_offset: int) -> None:
        """Set a pixel on the fifth line.
        
        Args:
            pos: LED position (0 to led_count-1)
            color: RGB color
        """
        self.set_pixel(pos, color, trail_start_offset, 0)
        
    def draw_score_lines(self, score: float) -> None:
        """Draw score lines (not supported in sACN)."""
        # logger.debug(f"Score lines requested with score {score}")
        pass
        
    def clear(self) -> None:
        """Clear all pixels by setting to black."""
        total_channels = self.led_count * 3  # 3 channels per LED
        self.dmx_data = [0] * total_channels     
        # print(f"len(self.dmx_data): {len(self.dmx_data)}")
           
    def show(self) -> None:
        """Send the current DMX data to all active universes."""
        for universe in self.universes:
            # Calculate start and end indices for this universe (170 LEDs per universe)
            start_idx = (universe - 1) * LEDS_PER_UNIVERSE * 3  # 170 LEDs * 3 channels per LED
            end_idx = min(start_idx + (LEDS_PER_UNIVERSE * 3), len(self.dmx_data))  # Don't exceed total data length
            
            # Get the slice of DMX data for this universe
            universe_data = self.dmx_data[start_idx:end_idx]
            
            # Pad to 512 bytes if needed
            if len(universe_data) < 512:
                universe_data = list(universe_data) + [0] * (512 - len(universe_data))
            
            # Send only this universe's portion of the data
            self.sender[universe].dmx_data = tuple(universe_data)
            # logger.debug(f"Sent universe {universe} data: {len(universe_data)} bytes (LEDs {start_idx//3}-{end_idx//3})")
        
    def cleanup(self) -> None:
        """Clean up sACN resources by stopping the sender."""
        self.sender.stop()
