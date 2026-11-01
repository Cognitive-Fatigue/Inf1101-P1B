"""Pair B: vault approval. Send CHAL with send_line(), check RESP in on_line()."""

send_line = None


def setup(send):
    global send_line
    send_line = send


def on_line(line):
    """Return True if this line was for you."""
    return False
