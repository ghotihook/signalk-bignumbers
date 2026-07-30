# signalk-bignumbers

Big, high-contrast number displays for [SignalK](https://signalk.org) —
mast and repeater screens for racing, showing one, two or three values
large enough to read from the rail.

![A screen strapped to a mast in bright sun, filled by the number 0.0 labelled STW and kt, black on white](docs/images/display-mast.jpg)

## Why this exists

A racing repeater has to do three things:

- **Perform.** Show what the instrument is reading now, at whatever rate
  the sensor produces it.
- **Be readable.** At a glance, from metres away, at an angle, in spray,
  in full sun or full dark.
- **Be trivial to deploy.** Minutes from a bare screen to a live number,
  with nothing installed or configured on the display.

How it meets them:

**Fast.** A delta arrives and paints. No queue, no batch, no
`requestAnimationFrame`, no animation, no rate limit — a 10 Hz source
updates the screen ten times a second. Nothing is smoothed, averaged or
damped; that belongs upstream in SignalK. A late update is dropped, not
shown late. See [Latency and load](#latency-and-load).

**Large, clear numbers.** One value fills the screen; three fill a third
each, all at the same digit size. Fixed high-contrast themes, not a
colour picker. A value with no update for 3 seconds drops to grey dashes
rather than holding a stale reading.

**Digits that don't jump.** A number whose digits shift sideways can't be
read from a moving boat, so the layout is fixed before any value arrives:
the digit template (`xx.x`) reserves a column per digit, figures are
`tabular-nums`, leading zeros are hidden rather than removed, and a value
that can go negative reserves its minus column. 9.9 to 10.0 and back
moves nothing but the digits.

**No bloat.** Two static HTML pages. No build step, bundler, framework,
dependency, backend or plugin. A Pi Zero 2 W runs a display with headroom
to spare.

**Nothing to install or configure on the display.** Anything with a
browser is a display the moment you open a URL on it: phone, old iPad,
laptop, Pi with an HDMI panel. Deploying one is open the URL, read the
name off the screen, add it in the webapp; configuring it is picking an
instrument from a dropdown. The display holds no config and no
credentials, so changing what it shows never means touching it.

Not an MFD: no charts, gauges, graphs, history, AIS, alarms, nothing to
touch.

<img src="docs/images/display-mast-three.jpg" alt="A mast-mounted screen showing three stacked bands: STW 0.0 kt black on white, SOG 0.0 kt white on black, AWS 6.4 kt cyan on black" width="520">

## Quick start

Five minutes, using a phone as the display.

**1. Install the webapp** — the only thing that gets installed anywhere.
In SignalK's admin UI: *Appstore → Available*, find `signalk-bignumbers`,
**Install**, then restart the server.

**2. Open this on the phone.** Substitute your own server address for
`signalk.local:3000` throughout — the same host and port you use to reach
SignalK's admin UI.

```
http://signalk.local:3000/signalk-bignumbers/instrument.html?display=phone
```

The screen fills with `phone` and "Not configured yet" — its name, and
nothing stored under it yet. `phone` is just a label you picked in the
URL; use the same word in the next step.

**3. Tell it what to show.** From any browser, open
`http://signalk.local:3000/signalk-bignumbers/` (also in SignalK's
Webapps menu). Log in at the top, **+ Add display**, type `phone`, pick an
instrument, **Save**.

![The webapp's display list: a row for phone showing STW, TWA and TWS, alongside a mast1 row from an earlier setup, each with Edit and Delete buttons](docs/images/webapp-displays.png)

**4. Watch the phone.** Within about 5 seconds it switches from its name
to the number. No reload, no restart.

<img src="docs/images/display-phone.png" alt="A phone showing three stacked bands: STW 0.0 kt white on black, TWA 13 degrees black on white, TWS 16.2 kt white on black" width="260">

That phone is done. Changing what it shows is **Edit**; going from one
value to three is **+ Add another number**. Nothing on the phone changes
either time.

## Proper install

The quick start is the whole software install. What's left is making a
device stay on the air unattended.

The two differ in one thing: **where the name comes from.** On a phone
you type it into the URL; on a Pi, systemd fills in the hostname, so one
service file works on every Pi in the fleet.

### Phone or tablet

For a repeater someone carries, or a screen up for one race. An old iPad
in a waterproof case works on the mast.

1. Open the display URL in Safari or Chrome, with a name you pick:
   `.../instrument.html?display=bow`
2. **Add to Home Screen** — it launches fullscreen, no address bar.
3. **Turn off auto-lock.** The page holds no wake-lock, so a screen
   timeout takes the display off the air. On iOS: *Settings → Display &
   Brightness → Auto-Lock → Never*.
4. Keep it on power. A bright screen on live data drains a battery fast.
5. Optional: iOS *Guided Access* (*Settings → Accessibility → Guided
   Access*) locks it to the page.

Name it for where it goes — `bow`, `pit`, `helm` — not for the device.
Swapping in a different phone is then one URL to open.

### Raspberry Pi Zero 2 W (permanent mast display)

For a screen that lives on the boat: it comes up on power, has no battery
or lock screen, and doesn't mind the rain. A Zero 2 W runs one with
plenty of headroom.

Full walkthrough: **[docs/raspberry-pi-kiosk.md](docs/raspberry-pi-kiosk.md)**.
In outline:

1. Raspberry Pi OS (Trixie) console-only, no desktop.
2. `sudo apt install -y cog` — a minimal WPE WebKit shell that renders
   straight to the framebuffer via DRM/KMS. No X11, no Wayland, no
   compositor between the delta and the glass.
3. Test by hand:
   `cog --platform=drm "http://signalk.local:3000/signalk-bignumbers/instrument.html?display=$(hostname)"`
4. Make it permanent with a systemd unit using `%H` in place of the
   hostname, so the file is identical on every Pi.
5. Free tty1 (`systemctl disable getty@tty1`) and add `consoleblank=0` to
   `/boot/firmware/cmdline.txt`.

Because the name is the hostname, deploying one is: name the Pi, plug it
in, read the name off its screen, add it in the webapp.

<img src="docs/images/display-unconfigured.jpg" alt="A Pi's screen showing the hostname mast1 in large pale blue text on dark blue, above a line saying it isn't configured yet and to add this hostname in the webapp" width="520">

### Anything else

| Display | How it opens the page |
|---|---|
| Raspberry Pi Zero 2 W + HDMI panel | boots into it fullscreen, hostname as its name ([guide](docs/raspberry-pi-kiosk.md)) |
| iPhone / iPad | Safari, **Add to Home Screen** |
| Android phone or tablet | Chrome, **Add to Home screen** |
| Laptop | any browser, fullscreen |

Mixed fleets are managed from one list, with no distinction between a
mast Pi and a borrowed phone.

---

# Reference

## Installing and updating

It's a SignalK webapp — static files, no plugin and no backend. Normally
you install and update it from the admin UI's **Appstore**, which
restarts into the new version.

To run the development version instead, install from GitHub:

```bash
cd ~/.signalk
npm install github:ghotihook/signalk-bignumbers
sudo systemctl restart signalk    # or however your server is run
```

`github:owner/repo` clones the repo rather than looking the name up in
the npm registry, so this gets the current `main`. Add `#<tag>` or
`#<branch>` to pin one:

```bash
npm install github:ghotihook/signalk-bignumbers#0.0.7
```

`cd ~/.signalk` matters: signalk-server scans that directory's
`node_modules` for webapps at startup, so anywhere else leaves it
invisible. Either way, **signalk-bignumbers** appears in the Webapps menu
after the restart, served at
`http://<your-server>:3000/signalk-bignumbers/`.

## The webapp

One row per display, showing what it's set to. **Edit** changes it and
the display picks it up within about 5 seconds; **Delete** sends it back
to showing its own name, ready to be reassigned. A display's name is
fixed once created.

<img src="docs/images/webapp-edit.png" alt="The display editor: dropdowns for Instrument and Colours, a Display name field, and an expanded Advanced section with Path, Field, Factor, Offset, Unit, Layout and Negative" width="460">

Per value:

| Field | Meaning |
|---|---|
| **Instrument** | A preset — AWS, TWA, SOG, STW, HDG, Depth, Heel, BATT and others. Fills in everything below. |
| **Colours** | Fixed high-contrast pairs. Red or amber on black preserve night vision; black on white or black on amber read better in direct sun. |
| **Display name** | The label above the number. |
| **Path** / **Field** | SignalK path, and the key to read from a compound value (e.g. `roll` from `navigation.attitude`). |
| **Factor** / **Offset** | Unit conversion from SignalK's SI units: `shown = raw * factor + offset`. |
| **Unit** | Label after the number. |
| **Layout** | Digit template, e.g. `xxx` or `xx.x` — sets the autosize and the decimal places. |
| **Negative** | Reserves a column for the minus sign, so digits don't shift when the value goes negative. |
| **Wrap to ±180°** | Folds the converted value into −180…180, for sources that send wind angle as 0…360. |

**+ Add another number** puts a second or third value on the same screen.
They split it into equal horizontal bands, top to bottom in the order
listed, each with its own colours, all at the same digit size. Bands
sharing a background are divided by a hairline; otherwise the colour
change is the divide. Use mixed backgrounds sparingly — they cost some of
the dark adaptation the night themes protect.

**Preview** opens the config in a new tab before saving.

## Configuration and permissions

Configs live in signalk-server's built-in `applicationData` store, keyed
by the display's name. Displays read it anonymously; saving requires a
SignalK login, which the webapp prompts for and keeps in the browser's
`localStorage`.

A display holds no credentials, so if signalk-server's security is on it
needs **Security → Settings → Allow Readonly Access** enabled, or nothing
reaches the screen at all. The webapp checks this on load and warns if
it's off, and a display that can't read its config says so rather than
falling through to the "not configured" screen.

An unconfigured display polls every 5s waiting for a config to appear; a
running one re-checks its own every 5s and reloads if it changed.
Restarting a display to change what it shows is never necessary.

## Reading the screen

- A value with no update for 3 seconds drops to **grey dashes**. It never
  holds a stale reading.
- The **dot top-right** is green while the connection to SignalK is live,
  dark red when it isn't. A dropped connection retries every second and
  recovers on its own, showing the next live value rather than replaying
  what was missed.

## Latency and load

**Late data is worse than no data.** A number two seconds old looks
current, and nothing on screen says otherwise.

So as little as possible sits between the delta and the glass:

- Subscriptions use `policy: "instant"`, no `period`, no `minPeriod`.
  Values arrive as they change, not on a timer.
- Each delta renders synchronously on arrival. No queue, no
  `requestAnimationFrame`, no `setTimeout`, no batching.
- Nothing animates — a tweened number shows readings the boat never took.
  Value changes carry `transition: none`.
- No smoothing, averaging or damping. Damping belongs upstream in
  SignalK, where every display gets it.
- No history, replay or backfill. A reconnected display shows the next
  live value, not what it missed.

There's no rate limit either, so a 10 Hz source updates the screen ten
times a second. That stays cheap:

- A display receives only the paths it shows: the socket opens
  `?subscribe=none` and subscribes by path, so the rest of the bus is
  never sent.
- Between deltas nothing paints. CPU follows the data rate, not the clock.
- An update writes the sign and digits, nothing else. Digit widths are
  reserved, so a new value doesn't reflow or resize the text;
  `fitDisplay()` runs at startup and on resize, not per value.
- Past the refresh rate the browser coalesces writes into one paint, so a
  source faster than the panel costs parsing, not drawing.

If a Pi still can't keep up, cut values or slow the source — never
buffer.

## Direct URLs

A display can be configured entirely from its URL, with no stored config
and no login — useful for testing, or a one-off screen:

```
instrument.html?path=environment.wind.speedApparent&name=AWS&layout=xx.xx&unit=kt&factor=1.9438444924406
```

| Parameter | Meaning |
|---|---|
| `path` | SignalK path to subscribe to (required) |
| `name` | Label shown top-left of the band (required) |
| `field` | Key to read from a compound value, e.g. `roll` |
| `layout` | Digit template, e.g. `xxx` or `xx.xx` — sets the autosize and decimal places |
| `neg` | `true` to reserve room for a minus sign |
| `wrap` | `true` to fold the converted value into −180…180 |
| `unit` | Label shown after the number |
| `factor`, `offset` | Unit conversion: `shown = raw * factor + offset` |
| `bg`, `fg` | Theme colours for this value's band; unsuffixed they also set the screen's. Hex only (`#000000`, `#fff`) — anything else is ignored |
| `host` | SignalK server, if not the one serving the page (whole screen) |
| `display` | Stored-config identifier — used *instead of* all of the above |

For a second and third value, suffix every per-value key with `2` and `3`.
The unsuffixed keys are the first value, so any single-value URL still
means what it did (wrapped here for readability — it's one line):

```
instrument.html?path=navigation.speedOverGround&name=SOG&layout=xx.x&unit=kt&factor=1.9438444924406
               &path2=environment.depth.belowTransducer&name2=DPT&layout2=xx.x&unit2=m
               &path3=navigation.attitude&field3=roll&name3=Heel&layout3=xx&neg3=true&unit3=%C2%B0&factor3=57.29577951308232
```

A missing `path2` ends the list, so values can't have gaps. `host` and
`display` belong to the display as a whole and are never suffixed.

`bg` and `fg` do double duty: suffixed (`bg2`, `fg3`) they colour just
that band; unsuffixed they set the first band's colours *and* the
screen's, which is what shows behind the "not configured" and error
screens — those exist before there are any bands.

The webapp's **Preview** button builds these URLs for you.

## What's here

- **`public/index.html`** — the webapp. Lists, adds, edits and deletes
  displays.
- **`public/instrument.html`** — the display itself. Fills the screen
  with up to three numbers, autosized to fit.
- **`docs/raspberry-pi-kiosk.md`** — building a display from a Pi.
- **`dev/dummy_signalk.py`** — a fake SignalK server that sweeps values
  through a range, for testing without a boat. Speaks only the delta
  protocol, so it drives `?path=` URLs, not `?display=` ones.

## License

MIT — see [LICENSE](LICENSE). Bundles
[Roboto](https://fonts.google.com/specimen/Roboto), Apache License 2.0.
