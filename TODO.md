# TODO

Known gaps, deliberately left for now.

- **A negative duration shows no sign.** `formatDuration()` takes the
  absolute value and no time presentation sets `neg`, so a start timer
  (`navigation.racing.timeToStart`) that goes negative after the gun reads
  10 s after the same as 10 s to go. Matters only for sources that count
  past zero.
- **Saving from the editor drops hand-written conversion keys.**
  `slotConfig()` writes path, field, name, format and colours only, so a
  stored config's own `factor`/`offset`/`unit`/`layout`/`neg`/`wrap` are
  lost on the next save. Those keys still work in direct URLs.
