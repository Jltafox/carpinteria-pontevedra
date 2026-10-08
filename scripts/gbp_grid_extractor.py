"""
gbp-grid-extractor · grid geográfico de rankings de Google Maps, vía SerpAPI (plan gratuito).

Implementa 03-skills/gbp-grid-extractor/SKILL.md del repo "Clase 1 · Agentes IA para SEO y webs
hiperoptimizadas" (YinyangSEO Academy). Reutiliza las utilidades de local_pack_multi_city.py.

Uso:
    py scripts/gbp_grid_extractor.py --center a-estrada --size 7 --radius 6 --dry-run
    py scripts/gbp_grid_extractor.py --center a-estrada --size 7 --radius 6 --target Estelar
    py scripts/gbp_grid_extractor.py --center 42.6880,-8.4907 --size 7 --radius 6 --from-raw

Cada punto del grid es una búsqueda de Google Maps (1 crédito de SerpAPI). Los puntos ya guardados
en raw/ se reutilizan: una ejecución cortada se reanuda sin volver a gastar (--force-refresh repite).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import date
from html import escape as html_escape
from math import atan2, cos, degrees, radians, sin
from pathlib import Path
from statistics import mean, median

from local_pack_multi_city import (CITY_SETS, GOOGLE, ROOT, account_credits, cell, compact, find_key, fmt,
                                   get_json, km, maps_places, pack_entry, point_of, save_json, slugify,
                                   write_csv)

KEYWORD = "carpintería"
TOP_X = 3  # posiciones de Maps que cuentan como "visible" (Local Pack)
MAPS_TOP = 20  # Maps devuelve hasta 20 por búsqueda: se guardan todos por el mismo crédito
ZOOM = "15z"
MAX_SIZE = 9  # la skill pide no lanzar grids de más de 9×9 sin avisar
# Fuerza de la competencia en cada punto = reseñas del negocio más fuerte de su top 3.
LEVELS = [(10, "débil", "#2e9e5b"), (40, "media", "#e0a526"), (None, "fuerte", "#d64545")]
NO_DATA = ("sin datos", "#9aa3b2")
EMOJI = {"débil": "🟢", "media": "🟡", "fuerte": "🔴", "sin datos": "⚪"}


# ── Grid ─────────────────────────────────────────────────────────────────────────
def resolve_center(value: str) -> tuple[str, str, float, float]:
    """(nombre, slug, lat, lng) a partir de un punto conocido (p. ej. a-estrada) o de 'lat,lng'."""
    for points in CITY_SETS.values():
        for slug, label, _, ll in points:
            if value == slug:
                return (label, slug, *point_of(ll))
    match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*", value)
    if not match:
        known = ", ".join(slug for points in CITY_SETS.values() for slug, *_ in points)
        sys.exit(f"✗ --center: usa 'lat,lng' o uno de estos puntos: {known}")
    lat, lng = float(match.group(1)), float(match.group(2))
    return f"{lat:.4f}, {lng:.4f}", f"{lat:.4f}_{lng:.4f}", lat, lng


def generate_grid(lat: float, lng: float, size: int, radius_km: float) -> list[dict]:
    """size × size puntos repartidos uniformemente (código de la skill). Fila 0 = norte, columna 0 = oeste."""
    deg_lat = 1 / 111
    deg_lng = 1 / (111 * cos(radians(lat)))
    step = 2 * radius_km / (size - 1)
    half = (size - 1) / 2
    return [{"id": f"r{i}c{j}", "row": i, "col": j,
             "lat": round(lat + (half - i) * step * deg_lat, 6),
             "lng": round(lng + (j - half) * step * deg_lng, 6)}
            for i in range(size) for j in range(size)]


def direction(origin: tuple[float, float], point: tuple[float, float]) -> str:
    lat1, lng1, lat2, lng2 = map(radians, (*origin, *point))
    bearing = degrees(atan2(sin(lng2 - lng1) * cos(lat2),
                            cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(lng2 - lng1)))
    return ["N", "NE", "E", "SE", "S", "SO", "O", "NO"][round(((bearing + 360) % 360) / 45) % 8]


def level(strongest: int | None) -> tuple[str, str]:
    if strongest is None:
        return NO_DATA
    for limit, name, color in LEVELS:
        if limit is None or strongest <= limit:
            return name, color
    return NO_DATA


# ── Captura ──────────────────────────────────────────────────────────────────────
def capture(key: str, keyword: str, cells: list[dict], raw_dir: Path, force: bool) -> int:
    raw_dir.mkdir(parents=True, exist_ok=True)
    used = 0
    for row in sorted({c["row"] for c in cells}):
        marks = []
        for c in (c for c in cells if c["row"] == row):
            path = raw_dir / f'{c["id"]}.json'
            if path.exists() and not force:
                marks.append("·")  # ya capturado: no se gasta
                continue
            params = {"engine": "google_maps", "type": "search", "q": keyword,
                      "ll": f'@{c["lat"]},{c["lng"]},{ZOOM}', **GOOGLE, "api_key": key}
            used += 1
            try:
                save_json(path, get_json("search.json", params), key)
                marks.append("✓")
            except RuntimeError as e:  # no se guarda: la siguiente ejecución lo reintenta
                marks.append("✗")
                print(f'  ✗ {c["id"]}: {e}')
            time.sleep(1)
        print(f"  fila {row + 1}: {' '.join(marks)}")
    return used


def load_cells(cells: list[dict], raw_dir: Path, origin: tuple[float, float]) -> None:
    for c in cells:
        path = raw_dir / f'{c["id"]}.json'
        page = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        c["error"] = "sin capturar" if page is None else page.get("error")
        c["results"] = []
        if page and not page.get("error"):
            for i, place in enumerate(maps_places(page)[:MAPS_TOP], 1):
                p = pack_entry(place, i)
                c["results"].append({"rank": i, **{k: p[k] for k in (
                    "name", "place_id", "category", "rating", "reviews", "lat", "lng", "domain", "unclaimed")}})
        top = c["results"][:TOP_X]
        c["strongest"] = max(r["reviews"] or 0 for r in top) if top else None
        c["level"], c["level_color"] = level(c["strongest"])
        c["distance_km"] = round(km(origin, (c["lat"], c["lng"])), 1)
        c["direction"] = direction(origin, (c["lat"], c["lng"])) if c["distance_km"] > 0 else "centro"


# ── Métricas ─────────────────────────────────────────────────────────────────────
def business_metrics(cells: list[dict], size: int, step: float) -> list[dict]:
    half = (size - 1) / 2
    by_id = {c["id"]: c for c in cells}
    found: dict[str, dict] = {}
    for c in cells:
        for r in c["results"]:
            b = found.setdefault(r["place_id"] or compact(r["name"]), {
                k: r[k] for k in ("name", "place_id", "category", "rating", "reviews", "lat", "lng",
                                  "domain", "unclaimed")} | {"ranks": {}})
            b["ranks"][c["id"]] = r["rank"]

    for b in found.values():
        ranks = b["ranks"]
        top = [cid for cid, rank in ranks.items() if rank <= TOP_X]
        b["cells_present"] = len(ranks)
        b["cells_top"] = len(top)
        b["avr"] = round(mean(ranks.values()), 1)  # AVR: posición media donde aparece (top 20)
        b["atgr_pct"] = round(100 * len(top) / len(cells), 1)  # ATGR (skill): % de puntos en top 3
        # SoLV: cuota de voz ponderada (#1 = 1, #2 = 2/3, #3 = 1/3) sobre todos los puntos
        b["solv_pct"] = round(100 * sum((TOP_X + 1 - ranks[cid]) / TOP_X for cid in top) / len(cells), 1)
        # Alcance: distancia de la ficha a los puntos donde sale en top 3
        dists = ([km((b["lat"], b["lng"]), (by_id[cid]["lat"], by_id[cid]["lng"])) for cid in top]
                 if b["lat"] is not None and b["lng"] is not None else [])
        b["reach_median_km"] = round(median(dists), 1) if dists else None
        b["reach_max_km"] = round(max(dists), 1) if dists else None
        # Radio efectivo (skill): anillos contiguos desde el centro con el negocio en top 3 en ≥ 50 % de sus puntos
        radius = None
        for k in range(int(half) + 1):
            ring = [c for c in cells if max(abs(c["row"] - half), abs(c["col"] - half)) == k]
            if sum(ranks.get(c["id"], MAPS_TOP + 1) <= TOP_X for c in ring) / len(ring) < 0.5:
                break
            radius = round(k * step, 1)
        b["effective_radius_km"] = radius
    return sorted(found.values(), key=lambda b: (-b["solv_pct"], -b["cells_top"], b["avr"]))


def is_target(business: dict, targets: list[str]) -> bool:
    return any(t == business["place_id"] or compact(t) in compact(business["name"]) for t in targets)


# ── Salidas ──────────────────────────────────────────────────────────────────────
def where(c: dict) -> str:
    return "centro del grid" if c["direction"] == "centro" else f'{fmt(c["distance_km"])} km al {c["direction"]}'


def write_report(path: Path, meta: dict, cells: list[dict], businesses: list[dict], tracked: list[dict]) -> None:
    lines: list[str] = []
    add = lines.append
    size = meta["size"]
    add(f'# Grid de Google Maps · "{meta["keyword"]}" · {meta["center"]["label"]}')
    add("")
    add(f'> Skill `gbp-grid-extractor` · {meta["date"]} · grid {size}×{size} ({len(cells)} puntos) · '
        f'radio {fmt(meta["radius_km"])} km (paso {fmt(meta["step_km"])} km) · zoom {ZOOM} · visible = top {TOP_X}  ')
    add(f'> SerpAPI (google_maps) · búsquedas: {cell(meta.get("requests_made"))} · '
        f'créditos consumidos: {cell(meta.get("credits_used"))} · mapa interactivo: `heatmap.html`')
    add("")

    add("## Fuerza de la competencia por punto")
    add("")
    add(f"_Reseñas del negocio más fuerte del top {TOP_X} en cada punto. "
        f"🟢 ≤ 10 débil · 🟡 11–40 media · 🔴 > 40 fuerte · ⚪ sin datos. Norte arriba, oeste a la izquierda._")
    add("")
    add("| | " + " | ".join(("O " if j == 0 else "") + str(j + 1) + (" E" if j == size - 1 else "")
                          for j in range(size)) + " |")
    add("|" + "|".join([":-:"] * (size + 1)) + "|")
    for i in range(size):
        label = ("N " if i == 0 else "") + str(i + 1) + (" S" if i == size - 1 else "")
        add(f"| **{label}** | " + " | ".join(
            f'{EMOJI[c["level"]]} {"–" if c["strongest"] is None else c["strongest"]}'
            for c in cells if c["row"] == i) + " |")
    add("")
    counts = Counter(c["level"] for c in cells)
    add(" · ".join(f'{EMOJI[name]} {name}: {counts[name]}' for name in ("débil", "media", "fuerte", "sin datos")
                   if counts[name]))
    add("")

    columns = (f"| Negocio | Categoría | ★ | Reseñas | Top {TOP_X} (puntos) | SoLV | AVR | "
               "Alcance desde su ficha (mediana · máx) | Radio efectivo desde el centro |")
    divider = "|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|"

    def business_row(b: dict) -> str:
        reach = f'{fmt(b["reach_median_km"])} · {fmt(b["reach_max_km"])} km' if b["reach_max_km"] is not None else "—"
        radius = b["effective_radius_km"]
        radius = "—" if radius is None else "solo el centro" if radius == 0 else f"{fmt(radius)} km"
        return (f'| {cell(b["name"])} | {cell(b["category"])} | {cell(b["rating"])} | {cell(b["reviews"])} | '
                f'{b["cells_top"]}/{len(cells)} | {fmt(b["solv_pct"])} % | {fmt(b["avr"])} | {reach} | {radius} |')

    if tracked:
        add("## Negocios seguidos (--target)")
        add("")
        add(columns)
        add(divider)
        lines.extend(business_row(b) for b in tracked)
        add("")

    add("## Competidores dominantes (top 10 por SoLV)")
    add("")
    add(columns)
    add(divider)
    lines.extend(business_row(b) for b in businesses[:10])
    add("")

    add("## Dónde la competencia es débil")
    add("")
    weak = sorted((c for c in cells if c["level"] == "débil"), key=lambda c: c["distance_km"])
    if weak:
        for c in weak:
            top = c["results"][:TOP_X]
            add(f'- **{where(c)}** ({c["id"]}): reseñas del top {TOP_X} {" · ".join(str(r["reviews"] or 0) for r in top)}'
                f' — {", ".join(r["name"] for r in top)}')
    else:
        add("_Ningún punto con competencia débil._")
    add("")

    add("## Cómo leer las métricas")
    add("")
    add(f"- **Top {TOP_X} (puntos)** = ATGR de la skill: en cuántos puntos del grid aparece en el top {TOP_X}.")
    add(f"- **SoLV**: cuota de voz ponderada sobre todos los puntos (#1 vale 1, #2 vale 2/3, #3 vale 1/3).")
    add(f"- **AVR**: posición media en los puntos donde aparece dentro del top {MAPS_TOP}.")
    add(f"- **Alcance desde su ficha**: distancia entre la ubicación del negocio y los puntos donde sale en top {TOP_X}.")
    add(f"- **Radio efectivo desde el centro**: hasta dónde, en anillos desde el centro del grid, sale en top {TOP_X} "
        f"en al menos la mitad de los puntos de cada anillo.")
    add("")

    add("## QA")
    add("")
    issues = [f'- {c["id"]} ({where(c)}): {c["error"]}' for c in cells if c["error"]]
    issues += [f'- {c["id"]} ({where(c)}): solo {len(c["results"])} resultados' for c in cells
               if not c["error"] and len(c["results"]) < TOP_X]
    lines.extend(issues or ["- Sin incidencias."])
    add("")
    path.write_text("\n".join(lines), encoding="utf-8")


HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
  :root { --ink: #1d2433; --muted: #5b6475; --bg: #f6f7f9; --card: #fff; --line: #e3e6eb; --hi: #eef3ff; }
  * { box-sizing: border-box; }
  body { margin: 0; font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: var(--ink); background: var(--bg); }
  header { padding: 12px 18px; background: var(--card); border-bottom: 1px solid var(--line); }
  h1 { font-size: 17px; margin: 0 0 2px; }
  .meta { color: var(--muted); font-size: 13px; }
  main { display: grid; grid-template-columns: 1fr 360px; height: calc(100vh - 62px); }
  #map { height: 100%; }
  aside { overflow: auto; padding: 14px 16px; background: var(--card); border-left: 1px solid var(--line); }
  label { font-weight: 600; display: block; margin-bottom: 6px; }
  select { width: 100%; padding: 7px; border: 1px solid var(--line); border-radius: 6px; font: inherit; background: #fff; }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 14px; margin: 12px 0 8px; font-size: 13px; }
  .dot { display: inline-block; width: 11px; height: 11px; border-radius: 50%; margin-right: 5px; vertical-align: -1px; }
  .stats { margin: 0 0 14px; font-size: 13px; color: var(--muted); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 5px 4px; border-bottom: 1px solid var(--line); }
  th { color: var(--muted); font-weight: 600; }
  .n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  #rows tr { cursor: pointer; }
  #rows tr:hover, #rows tr.active { background: var(--hi); }
  .pin { font: 700 12px/24px system-ui, sans-serif; color: #fff; text-align: center; width: 28px; height: 28px;
         border-radius: 50%; border: 2px solid #fff; box-shadow: 0 1px 3px rgba(0,0,0,.35); }
  @media (max-width: 820px) { main { grid-template-columns: 1fr; height: auto; } #map { height: 60vh; } aside { border-left: 0; } }
</style>
</head>
<body>
<header><h1>__TITLE__</h1><div class="meta">__SUBTITLE__</div></header>
<main>
  <div id="map"></div>
  <aside>
    <label for="mode">Colorear el grid por</label>
    <select id="mode"><option value="competition">Fuerza de la competencia (reseñas del top 3)</option></select>
    <div class="legend" id="legend"></div>
    <div class="stats" id="stats"></div>
    <table>
      <thead><tr><th>Negocio (clic para verlo)</th><th class="n">Top 3</th><th class="n">SoLV</th><th class="n">Reseñas</th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </aside>
</main>
<script>
const DATA = __DATA__;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, ch => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[ch]));
const num = n => n == null ? "–" : Number(n).toLocaleString("es-ES");
const RANK_LEGEND = [["#2e9e5b", "Top 3"], ["#e0a526", "4–10"], ["#d64545", "11–20"], ["#9aa3b2", "Fuera del top 20"]];
const COMP_LEGEND = [["#2e9e5b", "Débil (≤ 10 reseñas)"], ["#e0a526", "Media (11–40)"], ["#d64545", "Fuerte (> 40)"], ["#9aa3b2", "Sin datos"]];
const rankColor = r => !r ? "#9aa3b2" : r <= 3 ? "#2e9e5b" : r <= 10 ? "#e0a526" : "#d64545";

const map = L.map("map");
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 19, attribution: "&copy; OpenStreetMap"}).addTo(map);
map.fitBounds(L.latLngBounds(DATA.cells.map(c => [c.lat, c.lng])).pad(0.12));
const pins = L.layerGroup().addTo(map);
const spot = L.layerGroup().addTo(map);

DATA.businesses.forEach((b, i) => $("mode").add(new Option(`${b.name} · top 3 en ${b.cells_top}/${DATA.cells.length}`, String(i))));
$("rows").innerHTML = DATA.businesses.map((b, i) =>
  `<tr data-i="${i}"><td>${esc(b.name)}</td><td class="n">${b.cells_top}</td><td class="n">${num(b.solv_pct)} %</td><td class="n">${num(b.reviews ?? 0)}</td></tr>`).join("");

function popup(c, b) {
  const place = c.direction === "centro" ? "Centro del grid" : `${num(c.distance_km)} km al ${c.direction}`;
  const own = b ? `<div>${esc(b.name)}: ${b.ranks[c.id] ? "#" + b.ranks[c.id] : "fuera del top 20"}</div>` : "";
  const list = c.top3.length
    ? `<ol style="margin:6px 0 0;padding-left:18px">${c.top3.map(r => `<li>${esc(r.name)} · ${num(r.rating)}★ · ${num(r.reviews ?? 0)} reseñas</li>`).join("")}</ol>`
    : `<div>${esc(c.error || "Sin resultados")}</div>`;
  return `<strong>${place}</strong>${own}${list}`;
}

function render() {
  pins.clearLayers();
  spot.clearLayers();
  const mode = $("mode").value;
  const b = mode === "competition" ? null : DATA.businesses[Number(mode)];
  DATA.cells.forEach(c => {
    const rank = b ? b.ranks[c.id] : null;
    const color = b ? rankColor(rank) : c.level_color;
    const label = b ? (rank ?? "–") : (c.strongest ?? "–");
    const icon = L.divIcon({className: "", html: `<div class="pin" style="background:${color}">${label}</div>`, iconSize: [28, 28], iconAnchor: [14, 14]});
    L.marker([c.lat, c.lng], {icon}).bindPopup(popup(c, b)).addTo(pins);
  });
  if (b && b.lat != null) {
    L.circleMarker([b.lat, b.lng], {radius: 8, color: "#1d2433", weight: 3, fillColor: "#fff", fillOpacity: 1})
      .bindTooltip(`Ficha de ${esc(b.name)}`).addTo(spot);
  }
  $("legend").innerHTML = (b ? RANK_LEGEND : COMP_LEGEND)
    .map(([color, text]) => `<span><i class="dot" style="background:${color}"></i>${text}</span>`).join("");
  $("stats").innerHTML = b
    ? `<strong>${esc(b.name)}</strong> · ${esc(b.category || "")}<br>${num(b.rating)}★ · ${num(b.reviews ?? 0)} reseñas · top 3 en ${b.cells_top} de ${DATA.cells.length} puntos · SoLV ${num(b.solv_pct)} %. El círculo blanco es su ficha.`
    : "Cada número son las reseñas del negocio más fuerte del top 3 en ese punto. Verde = competencia débil. Haz clic en un punto para ver su top 3.";
  document.querySelectorAll("#rows tr").forEach(tr => tr.classList.toggle("active", tr.dataset.i === mode));
}

$("rows").addEventListener("click", e => { const tr = e.target.closest("tr"); if (tr) { $("mode").value = tr.dataset.i; render(); } });
$("mode").addEventListener("change", render);
render();
</script>
</body>
</html>
"""


def write_html(path: Path, meta: dict, cells: list[dict], shown: list[dict]) -> None:
    data = {
        "cells": [{k: c[k] for k in ("id", "lat", "lng", "distance_km", "direction", "strongest", "level_color", "error")}
                  | {"top3": [{k: r[k] for k in ("name", "rating", "reviews")} for r in c["results"][:TOP_X]]}
                  for c in cells],
        "businesses": [{k: b[k] for k in ("name", "category", "rating", "reviews", "lat", "lng", "cells_top",
                                          "solv_pct", "ranks")} for b in shown],
    }
    title = f'Grid Maps · "{meta["keyword"]}" · {meta["center"]["label"]}'
    subtitle = (f'{meta["date"]} · {meta["size"]}×{meta["size"]} puntos · radio {fmt(meta["radius_km"])} km '
                f'(paso {fmt(meta["step_km"])} km) · zoom {ZOOM} · SerpAPI google_maps')
    page = (HTML.replace("__TITLE__", html_escape(title)).replace("__SUBTITLE__", html_escape(subtitle))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    path.write_text(page, encoding="utf-8")


def build_outputs(out: Path, meta: dict, cells: list[dict], targets: list[str]) -> str:
    load_cells(cells, out / "raw", (meta["center"]["lat"], meta["center"]["lng"]))
    businesses = business_metrics(cells, meta["size"], meta["step_km"])
    tracked = [b for b in businesses if is_target(b, targets)]
    save_json(out / "grid.json", {"meta": meta, "cells": cells, "businesses": businesses})
    write_csv(out / "businesses.csv", businesses,
              ["name", "place_id", "category", "rating", "reviews", "cells_present", "cells_top", "atgr_pct",
               "solv_pct", "avr", "reach_median_km", "reach_max_km", "effective_radius_km", "domain",
               "unclaimed", "lat", "lng"])
    write_report(out / "grid-report.md", meta, cells, businesses, tracked)
    write_html(out / "heatmap.html", meta, cells, businesses[:15] + [b for b in tracked if b not in businesses[:15]])

    try:
        shown = out.resolve().relative_to(ROOT)
    except ValueError:
        shown = out
    counts = Counter(c["level"] for c in cells)
    summary = [f"✓ Resultados en {shown}",
               f"  puntos con datos: {sum(1 for c in cells if c['results'])}/{len(cells)} · "
               f"negocios distintos: {len(businesses)}",
               "  competencia por punto: " + " · ".join(f"{name} {counts[name]}" for name in
                                                        ("débil", "media", "fuerte", "sin datos") if counts[name]),
               "  dominantes: " + "; ".join(f'{b["name"]} (top 3 en {b["cells_top"]}/{len(cells)})'
                                            for b in businesses[:3])]
    if targets:
        summary.append("  seguidos: " + ("; ".join(f'{b["name"]} (top 3 en {b["cells_top"]}/{len(cells)})'
                                                   for b in tracked) or "no aparecen en el grid"))
    return "\n".join(summary)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keyword", default=KEYWORD, help=f'búsqueda a medir (por defecto "{KEYWORD}")')
    parser.add_argument("--center", required=True, help="punto conocido (p. ej. a-estrada) o 'lat,lng'")
    parser.add_argument("--label", help="nombre del centro para informes y carpeta (útil con 'lat,lng')")
    parser.add_argument("--size", type=int, default=7, help="lado del grid, impar entre 3 y 9 (por defecto 7 = 49 puntos)")
    parser.add_argument("--radius", type=float, default=3.0, help="km del centro al borde (por defecto 3)")
    parser.add_argument("--target", action="append", default=[], help="negocio a seguir (nombre o place_id); repetible")
    parser.add_argument("--dry-run", action="store_true", help="muestra el plan y el coste sin llamar a la API")
    parser.add_argument("--from-raw", action="store_true", help="recalcula desde raw/ sin gastar créditos")
    parser.add_argument("--force-refresh", action="store_true", help="repite también los puntos ya capturados")
    parser.add_argument("--out", type=Path, help="carpeta de salida (por defecto data/gbp-grid/<keyword>/<...>)")
    args = parser.parse_args()

    if args.size % 2 == 0 or not 3 <= args.size <= MAX_SIZE:
        sys.exit(f"✗ --size debe ser impar entre 3 y {MAX_SIZE}")
    label, center_slug, lat, lng = resolve_center(args.center)
    if args.label:
        label, center_slug = args.label, slugify(args.label)
    cells = generate_grid(lat, lng, args.size, args.radius)
    step = 2 * args.radius / (args.size - 1)
    folder = f"{date.today().isoformat()}_{center_slug}_{args.size}x{args.size}_{args.radius:g}km".replace(".", "-")
    out = args.out or ROOT / "data" / "gbp-grid" / slugify(args.keyword) / folder
    raw_dir = out / "raw"
    pending = [c for c in cells if args.force_refresh or not (raw_dir / f'{c["id"]}.json').exists()]

    if args.dry_run:
        print(f'Keyword: "{args.keyword}" · centro: {label} ({lat:.4f}, {lng:.4f}) · zoom {ZOOM}')
        print(f"Grid {args.size}×{args.size} = {len(cells)} puntos · radio {args.radius:g} km · paso {step:.2f} km")
        print(f"Esquinas: NO {cells[0]['lat']:.4f},{cells[0]['lng']:.4f} · SE {cells[-1]['lat']:.4f},{cells[-1]['lng']:.4f}")
        print(f"Créditos a gastar: {len(pending)} (ya capturados: {len(cells) - len(pending)})")
        print(f"Salida: {out}")
        print("SERPAPI_KEY:", "encontrada" if find_key() else "NO encontrada (rellena .env)")
        return

    run_file = raw_dir / "run.json"
    run = json.loads(run_file.read_text(encoding="utf-8")) if run_file.exists() else {}
    if not args.from_raw and pending:
        key = find_key()
        if not key:
            sys.exit("✗ Falta SERPAPI_KEY: pégala en .env (SERPAPI_KEY=...) o defínela como variable de entorno.")
        try:
            before = account_credits(key)  # valida la clave sin gastar créditos
        except RuntimeError as e:
            sys.exit(f"✗ SerpAPI: {e}")
        left = before.get("total_searches_left")
        print(f"Créditos disponibles: {left} ({before.get('plan_name')}) · límite por hora: "
              f"{before.get('account_rate_limit_per_hour')} · usadas esta hora: {before.get('this_hour_searches')}")
        if isinstance(left, int) and left < len(pending):
            sys.exit(f"✗ Quedan {left} créditos y el grid necesita {len(pending)}. Abortado.")
        print(f'Capturando "{args.keyword}" en {len(pending)} puntos (· = ya capturado, ✓ = nuevo, ✗ = error)…')
        used = capture(key, args.keyword, cells, raw_dir, args.force_refresh)
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
    elif not args.from_raw:
        print("Todos los puntos ya están capturados: recalculo sin gastar créditos.")

    meta = {"skill": "gbp-grid-extractor", "keyword": args.keyword, "date": run.get("date") or date.today().isoformat(),
            "center": {"label": label, "lat": lat, "lng": lng}, "size": args.size, "radius_km": args.radius,
            "step_km": round(step, 3), "zoom": ZOOM, "top_x": TOP_X, "targets": args.target,
            **{k: v for k, v in run.items() if k != "date"}}
    print(build_outputs(out, meta, cells, args.target))


if __name__ == "__main__":
    main()
