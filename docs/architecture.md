# Architecture

The browser and gateway are independent surfaces joined by versioned local HTTP
JSON. `BridgeApp` owns application flow; the HTTP layer owns transport controls;
`WorldStore` owns durable world facts; and the backend adapter owns response
generation. This separation lets the mock game and mock backend be replaced
without changing the public protocol.

The game-mod skeleton is intentionally outside the runnable gateway package. A
future mod may observe facts and deliver them to a dedicated ingestion boundary,
but v0.1 has no ingestion endpoint and cannot affect the game.
