"""TinyKey laptop program. Pair A owns this file. Run: python main.py"""
import asyncio

import remote
import security
from link import UsbLink


def on_line(line):
    for handler in (security.on_line, remote.on_line):
        if handler(line):
            return
    # unknown messages are ignored


def on_connect(port):
    print(f"Watch connected on {port}")


def on_disconnect():
    print("Watch disconnected")  # Week 2: lock the laptop here


async def main():
    link = UsbLink(on_line, on_connect, on_disconnect)
    security.setup(link.send_line)
    remote.setup(link.send_line)
    await link.run()


if __name__ == "__main__":
    asyncio.run(main())
