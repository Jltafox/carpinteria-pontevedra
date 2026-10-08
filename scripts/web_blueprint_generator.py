"""
web-blueprint-generator · plano de la web de captación a partir de las hipótesis del pattern aggregator.

Implementa 03-skills/web-blueprint-generator/SKILL.md del repo "Clase 1 · Agentes IA para SEO y webs
hiperoptimizadas" (YinyangSEO Academy). Este script es la fuente única de servicios, zonas y enlazado: escribe
url-map.yaml, internal-linking.yaml, schema-templates/*.jsonld y lighthouse-budget.json en blueprint/<negocio>/ y
valida (1) el JSON-LD contra el vocabulario oficial de schema.org, (2) que todo queda a ≤ 3 clics de la home y
(3) que ninguna zona enlazada cae fuera de la cobertura del briefing. Las plantillas de página se redactan a mano.

Uso:
    py scripts/web_blueprint_generator.py
    py scripts/web_blueprint_generator.py --no-validate     # sin descargar el vocabulario de schema.org
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path
from urllib.request import Request, urlopen

from local_pack_multi_city import ROOT

OUT = ROOT / "blueprint" / "carpinteria-pontevedra"
MAX_SERVICE_AREA = 30  # regla de la skill: avisar si las combinaciones servicio × zona superan el límite
VOCAB_URL = "https://schema.org/version/latest/schemaorg-current-https.jsonld"

# ── Cobertura (briefing de Fervenza Mobiliario) ──────────────────────────────────
COVERAGE = ["A Estrada", "Boqueixón", "Vedra", "Rois", "Brión", "Teo", "Santiago de Compostela", "Ames", "Oroso",
            "Cuntis", "Forcarei", "Cerdedo-Cotobade", "Caldas de Reis", "Campo Lameiro", "Moraña", "Portas",
            "Pontevedra", "Valga", "Pontecesures", "Padrón", "Dodro", "Catoira", "Vilagarcía de Arousa", "Ribadumia",
            "Meis", "Vilanova de Arousa", "Boiro", "A Illa de Arousa", "Cambados", "Meaño", "Vilaboa", "O Grove",
            "Sanxenxo", "Ribeira", "Silleda", "Vila de Cruces", "Dozón", "Lalín"]
EXCLUDED = ["O Pino", "Trazo", "Negreira", "Frades", "Arzúa", "Ordes", "Melide", "A Lama", "Poio", "Ponte Caldelas",
            "Marín", "Soutomaior", "Pazos de Borbén", "Redondela", "Rianxo"]

# ── Servicios (líneas del KW research; volúmenes/mes de la zona) ─────────────────
SERVICES = [
    {"slug": "cocinas-a-medida", "name": "Cocinas a medida", "gbp_category": "Tienda de muebles de cocina",
     "service_type": "Diseño, fabricación y montaje de cocinas a medida",
     "subservices": ["Diseño de cocina con render 3D", "Fabricación de muebles de cocina en taller propio",
                     "Encimeras de porcelánico, granito y Silestone", "Electrodomésticos de varias marcas",
                     "Reforma de cocina (parte de carpintería)", "Montaje por equipo propio"],
     "keywords": {"diseño de cocina": 50, "diseño cocinas": 30, "cocina a medida": 20, "muebles de cocina a medida": 20,
                  "muebles de cocina en pontevedra": 20, "muebles de cocina en santiago de compostela": 20,
                  "encimeras de cocina en pontevedra": 10, "precio reforma integral cocina": 10,
                  "presupuesto para cocina nueva": 10},
     "related": ["armarios-a-medida", "muebles-a-medida"], "zones": ["pontevedra", "santiago-de-compostela"]},
    {"slug": "armarios-a-medida", "name": "Armarios y vestidores a medida", "gbp_category": "Tienda de armarios",
     "service_type": "Fabricación e instalación de armarios empotrados y vestidores a medida",
     "subservices": ["Armarios empotrados", "Vestidores", "Frentes e interiores de armario", "Despensas a medida",
                     "Huecos irregulares y bajo cubierta"],
     "keywords": {"armarios medida": 50, "armarios empotrados a medida": 20, "precio armario empotrado por m2": 10,
                  "vestidor a medida precio": 10, "presupuesto armarios a medida": 10},
     "related": ["muebles-a-medida", "cocinas-a-medida"], "zones": ["pontevedra", "santiago-de-compostela"]},
    {"slug": "muebles-a-medida", "name": "Muebles a medida", "gbp_category": "Fábrica de muebles",
     "service_type": "Diseño y fabricación de muebles de madera a medida",
     "subservices": ["Muebles de salón y librerías", "Dormitorios juveniles e infantiles", "Muebles de baño a medida",
                     "Recibidores y zapateros", "Mobiliario para locales"],
     "keywords": {"a medida carpintería": 50, "muebles a medida": 30, "muebles de baño a medida": 10,
                  "muebles juveniles a medida": 10, "muebles a medida precios": 10},
     "related": ["armarios-a-medida", "cocinas-a-medida"], "zones": ["pontevedra", "santiago-de-compostela"]},
    {"slug": "rehabilitacion-de-madera", "name": "Rehabilitación de madera en viviendas",
     "gbp_category": "Carpintería", "service_type": "Rehabilitación de tejados, estructuras, vigas y forjados de madera",
     "subservices": ["Tejados y cubiertas de madera", "Armazones y estructuras de madera", "Vigas de madera",
                     "Forjados de madera", "Refuerzo y sustitución de piezas dañadas"],
     "keywords": {"reformas viviendas madera": 90, "reformas carpinteria madera": 90, "reformas madera sanxenxo": 60,
                  "rehabilitacion forjado madera": 30, "rehabilitacion de forjados de madera": 20,
                  "rehabilitacion estructura madera": 10, "rehabilitacion de tejados y cubiertas de madera": 10},
     "related": ["carpinteria-exterior", "suelos-de-madera"], "zones": ["pontevedra", "santiago-de-compostela", "sanxenxo"]},
    {"slug": "carpinteria-exterior", "name": "Carpintería exterior de madera", "gbp_category": "Fábrica de puertas",
     "service_type": "Porches, pérgolas, cobertizos y puertas exteriores de madera",
     "subservices": ["Porches de madera a medida", "Pérgolas", "Cobertizos de madera", "Puertas exteriores de madera",
                     "Muebles de exterior a medida"],
     "keywords": {"porche de madera a medida": 10, "porche a medida": 10, "cuanto cuesta un porche de madera": 10,
                  "cobertizo madera exterior": 10, "muebles exterior a medida": 10},
     "related": ["rehabilitacion-de-madera", "muebles-a-medida"], "zones": ["pontevedra", "santiago-de-compostela"]},
    {"slug": "suelos-de-madera", "name": "Suelos de madera", "gbp_category": "Servicio de instalación de suelos de madera",
     "service_type": "Instalación, pulido y barnizado de suelos de madera",
     "subservices": ["Tarima de madera", "Parquet", "Pulido y barnizado", "Escaleras y rodapiés"],
     "keywords": {"suelos de madera en pontevedra": 0, "suelos de madera en santiago de compostela": 0},
     "related": ["rehabilitacion-de-madera", "muebles-a-medida"], "zones": []},  # sin demanda local: solo pilar
]

# ── Zonas ────────────────────────────────────────────────────────────────────────
ZONES = {
    "pontevedra": {"name": "Pontevedra", "province": "Pontevedra", "phase": 1, "hub": False,  # la home hace de hub
                   "searches": 796, "gbp_listing": "probable primera ficha",
                   "areas": ["Casco histórico", "A Parda", "Monteporreiro", "Lérez", "Mourente", "Salcedo",
                             "Campañó", "Xeve", "Lourizán"],
                   "nearby": ["Vilaboa", "Cerdedo-Cotobade", "Campo Lameiro", "Moraña", "Caldas de Reis", "Meis"]},
    "santiago-de-compostela": {"name": "Santiago de Compostela", "province": "A Coruña", "phase": 1, "hub": True,
                               "searches": 1312, "gbp_listing": "sin ficha prevista: se capta por orgánico",
                               "areas": ["Zona Vella", "Ensanche", "Santiago Norte", "Fontiñas", "Conxo",
                                         "Vista Alegre", "Sar", "San Lázaro", "Lamas de Abade"],
                               "nearby": ["Ames", "Teo", "Boqueixón", "Vedra", "Oroso", "Brión"]},
    "sanxenxo": {"name": "Sanxenxo", "province": "Pontevedra", "phase": 1, "hub": False, "searches": None,
                 "gbp_listing": "alternativa (zona Cambados–Sanxenxo)",
                 "areas": ["Portonovo", "Vilalonga", "Dorrón", "Nantes", "Adina"],
                 "nearby": ["Meaño", "Cambados", "O Grove", "Meis", "Ribadumia"]},
}
HOME_ZONE = "pontevedra"  # la home ataca esta zona: sustituye a su hub
PHASE_2_ZONES = ["Caldas de Reis", "A Estrada", "Vilagarcía de Arousa", "Cambados", "Padrón", "Lalín", "Ames", "Teo"]
PHASE_2_GUIDES = ["precio-cocina-a-medida", "precio-armario-empotrado-por-m2", "precio-vestidor-a-medida",
                  "cuanto-cuesta-un-porche-de-madera", "rehabilitar-o-sustituir-un-forjado-de-madera"]
PAGES = {"presupuesto": "/presupuesto/", "proyectos": "/proyectos/", "sobre_nosotros": "/sobre-nosotros/"}
LEGAL = ["/aviso-legal/", "/politica-de-privacidad/", "/cookies/"]


# ── URL map y enlazado ───────────────────────────────────────────────────────────
def pillar(slug: str) -> str:
    return f"/{slug}/"


def service_area(slug: str, zone: str) -> str:
    return f"/{slug}/{zone}/"


def hub(zone: str) -> str:
    return f"/carpinteria/{zone}/"


def build_links() -> dict[str, list[str]]:
    hubs = [z for z, data in ZONES.items() if data["hub"]]
    footer = [PAGES["presupuesto"], *[hub(z) for z in hubs], *LEGAL]
    links: dict[str, list[str]] = {"/": [pillar(s["slug"]) for s in SERVICES] + [hub(z) for z in hubs] +
                                   list(PAGES.values())}
    for s in SERVICES:
        links[pillar(s["slug"])] = ([service_area(s["slug"], z) for z in s["zones"]] +
                                    [pillar(r) for r in s["related"]] + [PAGES["presupuesto"], PAGES["proyectos"]])
        for z in s["zones"]:
            same_zone = [service_area(o["slug"], z) for o in SERVICES if o["slug"] != s["slug"] and z in o["zones"]]
            other_zones = [service_area(s["slug"], o) for o in s["zones"] if o != z]
            links[service_area(s["slug"], z)] = ([pillar(s["slug"])] + other_zones + same_zone +
                                                 ([hub(z)] if ZONES[z]["hub"] else ["/"] if z == HOME_ZONE else []) +
                                                 [PAGES["presupuesto"]])
    for z in hubs:
        links[hub(z)] = ([service_area(s["slug"], z) for s in SERVICES if z in s["zones"]] +
                         [pillar(s["slug"]) for s in SERVICES if z not in s["zones"]] +
                         [hub(o) for o in hubs if o != z] + ["/", PAGES["presupuesto"]])
    links[PAGES["proyectos"]] = [pillar(s["slug"]) for s in SERVICES] + [PAGES["presupuesto"]]
    links[PAGES["sobre_nosotros"]] = [PAGES["proyectos"], PAGES["presupuesto"]]
    links[PAGES["presupuesto"]] = []
    for legal in LEGAL:
        links[legal] = []
    return {url: list(dict.fromkeys(targets + [t for t in footer if t != url])) for url, targets in links.items()}


def click_depths(links: dict[str, list[str]]) -> dict[str, int]:
    depth, queue = {"/": 0}, deque(["/"])
    while queue:
        url = queue.popleft()
        for target in links.get(url, []):
            if target not in depth:
                depth[target] = depth[url] + 1
                queue.append(target)
    return depth


# ── YAML mínimo (no hay PyYAML instalado) ────────────────────────────────────────
def to_yaml(value, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}{key}:")
                lines.append(to_yaml(item, indent + 1))
            else:
                lines.append(f"{pad}{key}: {scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                body = to_yaml(item, indent + 1).splitlines()
                lines.append(f"{pad}- {body[0].strip()}")
                lines.extend(body[1:])
            else:
                lines.append(f"{pad}- {scalar(item)}")
        return "\n".join(lines)
    return f"{pad}{scalar(value)}"


def scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[]"
    if isinstance(value, dict):
        return "{}"
    text = str(value)
    return f'"{text}"' if re.search(r"[:#\[\]{},&*!|>'\"%@`]|^\s|\s$|^$", text) else text


# ── Schema templates ({{variables}}; un único elemento de ejemplo = repetir por cada elemento) ──
def schema_templates() -> dict[str, dict]:
    business_id = "https://{{dominio}}/#negocio"
    city = {"@type": "City", "name": "{{zona}}",
            "containedInPlace": {"@type": "AdministrativeArea", "name": "Provincia de {{provincia}}"}}
    breadcrumb_item = lambda pos, name, url: {"@type": "ListItem", "position": pos, "name": name, "item": url}
    faq = {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": "{{pregunta}}",
                                               "acceptedAnswer": {"@type": "Answer", "text": "{{respuesta}}"}}]}
    return {
        "home.jsonld": {"@context": "https://schema.org", "@graph": [
            {"@type": "WebSite", "@id": "https://{{dominio}}/#web", "url": "https://{{dominio}}/", "name": "{{marca}}",
             "inLanguage": "es-ES", "publisher": {"@id": business_id}},
            {"@type": "HomeAndConstructionBusiness", "@id": business_id, "name": "{{marca}}",
             "url": "https://{{dominio}}/", "telephone": "{{telefono}}", "email": "{{email}}",
             "image": "{{imagen_url}}", "logo": "{{logo_url}}", "priceRange": "€€",
             "description": "{{meta_description}}",
             "address": {"@type": "PostalAddress", "streetAddress": "{{calle}}", "postalCode": "{{cp}}",
                         "addressLocality": "{{localidad}}", "addressRegion": "{{provincia}}", "addressCountry": "ES"},
             "geo": {"@type": "GeoCoordinates", "latitude": "{{lat}}", "longitude": "{{lng}}"},
             "openingHoursSpecification": [{"@type": "OpeningHoursSpecification",
                                            "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                                            "opens": "{{abre}}", "closes": "{{cierra}}"}],
             "areaServed": [{"@type": "City", "name": data["name"]} for data in ZONES.values()],
             "sameAs": ["{{gbp_url}}"],
             "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Servicios de carpintería", "itemListElement": [
                 {"@type": "Offer", "itemOffered": {"@type": "Service", "name": s["name"],
                                                    "url": "https://{{dominio}}" + pillar(s["slug"])}}
                 for s in SERVICES]}}]},
        "service-pillar.jsonld": {"@context": "https://schema.org", "@graph": [
            {"@type": "Service", "@id": "https://{{dominio}}/{{servicio_slug}}/#servicio", "name": "{{servicio}}",
             "serviceType": "{{servicio_tipo}}", "description": "{{meta_description}}",
             "url": "https://{{dominio}}/{{servicio_slug}}/", "provider": {"@id": business_id},
             "areaServed": [{"@type": "City", "name": "{{zona}}"}],
             "hasOfferCatalog": {"@type": "OfferCatalog", "name": "{{servicio}}", "itemListElement": [
                 {"@type": "Offer", "itemOffered": {"@type": "Service", "name": "{{subservicio}}"}}]}},
            {"@type": "BreadcrumbList", "itemListElement": [
                breadcrumb_item(1, "Inicio", "https://{{dominio}}/"),
                breadcrumb_item(2, "{{servicio}}", "https://{{dominio}}/{{servicio_slug}}/")]},
            faq]},
        "service-area.jsonld": {"@context": "https://schema.org", "@graph": [
            {"@type": "Service", "@id": "https://{{dominio}}/{{servicio_slug}}/{{zona_slug}}/#servicio",
             "name": "{{servicio}} en {{zona}}", "serviceType": "{{servicio_tipo}}", "description": "{{meta_description}}",
             "url": "https://{{dominio}}/{{servicio_slug}}/{{zona_slug}}/", "provider": {"@id": business_id},
             "areaServed": city},
            {"@type": "BreadcrumbList", "itemListElement": [
                breadcrumb_item(1, "Inicio", "https://{{dominio}}/"),
                breadcrumb_item(2, "{{servicio}}", "https://{{dominio}}/{{servicio_slug}}/"),
                breadcrumb_item(3, "{{zona}}", "https://{{dominio}}/{{servicio_slug}}/{{zona_slug}}/")]},
            faq]},
        "zone-hub.jsonld": {"@context": "https://schema.org", "@graph": [
            {"@type": "CollectionPage", "@id": "https://{{dominio}}/carpinteria/{{zona_slug}}/#pagina",
             "name": "Carpintería en {{zona}}", "url": "https://{{dominio}}/carpinteria/{{zona_slug}}/",
             "about": {"@id": business_id}, "spatialCoverage": city,
             "mainEntity": {"@type": "ItemList", "itemListElement": [
                 {"@type": "ListItem", "position": 1, "name": "{{servicio}} en {{zona}}",
                  "url": "https://{{dominio}}/{{servicio_slug}}/{{zona_slug}}/"}]}},
            {"@type": "BreadcrumbList", "itemListElement": [
                breadcrumb_item(1, "Inicio", "https://{{dominio}}/"),
                breadcrumb_item(2, "Carpintería en {{zona}}", "https://{{dominio}}/carpinteria/{{zona_slug}}/")]}]},
        "presupuesto.jsonld": {"@context": "https://schema.org", "@graph": [
            {"@type": "ContactPage", "@id": "https://{{dominio}}/presupuesto/#pagina", "name": "Pide presupuesto",
             "url": "https://{{dominio}}/presupuesto/", "about": {"@id": business_id}},
            {"@type": "BreadcrumbList", "itemListElement": [
                breadcrumb_item(1, "Inicio", "https://{{dominio}}/"),
                breadcrumb_item(2, "Pide presupuesto", "https://{{dominio}}/presupuesto/")]}]},
    }


# ── Validación contra schema.org ─────────────────────────────────────────────────
SAMPLE = {"dominio": "ejemplo.es", "marca": "Carpintería Ejemplo", "telefono": "+34 600 000 000",
          "email": "hola@ejemplo.es", "imagen_url": "https://ejemplo.es/img.jpg", "logo_url": "https://ejemplo.es/logo.png",
          "meta_description": "Descripción", "calle": "Rúa Ejemplo 1", "cp": "36001", "localidad": "Pontevedra",
          "provincia": "Pontevedra", "lat": "42.43", "lng": "-8.64", "abre": "09:00", "cierra": "19:00",
          "gbp_url": "https://maps.google.com/?cid=1", "servicio": "Cocinas a medida", "servicio_slug": "cocinas-a-medida",
          "servicio_tipo": "Cocinas", "zona": "Pontevedra", "zona_slug": "pontevedra", "subservicio": "Encimeras",
          "pregunta": "¿Cuánto cuesta?", "respuesta": "Depende."}


def fill(value):
    if isinstance(value, dict):
        return {k: fill(v) for k, v in value.items()}
    if isinstance(value, list):
        return [fill(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"\{\{(\w+)\}\}", lambda m: SAMPLE[m.group(1)], value)
    return value


def load_vocabulary() -> tuple[set, dict, dict]:
    request = Request(VOCAB_URL, headers={"User-Agent": "blueprint-validator/1.0"})
    with urlopen(request, timeout=90) as resp:  # se lee en memoria, no se guarda en disco
        graph = json.load(resp)["@graph"]
    as_list = lambda v: v if isinstance(v, list) else [v] if v else []
    strip = lambda ref: ref["@id"].split(":", 1)[1] if isinstance(ref, dict) else str(ref)
    classes, parents, domains = set(), {}, {}
    for node in graph:
        node_id = node["@id"].split(":", 1)[1]
        types = as_list(node.get("@type"))
        if "rdfs:Class" in types:
            classes.add(node_id)
            parents[node_id] = [strip(p) for p in as_list(node.get("rdfs:subClassOf"))]
        if "rdf:Property" in types:
            domains[node_id] = {strip(d) for d in as_list(node.get("schema:domainIncludes"))}
    return classes, parents, domains


def ancestors(cls: str, parents: dict) -> set:
    seen, stack = set(), [cls]
    while stack:
        current = stack.pop()
        if current not in seen:
            seen.add(current)
            stack.extend(parents.get(current, []))
    return seen


def validate_node(node, vocab, path: str, errors: list) -> None:
    classes, parents, domains = vocab
    if isinstance(node, list):
        for i, item in enumerate(node):
            validate_node(item, vocab, f"{path}[{i}]", errors)
        return
    if not isinstance(node, dict):
        return
    if "@graph" in node:
        validate_node(node["@graph"], vocab, f"{path}.@graph", errors)
        return
    node_type = node.get("@type")
    if node_type is None:
        return  # referencia {"@id": ...}
    if node_type not in classes:
        errors.append(f"{path}: tipo desconocido {node_type}")
        return
    lineage = ancestors(node_type, parents)
    for key, value in node.items():
        if key.startswith("@"):
            continue
        if key not in domains:
            errors.append(f"{path}: propiedad desconocida «{key}»")
        elif not domains[key] & lineage:
            errors.append(f"{path}: «{key}» no aplica a {node_type}")
        validate_node(value, vocab, f"{path}.{key}", errors)


def google_checks(name: str, doc: dict, errors: list) -> None:
    for node in doc.get("@graph", [doc]):
        kind = node.get("@type")
        if kind == "FAQPage":
            for q in node.get("mainEntity", []):
                if not (q.get("name") and q.get("acceptedAnswer", {}).get("text")):
                    errors.append(f"{name}: pregunta FAQ sin name o acceptedAnswer.text")
        if kind == "BreadcrumbList":
            for item in node.get("itemListElement", []):
                if not all(item.get(k) for k in ("position", "name", "item")):
                    errors.append(f"{name}: elemento de breadcrumb incompleto")
        if kind == "HomeAndConstructionBusiness":
            for required in ("name", "address", "telephone", "geo", "openingHoursSpecification", "url"):
                if required not in node:
                    errors.append(f"{name}: LocalBusiness sin «{required}»")


# ── Main ─────────────────────────────────────────────────────────────────────────
def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-validate", action="store_true", help="no descarga el vocabulario de schema.org")
    args = parser.parse_args()
    problems: list[str] = []

    for zone, data in ZONES.items():
        for place in data["nearby"]:
            if place in EXCLUDED:
                problems.append(f"{zone}: «{place}» está excluida en el briefing")
            elif place not in COVERAGE:
                problems.append(f"{zone}: «{place}» no está en la cobertura del briefing")
    if data_outside := [p for p in PHASE_2_ZONES if p not in COVERAGE]:
        problems.append(f"fase 2 fuera de cobertura: {data_outside}")

    combos = [service_area(s["slug"], z) for s in SERVICES for z in s["zones"]]
    if len(combos) > MAX_SERVICE_AREA:
        problems.append(f"{len(combos)} páginas servicio × zona superan el límite de {MAX_SERVICE_AREA}: priorizar")

    links = build_links()
    depth = click_depths(links)
    too_deep = [url for url in links if depth.get(url, 99) > 3]
    if too_deep:
        problems.append(f"páginas a más de 3 clics o inalcanzables: {too_deep}")

    url_map = {
        "negocio": "carpinteria-pontevedra",
        "fase": 1,
        "home": "/",
        "servicios": [{"slug": s["slug"], "nombre": s["name"], "url": pillar(s["slug"]),
                       "categoria_gbp": s["gbp_category"], "zonas": s["zones"],
                       "keywords": [f"{k} ({v}/mes)" for k, v in s["keywords"].items()]} for s in SERVICES],
        "zonas": [{"slug": z, "nombre": d["name"], "provincia": d["province"], "hub": hub(z) if d["hub"] else None,
                   "busquedas_mes_kw_research": d["searches"], "ficha_gbp": d["gbp_listing"],
                   "barrios_parroquias": d["areas"], "zonas_cercanas": d["nearby"]} for z, d in ZONES.items()],
        "servicio_x_zona": combos,
        "zonas_hub": [hub(z) for z, d in ZONES.items() if d["hub"]],
        "paginas": PAGES,
        "legales": LEGAL,
        "fase_2": {"zonas": PHASE_2_ZONES, "guias_de_precio": [f"/guias/{g}/" for g in PHASE_2_GUIDES],
                   "lineas_futuras": ["casetas, casas y cabañas de madera (1.030 búsquedas/mes; el cliente las lanza en 2027)"]},
        "total_paginas_fase_1": len(links),
    }
    linking = {
        "reglas": {
            "home": "→ todos los pilares de servicio, hubs de zona, presupuesto, proyectos y sobre nosotros",
            "pilar": "→ sus páginas servicio × zona + servicios relacionados + presupuesto + proyectos",
            "servicio_x_zona": "→ pilar (breadcrumb) + mismo servicio en otras zonas + otros servicios en la misma zona + hub de la zona + presupuesto",
            "hub_zona": "→ todos los servicios de esa zona (o su pilar si no hay página de zona) + otros hubs + presupuesto",
            "pie_global": "presupuesto + hubs de zona + legales en todas las páginas",
            "bloque_zonas_cercanas": "texto sin enlace con las zonas_cercanas de url-map.yaml (fase 1); se enlazan cuando existan en fase 2",
            "anchor_text": "descriptivo y variado: «{servicio} en {zona}», «{servicio}», «carpintería en {zona}»; nunca «click aquí»",
        },
        "profundidad_maxima_clics": max(depth.values()),
        "enlaces": links,
    }

    (OUT / "schema-templates").mkdir(parents=True, exist_ok=True)
    (OUT / "url-map.yaml").write_text(
        "# Generado por scripts/web_blueprint_generator.py: editar allí, no aquí.\n" + to_yaml(url_map) + "\n", encoding="utf-8")
    (OUT / "internal-linking.yaml").write_text(
        "# Generado por scripts/web_blueprint_generator.py: editar allí, no aquí.\n" + to_yaml(linking) + "\n", encoding="utf-8")
    templates = schema_templates()
    for name, doc in templates.items():
        (OUT / "schema-templates" / name).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    budget = [{"path": "/*",
               "timings": [{"metric": "largest-contentful-paint", "budget": 2500},
                           {"metric": "cumulative-layout-shift", "budget": 0.1},
                           {"metric": "total-blocking-time", "budget": 200},
                           {"metric": "first-contentful-paint", "budget": 1800},
                           {"metric": "interactive", "budget": 3500}],
               "resourceSizes": [{"resourceType": "script", "budget": 60}, {"resourceType": "image", "budget": 350},
                                 {"resourceType": "font", "budget": 60}, {"resourceType": "total", "budget": 700}],
               "resourceCounts": [{"resourceType": "third-party", "budget": 6}]}]
    (OUT / "lighthouse-budget.json").write_text(json.dumps(budget, indent=2) + "\n", encoding="utf-8")

    if not args.no_validate:
        try:
            vocab = load_vocabulary()
            for name, doc in templates.items():
                errors: list[str] = []
                validate_node(fill(doc), vocab, name, errors)
                google_checks(name, fill(doc), errors)
                problems += errors
                print(f"  {'✓' if not errors else '✗'} {name} contra schema.org")
        except OSError as e:
            problems.append(f"no se pudo descargar el vocabulario de schema.org: {e}")

    print(f"Páginas fase 1: {len(links)} · servicio × zona: {len(combos)} · profundidad máxima: {max(depth.values())} clics")
    print(f"→ {OUT.relative_to(ROOT)}")
    if problems:
        print("✗ Revisar:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("✓ Sin incidencias (cobertura, profundidad ≤ 3 clics, JSON-LD válido)")


if __name__ == "__main__":
    main()
