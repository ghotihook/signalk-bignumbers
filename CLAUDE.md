# signalk-bignumbers

Static SignalK webapp (no build step, no bundler) — `public/index.html` is
the instrument picker, `public/instrument.html` is the display, both
plain HTML/CSS/JS served as-is. `dev/dummy_signalk.py` is a standalone
Python dev server for local testing, unrelated to the webapp build.

`instrument.html` supports two config modes: full query-string params
(`?path=...&name=...`), or `?display=<id>`, which fetches its config from
SignalK's `applicationData` API — saved there by the picker's "Save to
SignalK" button. See `docs/raspberry-pi-kiosk.md` for the kiosk-display
use case this was built for.

## .gitignore

`.gitignore` covers `node_modules/`, Python `__pycache__/`/`*.pyc` (from
the dev server), `.DS_Store`, `*.log`, and `.env`. None of these exist in
the repo yet — it's there pre-emptively since there's no build tooling to
generate a lockfile-driven ignore list from.

## Versioning

`package.json` `version` and the `v0.0.1` label in `public/index.html`
are both hand-maintained — there's no build step to derive one from the
other, so bump both together, and tag the release commit (`git tag -a
X.Y.Z`).
