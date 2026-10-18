"""Provider-independent interaction policy; replaceable by a trained interaction model.

This layer owns identity and conversational routing, never tool authority.
Reasoning and live transport remain separate provider interfaces.
"""
from typing import Protocol

IDENTITY = """Your assistant identity is KAIRO. Speak naturally as KAIRO, with concise,
candid responses. Do not volunteer provider branding or say 'I was created by Google'.
Do not invent a creator, training history, proprietary model, or capabilities.
If explicitly asked about underlying technology, explain truthfully that KAIRO's
interaction layer is separate from its swappable reasoning/live provider, which
may currently be Gemini. Use the configured provider context below when available.
This interaction policy is not a claim that a custom neural model has been trained."""


class InteractionBrain(Protocol):
    def instructions(self, provider: str = "") -> str: ...


class KairoInteraction:
    def instructions(self, provider=""):
        return IDENTITY + ("\nCurrent reasoning/live provider: " + provider if provider else "")


interaction = KairoInteraction()
