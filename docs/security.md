# Security model

The v0.1 demo is local and least-capability by design.

- The server rejects any bind address except `127.0.0.1`.
- Host and Origin checks accept loopback names only.
- JSON bodies are capped at 16 KiB; protocol strings, arrays, depth, node count,
  and structured game-event payloads have tighter caps.
- Requests and backend responses are validated independently.
- Game events accept one fixed type/source/provenance, reject unknown fields and
  non-finite numbers, and are idempotent by canonical event content.
- UI output uses DOM `textContent`, not HTML injection.
- Content Security Policy disallows remote scripts, objects, framing, and remote
  connections.
- There are no shell, filesystem-browsing, arbitrary URL, or game-action endpoints.
- Diagnostic responses contain product status/counts, not environment variables,
  stack traces, secrets, or absolute paths.
- The SQLite file contains synthetic demo data unless the read-only source
  integration is deliberately connected.

The ingestion route inherits the same loopback Host and Origin checks as chat.
A remote webpage Origin cannot post it. Loopback is not authentication against
other local processes, so do not proxy or port-forward the gateway. Environment
text is persisted and passed to adapters only as untrusted data.

Future remote adapters change the privacy boundary. Their configuration must state
the destination and obtain informed user consent. See the README disclosure.
