# NyOwU 😸

Soon, a remote API for controlling the Yowu Selkirk 3G headphones LEDs and sound quality settings (and potentially other things in future?) over Bluetooth Low Energy (BLE).

For now, this repository will document what I've learned about the software and BLE calls.

## Rationale

Yowu provides an, in my opinion, bloated, telemetry-ridden app for controlling these headphones. More importantly for my purposes, it does not function on the desktop and does not allow control from third-party applications via an API or other mechanisms. My goal has been to use these headphones in connection with music and my Twitch stream, but to my knowledge Yowu only allows synchronizing the headphones to music via their app.

Yowu's app requires a (free) login to be able to access advanced settings to program custom colours and effects. This seems very silly to me since all the colours and effects remain stored locally. The headphones themselves do not communicate directly with Yowu's servers.

Another consideration is that, for my purposes, I want the headphones to be somewhat insecure, as I would like the system my headphones are connected to for monitoring audio to be different from the system controlling the colours over BLE. It seemed for awhile as I was sorting through the stack that there was some sort of BLE security on the headphones preventing access unless the same control device was also connected over Bluetooth Classic, but this turned out to be nonsense. Yes, the headphones must be connected to _something_, but any BLE client address can inspect and communicate with them after that connection is made. BLE is also available when the headphones are turned on while connected to USB.

## BLE Specification

Once a BLE client is connected, the relevant UUIDs are as follows:

* Service UUID: ```00001802-0000-1000-8000-00805f9b34fb```
* Characteristic UUID: ```00002a06-0000-1000-8000-00805f9b34fb```

Writing and notification occur on the above characteristic UUID. Once connected, the initialization bytes must be sent: ```FC040106080000000000F1```. This readies the device to receive other commands. It will not obey commands until the initialization bytes are sent.

When valid commands are sent, the characteristic will respond by executing the command and returning the command as sent via the characteristic notifications.

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
S = b0 + b1 + b2 + b3 + b4 + b5 + b6 + b7 + b8 + b9
CHKSUM = 100 - (S & 255)
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

Example: ```fc050202920069``` (original sound mode)