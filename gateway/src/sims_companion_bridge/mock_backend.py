"""Deterministic companion used by the zero-configuration demo."""

import hashlib

from sims_companion_sdk import BackendAdapter, BackendCapabilities, TurnResponse


class MockCompanionBackend(BackendAdapter):
    adapter_id = "deterministic-mock"

    def capabilities(self):
        return BackendCapabilities(semantic_intents=True)

    def respond(self, request):
        message = request.message
        world = request.world
        choices = (
            "I'm here with you in {zone}. You said: {message}",
            "From our game window in {zone}, I heard: {message}",
            "Let's keep that in mind while we're in {zone}: {message}",
        )
        digest = hashlib.sha256(message.encode("utf-8")).digest()[0]
        text = choices[digest % len(choices)].format(zone=world["zone"], message=message)
        return TurnResponse(request_id=request.request_id,
                            conversation_id=request.conversation_id,
                            text=text, intents=[])
