# TinyKey

The TinyScreen+ watch works as a security key and a remote for the laptop.
Watch (Arduino) <-- USB now, Bluetooth later --> Laptop (Python)

## Who works where

| Pair | Watch | Laptop |
|---|---|---|
| A – link and merging | `watch/watch.ino` | `laptop/link.py`, `laptop/main.py` |
| B – security | `watch/security.ino` | `laptop/security.py` |
| C – remote | `watch/remote.ino` | `laptop/remote.py` |

Pairs B and C never touch USB or Bluetooth. Use only these:

- Watch: `sendLine("CMD:NEXT")` to send. Your `...OnLine(line)` is called with each whole line received; return `true` if it was yours.
- Laptop: `send_line("CHAL:...")` to send. Your `on_line(line)` is called with each whole line; return `True` if it was yours.

## Running

- Watch: open `watch/watch.ino` in the Arduino IDE (the other tabs load with it), board "TinyScreen+", upload. Needs the STBLE library and the BLE TinyShield on the stack.
- STBLE fix (do this once): the installed library's `src/arduino_bluenrg_ble.cpp` has empty functions, so Bluetooth never starts. Copy `stble-patch/arduino_bluenrg_ble.cpp` over it (library folder: Arduino `libraries/STBLE/src/`), then rebuild. Without it, the watch still compiles and USB works, but no Bluetooth.
- Laptop: `pip install pyserial bleak`, then `python laptop/main.py` (Bluetooth; it finds the watch by the name `TinyKey`). Add `--usb` to use the cable instead.
- Link test: `python laptop/echo_test.py` sends 100 random lines and checks they all come back. `--usb` tests the cable; `--reconnect 10` also drops the Bluetooth link 10 times and checks each reconnect takes under 5 s.
- Known issue: most reconnects take about 2 s, but roughly 1 in 50 test drops takes about 15 s. When the watch ends the link (DROP), the laptop sometimes never confirms it, so the watch waits about 12 s for its Bluetooth chip to give up (reason 0x22) before it advertises again. Walking out of range ends the link a different way (a timeout on both sides), so this may not happen in real use; not yet tested.

## Credits

- `watch/ble.ino` is based on UART.ino from the STBLE library's UARTPassThrough example (Ben Rose, TinyCircuits).

## Message rules

- Format `TYPE:payload`, plain ASCII, no spaces, one message per line ending in `\n`.
- Type names uppercase. Hex values lowercase.
- Unknown messages are ignored, never crash. Lines over 127 characters are dropped.
- Same text over USB and Bluetooth. Over Bluetooth, Pair A splits lines into packets of at most 20 bytes and joins them back.

### Laptop to watch

| Message | Sent by | Meaning |
|---|---|---|
| `CHAL:<32 hex>:VAULT` | B | "Approve opening the vault?" The hex is a random 16-byte challenge. |
| `ECHO:<text>` | A | Link test. The watch sends the same line back. |

### Watch to laptop

| Message | Sent by | Meaning |
|---|---|---|
| `RESP:<64 hex>` | B | Approved by double-tap. HMAC-SHA256 result. |
| `RESP:REJECT` | B | No double-tap within 10 s. |
| `CMD:NEXT` / `CMD:PREV` | C | Right / left arrow (slides). |
| `CMD:PLAY` | C | Media play/pause. |
| `CMD:VOLUP` / `CMD:VOLDN` | C | Media volume up / down (long press). |

One button press sends exactly one message.

### Proposed, not agreed yet

- `MODE:KEY` / `MODE:MEDIA` (watch to laptop): the watch switched modes.
- `PING` (laptop) / `PONG` (watch) every second, so the laptop notices a lost watch within the 5 s lock target.

### HMAC

- Key: shared 32-byte key, hardcoded on both sides (known limitation, stated in the video).
- Input: the 16 raw challenge bytes (not the hex text), then the ASCII bytes of the action, e.g. `VAULT`.
- Output: HMAC-SHA256, sent as 64 lowercase hex characters.
- Python reference: `hmac.new(key, challenge + b"VAULT", hashlib.sha256).hexdigest()`
