"""Persistent declarative adapters. No downloaded code, imports, shell, or credentials.

Only fixed public HTTPS document adapters are executable here. Other integrations
are researched and remain proposals for owner-reviewed implementation.
"""
import json
import re
import time
from urllib.parse import urlsplit
from kairo.contracts import Tool, parameters


class Capabilities:
    def __init__(self, tools, research, directory):
        self.tools, self.research = tools, research
        self.path = directory / "capabilities.json"
        self.records = {}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("version") == 1:
                    for record in data.get("adapters", [])[:100]:
                        checked = self.validate(record)
                        # Persisted metadata is evidence, not authority. Re-test and
                        # explicitly activate in each process before execution.
                        self.records[checked["name"]] = {**checked, "status": "proposed",
                            "previous_test": {k: record[k] for k in ("tested_at", "sha256") if k in record}}
            except (ValueError, KeyError, TypeError):
                tools.events.emit("notice", text="Capability metadata could not be loaded; no adapters activated")

    @staticmethod
    def validate(a):
        name, url, description = a["name"], a["url"], a["description"]
        if not isinstance(name, str) or not re.fullmatch(r"adapter_[a-z][a-z0-9_]{0,30}", name):
            raise ValueError("Use adapter_ followed by a short lowercase name")
        if not isinstance(url, str) or len(url) > 2000:
            raise ValueError("Invalid public document URL")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.port not in {None, 443}:
            raise ValueError("Adapters require a fixed public HTTPS URL without credentials, query, or fragment")
        if not isinstance(description, str) or not 1 <= len(description) <= 300:
            raise ValueError("Supply a short non-sensitive capability description")
        if re.search(r"AIza[\w-]{30,}|sk-[\w-]{24,}|PRIVATE KEY", url + description):
            raise ValueError("Do not store credentials in capability metadata")
        return {"name": name, "url": url, "description": description, "kind": "public_document", "permissions": ["public_https_read"]}

    def save(self):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"version": 1, "adapters": list(self.records.values())}, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def catalog(self, query=""):
        words = set(re.findall(r"\w+", query.lower()))
        entries = [{"name": t.name, "description": t.description, "approval_required": t.approval,
                    "parameters": t.parameters, "available": True} for t in self.tools.items.values()]
        if words:
            entries.sort(key=lambda e: -len(words & set(re.findall(r"\w+", e["name"] + " " + e["description"].lower()))))
        return {"tools": entries[:60], "adapters": list(self.records.values()),
                "policy": "Metadata never grants permissions. Unknown executable integrations require owner review."}

    async def discover(self, a):
        result = await self.research.search(a["query"] + " official documentation API integration")
        return {"discovery": result, "next": "Read primary documentation with research_document. For a public document, propose a fixed-URL adapter, test it, then request activation. For software, credentials, purchases, destructive/security actions or new high-impact access, stop for explicit approval; no installer or arbitrary executable loader is available."}

    def propose(self, a):
        record = self.validate(a)
        if record["name"] in self.tools.items or len(self.records) >= 100:
            raise ValueError("Adapter already active or catalog full")
        self.records[record["name"]] = {**record, "status": "proposed"}
        self.save()
        return self.records[record["name"]]

    async def test(self, a):
        record = self.records[a["name"]]
        self.validate(record)
        # The public fetcher revalidates DNS and every redirect and pins TLS.
        record["status"] = "proposed"
        source = await self.research.retrieve(record["url"])
        if not source["text"].strip():
            raise ValueError("Adapter returned no readable text")
        record.update(status="tested", tested_at=time.time(), sha256=source["sha256"])
        self.save()
        return {"name": record["name"], "passed": True, "sha256": source["sha256"], "source_id": source["id"], "notice": "Retrieval tested; this does not establish source correctness."}

    def prepare_activation(self, a):
        record = self.records[a["name"]]
        if record["status"] != "tested" or time.time() - record["tested_at"] > 3600:
            raise ValueError("Test this adapter successfully before activation")
        return dict(record)

    def activate(self, prepared):
        if self.prepare_activation({"name": prepared["name"]}) != prepared:
            raise ValueError("Adapter changed since approval; test and review again")
        fixed = self.validate(prepared)
        async def execute(_):
            return await self.research.retrieve(fixed["url"])
        self.tools.add(Tool(fixed["name"], fixed["description"], parameters(), lambda a: a, execute))
        self.records[fixed["name"]]["status"] = "active"
        self.save()
        return {"registered": fixed["name"], "verified": "tested fixed public HTTPS reader", "live_usage": "Use capability_read with this name; available immediately in the current live session."}

    async def read(self, a):
        record = self.records[a["name"]]
        if record["status"] != "active" or a["name"] not in self.tools.items:
            raise ValueError("Adapter has not been tested and activated in this session")
        # Fixed read-only adapter only: never dispatch arbitrary tools through here.
        return await self.research.retrieve(record["url"])

    def register(self):
        for name, description, schema, execute, approval, prepare in [
            ("capability_catalog", "Find currently available tools and adapter metadata by task", parameters(query=500), lambda a: self.catalog(a["query"]), False, lambda a: a),
            ("capability_discover", "Research official web/docs integrations when a capability is absent", parameters(query=500), self.discover, False, lambda a: a),
            ("capability_propose", "Build a declarative fixed public HTTPS document adapter; no executable code or credentials", parameters(name=40, url=2000, description=300), self.propose, False, lambda a: a),
            ("capability_test", "Test proposed adapter through bounded public-web retrieval", parameters(name=40), self.test, False, lambda a: a),
            ("capability_activate", "Review and register the exact successfully tested adapter", parameters(name=40), self.activate, True, self.prepare_activation),
            ("capability_read", "Use an activated fixed public-document adapter, including during Live sessions", parameters(name=40), self.read, False, lambda a: a),
        ]:
            self.tools.add(Tool(name, description, schema, prepare, execute, approval))
