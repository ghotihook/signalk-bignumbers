// Presentations: how a SignalK value is turned into what the glass shows.
// Shared by index.html (which builds the Presentation dropdown from this)
// and instrument.html (which resolves a stored `format` slug through it),
// so the two can never disagree about what "temp-c" means.
//
// SignalK values are SI, so every presentation is a conversion plus a
// shape: scaled = raw * factor + offset, rendered into `layout`.
//   factor  multiplier, default 1
//   offset  added after scaling, default 0
//   layout  digit mask -- "xx.x" is 2 integer digits and 1 decimal;
//           "hh:mm:ss" is a time mask
//   neg     reserve a sign column, so a minus never shifts the digits
//   wrap    fold 0..360 back to -180..180
//   mode    "number" (default), "duration" (a count of seconds) or
//           "clock" (a timestamp, shown in local time)
const FORMATS = [
  { id: "angle-180", group: "Angle", name: "±180° — wind angle", factor: 57.29577951308232, unit: "°", layout: "xxx", neg: true, wrap: true },
  { id: "angle-360", group: "Angle", name: "0–360° — heading, course, direction", factor: 57.29577951308232, unit: "°", layout: "xxx" },
  { id: "angle-small", group: "Angle", name: "±99° — heel, trim, rudder", factor: 57.29577951308232, unit: "°", layout: "xx", neg: true },

  { id: "speed-kn", group: "Speed", name: "Knots — xx.x", factor: 1.9438444924406, unit: "kt", layout: "xx.x" },
  { id: "speed-kn-2", group: "Speed", name: "Knots — xx.xx", factor: 1.9438444924406, unit: "kt", layout: "xx.xx" },
  { id: "speed-kmh", group: "Speed", name: "Kilometres per hour", factor: 3.6, unit: "km/h", layout: "xxx" },
  { id: "speed-ms", group: "Speed", name: "Metres per second", unit: "m/s", layout: "xx.x" },

  { id: "depth-m", group: "Depth", name: "Metres — xx.x", unit: "m", layout: "xx.x" },
  { id: "depth-ft", group: "Depth", name: "Feet", factor: 3.280839895013123, unit: "ft", layout: "xxx" },

  { id: "dist-nm", group: "Distance", name: "Nautical miles — xxx.x (trip)", factor: 0.0005399568034557235, unit: "nm", layout: "xxx.x" },
  { id: "dist-nm-long", group: "Distance", name: "Nautical miles — xxxxx.x (log)", factor: 0.0005399568034557235, unit: "nm", layout: "xxxxx.x" },
  { id: "dist-m", group: "Distance", name: "Metres", unit: "m", layout: "xxxx" },

  { id: "temp-c", group: "Temperature", name: "Celsius", offset: -273.15, unit: "°C", layout: "xx.x", neg: true },
  { id: "temp-f", group: "Temperature", name: "Fahrenheit", factor: 1.8, offset: -459.67, unit: "°F", layout: "xxx", neg: true },

  { id: "dur-hms", group: "Time", name: "Duration — HH:MM:SS", layout: "hh:mm:ss", mode: "duration" },
  { id: "dur-ms", group: "Time", name: "Duration — MM:SS", layout: "mm:ss", mode: "duration" },
  { id: "dur-hm", group: "Time", name: "Duration — HH:MM", layout: "hh:mm", mode: "duration" },
  { id: "clock-hms", group: "Time", name: "Clock — HH:MM:SS (local)", layout: "hh:mm:ss", mode: "clock" },
  { id: "clock-hm", group: "Time", name: "Clock — HH:MM (local)", layout: "hh:mm", mode: "clock" },

  { id: "volts", group: "Electrical", name: "Volts", unit: "V", layout: "xx.x" },
  { id: "amps", group: "Electrical", name: "Amps — signed", unit: "A", layout: "xxx.x", neg: true },
  { id: "watts", group: "Electrical", name: "Watts", unit: "W", layout: "xxxx" },
  { id: "percent", group: "Electrical", name: "Percent", factor: 100, unit: "%", layout: "xxx" },

  { id: "pressure-hpa", group: "Other", name: "Pressure — hPa", factor: 0.01, unit: "hPa", layout: "xxxx" },
  { id: "rpm", group: "Other", name: "Engine — RPM", factor: 60, unit: "rpm", layout: "xxxx" },
  { id: "volume-l", group: "Other", name: "Litres", factor: 1000, unit: "L", layout: "xxx" },

  { id: "count", group: "Number", name: "Count — up to 99", layout: "xx" },
  { id: "num-0", group: "Number", name: "Whole number — up to 9999", layout: "xxxx" },
  { id: "num-1", group: "Number", name: "1 decimal", layout: "xxx.x" },
  { id: "num-2", group: "Number", name: "2 decimals", layout: "xx.xx" },
  { id: "num-1-neg", group: "Number", name: "1 decimal, signed", layout: "xxx.x", neg: true },
];

const FORMAT_BY_ID = Object.fromEntries(FORMATS.map((f) => [f.id, f]));
