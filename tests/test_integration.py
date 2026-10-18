import asyncio
import json
import threading
from pathlib import Path
import httpx
import pytest
from kairo.application import Application
from kairo.web import Bridge, make_server
from kairo.workspace import Workspace, digest


class SilentVoice:
    async def speak(self, text):
        self.spoken = text

    async def stop(self):
        pass


class TestBrain:
    async def complete(self, messages, tools):
        return {"content": "A test response", "tool_calls": []}


def test_http_auth_origin_conversation_and_approval(tmp_path):
    async def run():
        app = Application(tmp_path / "data", brain=TestBrain(), voice=SilentVoice())
        bridge = Bridge(app, asyncio.get_running_loop())
        static = tmp_path / "static"
        static.mkdir()
        (static / "index.html").write_text("KAIRO")
        server = make_server(bridge, static)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        headers = {"Authorization": "Bearer " + bridge.token, "Origin": origin}
        try:
            async with httpx.AsyncClient(base_url=origin, trust_env=False) as client:
                assert (await client.get("/")).text == "KAIRO"
                assert (await client.get("/api/events")).status_code == 401
                assert (await client.get("/api/events", headers={**headers, "Host": "evil.example"})).status_code == 403
                assert (await client.post("/api/command", headers={**headers, "Origin": "https://evil.example"}, json={"action": "request", "text": "no"})).status_code == 403
                assert (await client.post("/api/command", headers=headers, json={"action": "request", "text": "hello"})).status_code == 200
                await asyncio.sleep(.02)
                events = (await client.get("/api/events", headers=headers)).json()
                assert any(e["kind"] == "result" and e["payload"]["answer"] == "A test response" for e in events["events"])
                approval = asyncio.create_task(app.authority.request("t1", "write", {"content": "exact"}))
                await asyncio.sleep(0)
                review = (await client.get("/api/events", headers=headers)).json()["approval"]
                forged = {"action": "approve", "task": "t1", "token": "forged", "allowed": True}
                assert (await client.post("/api/command", headers=headers, json=forged)).status_code == 400
                proper = {**forged, "token": review["token"]}
                assert (await client.post("/api/command", headers=headers, json=proper)).status_code == 200
                assert await approval
                assert (await client.post("/api/command", headers=headers, json=proper)).status_code == 400
                waiting = asyncio.create_task(app.authority.request("t2", "write", {}))
                await asyncio.sleep(0)
                assert (await client.post("/api/command", headers=headers, json={"action": "stop"})).status_code == 200
                with pytest.raises(asyncio.CancelledError):
                    await waiting
                assert (await client.get("/api/events", headers=headers)).json()["approval"] is None
        finally:
            await asyncio.to_thread(server.shutdown)
            server.server_close()
            app.journal.close()
    asyncio.run(run())


def test_checkpoint_undo_and_stale_guard(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    storage = tmp_path / "state"
    workspace = Workspace({"test": {"root": str(root)}}, storage)
    (root / "a.txt").write_text("before")
    def edit(text, expected):
        return workspace.edit(workspace.prepare_edit({"project": "test", "path": "a.txt", "content": text, "expected_hash": expected}))
    first = edit("after", digest("before"))
    identity = Path(first["checkpoint"]).stem
    prepared = workspace.prepare_undo({"checkpoint": identity})
    (root / "a.txt").write_text("newer")
    with pytest.raises(ValueError, match="newer work"):
        workspace.undo(prepared)
    (root / "a.txt").write_text("after")
    workspace.undo(prepared)
    assert (root / "a.txt").read_text() == "before"
    assert workspace.revisions["test"] == 2


def test_memory_recall_beyond_initial_hundred(tmp_path):
    from kairo.journal import Journal
    journal = Journal(tmp_path)
    for index in range(120):
        journal.remember(f"preference {index}")
    journal.remember("unique astronomy preference")
    assert journal.recall("astronomy")[0]["text"] == "unique astronomy preference"
    journal.close()
