#!/usr/bin/env python3
"""Dummy SignalK server for pressure/load testing instrument.html.

Speaks just enough of the SignalK delta protocol (hello message, subscribe
handling, delta updates) to drive the instrument display, but instead of
real sensor data it sweeps each path back and forth through a fixed range at
a fixed rate -- useful for stress-testing rendering (digit ghosting, sign
flips, stale/reconnect handling) independent of the boat.

All currently connected clients are broadcast the same synchronized values,
so you can open many instrument.html tabs/processes at once to pressure-test
concurrent connections.

Examples:
  # Apparent wind speed, 0-15 m/s triangle wave, 10 updates/sec
  ./dummy_signalk.py --path environment.wind.speedApparent --min 0 --max 15 --step 0.1 --rate 10

  # Roll, sweeping -0.5..0.5 rad inside navigation.attitude, 20 updates/sec
  ./dummy_signalk.py --path navigation.attitude --field roll --min -0.5 --max 0.5 --step 0.02 --rate 20

  # Three paths at once, to drive a multi-value display. --field is matched
  # to --path by position, so pass an empty one to skip a path:
  ./dummy_signalk.py --path environment.wind.speedApparent \\
                     --path environment.depth.belowTransducer \\
                     --path navigation.attitude --field "" --field "" --field roll

Every path shares one sweep range but starts at a different point in it, so
the numbers on a multi-value display are visibly independent.

Then point instrument.html at it with ?host=localhost:PORT
"""
import argparse
import asyncio
import json
import time

import websockets


def triangle_wave(min_v, max_v, step, start):
    value = start
    direction = 1
    while True:
        yield value
        value += direction * step
        if value >= max_v:
            value = max_v
            direction = -1
        elif value <= min_v:
            value = min_v
            direction = 1


def build_delta(signals, values):
    # One delta carrying every path. Two signals may share a path with
    # different fields (roll and pitch of navigation.attitude); each gets its
    # own entry, and the display ignores the field it isn't watching.
    return json.dumps({
        "context": "vessels.self",
        "updates": [{
            "source": {"label": "dummy"},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "values": [
                {"path": path, "value": {field: value} if field else value}
                for (path, field), value in zip(signals, values)
            ],
        }],
    })


async def broadcaster(clients, signals, args):
    span = args.max - args.min
    waves = [
        triangle_wave(args.min, args.max, args.step, args.min + span * i / len(signals))
        for i in range(len(signals))
    ]
    interval = 1 / args.rate
    while True:
        values = [round(next(wave), 6) for wave in waves]
        if clients:
            websockets.broadcast(clients, build_delta(signals, values))
        await asyncio.sleep(interval)


async def handler(websocket, clients):
    clients.add(websocket)
    print(f"client connected ({len(clients)} total)")
    hello = {
        "name": "dummy-signalk",
        "version": "0.0.1",
        "self": "vessels.self",
        "roles": ["master", "main"],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
    }
    await websocket.send(json.dumps(hello))
    try:
        async for _ in websocket:
            pass  # ignore subscribe messages -- everyone gets the same broadcast
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.discard(websocket)
        print(f"client disconnected ({len(clients)} total)")


def signals_from(args):
    """Pair up --path and --field by position, padding missing fields."""
    paths = args.path or ["environment.wind.speedApparent"]
    fields = list(args.field or [])
    fields += [None] * (len(paths) - len(fields))
    return [(path, field or None) for path, field in zip(paths, fields)]


async def main(args):
    clients = set()
    signals = signals_from(args)
    async with websockets.serve(lambda ws: handler(ws, clients), args.bind, args.port):
        print(f"dummy SignalK on ws://{args.bind}:{args.port}/signalk/v1/stream")
        for path, field in signals:
            print(f"  serving {path}{'.' + field if field else ''}")
        print(f"sweeping {args.min}..{args.max} step {args.step} at {args.rate}/s")
        await broadcaster(clients, signals, args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--path", action="append", help="SignalK path to emit; repeat for a multi-value display (default: environment.wind.speedApparent)")
    parser.add_argument("--field", action="append", help="wrap the value in {field: value} to simulate compound paths like navigation.attitude; matched to --path by position")
    parser.add_argument("--min", type=float, default=0, help="sweep range minimum")
    parser.add_argument("--max", type=float, default=15, help="sweep range maximum")
    parser.add_argument("--step", type=float, default=0.1, help="amount to move per update")
    parser.add_argument("--rate", type=float, default=10, help="updates per second")
    parser.add_argument("--port", type=int, default=3001, help="port to listen on")
    parser.add_argument("--bind", default="0.0.0.0", help="address to bind")
    args = parser.parse_args()
    asyncio.run(main(args))
