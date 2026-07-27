#!/usr/bin/env python3
"""Dummy SignalK server for pressure/load testing instrument.html.

Speaks just enough of the SignalK delta protocol (hello message, subscribe
handling, delta updates) to drive the instrument display, but instead of
real sensor data it sweeps one path back and forth through a fixed range at
a fixed rate -- useful for stress-testing rendering (digit ghosting, sign
flips, stale/reconnect handling) independent of the boat.

All currently connected clients are broadcast the same synchronized value,
so you can open many instrument.html tabs/processes at once to pressure-test
concurrent connections.

Examples:
  # Apparent wind speed, 0-15 m/s triangle wave, 10 updates/sec
  ./dummy_signalk.py --path environment.wind.speedApparent --min 0 --max 15 --step 0.1 --rate 10

  # Roll, sweeping -0.5..0.5 rad inside navigation.attitude, 20 updates/sec
  ./dummy_signalk.py --path navigation.attitude --field roll --min -0.5 --max 0.5 --step 0.02 --rate 20

Then point instrument.html at it with ?host=localhost:PORT
"""
import argparse
import asyncio
import itertools
import json
import time

import websockets


def triangle_wave(min_v, max_v, step):
    value = min_v
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


def build_delta(path, field, value):
    payload_value = {field: value} if field else value
    return json.dumps({
        "context": "vessels.self",
        "updates": [{
            "source": {"label": "dummy"},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "values": [{"path": path, "value": payload_value}],
        }],
    })


async def broadcaster(clients, args):
    wave = triangle_wave(args.min, args.max, args.step)
    interval = 1 / args.rate
    for value in wave:
        if clients:
            websockets.broadcast(clients, build_delta(args.path, args.field, round(value, 6)))
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


async def main(args):
    clients = set()
    async with websockets.serve(lambda ws: handler(ws, clients), args.bind, args.port):
        print(f"dummy SignalK serving {args.path!r} on ws://{args.bind}:{args.port}/signalk/v1/stream")
        print(f"sweeping {args.min}..{args.max} step {args.step} at {args.rate}/s")
        await broadcaster(clients, args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--path", default="environment.wind.speedApparent", help="SignalK path to emit")
    parser.add_argument("--field", default=None, help="wrap the value in {field: value} to simulate compound paths like navigation.attitude")
    parser.add_argument("--min", type=float, default=0, help="sweep range minimum")
    parser.add_argument("--max", type=float, default=15, help="sweep range maximum")
    parser.add_argument("--step", type=float, default=0.1, help="amount to move per update")
    parser.add_argument("--rate", type=float, default=10, help="updates per second")
    parser.add_argument("--port", type=int, default=3001, help="port to listen on")
    parser.add_argument("--bind", default="0.0.0.0", help="address to bind")
    args = parser.parse_args()
    asyncio.run(main(args))
