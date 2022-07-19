# <sub>*nyan*</sub>OwO 😸

Demo code and detail for controlling the Yowu Selkirk 3G headphones LEDs and sound quality settings (and potentially other things in future?) over Bluetooth Low Energy (BLE) using an Unexpected Maker FeatherS3 (ESP32-S3). Leverages CircuitPython which is layered atop the Espressif ESP-IDF and Apache NimBLE.

> This project is in no way affiliated with YOWU. I enjoy and support their hardware and wish their developers all the best in business and in life.

## Dependencies

This code depends on a relatively minor patch to the _bleio implementation in CircuitPython. For those using identical hardware to me, I've saved you the trouble of a build by including the .uf2 image to load directly onto your Unexpected Maker FeatherS3.

This code has only been tested on the Espressif port of CircuitPython, so depending on the underlying Bluetooth stack in other ports, it may or may not work. Your mileage may vary.

Otherwise, you're going to be [compiling the source code yourself](https://learn.adafruit.com/building-circuitpython/build-circuitpython), but use [my forked repository](https://github.com/litui/circuitpython/) as your git source until [my pull request](https://github.com/adafruit/circuitpython/pull/6614) is merged.

Steps:

1. Build and install CircuitPython from my fork, above (or use my .uf2 from the `build` path here if it matches your hardware). Follow the guides to your hardware for how to build and install CircuitPython.

2. Download a current [Adafruit CircuitPython Library Bundle for version 8.x](https://circuitpython.org/libraries).

3. Copy the `adafruit_ble` directory from the library bundle into the `lib` path of your `CIRCUITPY` drive.

4. Copy the `handlers` directory from this repo into the root of your `CIRCUITPY` drive.

5. Copy the `code.py` file into the root of your `CIRCUITPY` drive.

6. Power up your YOWU-SELKIRK-3G headphones, pair them with _another_ device (like your phone, laptop, stereo, etc., your choice) over Bluetooth Classic. Like magic they should start advertising BLE services. You can confirm this with widely available software LightBlue or your BLE scanner of choice.

7. If your Feather32 was already powered up, it should have connected and started cycling the colours on your headphones.

I've given you the handler to do what you will with the colour, but the only thing this demo does is cycle the colour. Through the demo it should be easy enough to modify to suit your purposes.

## Considerations

There are two major considerations with this device:

1. The headphones must be connected to _something_ over Bluetooth Classic before they will advertise BLE services. You cannot connect to them with BLE unless they are already connected to _something_ over Bluetooth Classic. It doesn't have to be the same system you're using as a BLE client (in fact, it can't be if your microcontroller only supports BLE).

2. Without getting into the weeds (I will below), the developers of this hardware did something quirky with the service advertisements: they doubled up on the Immediate Alert service at UUID 0x1802 and the Alert Level notify/write characteristic at UUID 0x2a06. Not only are they doubled, but the first one reporting its UUID (and thus being detected by most BLE client software) is apparently useless.

My patched _bleio code with the Espressif port of the NimBLE backend works reasonably well to be able to differentiate the two services and characteristics with the same UUID, but many (most?) do not. Those that have trouble for one reason or another in my tests include: Bluez, Arduino_BLE, BluetoothSerial, and Adafruit_BLE (though this one I'm using for part of the connection process as it's quicker for that than raw _bleio). If you have success with any of these, please let me know and I'll update this list.

## Rationale

Yowu provides an, in my opinion, bloated, telemetry-ridden app for controlling these headphones. More importantly for my purposes, it does not function on the desktop and does not allow control from third-party applications via an API or other mechanisms. My goal has been to use these headphones in connection with music and my Twitch stream, but to my knowledge Yowu only allows synchronizing the headphones to music via their app.

Yowu's app requires a (free) login to be able to access advanced settings to program custom colours and effects. This seems very silly to me since all the colours and effects remain stored locally. The headphones themselves do not communicate directly with Yowu's servers.

In short, I bought the hardware and should be able to use it as I choose, with the devices I choose, to the full extent I can make use of the feature set.

## BLE Specification

Once a BLE client is connected, the relevant UUIDs are as follows:

* 16 bit Service UUID: ```0x1802``` (128: ```00001802-0000-1000-8000-00805f9b34fb```)
* Characteristic UUID: ```0x2a06``` (128:  ```00002a06-0000-1000-8000-00805f9b34fb```)

Writing and notification occur on the **second appearance** of the above service and characteristic UUIDs. Again, the underlying BLE stack you're using **MUST** be able to differentiate between these for it to work.

Once connected (you may see a status ), the initialization bytes must be sent (properly translated to binary pairs... not all BLE implementations will do this for you): ```FC040106080000000000F1```. This readies the device to receive other commands. It will not obey commands until the initialization bytes are sent.

When subscribed to notifications you may see 0x37 fill the dead air. This seems to be a keepalive byte.

When valid colour commands are sent, the characteristic will respond by executing the command and returning the *previous colour value* as a response. You'll see how this works looking over my BLE handler code.

Here are the basics of command byte composition, including calculation of the checksum value.

### Byte Map - Mode 0 (Colour Commands)

| Byte #     | Description                   |
|------------|-------------------------------|
| 0, 1, 2, 3 | Command Prefix (FC040106)     |
| 4          | Mode (00)                     |
| 5, 6, 7    | RGB Colour                    |
| 8, 9       | Unused (0000)                 |
| 10         | Checksum (algorithm below)    |

Example: ```FC040106080000000000F1``` (initialization command)

#### Checksum Algorithm

Appended to the end of the Byte Map as the eleventh byte.

```
composed_command = b0 + b1 + b2 + b3 + b4 + b5 + b6 + b7 + b8 + b9
completed_command = 0x100 - (composed_command & 0xFF)
```

### Byte Map - Modes 1, 2, 3, 4 (Effect Type Commands)

| Byte #     | Description                   |
|------------|-------------------------------|
| 0, 1, 2, 3 | Command Prefix (FC040106)     |
| 4          | Mode (01, 02, 03, and 04)     |
| 5, 6, 7    | Unused?                       |
| 8          | Frequency  (8 & 9 might be in reverse order) |
| 9          | Duration                      |
| 10         | Checksum (same as Mode 0)     |

Example: ```FC0401060000FF000000FA``` (set colour to green)

### Byte Map - Audio Profile Mode

| Byte #     | Description                    |
|------------|--------------------------------|
| 0, 1, 2, 3 | Command Prefix (FC050202)      |
| 4          | ? (92)                         |
| 5          | Audio Profile (0, 1, 2, 3)     |
| 6          | Checksum (haven't decoded yet) |

Example: ```FC050202920069``` (original sound mode)

## Next steps

There is more to discover and implement in this code, but I hope this gives folks a good starting point to build support into other frameworks and languages and expand support to other models (will accept donations of YOWU elf-ear earphones or Hatsune Miku headphones...for the cause).
