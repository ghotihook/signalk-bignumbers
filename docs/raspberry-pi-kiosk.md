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
ExecStart=/usr/bin/cog --platform=drm "http://hl.local:3000/signalk-bignumbers/instrument.html?host=epi.local%%3A2001&path=navigation.attitude&field=roll&name=HEEL&layout=xx&neg=true&unit=%%C2%%B0&factor=57.29577951308232"
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

Adjust the `ExecStart` URL for the instrument you want to show — see the
main repo README for the query-string parameters. Two escaping gotchas to
keep in mind if you edit it:

- **`%` in unit files is a systemd specifier prefix.** Any literal `%` in
  the URL (e.g. URL-encoded characters like `%3A` for `:`) must be doubled
  to `%%3A`, or systemd fails with `Failed to resolve unit specifiers` and
  the unit won't load at all (`bad-setting` state). This only applies
  inside the `.service` file — not when running `cog` directly from a
  shell.
- **Non-ASCII characters (e.g. `°`) typed directly on an SSH command line
  can get mangled** if the shell session isn't in a UTF-8 locale, which
  cog then rejects as invalid UTF-8. Percent-encode them instead of typing
  the raw character: `°` is UTF-8 bytes `C2 B0`, so use `%C2%B0` on the
  command line (`%%C2%%B0` inside the unit file).

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cog-kiosk.service
systemctl status cog-kiosk.service
journalctl -u cog-kiosk -f   # tail logs
```

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
