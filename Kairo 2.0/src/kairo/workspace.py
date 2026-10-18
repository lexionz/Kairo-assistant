import asyncio
import difflib
import hashlib
import json
import os
import stat
import uuid
from pathlib import Path, PureWindowsPath


def digest(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class Workspace:
    suffixes = {".md", ".txt", ".json", ".py", ".js", ".cjs", ".mjs", ".ts", ".tsx", ".jsx", ".html", ".css", ".cpp", ".h", ".cs", ".gd", ".godot", ".tscn", ".toml", ".yaml", ".yml", ".ini", ".uproject"}
    forbidden = {".git", ".ssh", ".aws", ".azure", ".codex", ".agents", "node_modules", ".venv", "venv", "appdata", "credentials.json", "secrets.json", "api_keys.json"}

    def __init__(self, projects, storage):
        self.projects = projects
        self.storage = Path(storage)
        self.revisions = {name: 0 for name in projects}
        self.observations = []

    def root(self, name):
        if name not in self.projects:
            raise ValueError("Project is not approved")
        root = Path(self.projects[name]["root"]).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Invalid project root")
        return root

    def path(self, name, relative, directory=False):
        if not relative or ":" in relative or "\x00" in relative or PureWindowsPath(relative).is_absolute() or Path(relative).is_absolute():
            raise ValueError("Expected a relative project path")
        parts = relative.replace("\\", "/").split("/")
        if any(p == ".." or p.lower() in self.forbidden or p.lower().startswith(".env") or (p != "." and p.endswith((".", " "))) for p in parts):
            raise ValueError("Protected or escaping path")
        root = self.root(name)
        current = root
        for part in parts:
            current = current / part
            if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
                raise ValueError("Links and junctions are not allowed")
        target = current.resolve()
        if not target.is_relative_to(root):
            raise ValueError("Path escaped project")
        if not directory and target.suffix.lower() not in self.suffixes:
            raise ValueError("File type is not allowlisted")
        return target

    def inspect(self, name, relative):
        target = self.path(name, relative, True)
        return {"entries": [{"name": p.name, "directory": p.is_dir()} for p in sorted(target.iterdir()) if not p.name.startswith(".") and p.name.lower() not in self.forbidden and not p.is_symlink()][:200]}

    def read(self, name, relative):
        target = self.path(name, relative)
        if not target.is_file() or target.stat().st_size > 128000:
            raise ValueError("Read requires a text file no larger than 128 KB")
        text = target.read_bytes().decode("utf-8")
        if "\x00" in text:
            raise ValueError("Binary content is not allowed")
        return {"path": relative, "text": text, "sha256": digest(text)}

    def prepare_edit(self, args):
        name, relative = args["project"], args["path"]
        target = self.path(name, relative)
        before = self.read(name, relative)["text"] if target.exists() else None
        expected = digest(before) if before is not None else "NEW"
        if expected != args["expected_hash"]:
            raise ValueError("Stale file hash; read it again")
        if target.exists() and target.stat().st_nlink > 1:
            raise ValueError("Hard links cannot be edited")
        if not target.parent.is_dir():
            raise ValueError("Parent directory must already exist")
        after = args["content"]
        if len(after.encode("utf-8")) > 128000:
            raise ValueError("Edit exceeds 128 KB")
        diff = "".join(difflib.unified_diff((before or "").splitlines(True), after.splitlines(True), fromfile=relative + " before", tofile=relative + " after"))
        return {**args, "before": before, "diff": diff, "notice": "Exact replacement; checkpoint saved. Does not verify a build."}

    def edit(self, prepared):
        self.prepare_edit(prepared)
        target = self.path(prepared["project"], prepared["path"])
        identity = uuid.uuid4().hex
        checkpoint = self.storage / "checkpoints" / (identity + ".json")
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps(prepared, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary = target.with_name(target.name + ".kairo-" + identity)
        try:
            with temporary.open("x", encoding="utf-8", newline="") as stream:
                stream.write(prepared["content"])
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        actual = self.read(prepared["project"], prepared["path"])
        if actual["sha256"] != digest(prepared["content"]):
            raise RuntimeError("Write verification failed")
        self.revisions[prepared["project"]] += 1
        result = {"kind": "edit", "project": prepared["project"], "path": prepared["path"], "revision": self.revisions[prepared["project"]], "verified": "bytes match", "checkpoint": str(checkpoint)}
        self.observations.append(result)
        return result

    def prepare_command(self, args):
        name = args["project"]
        root = self.root(name)
        command = self.projects[name].get("commands", {}).get(args["command"])
        if not command or not Path(command["executable"]).is_absolute() or not isinstance(command.get("args"), list):
            raise ValueError("Command is not owner-allowlisted")
        if Path(command["executable"]).suffix.lower() in {".bat", ".cmd", ".ps1"} or any(not isinstance(x, str) for x in command["args"]):
            raise ValueError("Use a fixed executable and argument list")
        return {**args, "executable": command["executable"], "args": list(command["args"]), "cwd": str(root), "notice": "Runs project code with your Windows account permissions; not an OS sandbox."}

    def prepare_undo(self, args):
        identity = args["checkpoint"]
        if len(identity) != 32 or any(c not in "0123456789abcdef" for c in identity):
            raise ValueError("Expected a checkpoint identifier")
        saved = json.loads((self.storage / "checkpoints" / (identity + ".json")).read_text(encoding="utf-8"))
        current = self.read(saved["project"], saved["path"])
        if current["sha256"] != digest(saved["content"]):
            raise ValueError("File changed after the action; undo would overwrite newer work")
        return {"checkpoint": identity, "project": saved["project"], "path": saved["path"],
                "expected_hash": current["sha256"], "content": saved["before"],
                "notice": "Restore checkpoint contents" if saved["before"] is not None else "Remove the file created by this action"}

    def undo(self, prepared):
        if self.prepare_undo(prepared) != prepared:
            raise ValueError("Undo changed since approval")
        if prepared["content"] is not None:
            result = self.edit(self.prepare_edit(prepared))
        else:
            target = self.path(prepared["project"], prepared["path"])
            if target.stat().st_nlink > 1:
                raise ValueError("Hard links cannot be removed")
            target.unlink()
            self.revisions[prepared["project"]] += 1
            result = {"kind": "edit", "project": prepared["project"], "path": prepared["path"], "revision": self.revisions[prepared["project"]], "verified": "created file removed"}
            self.observations.append(result)
        return result

    async def run(self, prepared):
        if prepared != self.prepare_command(prepared):
            raise ValueError("Command changed since approval")
        env = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "PATH", "TEMP", "TMP", "USERPROFILE", "WINDIR"}}
        process = await asyncio.create_subprocess_exec(prepared["executable"], *prepared["args"], cwd=prepared["cwd"], env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, **({"creationflags": 0x08000000} if os.name == "nt" else {}))
        chunks = bytearray()

        async def collect():
            while data := await process.stdout.read(4096):
                chunks.extend(data)
                if len(chunks) > 32000:
                    del chunks[:-32000]
            return await process.wait()

        async def terminate():
            if process.returncode is not None:
                return
            if os.name == "nt":
                killer = await asyncio.create_subprocess_exec(str(Path(os.environ["SystemRoot"]) / "System32/taskkill.exe"), "/PID", str(process.pid), "/T", "/F", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL, creationflags=0x08000000)
                await killer.wait()
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            await process.wait()

        try:
            code = await asyncio.wait_for(collect(), 120)
        except (asyncio.CancelledError, TimeoutError):
            await terminate()
            raise
        result = {"kind": "command", "project": prepared["project"], "command": prepared["command"], "exit_code": code, "output": chunks.decode("utf-8", errors="replace"), "revision": self.revisions[prepared["project"]], "passed": code == 0}
        self.observations.append(result)
        return result

    def evidence(self, name):
        self.root(name)
        records = [r for r in self.observations if r["project"] == name]
        latest = {r["command"]: r for r in records if r["kind"] == "command" and r["revision"] == self.revisions[name]}
        return {"project": name, "revision": self.revisions[name], "observations": records[-20:], "current_command_passed": bool(latest) and all(r["passed"] for r in latest.values())}
