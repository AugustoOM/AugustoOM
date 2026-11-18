"""Validate the poster XML, profile content, asset size and README links."""

import argparse
import re
from pathlib import Path
from xml.etree.ElementTree import fromstring

from poster import CONFIG, CONTACT_LABELS, OUTPUT, ROOT, SVG_NS, https_url, load_profile

MAX_BYTES = 500_000
LINK = re.compile(r"\]\((https://[^)\s]+)\)|<a\b[^>]*\bhref=\"(https://[^\"]+)\"")
IMAGE = re.compile(r'<img\b(?=[^>]*\bsrc="assets/poster\.svg")(?=[^>]*\balt="[^"]+")[^>]*>')
FORBIDDEN = {"script", "foreignObject", "image", "iframe"}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def validate(path, profile, readme_path):
    data = path.read_bytes()
    check(len(data) < MAX_BYTES, f"El SVG debe pesar menos de {MAX_BYTES:,} bytes")
    check(not re.search(br"<!\s*(?:DOCTYPE|ENTITY)", data, re.I), "El SVG debe ser autocontenido")
    svg = fromstring(data)
    ns = f"{{{SVG_NS}}}"
    check(svg.tag == ns + "svg", "Se esperaba un elemento raíz SVG")
    width, height = int(svg.attrib["width"]), int(svg.attrib["height"])
    check(width == 960 and height > 0 and svg.get("viewBox") == f"0 0 {width} {height}",
          "El tamaño y el viewBox deben coincidir")
    description = svg.find(ns + "desc")
    check(svg.get("role") == "img" and svg.get("aria-label") and svg.findtext(ns + "title")
          and description is not None and description.text
          and svg.get("aria-describedby") == description.get("id"),
          "Faltan datos de accesibilidad en el SVG")
    css = svg.findtext(ns + "style", "")
    for expected in ("@keyframes fall", "@keyframes boot", "@keyframes cursor",
                     "(prefers-reduced-motion: reduce)"):
        check(expected in css, f"Falta {expected} en el CSS")
    check(not re.search(r"@import", css, re.I),
          "El CSS no debe cargar recursos externos")

    ids = {element.get("id") for element in svg.iter() if element.get("id")}
    internal_urls = re.compile(r"url\(\s*['\"]?([^'\")\s]+)", re.I)
    for target in internal_urls.findall(css):
        check(target.startswith("#") and target[1:] in ids, f"Referencia SVG no válida: {target}")
    links = set()
    for element in svg.iter():
        tag = element.tag.removeprefix(ns)
        check(tag not in FORBIDDEN, f"Elemento no permitido: {tag}")
        for attr, value in element.attrib.items():
            name = attr.rsplit("}", 1)[-1]
            check(not name.lower().startswith("on"), f"Atributo no permitido: {name}")
            for target in internal_urls.findall(value):
                check(target.startswith("#") and target[1:] in ids, f"Referencia SVG no válida: {target}")
            if name == "href":
                if tag == "a":
                    links.add(https_url(value))
                else:
                    check(value.startswith("#") and value[1:] in ids,
                          f"Referencia SVG no válida: {value}")

    def compact(value):
        return "".join(value.split())

    visible = compact(" ".join(element.text or "" for element in svg.iter(ns + "text")))
    expected_text = [
        profile["name"].upper(), f"@{profile['github_user']}", profile["about"],
        " · ".join(profile[key] for key in ("role", "studies", "location")),
        "Actividad en GitHub", "Contribuciones del último año", "Contacto",
        *profile["terminal"]["boot"], profile["terminal"]["exit"],
    ]
    if profile["stack"]:
        expected_text.append("Stack tecnológico")
    if profile["projects"]:
        expected_text.append("Proyectos destacados")
    for group, technologies in profile["stack"].items():
        expected_text.extend([group.upper(), *technologies])
    for project in profile["projects"]:
        expected_text.extend([project["name"], project["description"], *project["technologies"]])
    for value in expected_text:
        check(compact(value) in visible, f"Falta texto en el póster: {value}")
    columns = [group for group in svg.iter(ns + "g") if group.get("class") == "rain-column"]
    check(len(columns) == profile["rain"]["columns"], "La densidad de lluvia no coincide con la configuración")
    check(len({column.attrib["style"].split(";")[0] for column in columns}) > 1,
          "Las columnas de lluvia deben variar en velocidad")

    configured_links = {project["url"] for project in profile["projects"]}
    configured_links.update(profile["contact"][key] for key in CONTACT_LABELS if profile["contact"].get(key))
    check(links == configured_links, "Los enlaces del SVG no coinciden con la configuración")
    if readme_path is not None:
        readme = readme_path.read_text(encoding="utf-8")
        check(IMAGE.search(readme), "El README debe mostrar assets/poster.svg con texto alternativo")
        readme_links = {markdown or html for markdown, html in LINK.findall(readme)}
        check(configured_links <= readme_links,
              "El README debe enlazar a los contactos y proyectos configurados fuera de la imagen")
    return len(data), width, height


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", type=Path, default=OUTPUT, nargs="?")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--readme", type=Path)
    args = parser.parse_args()
    config = args.config or CONFIG
    readme = args.readme or (ROOT / "README.md" if config.resolve() == CONFIG else None)
    try:
        size, width, height = validate(args.svg, load_profile(config), readme)
    except (OSError, KeyError, TypeError, AttributeError, ValueError, SyntaxError) as error:
        parser.exit(1, f"Póster inválido: {error}\n")
    print(f"Póster válido: {width} × {height} px, {size:,} bytes")


if __name__ == "__main__":
    main()
