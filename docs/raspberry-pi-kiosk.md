# Raspberry Pi kiosk display setup

How to boot a Raspberry Pi Zero 2 W straight into a fullscreen browser showing
a signalk-bignumbers instrument, with no desktop environment.

## Hardware / OS assumptions

- Raspberry Pi Zero 2 W (quad-core Cortex-A53, `nproc` = 4)
- HDMI display
- Raspberry Pi OS, Debian Trixie, console-only (no desktop installed)

## Why cog

[cog](https://github.com/Igalia/cog) is a minimal WPE WebKit-based browser
shell built for embedded/kiosk use. Its DRM/KMS backend (`--platform=drm`)
renders directly to the framebuffer via the GPU — no X11, no Wayland
compositor, no window manager. That matters on a Zero 2 W's 512MB RAM.

The tradeoff: it's WebKit, not Chromium, and the CLI/config surface is much
smaller. Fine for a self-contained instrument page; would be worth
reconsidering (cage + `chromium --kiosk`) if the target page relied on
Chromium-only behavior.

Confirm hardware GPU acceleration is available before relying on this:

```bash
ls /dev/dri
# expect both card0 and renderD128 present
grep dtoverlay /boot/firmware/config.txt
# expect dtoverlay=vc4-kms-v3d
```

If `renderD128` is missing, cog falls back to software rendering, which is
much more CPU-hungry.

## Install

```bash
sudo apt update
sudo apt install -y cog
```

Verify the DRM platform plugin is present:

```bash
ls /usr/lib/*/cog/modules/
# expect libcogplatform-drm.so among the listed .so files
```

## systemd service

Running as root, so no PAM/logind session dance is needed for DRM access.
The unit takes over `tty1` from the console getty so cog can acquire DRM
master and doesn't fight `getty@tty1` for the same VT.

```bash
sudo systemctl disable getty@tty1.service
```

The URL to display lives in a separate one-line config file, not the unit
file itself — see [Configuring what a display shows](#configuring-what-a-display-shows)
below for why. Its display id is derived once from the Pi's own MAC
address (last 4 hex chars) rather than a name you have to invent and keep
in sync by hand:

```bash
ID=$(cat /sys/class/net/wlan0/address | tr -d ':' | tail -c 5)
echo "KIOSK_URL=\"http://hl.local:3000/signalk-bignumbers/instrument.html?display=$ID\"" | sudo tee /etc/default/cog-kiosk
```

`/etc/systemd/system/cog-kiosk.service`:

```ini
[Unit]
Description=Cog kiosk browser
After=systemd-user-sessions.service getty@tty1.service network-online.target
Wants=network-online.target
Conflicts=getty@tty1.service

[Service]
Type=simple
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
StandardInput=tty
StandardOutput=journal
StandardError=journal
EnvironmentFile=/etc/default/cog-kiosk
ExecStart=/usr/bin/cog --platform=drm "$KIOSK_URL"
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

`ExecStart` never needs editing again — to point this Pi at a different
display, edit the one line in `/etc/default/cog-kiosk` and
`sudo systemctl restart cog-kiosk`.

This also sidesteps a couple of escaping gotchas that only bite when a URL
is written directly into a `.service` file's `ExecStart`: systemd treats
`%` as a specifier prefix there (a literal `%3A` breaks unit parsing unless
doubled to `%%3A`), and non-ASCII characters like `°` typed on a
non-UTF-8-locale SSH session can get mangled before cog ever sees them —
worth percent-encoding them (`°` is `%C2%B0`) regardless of which file
they end up in.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cog-kiosk.service
systemctl status cog-kiosk.service
journalctl -u cog-kiosk -f   # tail logs
```

## Configuring what a display shows

Each kiosk should stay as dumb as possible: its only local config is
`KIOSK_URL`, pointing at `instrument.html?display=<id>` — a display id
derived from its own MAC address (see above), not an instrument. What
that id actually shows lives on the SignalK server itself, in SignalK's
built-in [applicationData](https://signalk.org) store, so changing a
display never means SSHing into the Pi again, and there's no id to invent
or keep in sync by hand.

**A display with no saved config yet shows its own code, large, on
screen** — that's the normal state right after first boot. Read the code
off the physical screen (no SSH needed) and register it:

1. Open the webapp (`index.html`) from any browser on the network. It
   opens on a list of every display already configured.
2. Log in using the bar at the top — SignalK requires auth for writes
   even when reads are open, so this applies to this page only, never to
   a display. The token is kept in the browser's `localStorage`.
3. Click **+ Add display**, enter the code shown on the kiosk's screen,
   pick the instrument, and **Save**. **Preview** opens the config in a
   new tab first if you want to eyeball it before saving.

Displays pick up changes on their own — an unconfigured one polls every
5s waiting for a config to appear, and a running one re-checks its own
config every 5s, reloading if it changed. So saving in the picker takes
effect within a few seconds, and `systemctl restart cog-kiosk` is never
needed to change what a display shows. Deleting a display's entry sends
it back to showing its code, ready to be reassigned.

A Pi's local config only needs to change at all if you're pointing it at
a different SignalK server entirely.

Back on the list, **Edit** and **Delete** manage existing entries. A
display's code is fixed once created — to change it, delete the entry and
add it again, which keeps an edit from silently creating a duplicate
under a new code.

## Disable console blanking

Append to `/boot/firmware/cmdline.txt` (same line, space-separated, no
newline):

```
consoleblank=0
```

Then `sudo reboot` to confirm the whole chain (boot → tty1 freed → network
online → cog → display) comes up clean without a login session.

## Debugging by hand

Before trusting the service, it's easiest to run cog directly over SSH —
DRM master isn't tied to which tty your SSH session is attached to, so this
works as long as nothing else (i.e. a running `cog-kiosk.service`) already
holds the display:

```bash
cog --platform=drm "http://hl.local:3000/signalk-bignumbers/instrument.html?host=epi.local%3A2001&path=..."
```

Use plain (non-doubled) `%` escaping here since this is a shell command,
not a unit file. `Ctrl+C` stops it.

## Expected resource usage

On a Zero 2 W (4 cores), steady-state CPU around 25% with load average
~1 is normal for a live-updating page — that's roughly one core kept busy
compositing frames, with three cores idle. Not a sign of trouble by
itself; the thing actually worth checking is that `/dev/dri/renderD128`
exists (GPU acceleration active) rather than watching the load number.
