"""Deterministic Matrix rain with vertically tiled streams."""

from math import ceil
from random import Random

from svg_components import gradient, label, node

GLYPHS = "01ABCDEFHKNPRSTVX+*#<>:/"
TILE = 480


def add_rain(root, defs, width, height, settings):
    rng = Random(settings["seed"])
    columns = settings["columns"]
    gradient(defs, "rain-tail", [
        ("0%", "var(--secondary)", 0.13),
        ("65%", "var(--secondary)", 0.65),
        ("100%", "var(--accent)", 0.85),
    ], x1="0%", y1="0%", x2="0%", y2="100%")
    for axis, stops, vector in (
        ("side", [("0%", .8), ("9%", 1), ("34%", .18),
                  ("63%", .24), ("90%", .95), ("100%", .85)], ("100%", "0%")),
        ("end", [("0%", .2), ("7%", 1), ("74%", .75),
                 ("100%", .12)], ("0%", "100%")),
    ):
        gradient(defs, f"rain-{axis}-fade", [
            (offset, "#fff", opacity) for offset, opacity in stops
        ], x1="0%", y1="0%", x2=vector[0], y2=vector[1])
        mask = node(defs, "mask", id=f"rain-{axis}-mask", maskUnits="userSpaceOnUse",
                    x=0, y=0, width=width, height=height)
        node(mask, "rect", x=0, y=0, width=width, height=height,
             fill=f"url(#rain-{axis}-fade)")
    outer = node(root, "g", cls="rain", mask="url(#rain-side-mask)", aria_hidden="true")
    layer = node(outer, "g", mask="url(#rain-end-mask)")

    for index in range(columns):
        x = round(width * (index + .5) / columns + (rng.random() - .5) * 6)
        identifier = f"stream-{index}"
        stream = node(defs, "g", id=identifier)
        start = round(rng.random() * 245)
        count = 6 + int(rng.random() * 8)
        gap = 15 + int(rng.random() * 4)
        glyphs = "".join(GLYPHS[int(rng.random() * len(GLYPHS))] for _ in range(count))
        label(stream, " ".join([str(x)] * count), start, glyphs, 15, "rain-trail",
              dy="0 " + " ".join([str(gap)] * (count - 1)))
        label(stream, x, start + count * gap, glyphs[-1], 15, "rain-tip")

        duration = (14 + rng.random() * 23) / settings["speed"]
        phase = -duration * rng.random()
        opacity = .25 + rng.random() * .42
        column = node(layer, "g", cls="rain-column", opacity=f"{opacity:.3f}",
                      style=f"--duration:{duration:.3f}s;--phase:{phase:.3f}s;--tile:{TILE}px")
        # Adjacent copies cross the viewport together, so resetting by one tile is seamless.
        for tile in range(-2, ceil(height / TILE) + 1):
            node(column, "use", href=f"#{identifier}", y=tile * TILE)
