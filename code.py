import asyncio
from handlers.ble import BLE

ble = BLE()

# This function taken from feathers3.py:
#FeatherS3 Helper Library
# 2022 Seon Rozenblum, Unexpected Maker
#
# Project home:
#   https://feathers3.io
#
def rgb_color_wheel(wheel_pos):
    """Color wheel to allow for cycling through the rainbow of RGB colors."""
    wheel_pos = wheel_pos % 255

    if wheel_pos < 85:
        return 255 - wheel_pos * 3, 0, wheel_pos * 3
    elif wheel_pos < 170:
        wheel_pos -= 85
        return 0, wheel_pos * 3, 255 - wheel_pos * 3
    else:
        wheel_pos -= 170
        return wheel_pos * 3, 255 - wheel_pos * 3, 0

def rgb_cycler(inc=1, offset=0):
    while True:            
        for i in range(0, 255, inc):
            r, g, b = rgb_color_wheel(i)
            yield (r/255, g/255, b/255)

async def minicron(sleep_duration=1):
    rgbicycle = rgb_cycler()

    while True:
        r, g, b = next(rgbicycle)
        await ble.set_color(r, g, b)
        await asyncio.sleep(sleep_duration)

async def main():
    ble_setup = asyncio.create_task(ble.setup())
    await asyncio.gather(ble_setup)

    ble_loop = asyncio.create_task(ble.loop())
    minicron_loop = asyncio.create_task(minicron())
    await asyncio.gather(ble_loop, minicron_loop)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass