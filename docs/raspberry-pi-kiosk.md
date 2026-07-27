# Raspberry Pi kiosk display setup

Boot a Raspberry Pi straight into a fullscreen signalk-bignumbers
instrument, with no desktop environment.

Written for a Pi Zero 2 W with an HDMI screen, running Raspberry Pi OS
(Trixie) console-only. Everything below runs on the Pi over SSH.

## Install

**1. Install cog**

```bash
sudo apt update
sudo apt install -y cog
```

**2. Free up tty1** so cog can take the screen from the console getty:

```bash
sudo systemctl disable getty@tty1.service
```

**3. Create the service** at `/etc/systemd/system/cog-kiosk.service`,
replacing `hl.local:3000` with your SignalK server. `%H` is a systemd
specifier for the hostname — it becomes this display's code, so there's
nothing to generate or keep in sync:

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
ExecStart=/usr/bin/cog --platform=drm "http://hl.local:3000/signalk-bignumbers/instrument.html?display=%H"
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

**4. Stop the console blanking.** Append to `/boot/firmware/cmdline.txt`
(same line, space-separated, no newline):

```
consoleblank=0
```

**5. Start it:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cog-kiosk.service
sudo reboot
```

After the reboot the screen shows the Pi's hostname — that's a display
with no config yet. Register it using the webapp (next section).

To check on it:

```bash
systemctl status cog-kiosk.service
journalctl -u cog-kiosk -f
systemctl show cog-kiosk -p ExecStart   # confirm %H expanded to the hostname
```

## Configuring what a display shows

Each kiosk stays as dumb as possible: all it knows is its own hostname
and where the SignalK server is — it asks for `?display=<hostname>` and
takes whatever it's given. What that code shows lives on the SignalK
server, in signalk-server's built-in `applicationData` store, so changing
a display never means SSHing into the Pi again.

**A display with no saved config shows its own code, large, on screen** —
the normal state right after first boot. Read the code off the physical
screen and register it:

1. Open the webapp (`index.html`) from any browser on the network. It
   opens on a list of every display already configured.
2. Log in using the bar at the top — SignalK requires auth for writes
   even when reads are open, so this applies to this page only, never to
   a display. The token is kept in the browser's `localStorage`.
3. Click **+ Add display**, enter the code shown on the kiosk's screen,
   pick the instrument, and **Save**. **Preview** opens the config in a
   new tab first if you want to eyeball it before saving.

Back on the list, **Edit** and **Delete** manage existing entries. A
display's code is fixed once created — to change it, delete the entry and
add it again, which keeps an edit from silently creating a duplicate
under a new code.

Displays pick up changes on their own — an unconfigured one polls every
5s waiting for a config to appear, and a running one re-checks its own
config every 5s, reloading if it changed. So saving takes effect within a
few seconds, and `systemctl restart cog-kiosk` is never needed to change
what a display shows. Deleting an entry sends that display back to
showing its code, ready to be reassigned. A Pi's local config only needs
to change at all if you're pointing it at a different SignalK server, or
swapping which code that Pi answers to.

---

## Notes

### Why cog

[cog](https://github.com/Igalia/cog) is a minimal WPE WebKit browser
shell built for embedded/kiosk use. Its DRM/KMS backend
(`--platform=drm`) renders directly to the framebuffer via the GPU — no
X11, no Wayland compositor, no window manager. That matters on a Zero
2 W's 512MB RAM.

The tradeoff: it's WebKit, not Chromium, and the CLI/config surface is
much smaller. Fine for a self-contained instrument page; worth
reconsidering (cage + `chromium --kiosk`) if the page needed
Chromium-only behavior.

The service runs as root, so no PAM/logind session setup is needed for
DRM access.

### Verifying GPU acceleration

If cog falls back to software rendering it's much more CPU-hungry:

```bash
ls /dev/dri
# expect both card0 and renderD128
grep dtoverlay /boot/firmware/config.txt
# expect dtoverlay=vc4-kms-v3d
ls /usr/lib/*/cog/modules/
# expect libcogplatform-drm.so
```

### Expected resource usage

On a Zero 2 W (4 cores), steady-state CPU around 25% with load average
~1 is normal for a live-updating page — roughly one core kept busy
compositing frames, three idle. Not a sign of trouble by itself; what's
actually worth checking is that `/dev/dri/renderD128` exists.

### The display code, and `%` in unit files

`%H` works because systemd expands specifiers in `ExecStart` before
running it. That same expansion is a trap if you ever put a
full-parameter URL there instead of `?display=`: **any literal `%` must
be doubled**. A URL-encoded `%3A` breaks unit parsing outright (`Failed
to resolve unit specifiers`, and the unit won't load at all) unless
written `%%3A`. The doubling applies only inside the unit file — not when
running cog from a shell.

Related: **non-ASCII characters can be mangled** if typed on an SSH
session that isn't in a UTF-8 locale, and cog then rejects the URL as
invalid UTF-8. Percent-encode them — `°` is `%C2%B0` (`%%C2%%B0` in a
unit file).

Using the hostname as the code means renaming the Pi changes its code,
and the display drops back to the unconfigured screen until you register
the new name. Both are usually what you want. If you'd rather have a code
that survives a rename, `%m` expands to the machine ID — but it's 32 hex
characters, which is unpleasant to read off a screen and type in.

### Running cog by hand

Useful for testing a URL before committing it to the service. Works as
long as `cog-kiosk.service` isn't already holding the display — DRM
master isn't tied to which tty your SSH session is on:

```bash
sudo systemctl stop cog-kiosk
cog --platform=drm "http://hl.local:3000/signalk-bignumbers/instrument.html?display=f3a9"
```

Use plain (non-doubled) `%` escaping here — that's a shell command, not a
unit file. `Ctrl+C` stops it.
