"""Line link to the watch. Pair A owns this file.

Pairs B and C only use send_line() and their own on_line(). USB now, Bluetooth (bleak) later,
behind the same two calls.
"""
import asyncio

import serial
from serial.tools import list_ports

WATCH_IDS = (0x03EB, 0x8009)  # TinyScreen+ running a sketch


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


if __name__ == "__main__":
    assert split_lines(b"CMD:NEXT\nRESP:ab") == (["CMD:NEXT"], b"RESP:ab")
    assert split_lines(b"A\r\n\nB\n") == (["A", "B"], b"")
    assert split_lines(b"") == ([], b"")
    print("split_lines ok")
