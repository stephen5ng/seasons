import platform

from PIL import Image
import pygame
from pygame.image import tobytes
from pygame.time import get_ticks

if platform.system() != "Darwin":
    from rgbmatrix import graphics, RGBMatrix, RGBMatrixOptions
    import rgbmatrix
else:
    from RGBMatrixEmulator import graphics, RGBMatrix, RGBMatrixOptions
    import RGBMatrixEmulator
from typing import Union

matrix: RGBMatrix = None
offscreen_canvas: Union["RGBMatrixEmulator.emulation.canvas.Canvas","RGBMatrix.Canvas"]

def create_rgbmatrix() -> Union["RGBMatrixEmulator.RGBMatrix", "rgbmatrix.RGBMatrix"]:
    options = RGBMatrixOptions()

    options.brightness = 100
    options.disable_hardware_pulsing = True
    options.drop_privileges = True
    options.gpio_slowdown = 5
    options.hardware_mapping = "regular"
    options.led_rgb_sequence = "RGB"
    options.multiplexing = 1
    options.panel_type = ""
    options.pwm_bits = 11
    options.pwm_lsb_nanoseconds = 130
    options.row_address_type = 0

    if platform.system() == "Darwin":
        options.rows = 96
        options.cols = 128
        options.chain_length = 1
        options.parallel = 1
    else:
        options.rows = 32
        options.cols = 64
        options.chain_length = 2
        options.parallel = 1

    #sudo examples-api-use/demo -D0 --led-no-hardware-pulse --led-cols=64 --led-rows=32 --led-slowdown-gpio=5 --led-multiplexing=1 --led-pixel-mapper=U-mapper --led-chain 8 --led-parallel=3

    return RGBMatrix(options=options)


def init() -> None:
    global matrix, offscreen_canvas

    matrix = create_rgbmatrix()
    offscreen_canvas = matrix.CreateFrameCanvas()

last_image: bytes = b''
update_count = 0
total_time = 1
def update(screen: pygame.Surface) -> None:
    global last_image, total_time,update_count
    pixels = tobytes(screen, "RGB")
    if pixels == last_image:
        return
    last_image = pixels
    img = Image.frombytes("RGB", (screen.get_width(), screen.get_height()), pixels)

    if platform.system() != "Darwin":
# mypy: disable-error-code=attr-defined
        img = img.rotate(180, Image.NEAREST, expand=1)

    start = get_ticks()
    offscreen_canvas.SetImage(img)
    matrix.SwapOnVSync(offscreen_canvas)
    total_time += get_ticks() - start
    update_count += 1
    # print(f"fps: {1000*update_count/total_time}")
