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
from local_pack_multi_city import ROOT

CONTENT = bp.OUT / "content"
WEB_DATA = ROOT / "web" / "src" / "data"
JACCARD_MAX = 0.7
MAX_COMBOS = 50
BUSINESS_TEMPLATE = {
    "marca": "", "dominio": "", "telefono": "", "telefono_visible": "", "whatsapp": "", "email": "",
    "calle": "", "cp": "", "localidad": "", "provincia": "", "lat": "", "lng": "",
    "abre": "", "cierra": "", "horario_texto": "", "gbp_url": "", "logo_url": "", "imagen_url": "",
    "form_endpoint": "", "titular_legal": "", "nif": "", "domicilio_legal": "", "empresa_ejecutora": "",
    "indexable": False,  # la web no se indexa ni rastrea hasta ponerlo a true a propósito
    "publicar_precios": False, "proyectos": [], "testimonios": [],
}
PAGE_LABELS = {"/": "Inicio", "/presupuesto/": "Pide presupuesto", "/proyectos/": "Trabajos realizados",
               "/sobre-nosotros/": "Quiénes somos", "/aviso-legal/": "Aviso legal",
               "/politica-de-privacidad/": "Política de privacidad", "/cookies/": "Cookies"}
BUSINESS_ID = "https://{{dominio}}/#negocio"


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
    return {"@type": "Service", "@id": "https://{{dominio}}" + url + "#servicio", "name": name,
            "serviceType": service["service_type"], "description": description, "url": "https://{{dominio}}" + url,
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
    description = ("Cocinas, armarios y muebles a medida, rehabilitación de tejados y vigas de madera y carpintería "
                   "exterior. Taller propio. Presupuesto: {{telefono}}")
    home_faqs = home["faqs"]
    pages.append({
        "route": "/", "type": "home", "params": {},
        "title": "Carpintería de madera en Pontevedra y Santiago | {{marca}}", "description": description,
        "h1": "Carpintería de madera a medida en Pontevedra y Santiago", "lead": home["lead"],
        "breadcrumbs": [], "cta": {},
        "sections": [
            {"kind": "cards", "h2": "Qué hacemos", "cards": [
                {"title": s["name"], "text": services_copy[s["slug"]]["card"], "url": bp.pillar(s["slug"])}
                for s in bp.SERVICES]},
            {"kind": "items", "h2": "Por qué elegirnos", "items": home["why"]},
            process,
            {"kind": "projects", "h2": "Trabajos realizados", "service": None},
            {"kind": "testimonials", "h2": "Lo que dicen nuestros clientes"},
            {"kind": "links", "h2": "Dónde trabajamos", "text": home["where"], "links": link_list([bp.hub(z) for z in hubs])},
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
            "title": f'{s["name"]} en Pontevedra y Santiago | {{{{marca}}}}', "description": description,
            "h1": s["name"], "lead": copy["intro"], "breadcrumbs": bc, "cta": {"servicio": s["slug"]},
            "sections": [
                {"kind": "items", "h2": "Qué hacemos", "items": copy["subservices"]},
                process,
                price_section(s, copy, None),
                {"kind": "text", "h2": "Materiales y acabados", "paragraphs": copy["materials"]},
                {"kind": "links", "h2": "Dónde trabajamos", "text": coverage_text,
                 "links": link_list([bp.service_area(s["slug"], z) for z in s["zones"]])},
                {"kind": "projects", "h2": "Trabajos realizados", "service": s["slug"]},
                {"kind": "testimonials", "h2": "Opiniones"},
                {"kind": "faq", "h2": f'Preguntas frecuentes sobre {copy["topic"]}', "faqs": copy["faqs"]},
                {"kind": "links", "h2": "Servicios relacionados", "links": link_list([bp.pillar(r) for r in s["related"]])},
            ],
            "jsonld": {"@context": "https://schema.org", "@graph": [
                service_ld(s, url, s["name"], description, [city(z) for z in bp.ZONES]),
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
                     "links": link_list(same_zone + ([bp.hub(z)] if zone["hub"] else []) + [bp.pillar(s["slug"])])},
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
            "title": f'Carpintería en {zone["name"]}: cocinas, armarios y rehabilitación | {{{{marca}}}}',
            "description": description, "h1": f'Carpintería de madera en {zone["name"]}', "lead": copy["lead"],
            "breadcrumbs": bc, "cta": {"zona": z},
            "sections": [
                {"kind": "cards", "h2": f'Servicios en {zone["name"]}', "cards": cards},
                {"kind": "text", "h2": f'Dónde trabajamos en {zone["name"]}', "paragraphs": copy["paragraphs"],
                 "list_title": "Barrios y parroquias", "list": zone["areas"]},
                {"kind": "projects", "h2": f'Trabajos en {zone["name"]}', "service": None},
                {"kind": "links", "h2": "Zonas cercanas", "text": ", ".join(zone["nearby"]) + ".",
                 "links": link_list([bp.hub(o) for o in hubs if o != z])},
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
    return pages


# ── QA ───────────────────────────────────────────────────────────────────────────
def page_text(page: dict) -> str:
    parts = [page["h1"], page["lead"]]
    for section in page["sections"]:
        parts += section.get("paragraphs", []) + section.get("list", []) + section.get("factors", [])
        parts += [section.get("text", "")] + [i["text"] for i in section.get("items", []) + section.get("steps", [])]
        parts += [c["text"] for c in section.get("cards", [])]
        parts += [f["q"] + " " + f["a"] for f in section.get("faqs", [])]
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
    business = WEB_DATA / "business.json"
    if not business.exists():  # nunca se sobrescriben los datos reales del negocio
        business.write_text(json.dumps(BUSINESS_TEMPLATE, ensure_ascii=False, indent=2), encoding="utf-8")
    service_area_words = [r["words"] for r in report if r["type"] == "service-area"]
    print(f"✓ {len(ok)}/{len(pages)} páginas escritas en web/src/data/pages.json · servicio × zona: {len(areas)} "
          f"(palabras {min(service_area_words)}–{max(service_area_words)}, Jaccard máx "
          f"{max(similarity.values()):.2f}) · JSON-LD validado contra schema.org")


if __name__ == "__main__":
    main()
