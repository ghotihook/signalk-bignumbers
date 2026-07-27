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
-config path needs a real signalk-server. Repeat `--path` (and `--field`,
matched by position) to drive a multi-value display.

## One, two or three values

A display shows up to `MAX_ITEMS` (3) values, stacked in equal bands. One
value is not a special case anywhere: its band is the whole viewport, so
the single-value display falls out of the general code unchanged.

Both config sources normalise to the same list before anything else runs:
stored configs are `{bg, fg, items: [...]}`, and per-value URL params take
a `2`/`3` suffix with the unsuffixed keys meaning the first value. So
every pre-existing single-value URL still parses identically. Suffixes
were chosen over repeated params (`?path=a&path=b`) because repeated
params misalign the moment one value omits an optional key like `unit`.

A stored config with no `items` array is a config saved before this
existed; `itemsOf()`/the `Array.isArray` check in `fetchDisplayConfig`
read it as a one-value config. Don't drop those paths — they're the
upgrade story for anything already deployed.

`bg`, `fg`, `host` and `display` belong to the display as a whole and are
never suffixed or per-item.

All bands render at the same digit size: `fitDisplay()` takes the `min`
scale across every cell so the screen reads as one instrument. Each cell
is measured against its own box, not the viewport.

Writes to `applicationData` need a SignalK login even when reads are
anonymous, and the endpoint takes `POST` (not `PUT`) — a `PUT` returns
401 unauthenticated and 404 once authenticated.

## Two invariants in instrument.html

Both were bugs once; the code comments say so locally, but they're easy
to reintroduce from a distance:

1. **Cells are built once, by `buildCells()`, and never rebuilt.** Each
   cell object holds the `signEl`/`valueEl` references captured when its
   elements were created; only the text inside those two ever changes
   afterwards. Recreating a cell (or writing a row's `innerHTML`)
   detaches them, and every later update silently writes to orphaned
   nodes — a stale-looking number rather than an obvious DOM error.
   Error and "unconfigured" states render into the separate `#message`
   element and the two panes are toggled.
2. **`start()` and `run()` must each be called at most once per page
   load.** `start()` builds the cells; `run()` attaches a resize listener
   and opens a websocket, neither of which is torn down. Config changes
   are handled by reloading the page, not by re-running either. The
   config fetch uses two-argument `then(ok, fail)` rather than `.catch()`
   so a throw inside the success handler can't be retried into a second
   `run()`.

## .gitignore

`.gitignore` covers `node_modules/`, Python `__pycache__/`/`*.pyc` (from
the dev server), `.DS_Store`, `*.log`, `.env` and `.claude/`. None of
these exist in the repo — it's pre-emptive, since there's no build
tooling to generate a lockfile-driven ignore list from.

## Versioning

`package.json` `version` and the `v0.1.0` label in `public/index.html`
are both hand-maintained — there's no build step to derive one from the
other, so bump both together, and tag the release commit (`git tag -a
X.Y.Z`).
