# signalk-bignumbers

## What this is

Mast and repeater displays for **racing**. Someone on the rail reads a
number off a screen metres away, in spray, at an angle, in anything from
full sun to full dark. That's the whole job.

**Not an MFD.** No charts, gauges, graphs, trends, history, AIS, routing,
alarms or touch targets. A pixel that isn't a number, its label or its
unit has to justify itself against reading distance.

Three things are optimised, in this order.

## Latency — late data is worse than no data

Someone is trimming to the number in real time. A two-second-old reading
that looks current is worse than dashes, because nothing on screen says
not to trust it. **Given the choice between showing an update late and
not showing it, drop it.**

All of these are load-bearing:

- `policy: "instant"`, **no `period`, no `minPeriod`**. Adding one is the
  obvious-looking way to "reduce load on the Pi"; it buys latency. Don't.
- Every delta renders synchronously in `onmessage`. No queue, no
  `requestAnimationFrame`, no `setTimeout`, no idle callback, no batching.
- `.sign`/`.value` carry `transition: none`. An animating number shows
  readings the boat never took, and shows them late.
- No smoothing, averaging or damping in the client. Damping belongs
  upstream in SignalK, where every display reading the path gets it.
- The socket opens `?subscribe=none` and subscribes only to paths on
  screen — a latency decision as much as a bandwidth one.
- No history, replay or backfill. A reconnect shows the next live value.
- If the Pi can't keep up, cut values or slow the source. Never buffer.

After `staleMs` (3s) with no update a band fades to dashes rather
than holding its last reading, so a dead feed looks dead rather than
looking like a becalmed boat.

Deltas are trusted in arrival order; a delta's `timestamp` is never read.
That's sound over one websocket, since TCP preserves order — it stops
being sound the moment anything replays history into the stream.

## Clarity

- `fitDisplay()` makes glyphs as large as the band allows, at one size
  across every band (`min` scale over all cells) so the screen reads as
  one instrument. Each cell is measured against its own box.
- **Digits never move horizontally**: `tabular-nums`, ghosted leading
  zeros that keep their width, a reserved sign column when `neg` is set.
  A reading with more integer digits than its mask shows the mask as `^`
  rather than growing: an extra digit overflows the fitted row and clips
  the leading one, so 140.2 would read as 40.2.
- Fixed high-contrast themes, not colour pickers — nothing selectable
  should wash out in sun or wreck night vision. Day themes are dark digits
  on a bright ground; night reds light the red sub-pixel only (`#ff0000`,
  never a red with green or blue in it). A retired theme goes into
  `RETIRED` rather than being deleted: the editor matches saved colours
  exactly, so a retired pair would otherwise show as "Custom" and never
  move to its replacement. A valid pair nothing matches stays selectable
  as Custom, so saving another field can't recolour it.
- `MAX_ITEMS` is 3; past that the digits are too small to read from the
  rail. Raising it trades away the only thing this does well.
- `cursor: none`, `overflow: hidden`. There's nothing to interact with.

## Speed

- No build step, bundler, framework or runtime dependencies — static
  files the SignalK server hands over as-is. Keep it that way.
- Target is a Pi Zero 2 W (512MB) on cog/WPE WebKit straight to DRM.
  WebKit only; no Chromium-specific APIs.
- `font-display: block`, so nothing is measured against a fallback face.
- One websocket per display however many values, paths deduped first.

## The repo

- `public/index.html` — the manager: lists displays, edits them, writes
  their configs.
- `public/instrument.html` — the display.
- `public/formats.js` — the one presentation table, loaded by both pages
  with a plain `<script src>`. Two copies would drift, and there's no
  build step to generate one from the other.
- `TODO.md` — known gaps, deliberately left for now.
- `dev/dummy_signalk.py` — delta/websocket dev server.
  `dev/make_icon.py` generates `public/icon.png`.

`instrument.html` takes either full query params (`?path=…&name=…`) or
`?display=<hostname>`, which fetches a stored config from SignalK's
`applicationData`. The identifier is the Pi's hostname via systemd's `%H`.
See `docs/raspberry-pi-kiosk.md` for the kiosk case this was built for.

**Verifying a change.** No test suite, no build. `dummy_signalk.py`
drives `?path=` URLs — repeat `--path`, and `--field` matched by
position, for a multi-value display. `?display=` and the editor's path
dropdown need a real signalk-server. `node --check` on the extracted
`<script>` is a cheap syntax gate, and jsdom will drive `index.html`
headlessly for anything in the editor.

## Path and presentation

A value is `path` + `format` + `name` + colours. Nothing else is
configurable, and the two dropdowns being orthogonal is the point: any
path can be shown any way, without anyone having foreseen the pairing.

**The path dropdown is live.** `loadPaths()` reads
`/signalk/v1/api/vessels/self`; `flattenPaths()` treats any node carrying
a `value` as a leaf, and an object value (`navigation.attitude`) becomes
one entry per numeric key — the `path`/`field` pair a cell subscribes
with. No hardcoded list, no free-text box. A *saved* path missing from
the live list is re-added at the top marked "not currently reporting":
editing colours at the dock with the instruments off must not drop it.

Meta-driven discovery was rejected and shouldn't return on the strength
of this: `meta` has no number-format or sign field, so it can't supply
`layout` or `neg`, and `meta.units` is always SI, which `factor` assumes.

**`format` expands, raw keys override.** `makeItem()` resolves
`FORMAT_BY_ID[raw.format]`, then lets an explicit
`factor`/`offset`/`unit`/`layout`/`neg`/`wrap` win. That ordering — not a
migration — is what keeps every config and URL written before formats
meaning what it did, and it leaves a way to show what no presentation
covers. An unknown slug changes no key. `mode` (`"duration"`, `"clock"`)
comes from the table only, so a hand-written config can't reach a time
rendering by accident.

`matchFormat()` recognises a pre-format config by its conversion keys and
upgrades it to a slug on the next save. `mode` is in its signature so the
two otherwise-identical HH:MM:SS entries can never match.

The digit mask is the single source of width: `layout` gives both the
placeholder (`--:--:--`) and `fitDisplay()`'s sample (`88:88:88`), which
is why a colon measures as a colon. Time renderings clamp the leading
field to two digits rather than growing a third.

## One, two or three values

Up to `MAX_ITEMS` (3), stacked in equal bands. One value is not a special
case anywhere — its band is the whole viewport.

Both config sources normalise to one list before anything else runs:
stored configs are `{bg, fg, items: [...]}`; URL params take a `2`/`3`
suffix, unsuffixed meaning the first value, so every pre-existing
single-value URL still parses identically. Suffixes beat repeated params
(`?path=a&path=b`), which misalign as soon as one value omits an optional
key.

A stored config with no `items` predates multi-value support; `itemsOf()`
and the `Array.isArray` check in `fetchDisplayConfig` read it as one
value. Don't drop those paths — they're the upgrade story for anything
already deployed.

`host` and `display` belong to the display as a whole, never suffixed.

`bg`/`fg` are deliberately both per-item (`bg2`/`fg3` colour one band)
and display-level. The page-level pair backs the "not configured" and
error screens, which exist before any cell does, so don't drop it for
per-item only; the editor mirrors value 1's theme up for exactly this.
`.cell` re-declares `background`/`color` from the variables rather than
inheriting body's computed values, which is what lets a per-band override
reach the opacity-derived title and the `currentColor` divider.

## Talking to SignalK

Writes to `applicationData` need a login even when reads are anonymous,
and take `POST`, not `PUT` — a `PUT` is 401 unauthenticated and 404 once
authenticated.

Anonymous reads are a server setting, not a given. With security on and
**Allow Readonly Access** off, a display gets 401 for both its config and
the stream, and holds no credentials to fix it. Two things depend on
catching that: `instrument.html` tells 401/403 apart from an empty config
document, or it falls through to "not configured" and sends whoever reads
it off to add a display that's already there; and `checkAnonymousRead()`
in `index.html` probes with `credentials: "omit"` — the omit is the whole
point, since the login cookie would otherwise pass the probe on a server
where every display fails.

## Mandatory fields in the editor

Every field is mandatory except Colours, which always has a value. So
validation is about naming *which* field is missing, and there are no
asterisks on the labels, because marking all but one is noise.

`checkEditor(problems)` takes `[element, message]` pairs, so Save and
Preview compose different checks:

- **Preview checks the value slots only** — its URL carries every value
  as a parameter and never reads the hostname. It does insist on the
  values: `itemsFromParams()` stops at the first missing path, dropping
  that value and every one after it, and a value with no presentation
  falls back to a one-digit layout on the raw SI number. Either way the
  preview is a screen nobody configured.
- **The hostname check is skipped while the field is disabled**, which is
  whenever an existing display is edited. The hostname is fixed at
  creation, so checking it would permanently strand any display created
  before the check existed, or written straight into `applicationData`.

Correcting any outlined field drops the message; the outlines track the
rest. Pinning the message to one field instead costs a variable touched
from three places and buys a message that can outlive what it describes.

`HOSTNAME_RE` allows dots so an FQDN passes. The point isn't strictness —
the name has to match `%H` character for character, or the display
silently never finds its config.

Validation reads the DOM directly, so it can name a field; nothing about
the stored shape changes. There's no `<form>`, no `required` and no
constraint-validation API — the page has no form element, and native
validation bubbles don't match the theme.

`start()` in `instrument.html` refuses the same config from the other
end, with a message named for which source it came from: a display on
`?display=` has no `?path=` to point anyone at.

## Two invariants in instrument.html

Both were bugs once, and both are easy to reintroduce from a distance:

1. **Cells are built once by `buildCells()` and never rebuilt.** Each
   cell holds the `signEl`/`valueEl` captured at creation; only their
   text changes afterwards. Recreating a cell, or writing a row's
   `innerHTML`, detaches them, and every later update writes to orphaned
   nodes — a stale-looking number rather than a visible error. Error and
   unconfigured states render into the separate `#message` element.
2. **`start()` and `run()` are called at most once per page load.**
   `run()` attaches a resize listener and opens a websocket, neither of
   which is torn down. Config changes reload the page instead. The config
   fetch uses two-argument `then(ok, fail)` rather than `.catch()`, so a
   throw inside the success handler can't be retried into a second
   `run()`.

## Security invariants

Both were live vulnerabilities, fixed in 0.0.5, and both look like
conveniences.

1. **`index.html` talks only to the origin that served it — no `?host=`,
   ever.** It posts a username and password, so a parameter that moves
   the origin turns any link into a credential harvester, with the real
   SignalK server still showing in the address bar. `instrument.html`
   keeps its `?host=` because it holds no credentials.
2. **Colours are validated to literal hex before reaching CSS.** `bg`/`fg`
   feed `background: var(--bg)`, and the `background` shorthand accepts an
   image — an unvalidated `url(https://elsewhere/x.png)` is a *valid*
   background that makes every display announce the boat. `colour()` is
   the only way a colour reaches `style.setProperty`.

Behind both: **a stored config is attacker-controlled input.** It lives
in `applicationData/global/`, writable by any authenticated SignalK user.
`name` and `unit` are safe only because they go through `textContent` —
never build a cell with `innerHTML`. `format` is safe only as a key into
`FORMAT_BY_ID`; it must never reach the DOM or CSS as a string, and the
values it resolves to come from `formats.js`, not the store.

Known and accepted, so they don't get re-litigated: the token sits in
`localStorage` (one origin serves every SignalK webapp, so a compromised
sibling could read it), and credentials cross a boat LAN in the clear
over http. Neither is fixable from inside this webapp.

## Releasing

Three hand-maintained version strings, with no build step to derive one
from another: `package.json` `version`, the `v0.0.11` label in
`public/index.html`, and the `#X.Y.Z` pin on the GitHub-install example
in `README.md`. Bump all three together and tag the release commit (`git
tag -a X.Y.Z`).

Then `npm publish` — **the Appstore serves the published version, not the
tag.** 0.0.9 was tagged and never published, so boats stayed on 0.0.8.
The README pin rots the same way: nothing reads it, so a stale one
installs the wrong code without erroring.
