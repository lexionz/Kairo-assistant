import asyncio
import json
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Event:
    kind: str
    payload: dict


class Events:
    def __init__(self):
        self.listeners = []

    def subscribe(self, callback):
        self.listeners.append(callback)

    def emit(self, kind, **payload):
        event = Event(kind, payload)
        for callback in tuple(self.listeners):
            try:
                callback(event)
            except Exception:
                continue


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    prepare: Callable
    execute: Callable
    approval: bool = False

    def schema(self):
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


def parameters(**fields):
    return {"type": "object", "properties": {k: {"type": "string", "maxLength": v} for k, v in fields.items()}, "required": list(fields), "additionalProperties": False}


def validate(schema, args):
    if not isinstance(args, dict) or len(json.dumps(args)) > 260000:
        raise ValueError("Invalid argument object")
    properties = schema.get("properties", {})
    if set(args) - set(properties) or set(schema.get("required", [])) - set(args):
        raise ValueError("Unexpected or missing arguments")
    for key, value in args.items():
        rule = properties[key]
        kind = rule.get("type")
        valid = (kind == "string" and isinstance(value, str) and len(value) <= min(rule.get("maxLength", 128000), 128000)) or (kind == "boolean" and isinstance(value, bool)) or (kind == "integer" and type(value) is int)
        if not valid or ("enum" in rule and value not in rule["enum"]):
            raise ValueError("Invalid value: " + key)


async def invoke(function, *args):
    result = function(*args)
    return await result if asyncio.iscoroutine(result) else result
