# Security model

The v0.1 demo is local and least-capability by design.

- The server rejects any bind address except `127.0.0.1`.
- Host and Origin checks accept loopback names only.
- JSON bodies are capped at 64 KiB; protocol strings and arrays have tighter caps.
- Requests and backend responses are validated independently.
- UI output uses DOM `textContent`, not HTML injection.
- Content Security Policy disallows remote scripts, objects, framing, and remote
  connections.
- There are no shell, filesystem-browsing, arbitrary URL, or game-action endpoints.
- Diagnostic responses contain product status/counts, not environment variables,
  stack traces, secrets, or absolute paths.
- The SQLite file contains synthetic demo data unless a future game integration is
  deliberately connected.

Future remote adapters change the privacy boundary. Their configuration must state
the destination and obtain informed user consent. See the README disclosure.
