"""Pair C: turn CMD lines into key presses (pynput)."""

send_line = None


def setup(send):
    global send_line
    send_line = send


def on_line(line):
    """Return True if this line was for you."""
    return False
