"""
web-pattern-extractor · matriz comparativa de las webs de los competidores (no gasta créditos de SerpAPI).

Implementa 03-skills/web-pattern-extractor/SKILL.md del repo "Clase 1 · Agentes IA para SEO y webs
hiperoptimizadas" (YinyangSEO Academy). Toma las webs de los perfiles de gbp_deep_profile.py y analiza la
portada + 1 página de servicios por dominio (profundidad 2).

Uso:
    py scripts/web_pattern_extractor.py --profiles data/gbp-profiles/<carpeta> --label pontevedra --dry-run
    py scripts/web_pattern_extractor.py --profiles data/gbp-profiles/<carpeta> --label pontevedra
    py scripts/web_pattern_extractor.py --profiles data/gbp-profiles/<carpeta> --label pontevedra --no-psi

El HTML se descarga directamente con User-Agent móvil y respetando robots.txt. Lighthouse móvil sale de la
API pública de PageSpeed Insights (gratuita, sin clave). Todo se guarda en raw/ y no se repite (--refresh).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from statistics import median
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from local_pack_multi_city import ROOT, cell, domain_of, domain_type, fmt, save_json, slugify, write_csv

UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/129.0 Mobile Safari/537.36")
KEYWORD = "carpintería"
MIN_WORDS = 80  # por debajo, la página probablemente se pinta con JavaScript: se renderiza con Edge headless
EDGE_PATHS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
LOCAL_BUSINESS = {"LocalBusiness", "HomeAndConstructionBusiness", "GeneralContractor", "RoofingContractor",
                  "Store", "FurnitureStore", "HomeGoodsStore", "HardwareStore", "ProfessionalService"}
SCHEMA_FIELDS = ["name", "address", "telephone", "url", "image", "geo", "openingHoursSpecification",
                 "priceRange", "aggregateRating", "areaServed", "sameAs", "description", "logo"]
LOCATIONS = ["pontevedra", "santiago", "compostela", "vigo", "galicia", "estrada", "caldas", "cambados",
             "sanxenxo", "poio", "marin", "vilagarcia", "lalin", "padron", "salnes", "coruna", "ourense"]
SERVICE_WORDS = (r"servici|cocin|cocin|armari|vestidor|puerta|mueble|mobiliari|moble|suelo|tarima|parquet|escaler|"
                 r"ventan|porche|pergol|tejad|cubiert|bano|reform|rehabilit|restaur|carpinter|ebanist|interiorism|"
                 r"madeira|madera|baixo|cociña")
SERVICE_PATH = re.compile(r"servici|producto|trabajo|que-hacemos|carpinter|cocin|mueble|armario|puerta|proyecto", re.I)
LEGAL = re.compile(r"aviso|legal|privacidad|privacy|cookie|condiciones|terminos", re.I)
BLOG = re.compile(r"blog|noticia|news|articulo|post", re.I)
CONTACT = re.compile(r"contact", re.I)
CTA_WORDS = re.compile(r"presupuesto|contact|ll[aá]m|llama|solicit|pide|p[ií]denos|consult|escr[ií]benos|whatsapp", re.I)
HERO = re.compile(r"hero|banner|slider|carousel|swiper|jumbotron|masthead|rev_slider|elementor-slides|cover", re.I)
REVIEWS = re.compile(r"opini[oó]n|opiniones|testimoni|rese[nñ]a|valoraci|lo que dicen|clientes satisfechos", re.I)
REVIEW_CLASSES = re.compile(r"testimonial|review|trustindex|elfsight|grw|google-reviews", re.I)
FAQ = re.compile(r"preguntas frecuentes|\bfaq|dudas frecuentes|preguntas habituales", re.I)
FAQ_CLASSES = re.compile(r"faq|accordion|acordeon|toggle", re.I)
GALLERY = re.compile(r"galer[ií]a|portfolio|proyectos|trabajos realizados|nuestros trabajos", re.I)
FLOAT_WA = re.compile(r"joinchat|whatsapp|ht-ctc|wa[-_]?(float|button|btn|chat)|click-to-chat", re.I)
TRUST = re.compile(r"desde (?:el a[nñ]o )?(?:19|20)\d\d|(?:m[aá]s de )?\d+ a[nñ]os(?: de experiencia| en el sector)?|"
                   r"garant[ií]a|certificad\w*|homologad\w*|iso ?9001|fsc|pefc|f[aá]brica propia|taller propio", re.I)
PHONE = re.compile(r"(?:\+34[\s.-]?)?\b[6789]\d{2}(?:[\s.-]?\d{2,3}){2,3}\b")
POSTCODE = re.compile(r"\b(?:15|27|32|36)\d{3}\b")
STOPWORDS = set("""a al algo algunas algunos ante antes como con contra cual cuando de del desde donde durante e el
ella ellas ellos en entre era es esa esas ese eso esos esta estas este esto estos fue fueron ha han hasta hay la
las le les lo los mas me mi mis mucho muy nada ni no nos nuestra nuestras nuestro nuestros o os otra otras otro otros
para pero poco por porque que quien se sea ser si sin sobre son su sus tambien te tiene tienen todo todos tu tus un
una uno unos usted vosotros y ya yo cada cual cualquier asi aqui alli este estan estamos hemos hace hacen hacemos
puede pueden podemos sea seran sera siempre tanto tan solo sus les nos ese esa da do das dos na no unha co coa ao aos
polo pola máis moi ou se sen xa cando onde tamen tamén son está están ofrecemos realizamos contamos dispone disponemos
cookies cookie privacidad politica aviso legal derechos reservados aceptar rechazar configuracion preferencias
consentimiento navegacion web sitio pagina inicio menu leer ver click clic haz aqui siguiente anterior copyright
mas informacion info email correo telefono tel mail saltar contenido uso usamos""".split())


def norm(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()


# ── Descarga ─────────────────────────────────────────────────────────────────────
def fetch(url: str, timeout: int = 25) -> tuple[int, str, str]:
    """(status, url final, html). Reintenta 2 veces duplicando el timeout (QA de la skill)."""
    last = None
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
                                            "Accept-Language": "es-ES,es;q=0.9,gl;q=0.8"})
            with urlopen(request, timeout=timeout * 2 ** attempt) as resp:
                raw = resp.read(4_000_000)
                charset = resp.headers.get_content_charset()
                if not charset:
                    match = re.search(rb'charset=["\']?([\w-]+)', raw[:4000])
                    charset = match.group(1).decode() if match else "utf-8"
                try:
                    text = raw.decode(charset, "replace")
                except LookupError:
                    text = raw.decode("utf-8", "replace")
                return resp.status, resp.geturl(), text
        except HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}") from None
        except (URLError, TimeoutError, ConnectionError) as e:
            last = getattr(e, "reason", e)
            time.sleep(2)
    raise RuntimeError(f"sin respuesta ({last})")


def allowed(url: str, robots_cache: dict) -> bool:
    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in robots_cache:
        parser = RobotFileParser()
        try:
            status, _, text = fetch(base + "/robots.txt", timeout=15)
            parser.parse(text.splitlines() if status == 200 else [])
        except RuntimeError:
            parser.parse([])  # sin robots.txt legible: permitido
        robots_cache[base] = parser
    return robots_cache[base].can_fetch("*", url)


def render(url: str) -> str:
    """HTML ya pintado por JavaScript, con Edge headless (instalado en Windows; no descarga nada)."""
    edge = next((p for p in EDGE_PATHS if Path(p).exists()), None)
    if not edge:
        raise RuntimeError("Edge no encontrado para renderizar")
    with tempfile.TemporaryDirectory() as profile:  # perfil aparte: no toca el Edge del usuario
        result = subprocess.run([edge, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}",
                                 f"--user-agent={UA}", "--virtual-time-budget=15000", "--dump-dom", url],
                                capture_output=True, timeout=120)
    html = result.stdout.decode("utf-8", "replace")
    if "<html" not in html.lower():
        raise RuntimeError("Edge no devolvió HTML")
    return html


def env_value(name: str) -> str:
    """Variable de entorno o línea NAME=valor del .env del proyecto (la escribe el usuario)."""
    value = os.environ.get(name, "").strip()
    env_file = ROOT / ".env"
    if not value and env_file.exists():
        raw = env_file.read_bytes()
        text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", "replace")
        for line in text.splitlines():
            key, sep, val = line.strip().partition("=")
            if sep and key.strip() == name:
                value = val.strip().strip('"').strip("'")
    return value


def pagespeed(url: str) -> dict:
    params = [("url", url), ("strategy", "mobile"), ("locale", "es"), ("category", "performance"),
              ("category", "accessibility"), ("category", "best-practices"), ("category", "seo")]
    key = env_value("PAGESPEED_API_KEY")  # opcional y gratuita; sin ella se usa la cuota pública
    api = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + urlencode(params + ([("key", key)] if key else []))
    try:
        with urlopen(Request(api, headers={"User-Agent": UA}), timeout=150) as resp:
            data = json.load(resp)
    except HTTPError as e:
        return {"error": f"PageSpeed HTTP {e.code}" + (" (cuota sin clave agotada)" if e.code == 429 else "")}
    except (URLError, TimeoutError) as e:
        return {"error": f"PageSpeed sin respuesta ({getattr(e, 'reason', e)})"}
    lighthouse = data.get("lighthouseResult") or {}
    categories, audits = lighthouse.get("categories") or {}, lighthouse.get("audits") or {}
    score = lambda name: round(100 * categories[name]["score"]) if categories.get(name, {}).get("score") is not None else None
    value = lambda name: (audits.get(name) or {}).get("numericValue")
    return {"performance": score("performance"), "accessibility": score("accessibility"),
            "best_practices": score("best-practices"), "seo": score("seo"),
            "lcp_ms": round(value("largest-contentful-paint")) if value("largest-contentful-paint") else None,
            "cls": round(value("cumulative-layout-shift"), 3) if value("cumulative-layout-shift") is not None else None,
            "tbt_ms": round(value("total-blocking-time")) if value("total-blocking-time") is not None else None,
            "fcp_ms": round(value("first-contentful-paint")) if value("first-contentful-paint") else None}


# ── Análisis de una página ───────────────────────────────────────────────────────
class PageParser(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template", "iframe"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title, self.meta, self.canonical, self.lang, self.generator = "", {}, None, None, None
        self.headings: list[tuple[int, str]] = []
        self.jsonld: list[str] = []
        self.links: list[tuple[str, str, int]] = []  # (href, texto, posición en el texto)
        self.buttons: list[tuple[str, int]] = []
        self.words: list[str] = []  # todo el texto visible
        self.main_words: list[str] = []  # sin nav ni footer
        self.footer_words: list[str] = []
        self.classes: Counter = Counter()
        self.itemtypes: list[str] = []
        self.iframes: list[str] = []
        self.forms = self.details = 0
        self._skip = self._nav = self._footer = 0
        self._in_title = False
        self._heading = self._link = self._button = None
        self._ld: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = {k: v or "" for k, v in attrs}
        for token in a.get("class", "").split() + ([a["id"]] if a.get("id") else []):
            self.classes[token.lower()] += 1
        if a.get("itemtype"):
            self.itemtypes.append(a["itemtype"])
        if a.get("typeof"):
            self.itemtypes.append(a["typeof"])
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            if name:
                self.meta[name] = a.get("content", "")
            if name == "generator":
                self.generator = a.get("content")
        elif tag == "link" and "canonical" in a.get("rel", "").lower():
            self.canonical = a.get("href")
        elif tag == "title":
            self._in_title = True
        elif tag in ("h1", "h2", "h3"):
            self._heading = [int(tag[1]), []]
        elif tag == "a":
            self._link = [a.get("href", ""), [], len(self.words)]
        elif tag == "button":
            self._button = [[], len(self.words)]
        elif tag == "form":
            self.forms += 1
        elif tag == "details":
            self.details += 1
        elif tag == "nav":
            self._nav += 1
        elif tag == "footer":
            self._footer += 1
        if tag == "iframe":
            self.iframes.append(a.get("src", ""))
        if tag == "script" and "ld+json" in a.get("type", "").lower():
            self._ld = []
        if tag in self.SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("h1", "h2", "h3") and self._heading:
            text = " ".join(" ".join(self._heading[1]).split())
            if text:
                self.headings.append((self._heading[0], text))
            self._heading = None
        elif tag == "a" and self._link:
            self.links.append((self._link[0], " ".join(" ".join(self._link[1]).split()), self._link[2]))
            self._link = None
        elif tag == "button" and self._button:
            self.buttons.append((" ".join(" ".join(self._button[0]).split()), self._button[1]))
            self._button = None
        elif tag == "nav":
            self._nav = max(0, self._nav - 1)
        elif tag == "footer":
            self._footer = max(0, self._footer - 1)
        if tag == "script" and self._ld is not None:
            self.jsonld.append("".join(self._ld))
            self._ld = None
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._ld is not None:
            self._ld.append(data)
            return
        if self._skip:
            return
        if self._in_title:
            self.title += data
            return
        words = data.split()
        if not words:
            return
        self.words += words
        if self._footer:
            self.footer_words += words
        if not self._nav and not self._footer:
            self.main_words += words
        for open_item in (self._heading, self._link):
            if open_item:
                open_item[1].append(data)
        if self._button:
            self._button[0].append(data)


def schema_nodes(blobs: list[str]) -> tuple[list[dict], int]:
    """Nodos JSON-LD (incluidos @graph y anidados) y nº de bloques que no son JSON válido."""
    nodes, invalid = [], 0

    def walk(item):
        if isinstance(item, dict):
            if "@type" in item:
                nodes.append(item)
            for value in item.values():
                walk(value)
        elif isinstance(item, list):
            for value in item:
                walk(value)

    for blob in blobs:
        try:
            walk(json.loads(blob.strip()))
        except ValueError:
            invalid += 1
    return nodes, invalid


def types_of(node: dict) -> list[str]:
    value = node.get("@type")
    return [v.split("/")[-1] for v in (value if isinstance(value, list) else [value]) if isinstance(v, str)]


def analyze(html: str, url: str) -> dict:
    p = PageParser()
    p.feed(html)
    p.close()
    host = urlparse(url).netloc.lower()
    nodes, invalid = schema_nodes(p.jsonld)
    types = sorted({t for n in nodes for t in types_of(n)} | {t.split("/")[-1] for t in p.itemtypes if t})
    business = next((n for n in nodes if set(types_of(n)) & LOCAL_BUSINESS), None) or \
        next((n for n in nodes if "Organization" in types_of(n)), None)
    present = [f for f in SCHEMA_FIELDS if business and (business.get(f) or (f == "openingHoursSpecification"
                                                                             and business.get("openingHours")))]
    internal, external, categories = set(), set(), Counter()
    tel = whatsapp = mailto = 0
    cta_positions = []
    for href, text, position in p.links:
        href = href.strip()
        lower = href.lower()
        if lower.startswith("tel:"):
            tel += 1
            cta_positions.append(position)
            continue
        if "wa.me" in lower or "whatsapp" in lower:
            whatsapp += 1
            cta_positions.append(position)
            continue
        if lower.startswith("mailto:"):
            mailto += 1
            continue
        if not href or lower.startswith(("#", "javascript:")):
            if CTA_WORDS.search(text):
                cta_positions.append(position)
            continue
        absolute = urldefrag(urljoin(url, href))[0]
        if urlparse(absolute).scheme not in ("http", "https"):
            continue
        if CTA_WORDS.search(text):
            cta_positions.append(position)
        if urlparse(absolute).netloc.lower() == host:
            if absolute not in internal:
                internal.add(absolute)
                path = urlparse(absolute).path
                categories["legal" if LEGAL.search(path) else "contacto" if CONTACT.search(path) else
                           "blog" if BLOG.search(path) else
                           "servicio" if re.search(SERVICE_WORDS, norm(path + " " + text)) else "otros"] += 1
        else:
            external.add(absolute)
    cta_positions += [pos for text, pos in p.buttons if CTA_WORDS.search(text)]
    total = max(1, len(p.words))
    first_cta = min(cta_positions) / total if cta_positions else None
    classes = " ".join(p.classes)
    heading_text = " ".join(t for _, t in p.headings)
    text = " ".join(p.words)
    footer = " ".join(p.footer_words) or " ".join(p.words[int(len(p.words) * 0.85):])
    h1 = [t for level, t in p.headings if level == 1]
    service_headings = sorted({t for level, t in p.headings if level in (2, 3) and re.search(SERVICE_WORDS, norm(t))})
    faq_questions = sum(1 for _, t in p.headings if t.strip().endswith("?"))

    return {
        "url": url,
        "title": " ".join(p.title.split()),
        "meta_description": p.meta.get("description"),
        "canonical": p.canonical,
        "lang": p.lang,
        "cms": ("WordPress" if "wp-content" in html else "Wix" if "wixstatic" in html or "wix.com" in html else
                "Google Sites" if "sites.google.com" in url else "Shopify" if "cdn.shopify.com" in html else
                "Squarespace" if "squarespace" in html else "Jimdo" if "jimdo" in html else p.generator),
        "h1": h1,
        "h2": [t for level, t in p.headings if level == 2],
        "h3": [t for level, t in p.headings if level == 3],
        "schema_types": types,
        "schema_invalid_blocks": invalid,
        "schema_business_type": types_of(business)[0] if business else None,
        "schema_completeness_pct": round(100 * len(present) / len(SCHEMA_FIELDS)) if business else 0,
        "schema_fields_present": present,
        "has_hero": bool(HERO.search(classes)),
        "service_headings": service_headings,
        "has_reviews_block": bool(REVIEWS.search(heading_text) or REVIEW_CLASSES.search(classes)),
        "has_faq_block": bool(FAQ.search(heading_text) or p.details or FAQ_CLASSES.search(classes)),
        "faq_count": p.details + faq_questions,
        "has_gallery": bool(GALLERY.search(heading_text) or re.search(r"gallery|galeria|portfolio", classes)),
        "trust_signals": sorted({m.group(0).lower() for m in TRUST.finditer(text)})[:8],
        "tel_links": tel,
        "whatsapp_links": whatsapp,
        "mailto_links": mailto,
        "forms": p.forms,
        "floating_whatsapp": bool(FLOAT_WA.search(classes)),
        "first_cta": None if first_cta is None else "arriba" if first_cta < 0.25 else "medio" if first_cta < 0.75 else "abajo",
        "nap_in_footer": bool(PHONE.search(footer) and POSTCODE.search(footer)),
        "phone_on_page": bool(PHONE.search(text)),
        "has_map_embed": any("google.com/maps" in s or "maps.google" in s for s in p.iframes),
        "internal_links": sorted(internal),
        "internal_links_count": len(internal),
        "external_links_count": len(external),
        "internal_by_category": dict(categories),
        "words": len(p.main_words),
        "text": " ".join(p.main_words),
    }


def find_services_page(home: dict) -> str | None:
    candidates = [u for u in home["internal_links"]
                  if SERVICE_PATH.search(urlparse(u).path) and not LEGAL.search(u) and not BLOG.search(u)
                  and not CONTACT.search(u) and urlparse(u).path.strip("/")]
    candidates.sort(key=lambda u: (0 if re.search(r"servici|producto", u, re.I) else 1, len(urlparse(u).path)))
    return candidates[0] if candidates else None


def ngrams(text: str) -> Counter:
    tokens = re.findall(r"[a-záéíóúüñç]+", text.lower())
    counts = Counter()
    for n in (1, 2, 3):
        for i in range(len(tokens) - n + 1):
            gram = tokens[i:i + n]
            if norm(gram[0]) in STOPWORDS or norm(gram[-1]) in STOPWORDS or any(len(t) < 3 for t in (gram[0], gram[-1])):
                continue
            counts[" ".join(gram)] += 1
    return counts


# ── Por dominio ──────────────────────────────────────────────────────────────────
def process_domain(site: dict, raw_dir: Path, robots: dict, refresh: bool, use_psi: bool) -> dict:
    domain = site["domain"]
    folder = raw_dir / domain.replace("/", "_")
    folder.mkdir(parents=True, exist_ok=True)
    pages = []
    for name, url in (("home", site["website"]), ("servicios", None)):
        if name == "servicios":
            url = find_services_page(pages[0]) if pages else None
            if not url:
                break
        cache = folder / f"{name}.json"
        if cache.exists() and not refresh:
            page = json.loads(cache.read_text(encoding="utf-8"))
        else:
            if not allowed(url, robots):
                page = {"url": url, "error": "bloqueado por robots.txt"}
            else:
                try:
                    status, final_url, html = fetch(url)
                    page = {"url": final_url, "status": status, "html": html}
                except RuntimeError as e:
                    page = {"url": url, "error": str(e)}
            save_json(cache, page)
            time.sleep(1.5)
        if page.get("error"):
            if name == "home":
                return {"domain": domain, "error": page["error"], **site}
            break
        analysis = analyze(page["html"], page["url"])
        if analysis["words"] < MIN_WORDS:  # QA de la skill: si no renderiza sin JS, se renderiza de verdad
            rendered_cache = folder / f"{name}-rendered.json"
            if rendered_cache.exists() and not refresh:
                rendered = json.loads(rendered_cache.read_text(encoding="utf-8"))
            else:
                try:
                    rendered = {"url": page["url"], "html": render(page["url"])}
                    save_json(rendered_cache, rendered)
                except (RuntimeError, subprocess.TimeoutExpired) as e:  # no se guarda: se reintenta la próxima vez
                    rendered = {"url": page["url"], "error": str(e)}
            if not rendered.get("error"):
                rendered_analysis = analyze(rendered["html"], rendered["url"])
                if rendered_analysis["words"] > analysis["words"]:
                    analysis = rendered_analysis | {"rendered": True}
        pages.append(analysis)

    psi_cache = folder / "pagespeed.json"
    if psi_cache.exists() and not refresh:
        psi = json.loads(psi_cache.read_text(encoding="utf-8"))
    elif use_psi:
        psi = pagespeed(pages[0]["url"])
        if not psi.get("error"):  # los errores (p. ej. cuota) no se guardan: se reintenta en la próxima ejecución
            save_json(psi_cache, psi)
    else:
        psi = {"error": "no medido (--no-psi)"}

    home = pages[0]
    flags = ("has_hero", "has_reviews_block", "has_faq_block", "has_gallery", "floating_whatsapp",
             "nap_in_footer", "phone_on_page", "has_map_embed")
    schema_types = sorted({t for p in pages for t in p["schema_types"]})
    # Datos tomados a mano en un navegador real cuando ni la descarga ni Edge headless ven el contenido.
    browser = folder / "home-browser.json"
    manual = json.loads(browser.read_text(encoding="utf-8")) if browser.exists() else {}
    return _domain_row(site, pages, home, flags, schema_types, psi) | \
        {k: v for k, v in manual.items() if k != "source"} | ({"manual_source": manual["source"]} if manual else {})


def _domain_row(site: dict, pages: list[dict], home: dict, flags: tuple, schema_types: list[str], psi: dict) -> dict:
    return {
        **site,
        "pages_analyzed": [p["url"] for p in pages],
        "cms": home["cms"],
        "lang": home["lang"],
        "title": home["title"],
        "meta_description": home["meta_description"],
        "h1_text": " | ".join(dict.fromkeys(home["h1"])) or None,  # sin duplicados (sliders que repiten el H1)
        "rendered_with_js": any(p.get("rendered") for p in pages),
        "h1_count": len(home["h1"]),
        "h1_keyword_match": any("carpinter" in norm(h) for h in home["h1"]),
        "title_has_location": any(loc in norm(home["title"]) for loc in LOCATIONS),
        "h1_has_location": any(loc in norm(h) for h in home["h1"] for loc in LOCATIONS),
        "h2_count": len(home["h2"]),
        "headings": {p["url"]: {"h1": p["h1"], "h2": p["h2"], "h3": p["h3"]} for p in pages},
        "schema_types": schema_types,
        "has_localbusiness_schema": bool(set(schema_types) & LOCAL_BUSINESS),
        "has_organization_schema": "Organization" in schema_types,
        "has_faq_schema": "FAQPage" in schema_types,
        "has_service_schema": "Service" in schema_types,
        "has_breadcrumb_schema": "BreadcrumbList" in schema_types,
        "has_review_schema": bool({"Review", "AggregateRating"} & set(schema_types)),
        "schema_completeness_pct": max(p["schema_completeness_pct"] for p in pages),
        "schema_invalid_blocks": sum(p["schema_invalid_blocks"] for p in pages),
        "n_services_listed": len({h for p in pages for h in p["service_headings"]}),
        "service_headings": sorted({h for p in pages for h in p["service_headings"]}),
        **{flag: any(p[flag] for p in pages) for flag in flags},
        "faq_count": max(p["faq_count"] for p in pages),
        "trust_signals": sorted({t for p in pages for t in p["trust_signals"]}),
        "tel_links": max(p["tel_links"] for p in pages),
        "whatsapp_links": max(p["whatsapp_links"] for p in pages),
        "has_form": any(p["forms"] for p in pages),
        "first_cta": home["first_cta"],
        "internal_links_count": home["internal_links_count"],
        "external_links_count": home["external_links_count"],
        "internal_by_category": home["internal_by_category"],
        "pillar_map": sorted({urlparse(u).path or "/" for u in home["internal_links"]}),
        "content_words_count": home["words"],
        "services_page_words": pages[1]["words"] if len(pages) > 1 else None,
        "mobile_performance": psi.get("performance"),
        "lighthouse_seo": psi.get("seo"),
        "lighthouse_accessibility": psi.get("accessibility"),
        "lighthouse_best_practices": psi.get("best_practices"),
        "mobile_lcp_ms": psi.get("lcp_ms"),
        "mobile_cls": psi.get("cls"),
        "mobile_tbt_ms": psi.get("tbt_ms"),
        "mobile_fcp_ms": psi.get("fcp_ms"),
        "pagespeed_error": psi.get("error"),
        "_text": " ".join(p["text"] for p in pages),
    }


# ── Salidas ──────────────────────────────────────────────────────────────────────
def yes(value) -> str:
    return "sí" if value else "no"


def write_report(path: Path, meta: dict, rows: list[dict], skipped: list[dict], errors: list[dict],
                 grams: list[tuple]) -> None:
    lines: list[str] = []
    add = lines.append
    ok = rows
    add(f'# Patrones web · {meta["label"]} · "{meta["keyword"]}"')
    add("")
    add(f'> Skill `web-pattern-extractor` · {meta["date"]} · {len(ok)} webs (portada + 1 página de servicios) · '
        f'HTML descargado con User-Agent móvil · Lighthouse móvil vía PageSpeed Insights · sin créditos de SerpAPI')
    add("")

    add("## Matriz")
    add("")
    add("| Web | Negocio · top 3 grid | CMS | Schema | H1 | Palabras | Servicios | Hero | Reseñas | FAQ | "
        "Tel · WhatsApp · Form | Mapa | Rend. móvil · LCP |")
    add("|---|---|---|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|")
    for r in ok:
        schema = ", ".join(t for t in r["schema_types"] if t in LOCAL_BUSINESS | {"Organization", "FAQPage", "Service",
                                                                                     "BreadcrumbList", "AggregateRating",
                                                                                     "Review", "WebSite"}) or "—"
        perf = ("—" if r["mobile_performance"] is None else
                f'{r["mobile_performance"]} · {fmt(r["mobile_lcp_ms"] / 1000) if r["mobile_lcp_ms"] else "—"} s')
        add(f'| {r["domain"]} | {cell(r["business"])} · {r["cells_top"]}/49 | {cell(r["cms"])} | {schema} | '
            f'{cell(r["h1_text"])} | {r["content_words_count"]} | {r["n_services_listed"]} | {yes(r["has_hero"])} | '
            f'{yes(r["has_reviews_block"])} | {yes(r["has_faq_block"])} | '
            f'{r["tel_links"]} · {r["whatsapp_links"]} · {yes(r["has_form"])} | {yes(r["has_map_embed"])} | {perf} |')
    add("")

    def share(test) -> str:
        return f"{sum(1 for r in ok if test(r))}/{len(ok)}"

    add("## Patrones")
    add("")
    add(f'- **Schema:** LocalBusiness (o subtipo) {share(lambda r: r["has_localbusiness_schema"])} · '
        f'Organization {share(lambda r: r["has_organization_schema"])} · FAQPage {share(lambda r: r["has_faq_schema"])} · '
        f'Service {share(lambda r: r["has_service_schema"])} · BreadcrumbList {share(lambda r: r["has_breadcrumb_schema"])} · '
        f'Review/AggregateRating {share(lambda r: r["has_review_schema"])}.')
    add(f'- **On-page:** H1 con "carpintería" {share(lambda r: r["h1_keyword_match"])} · ciudad en el title '
        f'{share(lambda r: r["title_has_location"])} · ciudad en el H1 {share(lambda r: r["h1_has_location"])} · '
        f'meta description {share(lambda r: r["meta_description"])} · sin H1 {share(lambda r: not r["h1_count"])} · '
        f'más de un H1 {share(lambda r: r["h1_count"] > 1)}.')
    add(f'- **Bloques:** hero {share(lambda r: r["has_hero"])} · reseñas/testimonios {share(lambda r: r["has_reviews_block"])} · '
        f'FAQ {share(lambda r: r["has_faq_block"])} · galería/proyectos {share(lambda r: r["has_gallery"])} · '
        f'mapa embebido {share(lambda r: r["has_map_embed"])} · NAP en el pie {share(lambda r: r["nap_in_footer"])}.')
    add(f'- **Conversión:** enlace tel: {share(lambda r: r["tel_links"])} · WhatsApp {share(lambda r: r["whatsapp_links"] or r["floating_whatsapp"])} · '
        f'formulario {share(lambda r: r["has_form"])} · primer CTA arriba {share(lambda r: r["first_cta"] == "arriba")}.')
    words = [r["content_words_count"] for r in ok]
    add(f'- **Contenido:** mediana de {fmt(median(words), 0)} palabras en la portada (mín. {min(words)}, máx. {max(words)}); '
        f'mediana de {fmt(median(r["n_services_listed"] for r in ok), 0)} servicios en encabezados.')
    trust = Counter(t for r in ok for t in r["trust_signals"])
    if trust:
        add(f'- **Señales de confianza:** {", ".join(f"{t} ({n})" for t, n in trust.most_common(8))}.')
    measured = [r for r in ok if r["mobile_performance"] is not None]
    if measured:
        add(f'- **Lighthouse móvil** ({len(measured)} webs): rendimiento mediano {fmt(median(r["mobile_performance"] for r in measured), 0)}, '
            f'SEO {fmt(median(r["lighthouse_seo"] for r in measured), 0)}, LCP mediano '
            f'{fmt(median(r["mobile_lcp_ms"] for r in measured if r["mobile_lcp_ms"]) / 1000)} s, CLS mediano '
            f'{fmt(median(r["mobile_cls"] for r in measured if r["mobile_cls"] is not None), 3)}.')
    cms = Counter(r["cms"] or "desconocido" for r in ok)
    add(f'- **CMS:** {", ".join(f"{c} ({n})" for c, n in cms.most_common())}.')
    add("")

    add("## Títulos y H1")
    add("")
    for r in ok:
        add(f'- **{r["domain"]}** — title: “{cell(r["title"])}” · H1: {cell(r["h1_text"])}')
    add("")

    add("## N-gramas más repetidos (portada + servicios)")
    add("")
    add("_Ordenados por nº de webs que los usan; el top 50 completo está en `ngrams.csv`._")
    add("")
    add(", ".join(f"{gram} ({domains} webs)" for gram, domains, _ in grams[:25]))
    add("")

    add("## QA")
    add("")
    issues = [f'- {s["domain"]} ({s["business"]}): {s["reason"]}' for s in skipped]
    issues += [f'- {e["domain"]}: {e["error"]}' for e in errors]
    psi_errors = Counter(r["pagespeed_error"] for r in ok if r["pagespeed_error"])
    issues += [f"- Lighthouse sin medir en {n}/{len(ok)} webs: {error}." for error, n in psi_errors.items()]
    rendered = [r["domain"] for r in ok if r["rendered_with_js"] and not r.get("manual_source")]
    if rendered:
        issues.append(f'- Renderizadas con Edge headless porque sin JavaScript no mostraban contenido: {", ".join(rendered)}.')
    issues += [f'- {r["domain"]}: sin JavaScript no muestra contenido; datos tomados de {r["manual_source"]} '
               f'(schema, H1, palabras, CTAs y enlaces; los bloques se detectan solo con el HTML descargado).'
               for r in ok if r.get("manual_source")]
    issues += [f'- {r["domain"]}: {r["schema_invalid_blocks"]} bloque(s) JSON-LD no válidos' for r in ok if r["schema_invalid_blocks"]]
    issues += [f'- {r["domain"]}: solo {r["content_words_count"]} palabras en la portada (¿contenido cargado con JS?)'
               for r in ok if r["content_words_count"] < 80]
    total = len(ok) + len(errors)
    if total and len(errors) / total > 0.3:
        issues.append("- Más del 30 % de los dominios fallan: revisar User-Agent o IP (regla de la skill).")
    lines.extend(issues or ["- Sin incidencias."])
    add("")
    add("_Bloques (hero, reseñas, FAQ…) detectados por heurística sobre clases CSS y encabezados: confirmar a mano "
        "antes de sacar conclusiones fuertes._")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profiles", type=Path, required=True, help="carpeta de gbp_deep_profile.py")
    parser.add_argument("--label", required=True, help="nombre de la zona (para la carpeta de salida)")
    parser.add_argument("--keyword", default=KEYWORD)
    parser.add_argument("--dry-run", action="store_true", help="muestra las webs a analizar sin descargar nada")
    parser.add_argument("--no-psi", action="store_true", help="no medir Lighthouse (PageSpeed Insights)")
    parser.add_argument("--refresh", action="store_true", help="vuelve a descargar aunque haya caché en raw/")
    args = parser.parse_args()

    sites, skipped = {}, []
    for path in sorted(args.profiles.glob("ChIJ*.json")):
        profile = json.loads(path.read_text(encoding="utf-8"))
        domain = profile.get("domain")
        if not profile.get("website"):
            skipped.append({"domain": "—", "business": profile["name"], "reason": "sin web en la ficha"})
        elif domain_type(domain) != "negocio/otro" and domain != "sites.google.com":
            skipped.append({"domain": domain, "business": profile["name"], "reason": f"no es una web ({domain_type(domain)})"})
        else:
            key = domain if domain != "sites.google.com" else domain + "/" + urlparse(profile["website"]).path.strip("/")
            sites.setdefault(key, {"domain": key, "website": profile["website"], "business": profile["name"],
                                   "cells_top": profile["grid"]["cells_top"], "solv_pct": profile["grid"]["solv_pct"]})
    out = ROOT / "data" / "web-patterns" / slugify(args.keyword) / f"{date.today().isoformat()}_{slugify(args.label)}"

    if args.dry_run:
        for s in sites.values():
            print(f'  · {s["domain"]:<44} {s["business"][:40]}')
        for s in skipped:
            print(f'  ✗ {s["business"][:40]}: {s["reason"]}')
        print(f"{len(sites)} webs · PageSpeed: {'no' if args.no_psi else 'sí'} · salida: {out}")
        return

    robots: dict = {}
    rows, errors = [], []
    for site in sites.values():
        result = process_domain(site, out / "raw", robots, args.refresh, not args.no_psi)
        if result.get("error"):
            errors.append({"domain": site["domain"], "error": result["error"]})
            print(f'  ✗ {site["domain"]}: {result["error"]}')
            continue
        rows.append(result)
        print(f'  ✓ {site["domain"]}: {len(result["pages_analyzed"])} páginas · {result["content_words_count"]} palabras · '
              f'PSI {result["mobile_performance"] if result["mobile_performance"] is not None else result["pagespeed_error"]}')

    per_domain = out / "per-domain"
    per_domain.mkdir(parents=True, exist_ok=True)
    totals, presence = Counter(), Counter()
    for r in rows:
        counts = ngrams(r["_text"])
        totals.update(counts)
        presence.update(counts.keys())
        save_json(per_domain / f'{r["domain"].replace("/", "_")}.json', {k: v for k, v in r.items() if k != "_text"})
    grams = sorted(((g, presence[g], totals[g]) for g in totals if presence[g] >= 2),
                   key=lambda x: (-x[1], -x[2]))[:50]
    write_csv(out / "ngrams.csv", [{"ngram": g, "domains": d, "count": c} for g, d, c in grams],
              ["ngram", "domains", "count"])
    write_csv(out / "matrix.csv", rows,
              ["domain", "business", "cells_top", "solv_pct", "has_localbusiness_schema", "has_faq_schema",
               "has_service_schema", "schema_completeness_pct", "h1_text", "h1_keyword_match", "h2_count",
               "n_services_listed", "has_hero", "has_reviews_block", "has_faq_block", "faq_count",
               "internal_links_count", "mobile_lcp_ms", "mobile_cls", "lighthouse_seo", "content_words_count",
               "cms", "title", "title_has_location", "h1_has_location", "schema_types", "has_review_schema",
               "has_map_embed", "tel_links", "whatsapp_links", "has_form", "first_cta", "nap_in_footer",
               "trust_signals", "mobile_performance", "pages_analyzed"])
    save_json(out / "errors.json", errors + [{"domain": s["domain"], "business": s["business"], "error": s["reason"]}
                                             for s in skipped])
    meta = {"label": args.label, "keyword": args.keyword, "date": date.today().isoformat()}
    write_report(out / "report.md", meta, rows, skipped, errors, grams)
    try:
        shown = out.resolve().relative_to(ROOT)
    except ValueError:
        shown = out
    print(f"✓ {len(rows)} webs analizadas en {shown} · errores: {len(errors)} · sin web: {len(skipped)}")


if __name__ == "__main__":
    main()
