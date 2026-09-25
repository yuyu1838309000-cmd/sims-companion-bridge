# Architecture

The browser and gateway are independent surfaces joined by versioned local HTTP
JSON. `BridgeApp` owns application flow; the HTTP layer owns transport controls;
`WorldStore` owns durable world facts and the complete Game Conversation;
and the backend adapter owns response generation. Before each turn, `BridgeApp`
passes the prior persisted Game Conversation to the backend separately from the
current message and world snapshot. This separation lets the mock game and mock
backend be replaced without changing the public protocol.

The game-mod is intentionally outside the runnable gateway package. Its lazy
reader produces a best-effort observation, its pure normalizer creates the
strict v0.1 `game.snapshot` envelope, and its bounded worker delivers that
envelope to `POST /api/v0.1/game/events` without doing HTTP on the simulation
thread. The current TS4Script candidate uses a thin loader and two explicit
read-only commands (`scb.snapshot`, `scb.status`); it does not poll the game.
There are no game-action or backend-output execution paths.

On first receipt, `WorldStore` inserts the immutable event and updates the
matching `(world_id, branch_id)` current structured snapshot in one SQLite
transaction. Exact event replays are no-ops; an event ID reused with different
content is a conflict. With no explicit query scope, the Game Window selects
the most recently observed branch and scopes its conversation ID to that
world/branch. `BridgeApp.chat()` then reads that same world row for
`TurnRequest.world`, so ingestion and backend context cannot silently diverge.
Older databases receive additive `current_snapshot`, `current_event_id`, and
canonical-event columns at startup.
