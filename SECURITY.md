# Security policy

## Supported version

Only the latest v0.1 development revision is supported during the public demo.

## Reporting

Please report suspected vulnerabilities privately through the repository host's
security-reporting feature. Do not include real chat logs, memory exports,
credentials, personal data, or machine-specific paths in a report. If no private
channel is configured, open a minimal issue that asks maintainers for one.

## Demo boundary

The gateway binds to loopback, checks Host and Origin, limits request sizes,
serves files only from the web root, and returns sanitized errors. Backend output
is untrusted and validated. Browser rendering uses text nodes, not HTML injection.
The Content Security Policy disallows external scripts and framing.

The game-ingestion route accepts only the closed, bounded `game.snapshot`
contract. It rejects unknown fields, malformed identifiers, non-finite numbers,
and conflicting reuse of an immutable event ID. Ingestion persists observations;
it does not invoke the backend or expose an action path.

Local processes and browser extensions can still access loopback services; this
demo is not an authentication boundary. Do not expose its port through a proxy or
port-forward. The SQLite file contains local demo conversations and should be
handled as user data even though the seeded content is synthetic.

## Future remote-backend boundary

Remote backends are intentionally not configurable in v0.1. A future remote
adapter may transmit the current message, the complete prior Game Conversation,
world/branch identifiers, selected event references, and explicitly selected
read-only world/environment data. That mode must be explicit opt-in and show the
destination and outbound data scope before use; backend credentials must never
be exposed to the browser bundle or written to ordinary logs.
