import asyncio
import json
import os
from urllib.parse import urlsplit
import httpx


class CompatibleBrain:
    def __init__(self, config):
        self.config = config

    async def complete(self, messages, tools):
        endpoint = self.config.get("endpoint", "")
        model = self.config.get("model", "")
        if not endpoint or not model:
            raise ValueError("Configure KAIRO model and endpoint in Settings. No model is bundled.")
        parsed = urlsplit(endpoint)
        local = parsed.hostname in {"127.0.0.1", "::1"}
        if parsed.username or parsed.password or not (parsed.scheme == "https" or local and parsed.scheme == "http"):
            raise ValueError("Use HTTPS or an explicit loopback model endpoint")
        key = os.environ.get("KAIRO_API_KEY", "")
        if not local and not key:
            raise ValueError("Set KAIRO_API_KEY in the launch environment for your provider")
        headers = {"Content-Type": "application/json"}
        if key and not local:
            headers["Authorization"] = "Bearer " + key
        async with httpx.AsyncClient(timeout=60, follow_redirects=False, trust_env=False) as client:
            for attempt in range(3):
                async with client.stream("POST", endpoint, headers=headers, json={"model": model, "messages": messages, "tools": tools, "stream": False}) as response:
                    if response.status_code in {429, 502, 503, 504} and attempt < 2:
                        await asyncio.sleep(.3 * 2 ** attempt)
                        continue
                    if response.status_code != 200:
                        raise RuntimeError("Model endpoint returned HTTP " + str(response.status_code))
                    payload = bytearray()
                    async for chunk in response.aiter_bytes():
                        payload.extend(chunk)
                        if len(payload) > 1000000:
                            raise ValueError("Model response exceeded the budget")
                    try:
                        message = json.loads(payload)["choices"][0]["message"]
                    except (ValueError, KeyError, IndexError):
                        raise ValueError("Model returned an invalid response") from None
                    if not isinstance(message, dict):
                        raise ValueError("Invalid model message")
                    return message
