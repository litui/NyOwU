import asyncio
import _bleio
from adafruit_ble import BLERadio
from adafruit_ble.uuid import StandardUUID
from adafruit_ble.advertising import Advertisement

NEKOMIMI_SERVICE_ID = StandardUUID(0x1802)
NEKOMIMI_CHARACTERISTIC_ID = StandardUUID(0x2a06)
NEKOMIMI_DEVICE_NAME = "YOWU-SELKIRK-3G"
NEKOMIMI_MAC_PREFIX_LE = b'\xa2\x5e\x78'  # Must be in Little Endian (reverse)
NEKOMIMI_INIT_BYTES = b'\xfc\x04\x01\x06\x08\x00\x00\x00\x00\x00\xf1' # Back to Big Endian =p

# This code is dependent upon a patched source tree for CircuitPython available here:
# https://github.com/litui/circuitpython/tree/litui-espressif-bleiofix
#
# (PR here: https://github.com/adafruit/circuitpython/pull/6614 )

# The real quirks to be aware of with these headphones are:
# 1) you can only connect to them (no bonding needed) if they are paired with
#    a (any) device over bluetooth classic. If they're not paired, they're not
#    advertising BLE.
# 2) there are two services with UUID 0x1802 and likewise two characteristics
#    with UUID 0x2a06. The first is seemingly useless, the other is legit.

# Using the Adafruit BLE as far as it can take us before
# switching to bleio.

class BLE:
    def __init__(self, adapter=None, name="OwO"):
        self._radio = BLERadio(adapter)
        self._radio.name = name
        self._adapter = self._radio._adapter
        self._discovered_addresses = []
        self._allow_loop = True
        self._conn = None
        self._services_cache = None
        self._char_cache = None
        self._packet_buffer = None
        self._write_lock = False

        self._last_responses = []

    @property
    def connected(self):
        return self._radio.connected

    @property
    def last_color(self):
        resp = self._parse_responses(self._last_responses)
        print(resp)
        return resp.get("last_color")

    @property
    def _bleio_conn(self):
        if self._conn:
            return self._conn._bleio_connection
        else:
            return None

    @property
    def _services(self):
        if not self._services_cache:
            try:
                self._services_cache = self._bleio_conn.discover_remote_services(
                    [NEKOMIMI_SERVICE_ID.bleio_uuid]
                )
            except _bleio.BluetoothError as e:
                print("Bluetooth error: {}".format(e))
            except TimeoutError as e:
                print("BLE connection timed out.")
        return self._services_cache

    @property
    def _characteristic(self):
        if not self._char_cache:
            if not self._services:
                print("Error: could not obtain BLE services.")
                return None
            for s in self._services:
                for c in s.characteristics:
                    try:
                        c.set_cccd(notify=True, indicate=True)
                        self._packet_buffer = _bleio.PacketBuffer(c, buffer_size=1024, max_packet_size=256)
                    except _bleio.BluetoothError as e:
                        # If no cccd on this characteristic, it's the wrong one.
                        continue
                    self._char_cache = c
        return self._char_cache

    async def initialize(self):
        await self._write(NEKOMIMI_INIT_BYTES)

    def _checksum(self, bs):
        total = sum(bs)
        csval = 0x100 - (total & 0xFF) - 1
        while csval < 0:
            csval = 0xFF + csval
        bs += bytes([csval])
        return bs

    async def _await_response(self):
        result = []
        if self.connected:
            found_first = False
            for i in range(0, 20):  # A reasonable assumption of max number of immediate responses
                rx = bytearray(self._packet_buffer.incoming_packet_length)
                self._packet_buffer.readinto(rx)
                filtbuf = bytes(rx).rstrip(b'\x00')
                if not filtbuf:
                    if found_first:
                        break
                else:
                    result.append(filtbuf)
                    found_first = True
                await asyncio.sleep(0.5)
        self._last_responses = result
        return result

    async def set_color(self, red=0.0, green=0.0, blue=0.0, neopixels=None):
        prefix = b'\xfc\x04\x01\x06\x00'
        affix = b'\x00\x00'
        redhex = bytes([int(red*255)])
        greenhex = bytes([int(green*255)])
        bluehex = bytes([int(blue*255)])
        combined = prefix + redhex + greenhex + bluehex + affix
        result = self._checksum(combined)
        await asyncio.sleep(0.1)
        if neopixels:
            color = (int(red*255) << 16) | (int(green*255) << 8) | int(blue*255)
            neopixels[0] = color
            # print(hex(color))
        await self._write(result)

    def _parse_responses(self, response):
        parsed = {}
        parsed["unknown"] = []
        for r in response:
            if r == b'7':
                parsed["connected"] = True
            elif r.startswith(b'\xfc\x03\x01\x05\x11'):
                print((r[5], r[6], r[7]))
                parsed["last_color"] = (r[4]/255, r[5]/255, r[6]/255)
            elif r.startswith(b'\xfc\x06\x04\x02'):
                parsed["unknown"].append({
                    "raw": r,
                    "speculation": "Initialization confirmation; ready to receive commands."
                })
            else:
                parsed["unknown"].append({
                    "raw": r,
                    "speculation": "None"
                })
        return parsed


    async def _write(self, input_bytes):
        if self.connected and self._characteristic:
            if not self._write_lock:
                self._write_lock = True
                self._characteristic.value = input_bytes
                await asyncio.sleep(0.5)
                response = await self._await_response()
                # print(response)
                if response:
                    self._write_lock = False
                    return True
            else:
                print("Attempted to write to BLE headphones while write-locked.")
        return False

    async def _connect(self, timeout=4):
        for address in self._discovered_addresses:
            try:
                self._conn = self._radio.connect(address, timeout=timeout)
                print("Successfully connected to Nekomimi!")
                return True
            except _bleio.BluetoothError:
                print("BLE failed to connect to {}.".format(address))
        if not self._discovered_addresses:
            print("No discovered addresses from previous scan.")
        return False

    async def _scan(self, scan_time=3, sleep_interval=3):
        # Use Adafruit BLE library for this part as it decodes the name for us.
        try:
            for adv in self._radio.start_scan(Advertisement, timeout=scan_time):
                if adv.connectable and adv.complete_name == NEKOMIMI_DEVICE_NAME:
                    if adv.address not in self._discovered_addresses:
                        self._discovered_addresses.append(adv.address)
            await asyncio.sleep(sleep_interval)
            self._radio.stop_scan()
        except _bleio.BluetoothError:
            # Sometimes we get "Unknown system firmware error: 30".
            # Might need to handle this somehow (reboot?)
            return False
        return True

    def _clear_discovered(self):
        self._discovered_addresses = []

    def _invalidate_caches(self):
        self._write_lock = False
        self._services_cache = None
        self._char_cache = None

    def stop(self):
        self._allow_loop = False

    async def setup(self):
        if await self._scan():
            if await self._connect():
                await asyncio.sleep(1)
                await self.initialize()
                return True
        return False

    async def loop(self, sleep_interval = 10):

        while self._allow_loop:
            if not self.connected:
                self._invalidate_caches()
                await self.setup()

            await asyncio.sleep(sleep_interval)