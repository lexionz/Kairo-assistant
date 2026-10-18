import asyncio
import hashlib
import json
import secrets
from dataclasses import dataclass


@dataclass
class Review:
    token: str
    task: str
    tool: str
    details: dict
    digest: str
    future: asyncio.Future


class Authority:
    def __init__(self, events, timeout=180):
        self.events = events
        self.timeout = timeout
        self.pending = None

    async def request(self, task, tool, details):
        if self.pending:
            raise RuntimeError("Another approval is pending")
        frozen = json.loads(json.dumps(details))
        digest = hashlib.sha256(json.dumps(frozen, sort_keys=True).encode()).hexdigest()
        review = Review(secrets.token_urlsafe(24), task, tool, frozen, digest, asyncio.get_running_loop().create_future())
        self.pending = review
        self.events.emit("state", state="permission", text=tool)
        self.events.emit("approval", token=review.token, task=task, tool=tool, details=frozen)
        try:
            return await asyncio.wait_for(review.future, self.timeout)
        except TimeoutError:
            return False
        finally:
            if self.pending is review:
                self.pending = None
            self.events.emit("approval_closed", token=review.token)

    def decide(self, token, task, allowed):
        review = self.pending
        if not review or token != review.token or task != review.task or review.future.done():
            return False
        review.future.set_result(allowed is True)
        return True

    def cancel(self):
        if self.pending and not self.pending.future.done():
            self.pending.future.cancel()
