"""Provider-neutral v0.1 types implemented by companion backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping


@dataclass(frozen=True)
class BackendCapabilities:
    protocol_versions: List[str] = field(default_factory=lambda: ["0.1"])
    chat: bool = True
    semantic_intents: bool = False
    cross_surface_recall: bool = False
    game_actions: bool = False


@dataclass(frozen=True)
class TurnRequest:
    request_id: str
    conversation_id: str
    world_id: str
    branch_id: str
    message: str
    input_event_ids: List[str] = field(default_factory=list)
    protocol_version: str = "0.1"
    surface: str = "sims"
    turn_source: str = "user"
    world: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class TurnResponse:
    request_id: str
    conversation_id: str
    text: str
    intents: List[Dict[str, Any]] = field(default_factory=list)
    protocol_version: str = "0.1"


class BackendAdapter(ABC):
    """Implement this boundary; never assume an adapter is trusted by the gateway."""

    adapter_id = "custom-adapter"

    @abstractmethod
    def capabilities(self) -> BackendCapabilities:
        raise NotImplementedError

    @abstractmethod
    def respond(self, request: TurnRequest) -> TurnResponse:
        raise NotImplementedError


class CrossSurfaceProvider(ABC):
    """Optional external-memory interface. Implementations must be explicit opt-in."""

    enabled = False

    @abstractmethod
    def recall(self, query: str, context: Mapping[str, Any]) -> List[Dict[str, Any]]:
        raise NotImplementedError
