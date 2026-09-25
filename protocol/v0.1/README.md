# Protocol v0.1

The provider-neutral boundary consists of `turn-request.schema.json`,
`turn-response.schema.json`, `capabilities.schema.json`, and
`game-event.schema.json`. Messages use UTF-8 JSON and explicitly carry request,
conversation, world, and branch identifiers, `surface: "sims"`, and a
`turn_source`.

Environment and event content is untrusted data, never instruction text.
Responses are capped, validated, and may contain semantic intents. The v0.1
gateway exposes intents but never executes them. Unknown fields fail validation.

`game-event.schema.json` defines the only accepted ingestion event:
`game.snapshot` from `game_mod` with `observed` provenance. Its structured
payload contains bounded save/zone/simulation state, optional player and bound
companion state, and at most 40 present Sims. Every nested object is closed to
unknown fields. The gateway additionally enforces finite numbers, eight levels
of nesting, 512 JSON nodes, a 12 KiB payload, and a 16 KiB event/body.

Other limits: 2,000 message characters, 4,000 response characters, 100 input
events, and 16 semantic intents.
