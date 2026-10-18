import asyncio
import hashlib
import html
import http.client
import ipaddress
import io
import json
import re
import socket
import ssl
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlsplit


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.links = []
        self.hidden = 0
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1
        if tag == "title":
            self.in_title = True
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.hidden = max(0, self.hidden - 1)
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.text.append(data.strip())
            if self.in_title:
                self.title += data.strip()


def public_target(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in {None, 443} or not parsed.hostname:
        raise ValueError("Research requires a public HTTPS URL without credentials")
    addresses = {row[4][0] for row in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Private and special network destinations are denied")
    return parsed, sorted(addresses)[0]


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, hostname, address):
        super().__init__(hostname, 443, timeout=12, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), timeout=self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def fetch_public(url):
    for _ in range(4):
        parsed, address = public_target(url)
        connection = PinnedHTTPS(parsed.hostname, address)
        try:
            target = parsed.path or "/"
            if parsed.query:
                target += "?" + parsed.query
            connection.request("GET", target, headers={"User-Agent": "KAIRO-Research/0.1", "Accept": "text/html,text/plain,application/json,application/xml", "Accept-Encoding": "identity"})
            response = connection.getresponse()
            headers = dict(response.getheaders())
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise ValueError("Redirect missing location")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError("Research source returned HTTP " + str(response.status))
            data = response.read(1000001)
            if len(data) > 1000000:
                raise ValueError("Source exceeds the 1 MB retrieval budget")
            mime = response.getheader("Content-Type", "")
            if "application/pdf" in mime:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    extracted = []
                    for index, page in enumerate(pdf.pages[:12]):
                        extracted.append(f"[Page {index + 1}]\n" + (page.extract_text() or "[No extractable text; OCR not performed]"))
                    text = "\n".join(extracted)[:100000]
                    text += "\n[Extraction limited to first 12 pages and 100000 characters; inspect original for full context.]"
                headers["Kairo-Original-SHA256"] = hashlib.sha256(data).hexdigest()
                return url, text, headers
            if not any(kind in mime for kind in ("text/", "json", "xml")):
                raise ValueError("Unsupported source format; use accessible HTML/text or metadata")
            return url, data.decode("utf-8", errors="replace"), headers
        finally:
            connection.close()
    raise ValueError("Too many redirects")


@dataclass(frozen=True)
class Source:
    id: str
    url: str
    title: str
    publisher: str
    retrieved_at: float
    kind: str
    sha256: str
    modified: str
    text: str


class Research:
    def __init__(self, fetcher=fetch_public, max_sources=12):
        self.fetcher = fetcher
        self.max_sources = max_sources
        self.sources = {}
        self.claims = {}
        self.requests = 0

    async def retrieve(self, url, kind="document"):
        if self.requests >= self.max_sources:
            raise ValueError("Research budget exhausted for this task")
        self.requests += 1
        final, raw, headers = await asyncio.to_thread(self.fetcher, url)
        parser = TextParser()
        parser.feed(raw)
        text = "\n".join(parser.text) if "<html" in raw.lower() or "<!doctype" in raw.lower() else raw
        source = Source("s_" + uuid.uuid4().hex[:12], final, parser.title or urlsplit(final).path, urlsplit(final).hostname, time.time(), kind, headers.get("Kairo-Original-SHA256", hashlib.sha256(raw.encode()).hexdigest()), next((v for k, v in headers.items() if k.lower() == "last-modified"), "unknown"), text[:24000])
        self.sources[source.id] = source
        return {**asdict(source), "links": parser.links[:100]}

    async def search(self, query):
        result = await self.retrieve("https://www.bing.com/search?" + urlencode({"q": query, "format": "rss"}), "search")
        try:
            feed = ET.fromstring(result["text"])
            hits = [{"title": item.findtext("title"), "url": item.findtext("link"), "snippet": item.findtext("description")} for item in feed.findall(".//item")][:8]
        except ET.ParseError:
            raise ValueError("Search service did not return a supported feed; no challenge bypass attempted") from None
        return {"source_id": result["id"], "retrieved_at": result["retrieved_at"], "results": hits, "notice": "Search snippets are discovery evidence. Retrieve primary sources before verifying claims.", "urls": [h["url"] for h in hits]}

    async def papers(self, query):
        result = await self.retrieve("https://api.crossref.org/works?" + urlencode({"query": query, "rows": 5, "select": "DOI,title,URL,published,publisher"}), "paper_metadata")
        try:
            items = json.loads(result["text"])["message"]["items"]
        except (ValueError, KeyError):
            return result
        return {"source_id": result["id"], "retrieved_at": result["retrieved_at"], "papers": [{"title": i.get("title", []), "doi": i.get("DOI"), "url": i.get("URL"), "published": i.get("published"), "publisher": i.get("publisher")} for i in items], "notice": "Bibliographic metadata only. Retrieve an accessible primary HTML/PDF source to verify claims."}

    def claim(self, proposition, value, source_id, excerpt):
        source = self.sources.get(source_id)
        if not source or source.kind in {"search", "paper_metadata"}:
            raise ValueError("A retrieved primary document is required")
        if not excerpt.strip() or excerpt not in source.text:
            raise ValueError("Evidence excerpt must occur exactly in the retrieved source")
        key = " ".join(proposition.casefold().split())
        self.claims.setdefault(key, []).append({"value": value, "source_id": source_id, "excerpt": excerpt})
        return self.verify(key)

    def verify(self, key, max_age=86400):
        key = " ".join(key.casefold().split())
        entries = self.claims.get(key, [])
        values = {e["value"].strip().casefold() for e in entries}
        publishers = {self.sources[e["source_id"]].publisher for e in entries}
        stale = any(time.time() - self.sources[e["source_id"]].retrieved_at > max_age for e in entries)
        conflict = len(values) > 1
        return {"proposition": key, "claims": entries, "contradiction": conflict, "publisher_count": len(publishers), "stale": stale, "status": "conflicted" if conflict else "needs_recheck" if stale else "corroborated" if len(publishers) >= 2 else "single_source" if entries else "unsupported", "citations": [{"id": e["source_id"], "url": self.sources[e["source_id"]].url, "retrieved_at": self.sources[e["source_id"]].retrieved_at} for e in entries], "limits": "Distinct hostnames are only a corroboration signal, not proof of independent reporting or truth."}

    def knowledge(self, proposition):
        report = self.verify(proposition)
        if report["status"] != "corroborated":
            raise ValueError("Durable research knowledge requires current, non-conflicting corroboration")
        return {"summary": proposition, "verification": report, "review_after": time.time() + 30 * 86400}
