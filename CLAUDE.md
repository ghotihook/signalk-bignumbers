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
the display manager, `public/instrument.html` is the display, both
plain HTML/CSS/JS served as-is. `dev/dummy_signalk.py` is a standalone
Python dev server for local testing, unrelated to the webapp build.

`instrument.html` supports two config modes: full query-string params
(`?path=...&name=...`), or `?display=<hostname>`, which fetches its
config from SignalK's `applicationData` API — written there by
`index.html`, which is a manager for those stored per-display configs.
The identifier is the display Pi's hostname, supplied by systemd's `%H`
specifier. See `docs/raspberry-pi-kiosk.md` for the kiosk use case this
was built for.

`public/formats.js` is the one table of presentations, loaded by both
pages with a plain `<script src>` — the editor builds its Presentation
dropdown from it, the display resolves a stored `format` slug through it.
Two copies of that table would drift, and there's no build step to make
one from the other.

`dev/dummy_signalk.py` only speaks the delta/websocket protocol, so it
can drive `?path=...` URLs but not `?display=` ones — testing the stored
-config path needs a real signalk-server, and so does the editor's path
dropdown, which reads `/signalk/v1/api/vessels/self`. Repeat `--path`
(and `--field`, matched by position) to drive a multi-value display.

## Path and presentation

A value is `path` + `format` + `name` + colours. Nothing else is
configurable from the webapp, and that's the point: the two dropdowns are
orthogonal, so any path can be shown any way without anyone having
thought of the combination in advance.

**The path dropdown is live.** `loadPaths()` fetches
`/signalk/v1/api/vessels/self` and `flattenPaths()` walks it: a leaf is
any node carrying a `value`, and an object value (`navigation.attitude`,
`navigation.position`) becomes one entry per numeric key — the same
`path`/`field` pair a cell subscribes with. There is no hardcoded path
list and no free-text box, so the dropdown is exactly what this boat
produces. The one concession: a *saved* path that isn't in the live list
is added back at the top marked "not currently reporting", because
editing a display's colours at the dock with the instruments off must not
silently drop its path.

An earlier attempt at path discovery was rejected because SignalK's
`meta` can't supply `layout` or `neg` — it has no number-format field and
no sign field, so discovery alone still left the two fiddliest fields
hand-set. The presentation dropdown is what supplies those. Don't
reintroduce meta-driven unit lookup on the strength of this: `meta.units`
is always the SI unit, which is what `factor` already assumes.

**`format` expands, raw keys override.** `makeItem()` resolves
`FORMAT_BY_ID[raw.format]` first and then lets any explicitly given
`factor`/`offset`/`unit`/`layout`/`neg`/`wrap` win. That ordering — not a
migration — is what keeps every config and URL written before formats
existed meaning exactly what it meant then, and it's what leaves a way to
show something no presentation covers. An unknown slug resolves to
nothing and changes no key. `mode` (`"duration"`, `"clock"`) is the
exception: it comes from the table only, never from a raw key, so a
hand-written config can't reach a time rendering by accident.

`matchFormat()` in the editor recognises a pre-format config by its
conversion keys and upgrades it to a slug on the next save. `mode` is in
its signature so the time entries can never match — a stored item has no
mode, and the two HH:MM:SS entries are otherwise identical.

The digit mask is the single source of width. `layout.replace(/[^.:]/g, …)`
gives the placeholder (`--:--:--`) and `fitDisplay()`'s measuring sample
(`88:88:88`) from the same string, which is why a colon is measured as a
colon rather than as a digit. Time renderings clamp their leading field
to two digits rather than growing a third — a number that changes width
can't be read from a moving boat.

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

Reads being anonymous is a server setting, not a given: with SignalK
security on and **Allow Readonly Access** off, a display gets 401 for both
its config and the stream, and it holds no credentials to fix that with.
Two things depend on catching it. `instrument.html` tells 401/403 apart
from an empty config document — the two are indistinguishable by the time
you reach `data[displayId]`, and falling through to the "not configured"
screen sends whoever reads it off to add a display that's already there.
`checkAnonymousRead()` in `index.html` probes the same two endpoints with
`credentials: "omit"`; the omit is the whole point, since SignalK's login
cookie would otherwise authenticate the probe and pass it on a server
where every display fails.

## Mandatory fields in the editor

Every field is mandatory except Colours, which always has a value. So
validation is about saying *which* field is missing, not about which ones
are optional — and there are no asterisks on the labels, because marking
all but one is noise.

`checkEditor(problems)` takes `[element, message]` pairs, which is what
lets Save and Preview compose different checks:

- **Preview checks the value slots only.** Its URL carries every value as
  a parameter and never reads the hostname, so requiring one would be a
  check for its own sake. It does insist on the values: `itemsFromParams()`
  stops at the first missing path, so a gap drops that value and every one
  after it, and a value with no presentation falls back to a one-digit
  layout on the raw SI number. Either way the preview is a screen nobody
  configured.
- **The hostname check is skipped while the field is disabled**, which is
  whenever an existing display is being edited. The hostname is fixed at
  creation, so checking it would strand any display created before the
  check existed, or written straight into `applicationData` — permanently
  uneditable over a field nobody can change.

Correcting any outlined field drops the message. Following one particular
field instead — so the message survives until *that* one is fixed — costs
a variable touched from three places and buys a message that can outlive
what it describes. The outlines are what track the rest.

`HOSTNAME_RE` allows dots so an FQDN passes. The point isn't strictness:
the name has to match systemd's `%H` character for character, and a space
or a slash makes a display that silently never finds its config.

Validation reads the DOM directly rather than going through
`currentConfig()`, so it can name a field; nothing about the stored shape
changes. There's no `<form>`, no `required` and no constraint-validation
API — the page has no form element, and native validation bubbles don't
match the theme.

`start()` in `instrument.html` refuses the same thing from the other end,
and its message is named for which config source it came from: a display
on `?display=` has no `?path=` to point anyone at. With the editor
refusing to save one, reaching that screen from the store now takes a
hand-written entry.

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

## Security invariants

Both of these were live vulnerabilities, found in review and fixed in
0.0.5. Both are easy to undo, because both look like conveniences.

1. **`index.html` talks only to the origin that served it.** No `?host=`
   override, ever. That page posts a username and password, so a
   parameter that moves the origin turns any link to it into a credential
   harvester: the address bar still shows the real SignalK server while
   the login POST goes wherever the link says. `instrument.html` keeps
   its `?host=` because it holds no credentials — its worst case is
   showing someone else's numbers.
2. **Colours are validated to literal hex before reaching CSS.** `bg`/`fg`
   land in custom properties feeding `background: var(--bg)`, and the
   `background` shorthand accepts an image — so an unvalidated
   `url(https://elsewhere/x.png)` is a *valid* background, and makes every
   display fetch it, announcing the boat to whoever wrote the config.
   `colour()` is the only way a colour should reach `style.setProperty`.

The rule behind both: **a stored config is attacker-controlled input.**
It lives in `applicationData/global/`, which any authenticated SignalK
user can write. `name` and `unit` are safe only because they go through
`textContent` — keep it that way, and never build a cell with
`innerHTML`.

`format` is safe for the same kind of reason: it is only ever a key into
`FORMAT_BY_ID`, so a hostile value selects nothing rather than
contributing anything to the page. It must never become a string that
reaches the DOM or CSS — and the values it resolves to come from
`formats.js`, not from the store, which is what keeps a stored config
from inventing its own conversion table.

Known and accepted, so they don't get re-litigated: the SignalK token
sits in `localStorage` (SignalK serves every webapp from one origin, so a
compromised sibling webapp could read it), and credentials cross a boat
LAN in the clear when SignalK is served over http. Neither is fixable
from inside this webapp.

## .gitignore

`.gitignore` covers `node_modules/`, Python `__pycache__/`/`*.pyc` (from
the dev server), `.DS_Store`, `*.log`, `.env` and `.claude/`. None of
these exist in the repo — it's pre-emptive, since there's no build
tooling to generate a lockfile-driven ignore list from.

## Versioning

Three hand-maintained places, with no build step to derive one from
another: `package.json` `version`, the `v0.0.10` label in
`public/index.html`, and the `#X.Y.Z` pin on the GitHub-install example
in `README.md`. Bump all three together and tag the release commit (`git
tag -a X.Y.Z`). The README pin is the one that rots unnoticed — nothing
reads it, so a stale version there installs the wrong code without
erroring.
