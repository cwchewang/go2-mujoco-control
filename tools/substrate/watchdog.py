"""Native-call watchdog: EOF cancels; an expired deadline terminates the owner.

The owner's normal SIGALRM permits clean evidence sealing. This independent
process bounds an unresponsive native call; SIGKILL may leave incomplete raw
evidence, which verification rejects and the persistent attempt ledger preserves.
"""

import os
from pathlib import Path
import select
import signal
import sys


def birth(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
    except FileNotFoundError:
        return None


def main():
    pid, seconds = int(sys.argv[1]), float(sys.argv[2])
    identity = birth(pid)
    if identity is None:
        return
    # Pipe EOF also disarms if the owner exits unexpectedly; avoid PID reuse.
    if select.select([sys.stdin], [], [], seconds + 1)[0]:
        return
    if birth(pid) != identity:
        return
    os.kill(pid, signal.SIGTERM)
    if select.select([sys.stdin], [], [], 1)[0]:
        return
    if birth(pid) == identity:
        os.kill(pid, signal.SIGKILL)


if __name__ == "__main__":
    main()
