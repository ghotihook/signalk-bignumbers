# Raspberry Pi kiosk display setup

Boot a Raspberry Pi straight into a fullscreen signalk-bignumbers
instrument, with no desktop environment: straight to the framebuffer, no
compositor, no input devices, nothing between the SignalK delta and the
glass.

Use this when you want a display that's *permanent* — one that comes up
by itself on power, has no battery to charge or lock screen to swipe
past, and can be left on the mast in the rain. A phone or tablet needs
none of it: open the URL and add the name in the webapp.

Written for a Pi Zero 2 W with an HDMI screen, running Raspberry Pi OS
(Trixie) console-only. Everything below runs on the Pi over SSH, and
assumes the webapp is already installed on the SignalK server (see
[the README](../README.md#installing-and-updating)).

**Substitute throughout:** `signalk.local:3000` stands for your SignalK
server — the same host and port you use to reach its admin UI, e.g.
`192.168.1.50:3000`. That's the *server's* address, not the Pi's: the Pi
is a dumb screen that fetches everything over the network. If SignalK
runs on the Pi itself, `localhost:3000`.

## 1. Install cog

```bash
sudo apt update
sudo apt install -y cog
```

## 2. Get a picture on the screen

Run it by hand first — no config files, nothing permanent:

```bash
cog --platform=drm "http://signalk.local:3000/signalk-bignumbers/instrument.html?display=$(hostname)"
```

The HDMI screen should show the Pi's hostname in large text:

<img src="images/display-unconfigured.jpg" alt="The Pi's screen showing the hostname mast1 in large pale blue text on dark blue, above a line saying it isn't configured yet and to add this hostname in the webapp" width="520">

That's a display saying "I have no config yet", which means cog, the GPU
and the network path to SignalK are all working. It also tells you the
name to type into the webapp next.

`Ctrl+C` stops it. Leave it running for the next step.

## 3. Tell it what to show

The display asks SignalK for whatever config is stored under its
hostname. Nothing is stored yet, so:

1. Open `http://signalk.local:3000/signalk-bignumbers/` from any browser
   on the network, or from SignalK's Webapps menu.
2. Log in using the bar at the top. SignalK requires auth for writes even
   when reads are open, so this applies to this page only. A display
   never logs in, so if SignalK's security is on it needs **Security →
   Settings → Allow Readonly Access** enabled — the webapp warns at the
   top if it isn't.
3. **+ Add display**, enter the hostname shown on the kiosk's screen,
   pick a path and a presentation, **Save**.

![The webapp's display list, with rows for mast1 and phone showing the instruments each is displaying](images/webapp-displays.png)

Within about 5 seconds the kiosk screen should switch from its hostname
to the instrument:

<img src="images/display-mast.jpg" alt="A mast-mounted screen filled by the number 0.0, labelled STW and kt, black on white" width="520">

If it does, you're done experimenting — `Ctrl+C` and make it permanent
below.

## 4. Start it automatically at boot

**Free up tty1** so cog can take the screen from the console getty:

```bash
sudo systemctl disable getty@tty1.service
```

**Create the service** at `/etc/systemd/system/signalk-bignumbers.service`,
with the same URL you tested above. `%H` is a systemd specifier for the
hostname, so this file is identical on every Pi:

```ini
[Unit]
Description=signalk-bignumbers display
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
ExecStart=/usr/bin/cog --platform=drm "http://signalk.local:3000/signalk-bignumbers/instrument.html?display=%H"
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

**Stop the console blanking.** Append to `/boot/firmware/cmdline.txt`
(same line, space-separated, no newline):

```
consoleblank=0
```

**Enable it and reboot:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now signalk-bignumbers.service
sudo reboot
```

To check on it:

```bash
systemctl status signalk-bignumbers.service
journalctl -u signalk-bignumbers -f
systemctl show signalk-bignumbers -p ExecStart   # confirm %H expanded to the hostname
```

## Managing displays

The kiosk knows only its hostname and where the SignalK server is. It
asks for `?display=<hostname>` and takes whatever it's given, so what it
shows is managed in the webapp — see [the
README](../README.md#the-webapp) for the fields. Two consequences on a
Pi:

- **Its local config never changes again**, unless you point it at a
  different server or rename the Pi. Going from one number to three is a
  save in the webapp; restarting the service is never necessary.
- **Renaming the Pi changes its identity.** It drops back to the
  unconfigured screen until you register the new name.

Phones and tablets are in the same list, their name coming from the URL
rather than systemd, so a mixed fleet is managed from one page.

---

## Notes

### Why cog

[cog](https://github.com/Igalia/cog) is a minimal WPE WebKit browser
shell for embedded/kiosk use. Its DRM/KMS backend (`--platform=drm`)
renders directly to the framebuffer via the GPU — no X11, no Wayland
compositor, no window manager. That matters on a Zero 2 W's 512MB, and it
keeps a compositor out of the path between delta and glass.

The tradeoff: WebKit, not Chromium, with a much smaller CLI/config
surface. Fine for a self-contained instrument page; worth reconsidering
(cage + `chromium --kiosk`) if the page needed Chromium-only behavior.

The service runs as root, so DRM access needs no PAM/logind session
setup.

### Running cog by hand later

Step 2 works before the service exists. Once it's installed, stop it
first or the two fight over the display — DRM master isn't tied to which
tty your SSH session is on:

```bash
sudo systemctl stop signalk-bignumbers
```

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

Measured on a Zero 2 W (4 cores) showing one value updating a few times a
second, with GPU acceleration working:

| | |
|---|---|
| WPEWebProcess | 10% of one core |
| cog | 1% of one core |
| WPENetworkProcess | 0.5% of one core |
| load average | 0.06 |
| memory | 216MB used, 199MB available of 416MB |
| temperature | 46°C, `throttled=0x0` |

About 3% of the machine, and swap untouched. Well above that usually
means software rendering — check `/dev/dri/renderD128` exists.

### The display identifier, and `%` in unit files

`%H` works because systemd expands specifiers in `ExecStart`. That same
expansion is a trap if you put a full-parameter URL there instead of
`?display=`: **any literal `%` must be doubled**. A URL-encoded `%3A`
breaks unit parsing outright (`Failed to resolve unit specifiers`, and
the unit won't load at all) unless written `%%3A`. The doubling applies
only inside the unit file, not when running cog from a shell — which is
why step 2 needs no escaping. It bites hardest on a multi-value URL,
which repeats every per-value parameter two or three times: one missed
`%` and the unit silently won't load. `?display=` avoids it entirely.

Related: **non-ASCII characters can be mangled** if typed on an SSH
session that isn't in a UTF-8 locale, and cog then rejects the URL as
invalid UTF-8. Percent-encode them — `°` is `%C2%B0` (`%%C2%%B0` in a
unit file).

If you'd rather have an identifier that survives a rename, `%m` expands
to the machine ID — but it's 32 hex characters, unpleasant to read off a
screen and type in.
