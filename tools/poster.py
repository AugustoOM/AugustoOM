"""Generate the GitHub profile poster without network access or dependencies."""

import argparse
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element, fromstring, indent, tostring

from matrix_rain import add_rain
from svg_components import arrow, gradient, heading, label, line, node, panel, paragraph, wrapped

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/profile.json"
OUTPUT = ROOT / "assets/poster.svg"
SVG_NS = "http://www.w3.org/2000/svg"
WIDTH = 960
PANEL_X, PANEL_WIDTH = 52, 856
LEFT, RIGHT = 80, 880
GAP = 24
COLORS = ("background", "panel", "accent", "secondary", "deep", "text", "muted", "border")
CONTACT_LABELS = {"portfolio": "Sitio web", "github": "GitHub", "linkedin": "LinkedIn"}

CSS = """
svg {
  color-scheme: dark;
  font-family: ui-monospace, "Cascadia Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  background: var(--background);
}
text { fill: var(--text); }
.strong { font-weight: 700; }
.name { font-weight: 800; }
.muted { fill: var(--muted); }
.accent { fill: var(--accent); }
.panel { fill: var(--panel); stroke: var(--border); }
.card { fill: var(--background); stroke: var(--border); }
.frame, .rule { fill: none; stroke: var(--border); }
.prompt { fill: none; stroke: var(--accent); stroke-width: 1.8; }
.rain-trail { fill: url(#rain-tail); }
.rain-tip { fill: var(--accent); opacity: .58; }
.rain-column { animation: fall var(--duration) var(--phase) linear infinite; }
.boot-line { animation: boot .65s var(--delay) ease-out both; }
.cursor { animation: cursor 2.4s ease-in-out infinite; }
a:hover .link, a:focus-visible .link { text-decoration: underline; }
@keyframes fall { to { transform: translateY(var(--tile)); } }
@keyframes boot {
  from { opacity: .55; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes cursor { 50% { opacity: .28; } }
@media (prefers-reduced-motion: reduce) {
  .rain-column, .boot-line, .cursor { animation: none; }
  .rain { opacity: .34; }
}
"""


def require_text(value, field):
    if not isinstance(value, str) or not value.strip() or not value.isprintable():
        raise ValueError(f"{field} debe ser texto de una línea")


def require_items(values, field):
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field} debe ser una lista de textos")
    for value in values:
        require_text(value, field)


def https_url(value):
    if (not isinstance(value, str) or not value.isprintable()
            or any(char.isspace() or char == "\\" for char in value)):
        raise ValueError("Se esperaba una URL HTTPS pública")
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("Se esperaba una URL HTTPS pública")
    return value


def load_profile(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    for field in ("name", "github_user", "role", "studies", "location", "about"):
        require_text(data[field], field)
    if not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?", data["github_user"]):
        raise ValueError("github_user debe ser un usuario válido de GitHub")
    for group, items in data["stack"].items():
        require_text(group, "stack")
        require_items(items, group)
    projects = data["projects"]
    if not isinstance(projects, list) or len(projects) > 4:
        raise ValueError("projects admite hasta cuatro proyectos")
    for project in projects:
        require_text(project["name"], "projects.name")
        require_text(project["description"], "projects.description")
        require_items(project["technologies"], "projects.technologies")
        https_url(project["url"])
    for key in CONTACT_LABELS:
        if key == "github" or data["contact"].get(key) is not None:
            https_url(data["contact"][key])
    for key in COLORS:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", data["palette"][key]):
            raise ValueError(f"palette.{key} debe tener formato #RRGGBB")
    require_items(data["terminal"]["boot"], "terminal.boot")
    require_text(data["terminal"]["exit"], "terminal.exit")
    if any(len(value) > 56 for value in [*data["terminal"]["boot"], data["terminal"]["exit"]]):
        raise ValueError("Las líneas de terminal admiten hasta 56 caracteres")
    rain = data["rain"]
    if type(rain["seed"]) is not int or type(rain["columns"]) is not int or not 8 <= rain["columns"] <= 64:
        raise ValueError("rain requiere una semilla entera y entre 8 y 64 columnas")
    if type(rain["speed"]) not in (int, float) or not .25 <= rain["speed"] <= 3:
        raise ValueError("rain.speed admite un multiplicador entre 0.25 y 3")
    return data


def hero_symbol(parent, y):
    mark = node(parent, "g", transform=f"translate(783 {y})", aria_hidden="true")
    node(mark, "path", d="M-104 -47 v-27 l28 -28 h26 M50 -102 h26 l28 28 v27 "
         "M104 47 v27 l-28 28 h-26 M-50 102 h-26 l-28 -28 v-27",
         fill="none", stroke="var(--secondary)", opacity=".72")
    node(mark, "path", d="M-72 -49 l23 -23 h98 l23 23 v98 l-23 23 h-98 l-23 -23 Z",
         fill="var(--deep)", fill_opacity=".36", stroke="var(--deep)")
    node(mark, "path", d="M-94 0 h14 m160 0 h14 M0 -94 v14 m0 160 v14",
         fill="none", stroke="var(--secondary)", opacity=".75")
    node(mark, "path", d="M-36 -20 l24 20 -24 20 M0 22 h33", fill="none",
         stroke="var(--accent)", stroke_width="6", opacity=".74")


def hero(parent, profile, subtitle):
    y = 133
    for index, command in enumerate(profile["terminal"]["boot"]):
        command_group = node(parent, "g", cls="boot-line", style=f"--delay:{index * 180}ms")
        label(command_group, LEFT, y, ">", 21, "accent strong")
        label(command_group, LEFT + 26, y, command, 21, "muted")
        y += 28

    name_lines = wrapped(profile["name"].upper(), 615, 82)
    y += 65
    hero_symbol(parent, y - 15)
    paragraph(parent, LEFT - 3, y, name_lines, 82, 81, "name")
    y += (len(name_lines) - 1) * 81 + 48
    label(parent, LEFT, y, f"@{profile['github_user']}", 27, "accent strong")
    y += 35
    subtitle_lines = wrapped(subtitle, RIGHT - LEFT, 20)
    paragraph(parent, LEFT, y, subtitle_lines, 20, 28)
    return y + 40 + (len(subtitle_lines) - 1) * 28


def about(parent, y, profile):
    lines = wrapped(profile["about"], RIGHT - LEFT, 23)
    height = 128 + (len(lines) - 1) * 33
    panel(parent, PANEL_X, y, PANEL_WIDTH, height)
    heading(parent, LEFT, y + 46, "Sobre mí")
    paragraph(parent, LEFT, y + 88, lines, 23, 33)
    return y + height


def stack(parent, y, groups):
    content = Element("g")
    heading(content, LEFT, y + 46, "Stack tecnológico")
    y_start = y
    y += 78
    items = list(groups.items())
    for index in range(0, len(items), 2):
        row_height = 0
        for (x, right), (title, technologies) in zip(
            ((LEFT, 459), (504, RIGHT)), items[index:index + 2]
        ):
            titles = wrapped(title.upper(), right - x, 17)
            lines = [line.strip(" ·") for line in wrapped(" · ".join(technologies), right - x, 21)]
            line(content, x, y, right, y)
            paragraph(content, x, y + 25, titles, 17, 22, "accent strong")
            values_y = y + 55 + (len(titles) - 1) * 22
            paragraph(content, x, values_y, lines, 21, 27)
            row_height = max(row_height, values_y - y + (len(lines) - 1) * 27 + 24)
        y += row_height
    panel(parent, PANEL_X, y_start, PANEL_WIDTH, y + 4 - y_start)
    parent.append(content)
    return y + 4


def projects(parent, y, items):
    heading(parent, LEFT, y + 34, "Proyectos destacados")
    y += 54
    for project in items:
        name, url = project["name"], project["url"]
        titles = wrapped(name, 695, 28)
        description = wrapped(project["description"], RIGHT - LEFT, 22)
        technologies = [line.strip(" ·") for line in wrapped(" · ".join(project["technologies"]), RIGHT - LEFT, 18)]
        body_y = y + 80 + (len(titles) - 1) * 34
        tech_y = body_y + len(description) * 29 + 2
        bottom = tech_y + (len(technologies) - 1) * 24 + 24
        anchor = node(parent, "a", href=url, aria_label=name)
        panel(anchor, PANEL_X, y, PANEL_WIDTH, bottom - y, "card")
        node(anchor, "rect", x=PANEL_X, y=y + 22, width=3, height=30, fill="var(--secondary)")
        paragraph(anchor, LEFT, y + 45, titles, 28, 34, "strong link")
        arrow(anchor, RIGHT - 12, y + 32)
        paragraph(anchor, LEFT, body_y, description, 22, 29)
        paragraph(anchor, LEFT, tech_y, technologies, 18, 24, "muted")
        y = bottom + 12
    return y - 12


def activity(parent, y, github):
    panel(parent, PANEL_X, y, PANEL_WIDTH, 146)
    heading(parent, LEFT, y + 46, "Actividad en GitHub")
    label(parent, LEFT, y + 85, "Contribuciones del último año", 22)
    anchor = node(parent, "a", href=github, aria_label="Ver contribuciones en el perfil de GitHub")
    label(anchor, LEFT, y + 119, "Ver calendario en el perfil", 20, "accent link")
    arrow(anchor, LEFT + 330, y + 111)
    node(parent, "path", d=f"M765 {y + 44} h97 v62 h-97 Z M786 {y + 63} l12 11 -12 11 "
         f"M808 {y + 86} h27", fill="none", stroke="var(--secondary)", opacity=".82",
         aria_hidden="true")
    return y + 146


def contact(parent, y, profile):
    content = Element("g")
    heading(content, LEFT, y + 44, "Contacto")
    line(content, LEFT, y + 59, RIGHT, y + 59)
    x, baseline = LEFT, y + 91
    for key, name in CONTACT_LABELS.items():
        url = profile["contact"].get(key)
        if url:
            caption = f"GitHub / @{profile['github_user']}" if key == "github" else name
            advance = round(len(caption) * 20 * .64)
            if x + advance + 20 > RIGHT:
                x, baseline = LEFT, baseline + 32
            anchor = node(content, "a", href=url, aria_label=name)
            label(anchor, x, baseline, caption, 20, "link")
            arrow(anchor, x + advance + 13, baseline - 7)
            x += advance + 54
    panel(parent, PANEL_X, y, PANEL_WIDTH, baseline + 25 - y)
    parent.append(content)
    return baseline + 25


def backdrop(root, defs, height):
    gradient(defs, "hero-ambient", [
        ("0%", "var(--deep)", .47), ("100%", "var(--deep)", 0)
    ], x1="100%", y1="0%", x2="38%", y2="100%")
    grid = node(defs, "pattern", id="grid", width=32, height=32, patternUnits="userSpaceOnUse")
    node(grid, "path", d="M32 0 H0 V32", fill="none", stroke="var(--border)", opacity=".48")
    node(root, "rect", width=WIDTH, height=height, fill="var(--background)")
    node(root, "rect", x=25, y=25, width=910, height=490, fill="url(#hero-ambient)")
    node(root, "rect", x=634, y=90, width=301, height=301, fill="url(#grid)")


def chrome(parent, height, username, exit_text):
    panel(parent, 24, 24, WIDTH - 48, height - 48, "frame")
    node(parent, "path", d="M24 68 V24 h73 M936 67 V40 l-16 -16 h-32",
         fill="none", stroke="var(--secondary)", stroke_width="2")
    line(parent, 25, 89, 935, 89)
    line(parent, 40, 106, 40, height - 47)
    node(parent, "path", d="M54 50 l8 7 -8 7 m14 0 h10", cls="prompt")
    label(parent, 91, 65, f"{username}@github:~", 21, "strong")
    label(parent, 908, 65, "~/profile", 18, "muted", text_anchor="end")
    footer_y = height - 49
    label(parent, LEFT, footer_y, ">", 21, "accent strong")
    label(parent, LEFT + 26, footer_y, exit_text, 21, "muted")
    x = LEFT + 29 + round(len(exit_text) * 13.5)
    node(parent, "rect", x=x, y=footer_y - 13, width=10, height=14, cls="cursor", fill="var(--accent)")


def render(profile):
    name, username = profile["name"], profile["github_user"]
    subtitle = " · ".join(profile[key] for key in ("role", "studies", "location"))
    content = Element("g")
    y = hero(content, profile, subtitle)
    y = about(content, y, profile)
    if profile["stack"]:
        y = stack(content, y + GAP, profile["stack"])
    if profile["projects"]:
        y = projects(content, y + GAP, profile["projects"])
    y = activity(content, y + GAP, profile["contact"]["github"])
    y = contact(content, y + GAP, profile)
    height = y + 85

    root = Element("svg", {
        "xmlns": SVG_NS, "xml:lang": "es", "width": str(WIDTH), "height": str(height),
        "viewBox": f"0 0 {WIDTH} {height}", "role": "img",
        "aria-label": f"Perfil de {name} (@{username})", "aria-describedby": "poster-description",
    })
    node(root, "title", f"{name} · @{username}")
    node(root, "desc", f"{subtitle}. Presentación, tecnologías, proyectos, actividad y contacto "
         "en una terminal oscura con lluvia roja.", id="poster-description")
    palette = " ".join(f"--{key}: {profile['palette'][key]};" for key in COLORS)
    node(root, "style", f"\n:root {{ {palette} }}{CSS}")
    defs = node(root, "defs")
    backdrop(root, defs, height)
    add_rain(root, defs, WIDTH, height, profile["rain"])
    chrome(root, height, username, profile["terminal"]["exit"])
    root.append(content)
    indent(root, space="  ")
    return tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        svg = render(load_profile(args.config))
        fromstring(svg)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=args.output.parent) as directory:
            temporary = Path(directory) / "poster.svg"
            temporary.write_bytes(svg)
            temporary.replace(args.output)
    except (OSError, KeyError, TypeError, AttributeError, ValueError, SyntaxError) as error:
        parser.exit(1, f"No se pudo generar el póster: {error}\n")
    print(f"Póster generado: {args.output} ({len(svg):,} bytes)")


if __name__ == "__main__":
    main()
