# The Sims 4 bridge source skeleton

This directory is a deliberately small, Python 3.7-compatible source skeleton for
a future game-side package. It has **not been tested inside The Sims 4** and is not
a distributable mod. It models a read-only snapshot/event boundary; there are no
game actions, autonomy controls, backend credentials, or network calls.

An eventual game-tested integration would connect approved TS4 callbacks to
`ReadOnlyBridge.publish_snapshot`, then transport queued JSON envelopes to the
loopback gateway. Keeping the snapshot extraction and transport boundaries separate
makes that work auditable.
