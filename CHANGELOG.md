# Changelog

## 0.0.15 — 2026-09-25

- A display can show four values, up from three. On a landscape screen
  the four sit two by two, left to right then down, which reads larger
  than three stacked; a portrait screen stacks them. Nothing changes for
  a display showing one, two or three.

## 0.0.14 — 2026-09-22

- Every entry in the Presentation dropdown shows its digit template —
  `Knots — xx.x`, `Amps — ±xxx.x` — so you can see how wide a number
  will be, and whether it has room for a minus sign, before you pick it.
- README explains more plainly what the display is for and why.

## 0.0.13 — 2026-09-20

- **Preview** on each row of the display list opens that display exactly
  as the screen on the boat shows it, from its saved config.

## 0.0.12 — 2026-09-17

- New themes chosen for sun and night vision. Day themes are black
  digits on a bright background, nine to choose from. Night red lights
  only the red sub-pixel, and a dim red joins it for screens that can't
  turn their backlight down. Green and cyan on black are gone; a display
  saved with a retired colour moves to its replacement on its next save.
- A reading too big for its presentation shows `^^.^` instead of a
  clipped number — 140.2 m on an `xx.x` depth used to read as 40.2.
- A display no longer shows "not configured" while SignalK is
  restarting, and one that boots before SignalK keeps retrying.
- Saving no longer recolours a display whose colours aren't in the list;
  they're kept as Custom.

## 0.0.11 — 2026-09-17

- The unit moves into the label, `STW (kt)`, giving its width back to
  the digits. Labels are brighter for contrast in sun.

## 0.0.10 — 2026-09-06

- The editor outlines each missing field and names it — "Value 2 needs
  a presentation." — instead of one general message. Preview checks too.
- A display name must be letters, digits, dots and hyphens, so it can
  match a Pi's hostname.

## 0.0.9 — 2026-09-03

Documentation only. Tagged but never published to npm.

## 0.0.8 — 2026-09-03

- Configure a value by picking a **path** and a **presentation** from two
  dropdowns, replacing the fixed list of presets. The path list is read
  live from your server, so it's exactly what your boat reports.
- New presentations: durations (HH:MM:SS) and a local-time clock.
- Existing displays and URLs show exactly what they did before.

## 0.0.7 — 2026-07-30

- Version bump only.

## 0.0.6 — 2026-07-30

- First release on the SignalK Appstore.
- A wind angle sent as 0–360 is folded back to ±180.
- A display says when SignalK refuses anonymous reads, instead of
  showing nothing.

## 0.0.5 — 2026-07-27

- Security fixes: the webapp can no longer be pointed at another server
  to capture your SignalK login, and display colours accept hex only.
  Update if you're on 0.0.4 or earlier.

## 0.0.4 — 2026-07-27

- One, two or three values per display, each with its own colours.

## 0.0.3 — 2026-07-27

- Fixed high-contrast colour choices per display.
- Displays are named by the Pi's hostname.

## 0.0.2 — 2026-07-27

- Displays fetch their config from SignalK and pick up changes within
  seconds, with no restart. The webapp manages the list of displays.

## 0.0.1 — 2026-07-27

- First release: one big number from a SignalK path, sized to fill the
  screen.
