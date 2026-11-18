"""Small SVG primitives shared by the poster and its backgrounds."""

from textwrap import wrap
from xml.etree.ElementTree import SubElement


def node(parent, tag, value=None, **attributes):
    element = SubElement(parent, tag, {
        ("class" if key == "cls" else key.replace("_", "-")): str(item)
        for key, item in attributes.items()
    })
    element.text = value
    return element


def label(parent, x, y, value, size, cls="", **attributes):
    return node(parent, "text", value, x=x, y=y, font_size=size, cls=cls, **attributes)


def line(parent, x1, y1, x2, y2, cls="rule"):
    return node(parent, "line", x1=x1, y1=y1, x2=x2, y2=y2, cls=cls)


def gradient(parent, identifier, stops, **attributes):
    element = node(parent, "linearGradient", id=identifier, **attributes)
    for offset, color, opacity in stops:
        node(element, "stop", offset=offset, stop_color=color, stop_opacity=opacity)
    return element


def wrapped(value, width, size):
    # Reserve a little more than the nominal 0.6 em advance of the system monospace fonts.
    return wrap(value, max(1, int(width / (size * 0.64))))


def paragraph(parent, x, y, lines, size, leading, cls=""):
    for index, value in enumerate(lines):
        label(parent, x, y + index * leading, value, size, cls)


def panel(parent, x, y, width, height, cls="panel"):
    right, bottom = x + width, y + height
    return node(parent, "path", cls=cls, d=(
        f"M{x} {y} H{right - 16} L{right} {y + 16} V{bottom} H{x} Z"
    ))


def heading(parent, x, y, title):
    node(parent, "path", d=f"M{x} {y - 15} l8 7 -8 7", cls="prompt")
    label(parent, x + 25, y, title, 27, "strong")


def arrow(parent, x, y):
    node(parent, "path", d=f"M{x - 6} {y + 6} l12 -12 m-10 0 h10 v10", cls="prompt")
