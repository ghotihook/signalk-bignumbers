# signalk-bignumbers

## What this is — and what it isn't

Mast and repeater displays for **racing**. Someone on the rail looks up
and reads a number off a screen several metres away, in spray, at an
angle, in anything from full sun to full dark. That is the whole job.

**This is not an MFD.** No charts, no gauges or dials, no graphs, trends
or sparklines, no history, no AIS, no routing, no alarms, no touch
targets, no pages to swipe between. A change that puts a pixel on screen
which isn't a number, its label or its unit has to justify itself against
reading distance first.

Three things are optimised, in this order.

### Latency — late data is worse than no data

What's on the mast must be what the instrument is reading *now*; someone
is trimming to it in real time. A number two seconds old that looks
current is worse than dashes, because nothing on the screen tells the
crew not to trust it. **Given the choice between showing an update late
and not showing it at all, drop it.**

Buffering between the delta arriving and the glass lighting up is kept at
the bare minimum. All of the following are load-bearing:

- Subscriptions use `policy: "instant"` with **no `period` and no
  `minPeriod`**. Adding either is the obvious-looking way to "reduce load
  on the Pi", and it buys latency directly. Don't.
- Every delta renders synchronously inside `onmessage`. Never put a
  queue, `requestAnimationFrame`, `setTimeout`, idle callback or batch
  between arrival and paint.
- `.sign`/`.value` carry `transition: none`. Never animate, tween or ease
  a value change: an animating number both shows readings the boat never
  took and shows them late.
- No smoothing, averaging or damping in the client, ever — all three are
  latency wearing a different hat. If a path genuinely needs damping it
  belongs upstream in SignalK, where every display reading it gets the
  same treatment.
- The socket opens `?subscribe=none` and subscribes only to the paths on
  screen. That's as much a latency decision as a bandwidth one: no
  firehose of irrelevant JSON to parse through before reaching the value
  that matters.
- No history, replay or backfill on reconnect. A recovered connection
  shows the next live value, never what was missed.
- If the Pi can't keep up, cut values from the screen or slow the source.
  Never buffer to cope.

The stale timeout is the same principle from the other side: after
`staleMs` (3s) with no update a band drops to grey dashes instead of
holding its last reading, so a dead sensor or a dropped feed looks
obviously dead rather than looking like a becalmed boat.

One thing the code deliberately does *not* do: it never reads a delta's
`timestamp`, and treats arrival order as truth. That is sound over a
single websocket — TCP preserves order, so the newest delta is always the
last one rendered. It would stop being sound the moment anything replayed
buffered history into the stream, which is the case to watch for.

### Clarity

Read at distance, at speed, by someone with half a second to spare.

- `fitDisplay()` makes the glyphs as large as the band allows.
- **Digits must never move horizontally as the value changes** —
  `tabular-nums`, leading zeros ghosted so they keep their width, and a
  reserved sign column when `neg` is set. A number that jitters can't be
  read from a moving boat.
- All bands share one digit size, so a screen reads as one instrument.
- Fixed high-contrast themes, not free colour pickers: nothing should be
  selectable that washes out in sun or wrecks night vision.
- `MAX_ITEMS` is 3 because past that the digits are too small to read
  from the rail. Raising it trades away the only thing this does well.
- `cursor: none`, `overflow: hidden` — there is nothing to interact with.

### Speed

A cheap Pi that has to boot into a live number and stay light.

- No build step, no bundler, no framework, no runtime dependencies —
  static files the SignalK server hands over as-is. Keep it that way.
- Target hardware is a Pi Zero 2 W (512MB) running cog/WPE WebKit straight
  to DRM. WebKit-only; no Chromium-specific APIs.
- `font-display: block`, so nothing is measured or painted against a
  fallback face.
- One websocket per display however many values it shows, with paths
  deduped before subscribing.

## Layout of the repo

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

`host` and `display` belong to the display as a whole and are never
suffixed or per-item.

`bg`/`fg` are deliberately both: they're in `ITEM_KEYS` (so `bg2`/`fg3`
colour one band) *and* read at display level. Unsuffixed they mean both
the first band's colours and the page's, which are the same thing — the
editor mirrors value 1's theme to the top level for exactly this. The
page-level pair is what backs the "not configured" and error screens,
which exist before any cell does, so don't drop it in favour of per-item
only. `.cell` re-declares `background`/`color` from the variables rather
than inheriting body's computed values, which is what lets a per-band
override cascade to the opacity-derived title/unit and the
`currentColor` divider.

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

`package.json` `version` and the `v0.0.4` label in `public/index.html`
are both hand-maintained — there's no build step to derive one from the
other, so bump both together, and tag the release commit (`git tag -a
X.Y.Z`).
