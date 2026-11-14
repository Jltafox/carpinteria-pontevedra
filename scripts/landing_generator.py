"""
landing-generator-servicio-barrio · compone las páginas de la web Astro (web/) a partir del blueprint.

Implementa 03-skills/landing-generator-servicio-barrio/SKILL.md del repo "Clase 1 · Agentes IA para SEO y webs
hiperoptimizadas" (YinyangSEO Academy).

Entradas: blueprint/carpinteria-pontevedra/ (servicios, zonas y enlazado vienen de web_blueprint_generator.py; el
contenido redactado, de content/*.json). Salida: web/src/data/pages.json (lo que pinta Astro), areas-served.json y,
solo si no existe, business.json con los datos del negocio vacíos (se muestran como {{variable}}).

Reglas de la skill: no se escribe ninguna página cuyo JSON-LD no valide contra schema.org; cada landing servicio ×
zona debe tener similitud Jaccard < 0,7 con sus hermanas; aviso si hay > 50 combinaciones.

Uso:
    py scripts/landing_generator.py --dry-run     # lista lo que se generaría
    py scripts/landing_generator.py               # valida y escribe
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from itertools import combinations

import web_blueprint_generator as bp
from local_pack_multi_city import ROOT, slugify

CONTENT = bp.OUT / "content"
WEB_DATA = ROOT / "web" / "src" / "data"
JACCARD_MAX = 0.7
MAX_COMBOS = 50
BUSINESS_TEMPLATE = {
    "marca": "", "dominio": "", "telefono": "", "telefono_visible": "", "whatsapp": "", "email": "",
    "calle": "", "cp": "", "localidad": "", "provincia": "", "lat": "", "lng": "",
    "abre": "", "cierra": "", "horario_texto": "", "gbp_url": "", "maps_embed_url": "", "logo_url": "", "imagen_url": "",
    "form_endpoint": "", "ga_id": "", "titular_legal": "", "nif": "", "domicilio_legal": "", "datos_registrales": "", "empresa_ejecutora": "", "ejecutora_nif": "", "ejecutora_domicilio": "",
    "indexable": False,  # la web no se indexa ni rastrea hasta ponerlo a true a propósito
    "publicar_precios": False, "proyectos": [], "testimonios": [],
}
PAGE_LABELS = {"/": f"Carpintería en {bp.ZONES[bp.HOME_ZONE]['name']}", "/presupuesto/": "Pide presupuesto", "/proyectos/": "Trabajos realizados",
               "/sobre-nosotros/": "Quiénes somos", "/aviso-legal/": "Aviso legal",
               "/politica-de-privacidad/": "Política de privacidad", "/cookies/": "Cookies"}
BUSINESS_ID = "https://{{dominio}}/#negocio"

# Titles definitivos, escritos a mano (05/11/2026). Tienen prioridad sobre los que compone el generador.
TITLES = {
    "/": "Carpintería de madera en Pontevedra | Carpintería Urexal",
    "/santiago-de-compostela/": "Carpintería en Santiago de Compostela | Urexal",
    "/cocinas-a-medida/": "Cocinas a medida en Pontevedra | Taller propio",
    "/armarios-a-medida/": "Armarios empotrados y vestidores a medida | Urexal",
    "/muebles-a-medida/": "Muebles a medida en Pontevedra | Taller propio",
    "/rehabilitacion-de-madera/": "Rehabilitación de tejados, vigas y forjados de madera",
    "/carpinteria-exterior/": "Carpintería exterior de madera | Porches y pérgolas",
    "/suelos-de-madera/": "Suelos de madera: tarima, parquet y pulido | Urexal",
    "/presupuesto/": "Pide presupuesto | Carpintería Urexal",
    "/sobre-nosotros/": "Quiénes somos | Carpintería Urexal",
    "/aviso-legal/": "Aviso legal | Carpintería Urexal",
    "/politica-de-privacidad/": "Política de privacidad | Urexal",
    "/cookies/": "Política de cookies | Carpintería Urexal",
}

# H2 optimizados con el keyword research por URL (05/11/2026): {ruta: {H2 generado: H2 definitivo}}.
# Se quedan comunes los de plazos, zona de trabajo y servicios relacionados.
H2 = {
    "/": {
        "Qué hacemos": "Servicios de carpintería de madera a medida",
        "Por qué elegirnos": "Por qué elegir nuestra carpintería en Pontevedra",
        "Dónde trabajamos en Pontevedra": "Carpintero en Pontevedra y alrededores",
        "Dónde estamos": "Nuestra carpintería en Pontevedra: dirección y horario",
        "Preguntas frecuentes": "Preguntas frecuentes sobre carpintería a medida",
    },
    "/cocinas-a-medida/": {
        "Qué hacemos": "Qué incluye una cocina a medida",
        "Materiales y acabados": "Materiales y acabados de los muebles de cocina a medida",
    },
    "/armarios-a-medida/": {
        "Qué hacemos": "Armarios empotrados, vestidores y despensas a medida",
        "Materiales y acabados": "Armarios empotrados de madera que resisten la humedad",
    },
    "/muebles-a-medida/": {
        "Qué hacemos": "Qué muebles a medida fabricamos",
        "Materiales y acabados": "Muebles de madera a medida: materiales y acabados",
    },
    "/rehabilitacion-de-madera/": {
        "Qué hacemos": "Qué incluye la rehabilitación de estructuras de madera",
        "Materiales y acabados": "Reformas de viviendas con madera: diagnóstico y materiales",
    },
    "/carpinteria-exterior/": {
        "Qué hacemos": "Porches, pérgolas, cobertizos y muebles de exterior a medida",
        "Materiales y acabados": "Carpintería exterior de madera que aguanta la intemperie",
    },
    "/suelos-de-madera/": {
        "Qué hacemos": "Tarima, parquet y pulido de suelos de madera",
        "Materiales y acabados": "Cómo instalamos un suelo de madera para que no se levante",
    },
    "/cocinas-a-medida/diseno/": {  # cambio pedido sobre el texto del redactor (14/11/2026)
        "Diseño de cocinas a medida: creamos una cocina especialmente pensada para ti":
            "Diseño de cocinas: creamos una cocina especialmente pensada para ti",
        "¿Cómo diseñamos tu cocina a medida?": "¿Cómo diseñamos tu cocina?",
    },
    "/santiago-de-compostela/": {
        "Servicios en Santiago de Compostela": "Cocinas, muebles y armarios a medida en Santiago de Compostela",
        "Dónde trabajamos en Santiago de Compostela": "Carpintería en Santiago de Compostela y alrededores",
    },
}


def load(name: str) -> dict:
    return json.loads((CONTENT / name).read_text(encoding="utf-8"))


def label(url: str) -> str:
    if url in PAGE_LABELS:
        return PAGE_LABELS[url]
    for s in bp.SERVICES:
        if url == bp.pillar(s["slug"]):
            return s["name"]
        for z in s["zones"]:
            if url == bp.service_area(s["slug"], z):
                return f'{s["name"]} en {bp.ZONES[z]["name"]}'
    for z, data in bp.ZONES.items():
        if url == bp.hub(z):
            return f'Carpintería en {data["name"]}'
    return url


def link_list(urls: list[str]) -> list[dict]:
    return [{"url": u, "label": label(u)} for u in urls]


def crumbs(*pairs: tuple[str, str]) -> list[dict]:
    return [{"name": "Inicio", "url": "/"}] + [{"name": n, "url": u} for n, u in pairs]


# ── JSON-LD (con tokens {{...}} del negocio; Astro los sustituye con business.json) ──
def breadcrumb_ld(items: list[dict]) -> dict:
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": c["name"], "item": "https://{{dominio}}" + c["url"]}
        for i, c in enumerate(items, 1)]}


def faq_ld(faqs: list[dict]) -> dict:
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faqs]}


def city(zone: str) -> dict:
    data = bp.ZONES[zone]
    return {"@type": "City", "name": data["name"],
            "containedInPlace": {"@type": "AdministrativeArea", "name": f'Provincia de {data["province"]}'}}


def service_ld(service: dict, url: str, name: str, description: str, area) -> dict:
    image = f'/img/{service["slug"]}/portada.webp'
    return {"@type": "Service", "@id": "https://{{dominio}}" + url + "#servicio", "name": name,
            "serviceType": service["service_type"], "description": description, "url": "https://{{dominio}}" + url,
            **({"image": "https://{{dominio}}" + image} if (ROOT / "web/public" / image.lstrip("/")).exists() else {}),
            "provider": {"@id": BUSINESS_ID}, "areaServed": area,
            "hasOfferCatalog": {"@type": "OfferCatalog", "name": service["name"], "itemListElement": [
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": sub}} for sub in service["subservices"]]}}


def home_ld(description: str) -> dict:
    template = bp.schema_templates()["home.jsonld"]
    graph = json.loads(json.dumps(template["@graph"]))
    graph[1]["description"] = description
    return {"@context": "https://schema.org", "@graph": graph}


# ── Composición de páginas ───────────────────────────────────────────────────────
def price_section(service: dict, copy: dict, zone_name: str | None) -> dict:
    question = copy["price_question"] + (f" en {zone_name}?" if zone_name else "?")
    return {"kind": "price", "h2": question, "text": copy["price"]["text"],
            "factors": copy["price"]["factors"], "ranges": copy["price"].get("ranges", [])}


def build_pages() -> list[dict]:
    services_copy, areas_copy, pages_copy = load("services.json"), load("areas.json"), load("pages.json")
    links = bp.build_links()
    process = {"kind": "process", "h2": "Cómo trabajamos y en qué plazos", "steps": pages_copy["process"]}
    hubs = [z for z, d in bp.ZONES.items() if d["hub"]]
    pages = []

    # Home
    home = pages_copy["home"]
    # La home ataca solo Pontevedra (indicación del cliente); Santiago se trabaja en sus propias páginas.
    description = ("Carpintería en Pontevedra: cocinas, armarios y muebles a medida, rehabilitación de tejados y vigas "
                   "de madera y carpintería exterior. Taller propio. Presupuesto: {{telefono}}")
    home_faqs = home["faqs"]
    pages.append({
        "route": "/", "type": "home", "params": {},
        "title": "Carpintería de madera en Pontevedra | {{marca}}", "description": description,
        "h1": "Carpintería de madera a medida en Pontevedra", "lead": home["lead"],
        "breadcrumbs": [], "cta": {},
        "sections": [
            {"kind": "cards", "h2": "Qué hacemos", "cards": [
                {"title": s["name"], "text": services_copy[s["slug"]]["card"], "url": bp.pillar(s["slug"])}
                for s in bp.SERVICES]},
            {"kind": "items", "h2": "Por qué elegirnos", "items": home["why"]},
            process,
            {"kind": "projects", "h2": "Trabajos realizados", "service": None},
            {"kind": "testimonials", "h2": "Lo que dicen nuestros clientes"},
            {"kind": "links", "h2": "Dónde trabajamos en Pontevedra", "text": home["where"],
             "links": link_list([bp.hub(z) for z in hubs])},
            {"kind": "nap", "h2": "Dónde estamos"},  # NAP + mapa de la ficha de Google (maps_embed_url)
            {"kind": "faq", "h2": "Preguntas frecuentes", "faqs": home_faqs},
        ],
        "jsonld": home_ld(description),
    })
    pages[-1]["jsonld"]["@graph"].append(faq_ld(home_faqs))

    # Pilares
    for s in bp.SERVICES:
        copy = services_copy[s["slug"]]
        url = bp.pillar(s["slug"])
        description = (f'{s["service_type"]} con taller propio en A Estrada y montaje por nuestro equipo. '
                       "Te llamamos en menos de 2 días. Presupuesto: {{telefono}}")
        coverage_text = ("También trabajamos en el resto de nuestra zona: A Estrada, Caldas de Reis, Padrón, "
                         "Vilagarcía de Arousa, Cambados, Sanxenxo, Lalín, Silleda y otros municipios entre "
                         "Pontevedra y Santiago.")
        bc = crumbs((s["name"], url))
        pages.append({
            "route": url, "type": "pillar", "params": {"servicio": s["slug"]},
            "title": f'{s["name"]} | {{{{marca}}}}', "description": description,
            "h1": s["name"], "lead": copy["intro"], "breadcrumbs": bc, "cta": {"servicio": s["slug"]},
            "sections": [
                {"kind": "items", "h2": "Qué hacemos", "items": copy["subservices"]},
                process,
                price_section(s, copy, None),
                {"kind": "text", "h2": "Materiales y acabados", "paragraphs": copy["materials"]},
                {"kind": "links", "h2": "Dónde trabajamos", "text": coverage_text,
                 "links": link_list(["/"] + [bp.hub(z) for z in hubs])},
                {"kind": "projects", "h2": "Trabajos realizados", "service": s["slug"]},
                {"kind": "testimonials", "h2": "Opiniones"},
                {"kind": "faq", "h2": f'Preguntas frecuentes sobre {copy["topic"]}', "faqs": copy["faqs"]},
                {"kind": "links", "h2": "Servicios relacionados", "links": link_list([bp.pillar(r) for r in s["related"]])},
            ],
            "jsonld": {"@context": "https://schema.org", "@graph": [
                service_ld(s, url, s["name"], description, bp.area_served()),
                breadcrumb_ld(bc), faq_ld(copy["faqs"])]},
        })

    # Servicio × zona
    for s in bp.SERVICES:
        copy = services_copy[s["slug"]]
        for z in s["zones"]:
            zone = bp.ZONES[z]
            area = areas_copy[f'{s["slug"]}/{z}']
            url = bp.service_area(s["slug"], z)
            faqs = copy["faqs"][:3] + area["faqs"]
            description = (f'{s["name"]} en {zone["name"]} con fabricación en taller propio y montaje por nuestro '
                           "equipo. Visita en 3–4 días laborables. Presupuesto: {{telefono}}")
            bc = crumbs((s["name"], bp.pillar(s["slug"])), (zone["name"], url))
            same_zone = [bp.service_area(o["slug"], z) for o in bp.SERVICES if o["slug"] != s["slug"] and z in o["zones"]]
            other_zones = [bp.service_area(s["slug"], o) for o in s["zones"] if o != z]
            pages.append({
                "route": url, "type": "service-area", "params": {"servicio": s["slug"], "zona": z},
                "title": f'{s["name"]} en {zone["name"]} | {{{{marca}}}}', "description": description,
                "h1": f'{s["name"]} en {zone["name"]}', "lead": area["lead"], "breadcrumbs": bc,
                "cta": {"servicio": s["slug"], "zona": z},
                "sections": [
                    {"kind": "text", "h2": area["h2"], "paragraphs": area["paragraphs"],
                     "list_title": "Barrios y parroquias donde trabajamos", "list": zone["areas"]},
                    {"kind": "items", "h2": "Qué incluye", "items": copy["subservices"]},
                    process,
                    price_section(s, copy, zone["name"]),
                    {"kind": "projects", "h2": "Trabajos realizados", "service": s["slug"]},
                    {"kind": "testimonials", "h2": "Lo que dicen nuestros clientes"},
                    {"kind": "faq", "h2": f'Preguntas frecuentes sobre {copy["topic"]} en {zone["name"]}', "faqs": faqs},
                    {"kind": "links", "h2": "También trabajamos en",
                     "text": "Zonas cercanas: " + ", ".join(zone["nearby"]) + ".", "links": link_list(other_zones)},
                    {"kind": "links", "h2": f'Otros servicios en {zone["name"]}',
                     "links": link_list(same_zone + ([bp.hub(z)] if zone["hub"] else ["/"] if z == bp.HOME_ZONE else []) +
                                        [bp.pillar(s["slug"])])},
                ],
                "jsonld": {"@context": "https://schema.org", "@graph": [
                    service_ld(s, url, f'{s["name"]} en {zone["name"]}', description, city(z)),
                    breadcrumb_ld(bc), faq_ld(faqs)]},
            })

    # Hubs de zona
    for z in hubs:
        zone, copy = bp.ZONES[z], pages_copy["hubs"][z]
        url = bp.hub(z)
        in_zone = [s for s in bp.SERVICES if z in s["zones"]]
        description = (f'Carpintería de madera en {zone["name"]} y alrededores: cocinas, armarios, muebles, '
                       "rehabilitación y exterior. Visita en 3–4 días laborables. Llámanos: {{telefono}}")
        bc = crumbs((f'Carpintería en {zone["name"]}', url))
        cards = [{"title": f'{s["name"]} en {zone["name"]}', "text": services_copy[s["slug"]]["card"],
                  "url": bp.service_area(s["slug"], z)} for s in in_zone]
        cards += [{"title": s["name"], "text": services_copy[s["slug"]]["card"], "url": bp.pillar(s["slug"])}
                  for s in bp.SERVICES if s not in in_zone]
        pages.append({
            "route": url, "type": "hub", "params": {"zona": z},
            "title": f'Carpintería en {zone["name"]} | {{{{marca}}}}',
            "description": description, "h1": f'Carpintería de madera en {zone["name"]}', "lead": copy["lead"],
            "breadcrumbs": bc, "cta": {"zona": z},
            "sections": [
                {"kind": "cards", "h2": f'Servicios en {zone["name"]}', "cards": cards},
                {"kind": "text", "h2": f'Dónde trabajamos en {zone["name"]}', "paragraphs": copy["paragraphs"],
                 "list_title": "Barrios y parroquias", "list": zone["areas"]},
                {"kind": "projects", "h2": f'Trabajos en {zone["name"]}', "service": None},
                {"kind": "links", "h2": "Zonas cercanas", "text": ", ".join(zone["nearby"]) + ".",
                 "links": link_list([bp.hub(o) for o in hubs if o != z] + ["/"])},
            ],
            "jsonld": {"@context": "https://schema.org", "@graph": [
                {"@type": "CollectionPage", "@id": "https://{{dominio}}" + url + "#pagina",
                 "name": f'Carpintería en {zone["name"]}', "url": "https://{{dominio}}" + url,
                 "about": {"@id": BUSINESS_ID}, "spatialCoverage": city(z),
                 "mainEntity": {"@type": "ItemList", "itemListElement": [
                     {"@type": "ListItem", "position": i, "name": c["title"], "url": "https://{{dominio}}" + c["url"]}
                     for i, c in enumerate(cards, 1)]}},
                breadcrumb_ld(bc)]},
        })

    # Páginas fijas (el contenido está en sus .astro; aquí solo meta, breadcrumbs y schema)
    fixed = [("/presupuesto/", "presupuesto", "Pide presupuesto de carpintería | {{marca}}",
              "Cuéntanos tu proyecto y te llamamos en menos de 2 días. Visita en 3–4 días laborables y presupuesto en 3–4 días."),
             ("/proyectos/", "proyectos", "Trabajos realizados | {{marca}}",
              "Cocinas, armarios, muebles, rehabilitaciones y carpintería exterior hechos por nuestro equipo."),
             ("/sobre-nosotros/", "sobre-nosotros", "Quiénes somos | {{marca}}",
              "Carpintería de madera con taller propio en A Estrada y equipo de montaje propio."),
             ("/aviso-legal/", "legal", "Aviso legal | {{marca}}", "Aviso legal de {{marca}}."),
             ("/politica-de-privacidad/", "legal", "Política de privacidad | {{marca}}", "Política de privacidad de {{marca}}."),
             ("/cookies/", "legal", "Política de cookies | {{marca}}", "Política de cookies de {{marca}}.")]
    for url, kind, title, description in fixed:
        if url == "/proyectos/" and not bp.SHOW_PROJECTS:
            continue
        bc = crumbs((PAGE_LABELS[url], url))
        graph = [breadcrumb_ld(bc)]
        if kind == "presupuesto":
            graph.insert(0, {"@type": "ContactPage", "@id": "https://{{dominio}}/presupuesto/#pagina",
                             "name": "Pide presupuesto", "url": "https://{{dominio}}/presupuesto/", "about": {"@id": BUSINESS_ID}})
        pages.append({"route": url, "type": kind, "params": {}, "title": title, "description": description,
                      "h1": PAGE_LABELS[url], "lead": "", "breadcrumbs": bc, "cta": {}, "sections": [],
                      "jsonld": {"@context": "https://schema.org", "@graph": graph},
                      "noindex": kind == "legal"})

    for page in pages:  # enlaces salientes según internal-linking.yaml (los usa el QA y el pie)
        page["links"] = link_list(links.get(page["route"], []))
    add_images(pages)
    return pages


# ── Imágenes: cada hueco tiene ya su URL definitiva (web/public/img/...) ───────────
HERO, ITEM, GALLERY = (1500, 1000), (900, 600), (1200, 900)
GALLERY_SLOTS = 3
HERO_ALT = {
    "cocinas-a-medida": "Cocina a medida de madera",
    "armarios-a-medida": "Armario empotrado a medida",
    "muebles-a-medida": "Mueble de madera a medida",
    "rehabilitacion-de-madera": "Rehabilitación de vigas y estructura de tejado de madera",
    "carpinteria-exterior": "Porche de madera a medida",
    "suelos-de-madera": "Suelo de tarima de madera",
}


def image(src: str, alt: str, size: tuple[int, int]) -> dict:
    return {"src": src, "alt": alt, "width": size[0], "height": size[1]}


def gallery(folder: str, alt: str) -> list[dict]:
    return [image(f"{folder}/trabajo-{n}.webp", f"{alt} · trabajo {n}", GALLERY) for n in range(1, GALLERY_SLOTS + 1)]


def add_images(pages: list[dict]) -> None:
    """Portada por página, foto por subservicio, miniaturas de tarjetas y galería de 3 trabajos (sustituye a «projects»)."""
    for p in pages:
        params, kind = p["params"], p["type"]
        if kind == "home":
            folder, hero_alt = "/img/home", "Taller de carpintería con muebles de madera a medida"
        elif kind == "pillar":
            folder, hero_alt = f'/img/{params["servicio"]}', HERO_ALT[params["servicio"]]
        elif kind == "service-area":
            zone = bp.ZONES[params["zona"]]["name"]
            folder, hero_alt = f'/img/{params["servicio"]}/{params["zona"]}', f'{HERO_ALT[params["servicio"]]} en {zone}'
        elif kind == "hub":
            zone = bp.ZONES[params["zona"]]["name"]
            folder, hero_alt = f'/img/{params["zona"]}', "Vivienda con estantería, cocina y escalera de madera a medida"
        elif kind == "sobre-nosotros":
            p["hero_image"] = image("/img/sobre-nosotros/taller.webp", "Taller de carpintería con maquinaria y muebles embalados", HERO)
            continue
        else:
            continue
        p["hero_image"] = image(f"{folder}/portada.webp", hero_alt, HERO)
        for section in p["sections"]:
            if section["kind"] == "projects":
                section.update({"kind": "gallery", "images": gallery(folder, hero_alt)})
                section.pop("service", None)
            if section["kind"] == "items" and kind in ("pillar", "service-area"):
                for item in section["items"]:
                    item["image"] = image(f'/img/{params["servicio"]}/{slugify(item["h3"])}.webp', item["h3"], ITEM)
    heroes = {p["route"]: p["hero_image"] for p in pages if "hero_image" in p}
    for p in pages:
        for section in p["sections"]:
            for card in section.get("cards", []):
                hero = heroes.get(card["url"])
                if hero:
                    card["image"] = image(hero["src"], hero["alt"], ITEM)


def image_manifest(pages: list[dict]) -> list[dict]:
    slots: dict[str, dict] = {}
    for p in pages:
        found = [("portada", p["hero_image"])] if "hero_image" in p else []
        for section in p["sections"]:
            found += [("subservicio", i["image"]) for i in section.get("items", []) if "image" in i]
            found += [("galería", i) for i in section.get("images", [])]
        for use, img in found:
            slot = slots.setdefault(img["src"], {"ruta": "web/public" + img["src"], "url": img["src"], "uso": use,
                                                 "tamaño": f'{img["width"]}×{img["height"]}', "alt_propuesto": img["alt"],
                                                 "paginas": []})
            if p["route"] not in slot["paginas"]:
                slot["paginas"].append(p["route"])
    return sorted(slots.values(), key=lambda s: s["url"])


# ── Subpáginas de servicio: /{servicio}/{slug}/ ─────────────────────────────────────
def plain(text) -> str:
    """Texto plano de una cadena o de una lista de trozos con enlaces."""
    return "".join(t if isinstance(t, str) else t.get("a") or t.get("b", "") for t in text) if isinstance(text, list) else (text or "")


def block_text(block: dict) -> str:
    if block["type"] == "ul":
        return " ".join(f'{plain(i.get("lead", ""))} {plain(i["text"])}' for i in block["items"])
    return plain(block.get("text", ""))


def apply_changes(page: dict, changes: list[dict]) -> None:
    """Cambios de texto acordados con el cliente sobre el texto del redactor (se aplican antes de los enlaces)."""
    def walk(node):
        nonlocal count
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, str) and k not in ("kind", "type", "href", "url") and change["de"] in v:
                    node[k] = v.replace(change["de"], change["a"]); count += 1
                else:
                    walk(v)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                if isinstance(v, str) and change["de"] in v:
                    node[i] = v.replace(change["de"], change["a"]); count += 1
                else:
                    walk(v)
    for change in changes:
        count = 0
        walk(page)
        if not count:
            print(f"⚠ {page['route']}: no encuentro «{change['de']}» para cambiarlo")


def add_links(page: dict, links: list[dict]) -> None:
    """Convierte en enlace la primera aparición de cada «texto» (dentro de su «contexto», si se indica).
    Solo cambia la estructura: el texto unido de cada campo es idéntico al del redactor."""
    def fields():
        for s in page["sections"]:
            if s["kind"] == "faq":
                continue  # las respuestas van también al schema FAQPage, en texto plano
            for b in s.get("blocks", []) + [x for x in s.get("intro", []) if isinstance(x, dict)]:
                if b["type"] == "p":
                    yield b, "text"
                for i in b.get("items", []):
                    yield i, "lead"
                    yield i, "text"
            for holder, key in [(s, k) for k in range(len(s.get("intro", []))) if isinstance(s["intro"][k], str)]:
                yield holder["intro"], key
            for i in s.get("items", []) + s.get("steps", []):
                yield i, "text"
                for k in range(len(i.get("more", []))):
                    yield i["more"], k
    for link in links:
        anchor, context = link["texto"], link.get("contexto", link["texto"])
        for holder, key in fields():
            value = holder[key] if isinstance(holder, list) or key in holder else None
            if value is None or isinstance(value, dict):
                continue
            segments = value if isinstance(value, list) else [value]
            text = plain(segments)
            if context not in text or anchor not in context:
                continue
            start, pos, out, done = text.index(context) + context.index(anchor), 0, [], False
            for seg in segments:  # parte el trozo de texto que contiene el anchor
                length = len(seg) if isinstance(seg, str) else len(plain([seg]))
                if not done and isinstance(seg, str) and pos <= start and start + len(anchor) <= pos + length:
                    i = start - pos
                    out += [p for p in (seg[:i], {"a": anchor, "href": link["url"]}, seg[i + len(anchor):]) if p]
                    done = True
                else:
                    out.append(seg)
                pos += length
            if done:
                holder[key] = out
                break
        else:
            print(f"⚠ {page['route']}: no encuentro «{anchor}» para enlazar a {link['url']}")


def hero_size(src: str) -> tuple[int, int]:
    try:
        from PIL import Image
        with Image.open(ROOT / "web" / "public" / src.lstrip("/")) as im:
            return im.size
    except Exception:  # sin Pillow o sin la foto todavía: tamaño de portada
        return HERO


def add_subpages(pages: list[dict]) -> None:
    """Lee content/subpaginas/*.json, crea cada subpágina detrás de su pilar y la enlaza desde él."""
    folder = CONTENT / "subpaginas"
    for f in sorted(folder.glob("*.json")) if folder.exists() else []:
        d = json.loads(f.read_text(encoding="utf-8"))
        parent = next(p for p in pages if p["type"] == "pillar" and p["params"]["servicio"] == d["servicio"])
        route, name = d["ruta"], d["title"].split(" | ")[0]
        service_id = "https://{{dominio}}" + route + "#servicio"
        bc = crumbs((parent["h1"], parent["route"]), (d["miga"], route))
        faqs = [q for s in d["sections"] if s["kind"] == "faq" for q in s["faqs"]]
        node = {"@type": "Service", "@id": service_id, "name": name, "serviceType": name, "description": d["description"],
                "url": "https://{{dominio}}" + route, "provider": {"@id": BUSINESS_ID}, "areaServed": bp.area_served(),
                "isRelatedTo": {"@id": "https://{{dominio}}" + parent["route"] + "#servicio"}}
        page = {"route": route, "type": "subservice", "params": {"servicio": d["servicio"], "sub": d["slug"]},
                "title": d["title"], "description": d["description"], "h1": d["h1"], "lead": d["lead"],
                "intro": d.get("intro", []), "breadcrumbs": bc, "cta": {"servicio": d["servicio"], "label": d.get("cta_label")},
                "sections": d["sections"], "cta_final": d.get("cta_final"), "links": link_list([parent["route"]])}
        if d.get("hero"):
            page["hero_image"] = image(d["hero"], d.get("hero_alt") or name, hero_size(d["hero"]))
            node["image"] = "https://{{dominio}}" + d["hero"]
        apply_changes(page, d.get("cambios", []))
        add_links(page, d.get("enlaces", []))
        page["jsonld"] = {"@context": "https://schema.org",
                          "@graph": [node, breadcrumb_ld(bc)] + ([faq_ld(faqs)] if faqs else [])}
        # El pilar enlaza a la subpágina desde su subservicio (texto y catálogo del schema)
        if d.get("item_padre"):
            for section in parent["sections"]:
                for item in section.get("items", []):
                    if item["h3"] == d["item_padre"]:
                        item["url"] = route
            for n in parent["jsonld"]["@graph"]:
                for offer in n.get("hasOfferCatalog", {}).get("itemListElement", []):
                    if offer["itemOffered"]["name"] == d["item_padre"]:
                        offer["itemOffered"].update({"@id": service_id, "url": "https://{{dominio}}" + route})
        pages.insert(pages.index(parent) + 1, page)


# ── QA ───────────────────────────────────────────────────────────────────────────
def page_text(page: dict) -> str:
    parts = [page["h1"], page["lead"]]
    for section in page["sections"]:
        parts += section.get("paragraphs", []) + section.get("list", []) + section.get("factors", [])
        parts += [section.get("text", "")] + [plain(i["text"]) for i in section.get("items", []) + section.get("steps", [])]
        parts += [plain(m) for i in section.get("items", []) + section.get("steps", []) for m in i.get("more", [])]
        parts += [c["text"] for c in section.get("cards", [])]
        parts += [f["q"] + " " + f["a"] for f in section.get("faqs", [])]
        parts += [block_text(b) for b in section.get("blocks", []) + [x for x in section.get("intro", []) if isinstance(x, dict)]]
        parts += [plain(x) for x in section.get("intro", []) if not isinstance(x, dict)]
    return " ".join(p for p in parts if p)


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-záéíóúüñ]{3,}", text.lower()))


def jaccard(a: str, b: str) -> float:
    wa, wb = words(a), words(b)
    return len(wa & wb) / len(wa | wb) if wa | wb else 0.0


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    pages = build_pages()
    add_subpages(pages)
    for page in pages:
        page["title"] = TITLES.get(page["route"], page["title"])
        renames = H2.get(page["route"], {})
        for section in page["sections"]:
            section["h2"] = renames.pop(section.get("h2"), section.get("h2"))
        if renames:  # un H2 de la tabla que ya no existe en la página: avisar en vez de ignorarlo
            print(f"⚠ {page['route']}: H2 sin coincidencia en la tabla: {', '.join(renames)}")
    areas = [p for p in pages if p["type"] == "service-area"]
    if len(areas) > MAX_COMBOS:
        print(f"⚠ {len(areas)} combinaciones servicio × zona (> {MAX_COMBOS}): revisar coste y priorizar")

    texts = {p["route"]: page_text(p) for p in pages}
    similarity = {p["route"]: 0.0 for p in areas}
    for a, b in combinations(areas, 2):
        if a["params"]["servicio"] == b["params"]["servicio"] or a["params"]["zona"] == b["params"]["zona"]:
            j = jaccard(texts[a["route"]], texts[b["route"]])
            similarity[a["route"]] = max(similarity[a["route"]], j)
            similarity[b["route"]] = max(similarity[b["route"]], j)

    vocab = None if args.dry_run else bp.load_vocabulary()
    rejected, report = [], []
    for p in pages:
        errors = []
        if vocab:
            filled = bp.fill(p["jsonld"])
            bp.validate_node(filled, vocab, p["route"], errors)
            bp.google_checks(p["route"], filled, errors)
        if p["route"] in similarity and similarity[p["route"]] >= JACCARD_MAX:
            errors.append(f"similitud {similarity[p['route']]:.2f} ≥ {JACCARD_MAX} con una hermana")
        if p["type"] == "service-area":
            internal = [l for l in p["links"] if l["url"] not in bp.LEGAL]
            if not any(l["url"] == bp.pillar(p["params"]["servicio"]) for l in internal):
                errors.append("sin enlace al pilar")
        if errors:
            rejected.append((p["route"], errors))
        report.append({"route": p["route"], "type": p["type"], "words": len(texts[p["route"]].split()),
                       "jaccard_max": round(similarity.get(p["route"], 0), 2), "links": len(p["links"]),
                       "schema": "✗" if errors else ("✓" if vocab else "—")})

    for r in report:
        extra = f' · Jaccard máx {r["jaccard_max"]}' if r["type"] == "service-area" else ""
        print(f'  {r["schema"]} {r["route"]:<52} {r["type"]:<13} {r["words"]:>5} palabras · {r["links"]:>2} enlaces{extra}')
    if rejected:
        print("✗ Páginas rechazadas (no se escriben):")
        for route, errors in rejected:
            print(f"  - {route}: {'; '.join(errors)}")
    if args.dry_run:
        print(f"(dry-run) {len(pages)} páginas · {len(areas)} servicio × zona")
        return

    ok = [p for p in pages if p["route"] not in {r for r, _ in rejected}]
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    (WEB_DATA / "pages.json").write_text(json.dumps(
        {"generado": date.today().isoformat(), "aviso": "Generado por scripts/landing_generator.py: no editar a mano.",
         "pages": ok}, ensure_ascii=False, indent=1), encoding="utf-8")
    (WEB_DATA / "areas-served.json").write_text(json.dumps(
        {"zonas": bp.ZONES, "cobertura": bp.COVERAGE, "excluidas": bp.EXCLUDED}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    manifest = image_manifest(ok)
    with (ROOT / "web" / "IMAGENES.csv").open("w", encoding="utf-8-sig", newline="") as f:
        f.write("url;ruta;uso;tamaño;alt_propuesto;paginas\n")
        for s in manifest:
            f.write(f'{s["url"]};{s["ruta"]};{s["uso"]};{s["tamaño"]};{s["alt_propuesto"]};{" | ".join(s["paginas"])}\n')
    print(f"✓ {len(manifest)} huecos de foto → web/IMAGENES.csv")
    business = WEB_DATA / "business.json"
    if not business.exists():  # nunca se sobrescriben los datos reales del negocio
        business.write_text(json.dumps(BUSINESS_TEMPLATE, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {len(ok)}/{len(pages)} páginas escritas en web/src/data/pages.json · servicio × zona: {len(areas)}"
          + (f" (Jaccard máx {max(similarity.values()):.2f})" if similarity else "") + " · JSON-LD validado contra schema.org")


if __name__ == "__main__":
    main()
