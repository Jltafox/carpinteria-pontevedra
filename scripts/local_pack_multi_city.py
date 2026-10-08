"""
local-pack-multi-city · Local Pack + orgánico de Google en N ciudades, vía SerpAPI.

Implementa 03-skills/local-pack-multi-city/SKILL.md del repo
"Clase 1 · Agentes IA para SEO y webs hiperoptimizadas" (YinyangSEO Academy).

Uso:
    py scripts/local_pack_multi_city.py --dry-run    # muestra el plan; no gasta créditos
    py scripts/local_pack_multi_city.py              # captura + consolida
    py scripts/local_pack_multi_city.py --from-raw   # reconsolida desde raw/ sin llamar a la API

La clave se lee de la variable de entorno SERPAPI_KEY o del archivo .env de la raíz del
proyecto. El script nunca la imprime ni la guarda en los resultados.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import date
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from statistics import median
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent

# ── Configuración de esta ejecución ──────────────────────────────────────────────
KEYWORD = "carpintería"
# Conjuntos de puntos (--set). Cada punto: (slug, nombre, location canónica de SerpAPI para la SERP
# —resuelta con serpapi.com/locations.json; None si SerpAPI no la tiene—, centro de búsqueda en Maps).
CITY_SETS = {
    "clase": [  # ejercicio de la Clase 1
        ("santiago-de-compostela", "Santiago de Compostela", "Santiago de Compostela,Galicia,Spain",
         "@42.8782,-8.5448,14z"),
        ("pontevedra", "Pontevedra", "Pontevedra,Galicia,Spain", "@42.4299,-8.6446,14z"),
        ("barcelona", "Barcelona", "Barcelona,Catalonia,Spain", "@41.3851,2.1734,14z"),
        ("madrid-centro", "Madrid Centro", "Centro,Community of Madrid,Spain", "@40.4169,-3.7035,14z"),  # Sol
        ("valencia", "Valencia", "Valencia,Valencian Community,Spain", "@39.4699,-0.3763,14z"),  # Ayuntamiento
    ],
    "zona": [  # zona de trabajo del cliente (A Estrada ± 50 km); solo Maps: SerpAPI no tiene estas locations
        ("a-estrada", "A Estrada", None, "@42.6880,-8.4907,14z"),
        ("lalin", "Lalín", None, "@42.6614,-8.1110,14z"),
        ("caldas-de-reis", "Caldas de Reis", None, "@42.6044,-8.6422,14z"),
        ("vilagarcia-de-arousa", "Vilagarcía de Arousa", None, "@42.5961,-8.7653,14z"),
        ("padron", "Padrón", None, "@42.7386,-8.6603,14z"),
    ],
}


def use_set(name: str) -> None:
    global CITIES, MAPS_LL
    CITIES = [(slug, label, location) for slug, label, location, _ in CITY_SETS[name]]
    MAPS_LL = {slug: ll for slug, _, _, ll in CITY_SETS[name]}


CITIES: list[tuple[str, str, str | None]] = []
MAPS_LL: dict[str, str] = {}
use_set("clase")

TOP_PACK = 3
TOP_ORGANIC = 10
DEVICE = "mobile"
GOOGLE = {"google_domain": "google.es", "gl": "es", "hl": "es"}
MAX_REQUESTS = 10  # tope duro de créditos: 5 ciudades × máx. 2 páginas de orgánico
OVERLAP_MIN_CITIES = 2

# --maps · Local Pack desde Google Maps (1 crédito por punto), buscando desde el centro de MAPS_LL.
MAPS_TOP = 20  # Maps devuelve hasta 20 por página: top 3 = Local Pack, el resto se guarda como contexto

# Competidores citados en el briefing del cliente (Fervenza Mobiliario) y el propio cliente.
WATCHLIST = ["Fervenza", "Mucarce", "Pose Mato", "Muebles Mato", "Life Home", "Deco Ideas",
             "Carpintería Estelar", "Maisk Mobles"]

SERPAPI = "https://serpapi.com"

# Heurística para no confundir directorios/redes con negocios al leer el orgánico.
DOMAIN_TYPES = {
    "habitissimo.es": "directorio", "cronoshare.com": "directorio",
    "starofservice.es": "directorio", "paginasamarillas.es": "directorio",
    "infoisinfo.es": "directorio", "cylex.es": "directorio", "qdq.com": "directorio",
    "vulka.es": "directorio", "empresite.eleconomista.es": "directorio",
    "einforma.com": "directorio", "axesor.es": "directorio", "infoempresa.com": "directorio",
    "guiaempresas.universia.es": "directorio", "yelp.es": "directorio", "yelp.com": "directorio",
    "tripadvisor.es": "directorio", "houzz.es": "directorio", "milanuncios.com": "directorio",
    "wallapop.com": "directorio", "google.com": "google", "google.es": "google",
    "facebook.com": "red social", "instagram.com": "red social", "youtube.com": "red social",
    "tiktok.com": "red social", "linkedin.com": "red social", "pinterest.com": "red social",
    "pinterest.es": "red social", "x.com": "red social", "twitter.com": "red social",
    "wikipedia.org": "informativo", "rae.es": "informativo", "definicion.de": "informativo",
    "significados.com": "informativo", "conceptodefinicion.de": "informativo",
}
SERP_META_KEYS = {"search_metadata", "search_parameters", "search_information",
                  "serpapi_pagination", "pagination", "error"}


# ── Utilidades ───────────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", " ", text)  # puntuación no ASCII (–, ·…) → separador
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def domain_of(url: str | None) -> str | None:
    host = urlparse(url).hostname if url else None
    if not host:
        return None
    return host[4:] if host.startswith("www.") else host


def domain_type(domain: str | None) -> str | None:
    if not domain:
        return None
    for known, kind in DOMAIN_TYPES.items():
        if domain == known or domain.endswith("." + known):
            return kind
    return "negocio/otro"


def to_int(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower().strip("()")
    number = re.search(r"\d+(?:[.,]\d+)*", text)
    if not number:
        return None
    if re.search(r"\d\s*(k|mil)\b", text):  # "1,2 mil", "1.2K"
        return int(float(number.group().replace(",", ".")) * 1000)
    return int(re.sub(r"[.,]", "", number.group()))


def to_float(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def find_key() -> str:
    key = os.environ.get("SERPAPI_KEY", "").strip()
    env_file = ROOT / ".env"
    if not key and env_file.exists():
        raw = env_file.read_bytes()
        # PowerShell 5.1 guarda en UTF-16 con ">"; el Bloc de notas, en UTF-8 (a veces con BOM).
        text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", "replace")
        for line in text.splitlines():
            name, sep, value = line.strip().partition("=")
            if sep and name.strip() == "SERPAPI_KEY":
                key = value.strip().strip('"').strip("'")
    return key


def save_json(path: Path, data, secret: str | None = None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if secret:
        text = text.replace(secret, "***")
    path.write_text(text, encoding="utf-8")


# ── SerpAPI ──────────────────────────────────────────────────────────────────────
def get_json(path: str, params: dict) -> dict:
    url = f"{SERPAPI}/{path}?{urlencode(params)}"
    try:
        with urlopen(url, timeout=120) as resp:
            return json.load(resp)
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            message = json.loads(body).get("error") or body[:200]
        except ValueError:
            message = body[:200]
        raise RuntimeError(f"HTTP {e.code}: {message}") from None
    except URLError as e:
        raise RuntimeError(f"sin conexión con SerpAPI ({e.reason})") from None


def account_credits(key: str) -> dict:
    """Créditos de la cuenta (gratis). La respuesta trae email y clave: solo se guardan números."""
    account = get_json("account.json", {"api_key": key})
    return {k: account.get(k) for k in ("plan_name", "searches_per_month", "plan_searches_left",
                                        "extra_credits", "total_searches_left", "this_month_usage",
                                        "account_rate_limit_per_hour", "this_hour_searches")}


def capture(key: str, raw_dir: Path) -> int:
    raw_dir.mkdir(parents=True, exist_ok=True)
    used = 0
    for slug, label, location in CITIES:
        (raw_dir / f"{slug}-p2.json").unlink(missing_ok=True)  # no mezclar con ejecuciones previas
        params = {"engine": "google", "q": KEYWORD, "location": location,
                  "device": DEVICE, **GOOGLE, "api_key": key}
        try:
            used += 1
            page = get_json("search.json", params)
            save_json(raw_dir / f"{slug}.json", page, key)
            n_organic = len(page.get("organic_results") or [])
            status = f"pack {len(pack_places(page))} · orgánico {n_organic}"
            if page.get("error"):
                status = f"sin resultados ({page['error']})"
            elif n_organic < TOP_ORGANIC and used < MAX_REQUESTS:
                used += 1
                page2 = get_json("search.json", {**params, "start": 10})
                save_json(raw_dir / f"{slug}-p2.json", page2, key)
                status += f" + {len(page2.get('organic_results') or [])} (pág. 2)"
            print(f"  ✓ {label}: {status}")
        except RuntimeError as e:
            save_json(raw_dir / f"{slug}.json", {"error": str(e)}, key)
            print(f"  ✗ {label}: {e}")
        time.sleep(1)
    return used


def capture_maps(key: str, raw_dir: Path) -> int:
    raw_dir.mkdir(parents=True, exist_ok=True)
    used = 0
    for slug, label, _ in CITIES:
        params = {"engine": "google_maps", "type": "search", "q": KEYWORD, "ll": MAPS_LL[slug],
                  **GOOGLE, "api_key": key}
        try:
            used += 1
            page = get_json("search.json", params)
            save_json(raw_dir / f"maps-{slug}.json", page, key)
            status = (f"sin resultados ({page['error']})" if page.get("error")
                      else f"{len(maps_places(page))} negocios")
            print(f"  ✓ {label} (Maps): {status}")
        except RuntimeError as e:
            save_json(raw_dir / f"maps-{slug}.json", {"error": str(e)}, key)
            print(f"  ✗ {label} (Maps): {e}")
        time.sleep(1)
    return used


# ── Extracción por ciudad ────────────────────────────────────────────────────────
def pack_places(page: dict) -> list[dict]:
    places = page.get("local_results")
    if isinstance(places, dict):
        places = places.get("places")
    return [p for p in (places or []) if isinstance(p, dict)]


def maps_places(page: dict) -> list[dict]:
    """Resultados orgánicos de Google Maps (sin fichas patrocinadas)."""
    return [p for p in page.get("local_results") or []
            if isinstance(p, dict) and not p.get("sponsored")]


def pack_entry(place: dict, index: int) -> dict:
    links = place.get("links") or {}
    gps = place.get("gps_coordinates") or {}
    website = links.get("website") or place.get("website")
    reviews = place.get("reviews") if place.get("reviews") is not None else place.get("reviews_original")
    return {
        "position": place.get("position") or index,
        "name": place.get("title"),
        "place_id": place.get("place_id"),
        "data_cid": place.get("data_cid"),
        "category": place.get("type"),
        "types": place.get("types") or [],
        "unclaimed": bool(place.get("unclaimed_listing")),
        "rating": to_float(place.get("rating")),
        "reviews": to_int(reviews),
        "address": place.get("address"),
        "phone": place.get("phone"),
        "lat": gps.get("latitude"),
        "lng": gps.get("longitude"),
        "website": website,
        "domain": domain_of(website),
        "snippet": place.get("description") or place.get("snippet"),
    }


def snippet_type(result: dict) -> list[str]:
    features = []
    rich = result.get("rich_snippet")
    if rich:
        features.append("estrellas" if "rating" in json.dumps(rich) else "rich snippet")
    for key, label in (("sitelinks", "sitelinks"), ("date", "fecha"), ("thumbnail", "imagen")):
        if result.get(key):
            features.append(label)
    return features or ["estándar"]


def organic_entries(pages: list[dict]) -> list[dict]:
    entries, seen = [], set()
    for page in pages:
        for result in page.get("organic_results") or []:
            url = result.get("link")
            if not url or url in seen:
                continue
            seen.add(url)
            domain = domain_of(url)
            entries.append({
                "rank": len(entries) + 1,
                "serp_position": result.get("position"),
                "title": result.get("title"),
                "url": url,
                "domain": domain,
                "domain_type": domain_type(domain),
                "description": result.get("snippet"),
                "snippet_type": snippet_type(result),
            })
            if len(entries) == TOP_ORGANIC:
                return entries
    return entries


def serp_snapshot(first: dict) -> dict:
    ai = first.get("ai_overview")
    answer = first.get("answer_box") or {}
    if isinstance(answer, list):
        answer = answer[0] if answer else {}
    local = first.get("local_results")
    return {
        "blocks": [k for k in first if k not in SERP_META_KEYS],
        "ai_overview": bool(ai),
        "ai_overview_needs_extra_call": bool(isinstance(ai, dict) and ai.get("page_token") and not ai.get("text_blocks")),
        "featured_snippet": (answer.get("title") or answer.get("snippet") or answer.get("answer")
                             or answer.get("type")) if answer else None,
        "people_also_ask": [q["question"] for q in first.get("related_questions") or []
                            if isinstance(q, dict) and q.get("question")],
        "related_searches": [s["query"] for s in first.get("related_searches") or []
                             if isinstance(s, dict) and s.get("query")],
        "knowledge_graph": (first.get("knowledge_graph") or {}).get("title"),
        "local_pack_places_shown": len(pack_places(first)),
        "local_pack_more_places": bool(isinstance(local, dict) and local.get("more_locations_link")),
    }


def local_links(page: dict) -> list[dict]:
    """Negocios que Google enlaza en el bloque móvil ask_ai_mode: solo web o nombre, sin datos de ficha."""
    links = []
    for item in page.get("ask_ai_mode") or []:
        url = item.get("link") or ""
        domain = domain_of(url) or ""
        if domain.startswith("google."):  # negocio sin web: Google enlaza una búsqueda con su nombre
            name = parse_qs(urlparse(url).query).get("q", [""])[0].strip()
            links.append({"position": item.get("position"), "name": name or None, "domain": None, "url": None})
        elif domain:
            links.append({"position": item.get("position"), "name": None, "domain": domain, "url": url})
    return links


def load_pages(raw_dir: Path, slug: str) -> list[dict]:
    pages = []
    for name in (f"{slug}.json", f"{slug}-p2.json"):
        path = raw_dir / name
        if path.exists():
            pages.append(json.loads(path.read_text(encoding="utf-8")))
    return pages


def load_maps(raw_dir: Path, slug: str) -> dict | None:
    path = raw_dir / f"maps-{slug}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def parse_city(slug: str, label: str, location: str, pages: list[dict], maps_page: dict | None = None) -> dict:
    city = {"slug": slug, "city": label, "location": location, "error": None,
            "local_pack_source": None, "local_pack_missing": True, "local_pack": [], "maps_top": [],
            "local_links": [], "organic": [], "serp": {}, "warnings": []}
    if not pages and maps_page is None:
        city["error"] = "sin datos: la ciudad no se capturó"
    elif pages:
        first = pages[0]
        city["error"] = first.get("error")
        city["local_pack"] = [pack_entry(p, i) for i, p in enumerate(pack_places(first)[:TOP_PACK], 1)]
        city["local_links"] = local_links(first)
        city["organic"] = organic_entries(pages)
        city["serp"] = serp_snapshot(first)
    # ¿Mostró Google el pack en la SERP? None si la SERP no se capturó (ejecución solo Maps).
    city["local_pack_missing"] = (not city["local_pack"]) if pages else None
    if city["local_pack"]:
        city["local_pack_source"] = "google_search"
    if maps_page is not None:
        city["maps_top"] = [{**pack_entry(p, i), "position": i}
                            for i, p in enumerate(maps_places(maps_page)[:MAPS_TOP], 1)]
        if city["maps_top"]:  # Maps es la fuente del ranking local: su top 3 hace de Local Pack
            city["local_pack"] = city["maps_top"][:TOP_PACK]
            city["local_pack_source"] = "google_maps"

    warnings = city["warnings"]
    if city["error"]:
        warnings.append(f"error: {city['error']}")
    elif city["local_pack_missing"]:
        warnings.append("local_pack_missing: Google no mostró Local Pack en la SERP"
                        + (" (top 3 tomado de Google Maps)" if city["local_pack_source"] == "google_maps" else ""))
    if maps_page is not None and maps_page.get("error"):
        warnings.append(f"Maps: {maps_page['error']}")
    elif maps_page is not None and not city["maps_top"]:
        warnings.append("Maps no devolvió negocios")
    zero = [p["name"] for p in city["local_pack"] if p["reviews"] == 0]
    if zero:
        warnings.append("0 reseñas (¿limited view?): " + ", ".join(zero))
    if pages and not city["error"] and len(city["organic"]) < TOP_ORGANIC:
        warnings.append(f"solo {len(city['organic'])} resultados orgánicos")
    return city


# ── Consolidación ────────────────────────────────────────────────────────────────
def consolidate(cities: list[dict]) -> tuple[list[dict], list[dict]]:
    domains: dict[str, dict] = {}
    for city in cities:
        for r in city["organic"]:
            if not r["domain"]:
                continue
            entry = domains.setdefault(r["domain"], {
                "domain": r["domain"], "domain_type": r["domain_type"], "n_cities": 0,
                "cities_seen": [], "positions": {}, "best_rank": None, "urls": [], "titles": []})
            if city["city"] not in entry["cities_seen"]:  # el primer resultado es el mejor rank
                entry["cities_seen"].append(city["city"])
                entry["positions"][city["city"]] = r["rank"]
            if r["url"] not in entry["urls"]:
                entry["urls"].append(r["url"])
            if r["title"] and r["title"] not in entry["titles"]:
                entry["titles"].append(r["title"])
    for entry in domains.values():
        entry["n_cities"] = len(entry["cities_seen"])
        entry["best_rank"] = min(entry["positions"].values())

    raw: dict[str, dict] = {}
    for city in cities:
        for p in city["local_pack"]:
            key = p["place_id"] or p["data_cid"] or "name:" + slugify(p["name"] or "?")
            b = raw.setdefault(key, {"name": p["name"], "place_id": p["place_id"], "domain": None,
                                     "website": None, "categories": [], "cities_seen": [],
                                     "pack_positions": {}, "ratings": [], "reviews": [],
                                     "address": p["address"], "phone": p["phone"],
                                     "lat": p["lat"], "lng": p["lng"]})
            b["domain"] = b["domain"] or p["domain"]
            b["website"] = b["website"] or p["website"]
            for category in p["types"] or [p["category"]]:
                if category and category not in b["categories"]:
                    b["categories"].append(category)
            if city["city"] not in b["cities_seen"]:
                b["cities_seen"].append(city["city"])
            b["pack_positions"][city["city"]] = p["position"]
            if p["rating"] is not None:
                b["ratings"].append(p["rating"])
            if p["reviews"] is not None:
                b["reviews"].append(p["reviews"])

    businesses = []
    for b in raw.values():
        # Solo cruzamos con el orgánico si la web es propia (no Facebook, directorios…).
        organic = domains.get(b["domain"]) if domain_type(b["domain"]) == "negocio/otro" else None
        businesses.append({
            "name": b["name"],
            "place_id": b["place_id"],
            "domain": b["domain"],
            "categories": b["categories"],
            "cities_seen": b["cities_seen"],
            "n_cities": len(b["cities_seen"]),
            "avg_rating": round(sum(b["ratings"]) / len(b["ratings"]), 2) if b["ratings"] else None,
            "total_reviews": max(b["reviews"]) if b["reviews"] else None,
            "pack_positions": b["pack_positions"],
            "organic_positions": dict(organic["positions"]) if organic else {},
            "website": b["website"],
            "address": b["address"],
            "phone": b["phone"],
            "lat": b["lat"],
            "lng": b["lng"],
        })
    businesses.sort(key=lambda b: (-b["n_cities"], min(b["pack_positions"].values())))
    organic_domains = sorted(domains.values(), key=lambda e: (-e["n_cities"], e["best_rank"]))
    return businesses, organic_domains


def compact(text: str | None) -> str:
    return slugify(text or "").replace("-", "")


def watchlist_hits(cities: list[dict]) -> dict[str, list[str]]:
    """Dónde aparece cada competidor vigilado: Maps, orgánico o bloque ask_ai_mode."""
    hits: dict[str, list[str]] = {}
    for name in WATCHLIST:
        term = compact(name)
        found = hits[name] = []
        for c in cities:
            for p in c["maps_top"] or c["local_pack"]:
                if term in compact(p["name"]) or term in compact(p["domain"]):
                    found.append(f'{c["city"]} · Maps #{p["position"]}')
            for r in c["organic"]:
                if term in compact(r["title"]) or term in compact(r["domain"]):
                    found.append(f'{c["city"]} · orgánico #{r["rank"]}')
            for link in c["local_links"]:
                if term in compact(link["name"]) or term in compact(link["domain"]):
                    found.append(f'{c["city"]} · ask_ai_mode #{link["position"]}')
    return hits


# ── Salidas ──────────────────────────────────────────────────────────────────────
def csv_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return str(value).replace(".", ",")  # Excel en español usa coma decimal
    if isinstance(value, dict):
        return " | ".join(f"{k}: {v}" for k, v in value.items())
    if isinstance(value, list):
        return " | ".join(str(v) for v in value)
    return str(value)


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    # ";" + BOM para que Excel en español lo abra bien con doble clic.
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([csv_value(row.get(c)) for c in columns])


def cell(value) -> str:
    if value in (None, "", [], {}):
        return "—"
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def positions_text(positions: dict) -> str:
    return " · ".join(f"{city} #{pos}" for city, pos in positions.items())


def write_report(path: Path, meta: dict, cities: list[dict], businesses: list[dict],
                 domains: list[dict], watch: dict[str, list[str]]) -> None:
    lines: list[str] = []
    add = lines.append
    add(f'# Local Pack multi-ciudad · "{meta["keyword"]}"')
    add("")
    add(f'> Skill `local-pack-multi-city` · {meta["date"]} · {meta["device"]} · google.es (hl=es) · SerpAPI  ')
    add(f'> Top {TOP_PACK} Local Pack + top {TOP_ORGANIC} orgánico · {len(cities)} ciudades · '
        f'peticiones: {cell(meta.get("requests_made"))} · créditos consumidos: {cell(meta.get("credits_used"))}  ')
    if any(c["local_pack_source"] == "google_maps" for c in cities):
        add(f"> Local Pack = top {TOP_PACK} de Google Maps buscando desde el centro de cada ciudad (zoom 14z); "
            f"el top {MAPS_TOP} completo está en `maps-top.csv`.")
    add("")

    add("## Resumen por ciudad")
    add("")
    add("| Ciudad | Local Pack | Orgánico | AI Overview | Featured snippet | PAA | Avisos |")
    add("|---|:-:|:-:|:-:|:-:|:-:|---|")
    for c in cities:
        s = c["serp"]
        add(f'| {c["city"]} | {len(c["local_pack"])} | {len(c["organic"])} | '
            f'{"sí" if s.get("ai_overview") else "no"} | {"sí" if s.get("featured_snippet") else "no"} | '
            f'{len(s.get("people_also_ask") or [])} | {cell("; ".join(c["warnings"]))} |')
    add("")

    add(f"## Local Pack por ciudad (top {TOP_PACK})")
    for c in cities:
        add("")
        source = {"google_maps": " · Google Maps", "google_search": " · SERP"}.get(c["local_pack_source"] or "", "")
        add(f'### {c["city"]}{source}')
        add("")
        if not c["local_pack"]:
            add("_Sin Local Pack._")
            continue
        add("| # | Negocio | Categoría | ★ | Reseñas | Web |")
        add("|:-:|---|---|:-:|:-:|---|")
        for p in c["local_pack"]:
            add(f'| {p["position"]} | {cell(p["name"])} | {cell(p["category"])} | {cell(p["rating"])} | '
                f'{cell(p["reviews"])} | {cell(p["domain"])} |')
    add("")

    add_watch_section(add, watch)

    if any(c["local_links"] for c in cities):
        add("## Negocios locales enlazados por Google (bloque móvil `ask_ai_mode`)")
        add("")
        add("_Google los asocia a la búsqueda en cada ciudad, pero este bloque no trae ficha "
            "(sin place_id, valoración ni reseñas)._")
        for c in cities:
            add("")
            add(f'**{c["city"]}:** ' + (", ".join(
                f'{link["domain"]}' if link["domain"] else f'{link["name"]} (sin web)'
                for link in c["local_links"]) or "—"))
        add("")

    add("## Top orgánico por ciudad")
    for c in cities:
        add("")
        add(f'### {c["city"]}')
        add("")
        if not c["organic"]:
            add("_Sin resultados orgánicos._")
            continue
        add("| # | Dominio | Tipo | Título | Snippet |")
        add("|:-:|---|---|---|---|")
        for r in c["organic"]:
            add(f'| {r["rank"]} | {cell(r["domain"])} | {cell(r["domain_type"])} | {cell(r["title"])} | '
                f'{cell(r["snippet_type"])} |')
    add("")

    add(f"## Overlap · negocios del Local Pack en ≥ {OVERLAP_MIN_CITIES} ciudades")
    add("")
    multi = [b for b in businesses if b["n_cities"] >= OVERLAP_MIN_CITIES]
    if not businesses:
        add("_Sin datos: Google no mostró Local Pack en ninguna ciudad._")
    elif multi:
        add("| Negocio | Ciudades | Posiciones en el pack | Web |")
        add("|---|:-:|---|---|")
        for b in multi:
            add(f'| {cell(b["name"])} | {b["n_cities"]} | {positions_text(b["pack_positions"])} | {cell(b["domain"])} |')
    else:
        add("_Ningún negocio se repite en el Local Pack de varias ciudades: en esta muestra el pack es 100 % local._")
    add("")

    add(f"## Overlap · dominios orgánicos en ≥ {OVERLAP_MIN_CITIES} ciudades")
    add("")
    multi = [d for d in domains if d["n_cities"] >= OVERLAP_MIN_CITIES]
    if multi:
        add("| Dominio | Tipo | Ciudades | Posiciones |")
        add("|---|---|:-:|---|")
        for d in multi:
            add(f'| {d["domain"]} | {cell(d["domain_type"])} | {d["n_cities"]} | {positions_text(d["positions"])} |')
    else:
        add("_Ningún dominio orgánico se repite entre ciudades._")
    add("")

    add("## Negocios del Local Pack que también rankean en orgánico")
    add("")
    both = [b for b in businesses if b["organic_positions"]]
    if not businesses:
        add("_Sin datos de Local Pack._")
    elif both:
        for b in both:
            add(f'- **{b["name"]}** ({b["domain"]}): pack {positions_text(b["pack_positions"])} · '
                f'orgánico {positions_text(b["organic_positions"])}')
    else:
        add("_Ninguno: las webs de los negocios del pack no aparecen en el top orgánico._")
    add("")

    add("## Preguntas (PAA) y búsquedas relacionadas")
    add("")
    for title, field in (("Preguntas relacionadas", "people_also_ask"), ("Búsquedas relacionadas", "related_searches")):
        seen: dict[str, list[str]] = {}
        for c in cities:
            for item in c["serp"].get(field) or []:
                seen.setdefault(item, []).append(c["city"])
        add(f"**{title}:**")
        add("")
        if seen:
            for item, where in sorted(seen.items(), key=lambda kv: -len(kv[1])):
                add(f"- {item} _({', '.join(where)})_")
        else:
            add("- —")
        add("")

    add("## Bloques de la SERP")
    add("")
    for c in cities:
        blocks = c["serp"].get("blocks") or []
        extra = " · AI Overview requiere petición extra (no realizada)" if c["serp"].get("ai_overview_needs_extra_call") else ""
        add(f'- **{c["city"]}:** {", ".join(blocks) or "—"}{extra}')
    add("")

    add("## QA")
    add("")
    issues = [f'- **{c["city"]}:** {w}' for c in cities for w in c["warnings"]]
    lines.extend(issues or ["- Sin incidencias."])
    add("")

    add("## Siguiente paso")
    add("")
    n_places = sum(1 for b in businesses if b["place_id"])
    n_domains = sum(1 for d in domains if d["domain_type"] == "negocio/otro")
    add(f"- `consolidated.json` → **gbp-deep-profile**: {n_places} place_id únicos.")
    add(f"- `consolidated.json` → **web-pattern-extractor**: {n_domains} dominios de negocio "
        f"(sin directorios, redes ni webs informativas).")
    linked = {link["domain"] for c in cities for link in c["local_links"]
              if link["domain"] and domain_type(link["domain"]) == "negocio/otro"}
    if linked:
        add(f"- Webs de negocios locales enlazadas por Google (`ask_ai_mode`): {len(linked)} dominios, "
            f"candidatos más locales que el orgánico para **web-pattern-extractor**.")
    add("")
    path.write_text("\n".join(lines), encoding="utf-8")


def point_of(ll: str) -> tuple[float, float]:
    lat, lng = ll.lstrip("@").split(",")[:2]
    return float(lat), float(lng)


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distancia en línea recta (haversine)."""
    lat1, lng1, lat2, lng2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(h))


def fmt(number: float | None, digits: int = 1) -> str:
    return "—" if number is None else f"{number:.{digits}f}".replace(".", ",")


def add_watch_section(add, watch: dict[str, list[str]]) -> None:
    if not watch:
        return
    add("## Competidores del briefing")
    add("")
    add(f"_Búsqueda por nombre o dominio en el top {MAPS_TOP} de Maps, el orgánico y el bloque `ask_ai_mode`._")
    add("")
    add("| Competidor | Dónde aparece |")
    add("|---|---|")
    for name, found in watch.items():
        add(f"| {name} | {cell('; '.join(found)) if found else 'no aparece'} |")
    add("")


def write_maps_report(path: Path, meta: dict, cities: list[dict], watch: dict[str, list[str]]) -> None:
    """Informe de una ejecución solo Maps: nivel de la competencia local en cada punto de búsqueda."""
    lines: list[str] = []
    add = lines.append
    add(f'# Google Maps por punto · "{meta["keyword"]}"')
    add("")
    add(f'> Skill `local-pack-multi-city` (solo Maps) · {meta["date"]} · {len(cities)} puntos · zoom 14z · '
        f'top {MAPS_TOP} por punto · peticiones: {cell(meta.get("requests_made"))} · '
        f'créditos consumidos: {cell(meta.get("credits_used"))}')
    add("")

    add("## Nivel de la competencia por punto")
    add("")
    add("| Punto | Reseñas top 3 | Mediana reseñas top 10 | ★ media top 3 | Distancia top 3 (km) | "
        "Con web (top 10) | Sin reclamar (top 20) | Categoría más común (top 20) |")
    add("|---|:-:|:-:|:-:|:-:|:-:|:-:|---|")
    for c in cities:
        top3, top10, top20 = c["maps_top"][:TOP_PACK], c["maps_top"][:10], c["maps_top"]
        if not top20:
            add(f'| {c["city"]} | — | — | — | — | — | — | — |')
            continue
        center = point_of(MAPS_LL[c["slug"]])
        ratings = [p["rating"] for p in top3 if p["rating"] is not None]
        dists = [km(center, (p["lat"], p["lng"])) for p in top3 if p["lat"] is not None and p["lng"] is not None]
        category = Counter(p["category"] for p in top20 if p["category"]).most_common(1)
        add(f'| {c["city"]} | {" · ".join(str(p["reviews"] or 0) for p in top3)} | '
            f'{fmt(median([p["reviews"] or 0 for p in top10]), 0)} | '
            f'{fmt(sum(ratings) / len(ratings)) if ratings else "—"} | '
            f'{"media " + fmt(sum(dists) / len(dists)) + " · máx " + fmt(max(dists)) if dists else "—"} | '
            f'{sum(1 for p in top10 if p["domain"])}/{len(top10)} | '
            f'{sum(1 for p in top20 if p["unclaimed"])}/{len(top20)} | '
            f'{cell(f"{category[0][0]} ({category[0][1]})") if category else "—"} |')
    add("")

    add(f"## Top {TOP_PACK} por punto")
    for c in cities:
        add("")
        add(f'### {c["city"]}')
        add("")
        if not c["local_pack"]:
            add("_Sin resultados._")
            continue
        center = point_of(MAPS_LL[c["slug"]])
        add("| # | Negocio | Categoría | ★ | Reseñas | km | Web |")
        add("|:-:|---|---|:-:|:-:|:-:|---|")
        for p in c["local_pack"]:
            dist = km(center, (p["lat"], p["lng"])) if p["lat"] is not None and p["lng"] is not None else None
            add(f'| {p["position"]} | {cell(p["name"])} | {cell(p["category"])} | {cell(p["rating"])} | '
                f'{cell(p["reviews"])} | {fmt(dist)} | {cell(p["domain"])} |')
    add("")

    add_watch_section(add, watch)

    add(f"## Negocios presentes en ≥ {OVERLAP_MIN_CITIES} puntos (top {MAPS_TOP})")
    add("")
    seen: dict[str, dict] = {}
    for c in cities:
        for p in c["maps_top"]:
            entry = seen.setdefault(p["place_id"] or compact(p["name"]), {"place": p, "where": {}})
            entry["where"][c["city"]] = p["position"]
    multi = sorted((e for e in seen.values() if len(e["where"]) >= OVERLAP_MIN_CITIES),
                   key=lambda e: (-len(e["where"]), min(e["where"].values())))
    if multi:
        add("| Negocio | Categoría | ★ | Reseñas | Puntos (posición) |")
        add("|---|---|:-:|:-:|---|")
        for e in multi:
            p = e["place"]
            add(f'| {cell(p["name"])} | {cell(p["category"])} | {cell(p["rating"])} | {cell(p["reviews"])} | '
                f'{positions_text(e["where"])} |')
    else:
        add("_Ningún negocio aparece en más de un punto._")
    add("")

    add(f"## Categorías principales (negocios únicos del top {MAPS_TOP})")
    add("")
    add("| Categoría | Negocios |")
    add("|---|:-:|")
    categories = Counter(e["place"]["category"] for e in seen.values() if e["place"]["category"])
    for name, count in categories.most_common(10):
        add(f"| {cell(name)} | {count} |")
    add("")

    add("## QA")
    add("")
    issues = [f'- **{c["city"]}:** {w}' for c in cities for w in c["warnings"]]
    lines.extend(issues or ["- Sin incidencias."])
    add("")

    add("## Siguiente paso")
    add("")
    add(f"- `maps-top.csv` / `consolidated.json` → **gbp-deep-profile**: {len(seen)} negocios únicos "
        f"(top {MAPS_TOP} de {len(cities)} puntos).")
    add("")
    path.write_text("\n".join(lines), encoding="utf-8")


def build_outputs(out: Path, run: dict) -> str:
    raw_dir = out / "raw"
    cities = [parse_city(slug, label, location, load_pages(raw_dir, slug), load_maps(raw_dir, slug))
              for slug, label, location in CITIES]
    businesses, domains = consolidate(cities)
    watch = watchlist_hits(cities)
    maps_used = any(c["maps_top"] for c in cities)
    meta = {
        "skill": "local-pack-multi-city",
        "keyword": KEYWORD,
        "date": run.get("date") or out.name,
        "device": DEVICE,
        **GOOGLE,
        "top_pack": TOP_PACK,
        "top_organic": TOP_ORGANIC,
        "source": "SerpAPI · engine=google" + (" + engine=google_maps (Local Pack)" if maps_used else ""),
        "cities": [{"city": label, "location": location, **({"maps_ll": MAPS_LL[slug]} if maps_used else {})}
                   for slug, label, location in CITIES],
        **{k: v for k, v in run.items() if k != "date"},
    }
    save_json(out / "consolidated.json",
              {"meta": meta, "businesses": businesses, "organic_domains": domains, "watchlist": watch,
               "cities": cities})
    if maps_used:
        write_csv(out / "maps-top.csv", [{"city": c["city"], **p} for c in cities for p in c["maps_top"]],
                  ["city", "position", "name", "category", "rating", "reviews", "domain", "address", "phone",
                   "place_id", "lat", "lng", "website"])
    write_csv(out / "consolidated.csv", businesses,
              ["name", "place_id", "domain", "categories", "cities_seen", "n_cities", "pack_positions",
               "avg_rating", "total_reviews", "organic_positions", "address", "phone", "lat", "lng", "website"])
    serp_used = any(c["organic"] or c["serp"] for c in cities)
    if serp_used:
        write_csv(out / "organic-domains.csv", domains,
                  ["domain", "domain_type", "n_cities", "cities_seen", "positions", "best_rank", "urls", "titles"])
        write_report(out / "overlap-report.md", meta, cities, businesses, domains, watch)
    else:  # ejecución solo Maps
        write_maps_report(out / "overlap-report.md", meta, cities, watch)

    try:
        shown = out.resolve().relative_to(ROOT)
    except ValueError:
        shown = out
    summary = [f"✓ Resultados en {shown}",
               f"  negocios únicos en Local Pack: {len(businesses)} "
               f"(en ≥{OVERLAP_MIN_CITIES} puntos: {sum(b['n_cities'] >= OVERLAP_MIN_CITIES for b in businesses)})"]
    if serp_used:
        summary.append(f"  dominios orgánicos únicos: {len(domains)} "
                       f"(en ≥{OVERLAP_MIN_CITIES} puntos: {sum(d['n_cities'] >= OVERLAP_MIN_CITIES for d in domains)})")
    if maps_used:
        summary.append(f"  negocios en Maps: {sum(len(c['maps_top']) for c in cities)} (top {MAPS_TOP} por punto)")
    summary += [f"  competidores del briefing encontrados: {sum(bool(f) for f in watch.values())}/{len(watch)}",
                f"  avisos QA: {sum(len(c['warnings']) for c in cities)}"]
    return "\n".join(summary)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="muestra el plan sin llamar a la API")
    parser.add_argument("--from-raw", action="store_true", help="reconsolida desde raw/ sin gastar créditos")
    parser.add_argument("--maps", action="store_true",
                        help="Local Pack desde Google Maps (1 crédito por ciudad); se suma a la captura del día")
    parser.add_argument("--set", choices=sorted(CITY_SETS), default="clase",
                        help="conjunto de puntos: clase (5 ciudades del ejercicio) o zona (zona del cliente, solo Maps)")
    parser.add_argument("--out", type=Path, help="carpeta de salida (por defecto data/local-pack/<keyword>/<fecha>)")
    args = parser.parse_args()
    use_set(args.set)

    folder = date.today().isoformat() + ("" if args.set == "clase" else f"-{args.set}")
    out = args.out or ROOT / "data" / "local-pack" / slugify(KEYWORD) / folder
    raw_dir = out / "raw"

    if args.dry_run:
        print(f'Keyword: "{KEYWORD}" · conjunto "{args.set}" · {DEVICE} · google.es (gl=es, hl=es)')
        for slug, label, location in CITIES:
            print(f"  · {label:<24} location={location or '— (solo Maps)'} · maps={MAPS_LL[slug]}")
        print(f"Top {TOP_PACK} Local Pack + top {TOP_ORGANIC} orgánico · máx. {MAX_REQUESTS} créditos")
        print(f"--maps: Google Maps desde el centro de cada ciudad · {len(CITIES)} créditos")
        print(f"Salida: {out}")
        print("SERPAPI_KEY:", "encontrada" if find_key() else "NO encontrada (rellena .env)")
        return

    if args.from_raw:
        if not raw_dir.is_dir():
            sys.exit(f"✗ No existe {raw_dir}")
        run_file = raw_dir / "run.json"
        run = json.loads(run_file.read_text(encoding="utf-8")) if run_file.exists() else {}
    else:
        if not args.maps and any(location is None for _, _, location in CITIES):
            sys.exit(f'✗ El conjunto "{args.set}" no tiene locations de SerpAPI para la SERP: usa --maps.')
        key = find_key()
        if not key:
            sys.exit("✗ Falta SERPAPI_KEY: pégala en .env (SERPAPI_KEY=...) o defínela como variable de entorno.")
        try:
            before = account_credits(key)  # valida la clave sin gastar créditos
        except RuntimeError as e:
            sys.exit(f"✗ SerpAPI: {e}")
        left = before.get("total_searches_left")
        print(f"Créditos disponibles: {left} ({before.get('plan_name')})")
        needed = len(CITIES) if args.maps else MAX_REQUESTS
        if isinstance(left, int) and left < needed:
            sys.exit(f"✗ Quedan {left} créditos y esta ejecución puede usar hasta {needed}. Abortado.")
        run_file = raw_dir / "run.json"
        # --maps se suma a la captura del día: el coste se acumula en el mismo run.json
        run = json.loads(run_file.read_text(encoding="utf-8")) if args.maps and run_file.exists() else {}
        if args.maps:
            print(f'Capturando "{KEYWORD}" en Google Maps ({len(CITIES)} ciudades)…')
            used = capture_maps(key, raw_dir)
            run["maps_requests"] = used
        else:
            print(f'Capturando "{KEYWORD}" en {len(CITIES)} ciudades…')
            used = capture(key, raw_dir)
        time.sleep(3)  # el contador de la cuenta tarda unos segundos en actualizarse
        try:
            after = account_credits(key).get("total_searches_left")
        except RuntimeError:
            after = None
        run.setdefault("date", date.today().isoformat())
        run.setdefault("credits_before", left)
        run["requests_made"] = run.get("requests_made", 0) + used
        run["credits_after"] = after
        start = run["credits_before"]
        run["credits_used"] = start - after if isinstance(start, int) and isinstance(after, int) else None
        save_json(run_file, run)

    print(build_outputs(out, run))


if __name__ == "__main__":
    main()
