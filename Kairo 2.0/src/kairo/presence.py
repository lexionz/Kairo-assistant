"""Local opt-in presence policy. No network or microphone side effects on import."""
import re
import time


def sleep_command(text):
    words = re.sub(r"[^a-z ]", "", text.lower()).strip()
    return words in {"kairo go to sleep", "kairo sleep", "go to sleep", "kairo go to sleep please"}


class WakePolicy:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.state = "disabled"
        self.last = float("-inf")

    def enable(self):
        self.state = "sleeping"

    def disable(self):
        self.state = "disabled"

    def wake(self, phrase=None, confidence=0, clap=False):
        if self.state != "sleeping" or self.clock() - self.last < 5:
            return False
        if not clap and not (phrase and phrase.lower().strip() == "hey kairo" and confidence >= .85):
            return False
        self.last = self.clock()
        self.state = "active"
        return True

    def sleep(self):
        if self.state != "disabled":
            self.state = "sleeping"
            self.last = self.clock()


class ClapDetector:
    """Two short transients following quiet, calibrated locally; rejects sustained noise."""
    def __init__(self, threshold=.35):
        if not .15 <= threshold <= .95:
            raise ValueError("Clap threshold must be 0.15–0.95")
        self.threshold = threshold
        self.noise = []
        self.first = None
        self.quiet = 0
        self.last = float("-inf")

    def feed(self, peak, rms, now):
        if len(self.noise) < 150:
            self.noise.append(rms)
            return False
        floor = max(sum(self.noise) / len(self.noise), .003)
        impulse = peak >= self.threshold and peak > rms * 3 and rms > floor * 3
        quiet = rms < max(.04, floor * 2)
        if impulse and self.quiet >= 3 and now - self.last > 5:
            if self.first is not None and .18 <= now - self.first <= .8:
                self.last, self.first, self.quiet = now, None, 0
                return True
            self.first = now
        self.quiet = self.quiet + 1 if quiet else 0
        return False
