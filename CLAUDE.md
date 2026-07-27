# signalk-bignumbers

Static SignalK webapp (no build step, no bundler) — `public/index.html` is
the instrument picker, `public/instrument.html` is the display, both
plain HTML/CSS/JS served as-is. `dev/dummy_signalk.py` is a standalone
Python dev server for local testing, unrelated to the webapp build.

`instrument.html` supports two config modes: full query-string params
(`?path=...&name=...`), or `?display=<hostname>`, which fetches its
config from SignalK's `applicationData` API — written there by
`index.html`, which is a manager for those stored per-display configs.
The identifier is the display Pi's hostname, supplied by systemd's `%H`
specifier. See `docs/raspberry-pi-kiosk.md` for the kiosk use case this
was built for.

`dev/dummy_signalk.py` only speaks the delta/websocket protocol, so it
can drive `?path=...` URLs but not `?display=` ones — testing the stored
-config path needs a real signalk-server.

Writes to `applicationData` need a SignalK login even when reads are
anonymous, and the endpoint takes `POST` (not `PUT`) — a `PUT` returns
401 unauthenticated and 404 once authenticated.

## .gitignore

`.gitignore` covers `node_modules/`, Python `__pycache__/`/`*.pyc` (from
the dev server), `.DS_Store`, `*.log`, and `.env`. None of these exist in
the repo yet — it's there pre-emptively since there's no build tooling to
generate a lockfile-driven ignore list from.

## Versioning

`package.json` `version` and the `v0.0.2` label in `public/index.html`
are both hand-maintained — there's no build step to derive one from the
other, so bump both together, and tag the release commit (`git tag -a
X.Y.Z`).
