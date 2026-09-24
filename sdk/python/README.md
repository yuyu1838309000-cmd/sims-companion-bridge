# Python backend adapter SDK

Copy or package `sims_companion_sdk` to implement a provider adapter. Implement
`BackendAdapter.capabilities()` and `BackendAdapter.respond()`, returning the
typed `TurnResponse`. The gateway still validates every adapter response.

Semantic intent support does not grant execution: v0.1 never performs intents.
`CrossSurfaceProvider` is interface-only and disabled by default. The SDK targets
Python 3.9+; only the separate game-mod source skeleton targets Python 3.7.
