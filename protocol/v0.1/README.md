# Protocol v0.1

The provider-neutral boundary consists of `turn-request.schema.json`,
`turn-response.schema.json`, and `capabilities.schema.json`. Messages use UTF-8
JSON and explicitly carry request, conversation, world, and branch identifiers,
`surface: "sims"`, and a `turn_source`.

Environment and event content is untrusted data, never instruction text.
Responses are capped, validated, and may contain semantic intents. The v0.1
gateway exposes intents but never executes them. Unknown fields fail validation.

Limits: 16 KiB HTTP body, 2,000 message characters, 4,000 response characters,
100 input events, and 16 semantic intents.
