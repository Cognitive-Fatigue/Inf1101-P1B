"""Line link to the watch. Pair A owns this file.

Pairs B and C only use send_line() and their own on_line(). BleLink (Bluetooth) and UsbLink
(cable) offer the same calls, so nothing else changes when switching between them.
"""
import asyncio

import serial
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
from serial.tools import list_ports

WATCH_IDS = (0x03EB, 0x8009)  # TinyScreen+ running a sketch
WATCH_NAME = "TinyKey"  # Bluetooth name set in watch/ble.ino
UART_WRITE = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Nordic UART: laptop writes here
UART_NOTIFY = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Nordic UART: watch notifies here
PACKET = 20  # bytes per Bluetooth packet


def find_port():
    for p in list_ports.comports():
        if (p.vid, p.pid) == WATCH_IDS:
            return p.device
    return None


def split_lines(buf):
    """Split received bytes into whole lines; returns (lines, leftover partial line)."""
    *lines, rest = buf.split(b"\n")
    return [l.rstrip(b"\r").decode("ascii", "replace") for l in lines if l.strip()], rest


class UsbLink:
    def __init__(self, on_line, on_connect=None, on_disconnect=None):
        self.on_line, self.on_connect, self.on_disconnect = on_line, on_connect, on_disconnect
        self.ser = None

    def send_line(self, text):
        if not self.ser:
            return False
        try:
            self.ser.write(text.encode("ascii") + b"\n")
            return True
        except serial.SerialException:
            return False  # the read loop notices the drop and reconnects

    async def run(self):
        """Connect, read lines forever, reconnect when the watch comes back."""
        while True:
            port = find_port()
            try:
                self.ser = serial.Serial(port, 115200, timeout=0.2, write_timeout=1) if port else None
            except serial.SerialException:
                self.ser = None
            if not self.ser:
                await asyncio.sleep(1)
                continue
            if self.on_connect:
                self.on_connect(port)
            buf = b""
            try:
                while True:
                    buf += await asyncio.to_thread(self.ser.read, self.ser.in_waiting or 1)
                    lines, buf = split_lines(buf)
                    for line in lines:
                        self.on_line(line)
            except serial.SerialException:
                pass
            self.ser.close()
            self.ser = None
            if self.on_disconnect:
                self.on_disconnect()


def packets(text):
    """Cut one message plus its newline into Bluetooth-sized packets."""
    data = text.encode("ascii") + b"\n"
    return [data[i:i + PACKET] for i in range(0, len(data), PACKET)]


class BleLink:
    def __init__(self, on_line, on_connect=None, on_disconnect=None):
        self.on_line, self.on_connect, self.on_disconnect = on_line, on_connect, on_disconnect
        self.client = None
        self.outbox = None

    def send_line(self, text):
        if not self.client:
            return False
        for packet in packets(text):
            self.outbox.put_nowait(packet)
        return True

    async def _write(self, client, gone):
        try:
            while True:
                await client.write_gatt_char(UART_WRITE, await self.outbox.get(), response=False)
        except (BleakError, OSError):
            gone.set()

    async def run(self):
        """Find the watch, read lines forever, reconnect when the link drops."""
        device = None
        while True:
            if device is None:
                device = await BleakScanner.find_device_by_name(WATCH_NAME, timeout=5)
                if not device:
                    continue
            gone = asyncio.Event()
            buf = b""

            def on_notify(_, data):
                nonlocal buf
                lines, buf = split_lines(buf + bytes(data))
                for line in lines:
                    self.on_line(line)

            connected = False
            try:
                # after a drop, connect straight to the known watch: a fresh scan on Windows sometimes took 7+ s
                async with BleakClient(device, disconnected_callback=lambda _: gone.set(), timeout=5) as client:
                    await client.start_notify(UART_NOTIFY, on_notify)
                    self.outbox = asyncio.Queue()
                    self.client, connected = client, True
                    if self.on_connect:
                        self.on_connect(device.address)
                    writer = asyncio.create_task(self._write(client, gone))
                    # also poll: under BleLink the disconnected_callback was seen not to fire (bleak 3.0.2, Windows)
                    while client.is_connected and not gone.is_set():
                        await asyncio.sleep(0.2)
                    writer.cancel()
            except (BleakError, OSError, asyncio.TimeoutError):
                if not connected:
                    device = None  # couldn't reach it by address: scan again
            self.client = None
            if connected and self.on_disconnect:
                self.on_disconnect()


if __name__ == "__main__":
    assert packets("ECHO:" + "x" * 30) == [b"ECHO:" + b"x" * 15, b"x" * 15 + b"\n"]
    assert packets("A" * 19) == [b"A" * 19 + b"\n"]
    assert packets("A" * 20) == [b"A" * 20, b"\n"]
    print("packets ok")
    assert split_lines(b"CMD:NEXT\nRESP:ab") == (["CMD:NEXT"], b"RESP:ab")
    assert split_lines(b"A\r\n\nB\n") == (["A", "B"], b"")
    assert split_lines(b"") == ([], b"")
    print("split_lines ok")
