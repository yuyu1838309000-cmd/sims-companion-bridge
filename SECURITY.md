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

Local processes and browser extensions can still access loopback services; this
demo is not an authentication boundary. Do not expose its port through a proxy or
port-forward. The SQLite file contains local demo conversations and should be
handled as user data even though the seeded content is synthetic.
