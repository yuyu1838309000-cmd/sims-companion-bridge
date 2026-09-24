# Memory and world-state model

The World Event Store is the only source of truth for game-world facts. Its append-
oriented events retain source and provenance so consumers can distinguish synthetic,
observed, and gateway-derived data.

- `World`: save/branch identity and current read-only snapshot.
- `GameConversation`: a conversation scoped to one world branch.
- `GameEvent`: a typed fact with provenance, wallclock, optional simulation time,
  and JSON payload.
- `Turn`: input event references and output message identity for one interaction.
- `WorldMemory`: evidence-linked derived game-world knowledge (schema present; the
  demo does not populate it).

External companion memory is separate. `CrossSurfaceProvider` defines an optional
recall interface, but the mock adapter reports it disabled and the gateway never
calls it. Enabling it later must require explicit user configuration and disclosure.
