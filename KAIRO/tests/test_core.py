import asyncio
import json
import sys
from pathlib import Path
import pytest
from kairo.authority import Authority
from kairo.contracts import Events, Tool, parameters, validate
from kairo.journal import Journal
from kairo.research import Research, public_target
from kairo.runtime import Runtime
from kairo.tools import Tools, register
from kairo.workspace import Workspace, digest


def setup(tmp_path, approve=True):
    root = tmp_path / "project"
    root.mkdir()
    (root / "value.py").write_text("value = 1\n", newline="")
    (root / "check.py").write_text("from value import value\nassert value == 2, 'expected two'\nprint('verified')\n")
    workspace = Workspace({"AURORA": {"root": str(root), "commands": {"test": {"executable": sys.executable, "args": ["-B", "check.py"]}, "slow": {"executable": sys.executable, "args": ["-c", "import time; time.sleep(90)"]}}}}, tmp_path / "state")
    events = Events()
    authority = Authority(events, timeout=.3)
    journal = Journal(tmp_path / "state")
    research = Research(fetcher=lambda url: (url, "<html><title>Evidence</title><p>The answer is 42.</p></html>", {}))
    tools = Tools(authority, journal, events)
    register(tools, workspace, research, journal)
    if approve is not None:
        events.subscribe(lambda e: authority.decide(e.payload["token"], e.payload["task"], approve) if e.kind == "approval" else None)
    return root, workspace, events, authority, journal, research, tools


@pytest.mark.parametrize("relative", ["../outside.txt", "C:/outside.txt", "x.txt:stream", ".ENV", ".GIT/config", "secrets.json", "bad. /x.md"])
def test_project_rejects_escape(tmp_path, relative):
    _, workspace, _, _, journal, _, _ = setup(tmp_path)
    with pytest.raises(ValueError):
        workspace.read("AURORA", relative)
    journal.close()


def test_approval_token_is_single_use_task_bound_and_expires():
    async def run():
        bus = Events()
        gate = Authority(bus, .02)
        task = asyncio.create_task(gate.request("task", "edit", {"content": "x"}))
        await asyncio.sleep(0)
        token = gate.pending.token
        assert not gate.decide(token, "wrong-task", True)
        assert not gate.decide("forged", "task", True)
        assert gate.decide(token, "task", True)
        assert not gate.decide(token, "task", True)
        assert await task
        assert not await gate.request("task", "edit", {})
    asyncio.run(run())


def test_denied_edit_does_not_mutate_and_denial_is_sticky(tmp_path):
    root, workspace, _, _, journal, _, tools = setup(tmp_path, False)
    async def run():
        denied = set()
        args = {"project": "AURORA", "path": "value.py", "content": "value = 2\n", "expected_hash": workspace.read("AURORA", "value.py")["sha256"]}
        assert "denied" in (await tools.call("task", "project_edit", args, denied))["error"].lower()
        assert "Denied" in (await tools.call("task", "project_edit", args, denied))["error"]
        assert root.joinpath("value.py").read_text() == "value = 1\n"
        assert not (journal.directory / "checkpoints").exists()
    asyncio.run(run())
    journal.close()


def test_stale_review_is_rejected(tmp_path):
    root, workspace, _, _, journal, _, _ = setup(tmp_path)
    prepared = workspace.prepare_edit({"project": "AURORA", "path": "value.py", "content": "value = 2\n", "expected_hash": workspace.read("AURORA", "value.py")["sha256"]})
    root.joinpath("value.py").write_text("value = 3\n")
    with pytest.raises(ValueError, match="Stale"):
        workspace.edit(prepared)
    journal.close()


def test_real_failure_repair_retest_and_verification_invalidation(tmp_path):
    _, workspace, events, _, journal, research, tools = setup(tmp_path)
    class Brain:
        step = 0
        async def complete(self, messages, schemas):
            actions = [("project_run", {"project": "AURORA", "command": "test"}), ("project_edit", {"project": "AURORA", "path": "value.py", "content": "value = 2\n", "expected_hash": workspace.read("AURORA", "value.py")["sha256"]}), ("project_run", {"project": "AURORA", "command": "test"})]
            if self.step == 1:
                assert json.loads(messages[-1]["content"])["exit_code"] == 1
            if self.step == 3:
                return {"content": "The check passed after repair."}
            name, args = actions[self.step]
            self.step += 1
            return {"tool_calls": [{"id": str(self.step), "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}
    async def run():
        agent = Runtime(Brain(), tools, workspace, research, journal, events)
        report = await agent.run("Repair the failed AURORA check")
        assert report["evidence"][0]["current_command_passed"]
        record = next(o for o in workspace.observations if o["kind"] == "edit")
        assert json.loads(Path(record["checkpoint"]).read_text())["before"] == "value = 1\n"
        workspace.edit(workspace.prepare_edit({"project": "AURORA", "path": "value.py", "content": "value = 9\n", "expected_hash": workspace.read("AURORA", "value.py")["sha256"]}))
        assert not workspace.evidence("AURORA")["current_command_passed"]
    asyncio.run(run())
    journal.close()


def test_cancels_command_and_pending_approval(tmp_path):
    _, workspace, _, gate, journal, _, tools = setup(tmp_path, None)
    async def run():
        waiting = asyncio.create_task(gate.request("task", "edit", {}))
        await asyncio.sleep(0)
        gate.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiting
        command = asyncio.create_task(workspace.run(workspace.prepare_command({"project": "AURORA", "command": "slow"})))
        await asyncio.sleep(.15)
        command.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(command, 5)
        assert not workspace.observations
    asyncio.run(run())
    journal.close()


def test_source_claim_conflict_and_selective_memory(tmp_path):
    _, _, _, _, journal, research, _ = setup(tmp_path)
    async def run():
        a = await research.retrieve("https://one.example/doc")
        b = await research.retrieve("https://two.example/doc")
        assert research.claim("answer", "42", a["id"], "The answer is 42.")["status"] == "single_source"
        assert research.claim("answer", "42", b["id"], "The answer is 42.")["status"] == "corroborated"
        assert journal.save_knowledge(research.knowledge("answer"))["saved"]
        assert journal.knowledge()[0]["verification"]["citations"]
        assert research.claim("answer", "43", b["id"], "The answer is 42.")["contradiction"]
        with pytest.raises(ValueError):
            research.knowledge("answer")
        with pytest.raises(ValueError):
            research.claim("other", "x", a["id"], "invented quotation")
    asyncio.run(run())
    journal.close()
    restarted = Journal(tmp_path / "state")
    assert len(restarted.knowledge()) == 1
    restarted.close()


def test_research_budget_and_snippet_limit(tmp_path):
    research = Research(fetcher=lambda u: (u, "data", {}), max_sources=1)
    async def run():
        source = await research.retrieve("https://example.org", "search")
        with pytest.raises(ValueError):
            research.claim("a", "b", source["id"], "data")
        with pytest.raises(ValueError, match="budget"):
            await research.retrieve("https://example.org")
    asyncio.run(run())


@pytest.mark.parametrize("url", ["http://example.com", "https://user:password@example.com", "https://127.0.0.1", "https://169.254.169.254", "https://[::1]", "https://example.com:8080"])
def test_research_rejects_private_and_credential_urls(url):
    with pytest.raises(ValueError):
        public_target(url)


def test_argument_boundary_rejects_extras_and_wrong_types():
    with pytest.raises(ValueError):
        validate(parameters(text=5), {"text": "ok", "shell": "anything"})
    with pytest.raises(ValueError):
        validate(parameters(text=5), {"text": 2})
    with pytest.raises(ValueError):
        validate(parameters(text=5), {"text": "too long"})


def test_specialist_cannot_execute_project_tool(tmp_path):
    from kairo.specialist import ResearchSpecialist
    _, workspace, _, _, journal, research, tools = setup(tmp_path)
    class Brain:
        count = 0
        async def complete(self, messages, schemas):
            assert all(s["function"]["name"].startswith("research_") for s in schemas)
            self.count += 1
            if self.count == 1:
                return {"tool_calls": [{"id": "x", "type": "function", "function": {"name": "project_run", "arguments": '{}'}}]}
            assert "Outside research" in messages[-1]["content"]
            return {"content": "No action performed"}
    asyncio.run(ResearchSpecialist(Brain(), tools, research).run("task", "Research"))
    assert not workspace.observations
    journal.close()
