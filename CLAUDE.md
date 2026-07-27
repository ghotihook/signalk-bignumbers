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

## Two invariants in instrument.html

Both were bugs once; the code comments say so locally, but they're easy
to reintroduce from a distance:

1. **Never rebuild `#valueRow` or its children.** `signEl`/`valueEl`/
   `unitEl` are captured once at startup. Writing `valueRowEl.innerHTML`
   detaches them, and every later update silently writes to orphaned
   nodes — the title still updates, so it looks like a rendering bug
   rather than a DOM one. Error and "unconfigured" states render into
   the separate `#message` element and the two panes are toggled.
2. **`run()` must be called at most once per page load.** It attaches a
   resize listener and opens a websocket, neither of which is torn down.
   Config changes are handled by reloading the page, not by re-running
   it. The config fetch uses two-argument `then(ok, fail)` rather than
   `.catch()` so a throw inside the success handler can't be retried
   into a second `run()`.

## .gitignore

`.gitignore` covers `node_modules/`, Python `__pycache__/`/`*.pyc` (from
the dev server), `.DS_Store`, `*.log`, `.env` and `.claude/`. None of
these exist in the repo — it's pre-emptive, since there's no build
tooling to generate a lockfile-driven ignore list from.

## Versioning

`package.json` `version` and the `v0.0.3` label in `public/index.html`
are both hand-maintained — there's no build step to derive one from the
other, so bump both together, and tag the release commit (`git tag -a
X.Y.Z`).
