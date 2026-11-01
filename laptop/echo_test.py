"""Link test: sends random ECHO lines and checks each comes back unchanged. Run: python echo_test.py [count]"""
import asyncio
import random
import string
import sys

from link import UsbLink


async def main(count):
    received = asyncio.Queue()
    connected = asyncio.Event()
    link = UsbLink(received.put_nowait, lambda port: connected.set())
    reader = asyncio.create_task(link.run())
    await asyncio.wait_for(connected.wait(), 10)

    failures = 0
    for i in range(count):
        # up to the watch's 127-character limit
        sent = "ECHO:" + "".join(random.choices(string.ascii_letters + string.digits, k=random.randint(1, 122)))
        link.send_line(sent)
        try:
            got = await asyncio.wait_for(received.get(), 2)
        except asyncio.TimeoutError:
            got = None
        if got != sent:
            failures += 1
            print(f"#{i} sent {sent!r} got {got!r}")
    reader.cancel()
    print(f"{count - failures}/{count} lines came back intact")
    return failures == 0


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 100)) else 1)
