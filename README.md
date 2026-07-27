# signalk-bignumbers

Big, high-contrast single-value instrument displays for
[SignalK](https://signalk.org) — designed to fill a screen and be read at
a glance from across a cockpit.

Each display is a cheap Raspberry Pi with an HDMI screen, running nothing
but a fullscreen browser. It knows only its own hostname; what it shows
is stored on the SignalK server and managed from a web page, so
reconfiguring a screen never means touching the Pi.

## What's here

- **`public/index.html`** — the webapp. Lists every configured display,
  and adds, edits and deletes them.
- **`public/instrument.html`** — the display itself. Fills the screen
  with one number, autosized to fit.
- **`docs/raspberry-pi-kiosk.md`** — how to build a display from a Pi.
- **`dev/dummy_signalk.py`** — a fake SignalK server that sweeps a value
  through a range, for testing the display without a boat.

## Install

It's a SignalK webapp — a package of static files, no plugin or backend.
Install it into your SignalK server's `node_modules` and restart the
server, and it appears in the Webapps menu:

```bash
cd ~/.signalk
npm install ghotihook/signalk-bignumbers
sudo systemctl restart signalk    # or however your server is run
```

## How a display gets configured

1. A Pi boots into `instrument.html?display=<its-hostname>` (see the
   [kiosk setup guide](docs/raspberry-pi-kiosk.md)).
2. With nothing stored for that hostname, the screen shows the hostname
   in large text.
3. In the webapp, add that hostname, choose an instrument and colours,
   and save.
4. The display picks it up within about 5 seconds. No restart, no SSH.

Configs live in signalk-server's built-in `applicationData` store, keyed
by hostname. Displays read it anonymously; saving requires a SignalK
login, which the webapp prompts for.

## Direct URLs

A display can also be configured entirely from its URL, with no stored
config — useful for testing, or for a one-off screen:

```
instrument.html?path=environment.wind.speedApparent&name=AWS&layout=xx.xx&unit=kt&factor=1.9438444924406
```

| Parameter | Meaning |
|---|---|
| `path` | SignalK path to subscribe to (required) |
| `name` | Label shown top-left (required) |
| `field` | Key to read from a compound value, e.g. `roll` |
| `layout` | Digit template, e.g. `xxx` or `xx.xx` — sets the autosize and decimal places |
| `neg` | `true` to reserve room for a minus sign |
| `unit` | Label shown after the number |
| `factor`, `offset` | Unit conversion: `shown = raw * factor + offset` |
| `bg`, `fg` | Theme colours |
| `host` | SignalK server, if not the one serving the page |
| `display` | Stored-config identifier — used *instead of* the above |

The webapp's **Preview** button builds these URLs for you.

## License

MIT — see [LICENSE](LICENSE). Bundles
[Roboto](https://fonts.google.com/specimen/Roboto), Apache License 2.0.
