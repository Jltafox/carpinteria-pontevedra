"""
gbp-deep-profile · ficha completa de Google Business Profile de los negocios de un grid, vía SerpAPI (gratis).

Implementa 03-skills/gbp-deep-profile/SKILL.md del repo "Clase 1 · Agentes IA para SEO y webs
hiperoptimizadas" (YinyangSEO Academy). Reutiliza las utilidades de local_pack_multi_city.py.

Uso:
    py scripts/gbp_deep_profile.py --grid data/gbp-grid/carpinteria/<carpeta> --label pontevedra --dry-run
    py scripts/gbp_deep_profile.py --grid data/gbp-grid/carpinteria/<carpeta> --label pontevedra --limit 1
    py scripts/gbp_deep_profile.py --grid data/gbp-grid/carpinteria/<carpeta> --label pontevedra

Por negocio: 1 crédito para la ficha (google_maps + place_id) y hasta 2 para reseñas (google_maps_reviews,
las más recientes primero: 8 en la 1.ª página y hasta 20 en la 2.ª). Lo ya descargado en raw/ no se repite.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from statistics import median

from local_pack_multi_city import (GOOGLE, ROOT, account_credits, cell, compact, domain_of, find_key, fmt,
                                   get_json, save_json, slugify, write_csv)

TOP = 11
# Fuera del perfilado: no compiten con una carpintería de madera aunque salgan por "carpintería".
EXCLUDE_CATEGORIES = ["Parada de autobús", "Carpintería metálica y de aluminio", "Fábrica de acero inoxidable"]
ALWAYS_INCLUDE_MIN_REVIEWS = 90  # el negocio con más reseñas del grid es referencia aunque no lidere en SoLV
REVIEWS_PAGE_1 = 8  # la API de reseñas devuelve 8 en la primera página


# ── Selección ────────────────────────────────────────────────────────────────────
def select_businesses(grid: dict, top: int, exclude: list[str]) -> list[dict]:
    candidates = [b for b in grid["businesses"] if b["place_id"] and b["category"] not in exclude and b["cells_top"]]
    chosen = candidates[:top]
    chosen += [b for b in candidates[top:] if (b["reviews"] or 0) >= ALWAYS_INCLUDE_MIN_REVIEWS]
    return chosen


# ── Captura ──────────────────────────────────────────────────────────────────────
def fetch(key: str, path: Path, params: dict) -> tuple[dict, bool]:
    """Devuelve (respuesta, gastó_crédito). Reutiliza raw/ si ya existe."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")), False
    data = get_json("search.json", {**params, "api_key": key})
    save_json(path, data, key)
    time.sleep(1)
    return data, True


def capture(key: str, business: dict, raw_dir: Path) -> int:
    pid = business["place_id"]
    used = 0
    place, spent = fetch(key, raw_dir / f"{pid}-place.json", {"engine": "google_maps", "place_id": pid, **GOOGLE})
    used += spent
    info = place.get("place_results") or {}
    total = info.get("reviews") or 0
    if not info.get("data_id") or not total:
        return used
    base = {"engine": "google_maps_reviews", "data_id": info["data_id"], "hl": GOOGLE["hl"], "sort_by": "newestFirst"}
    page1, spent = fetch(key, raw_dir / f"{pid}-reviews-1.json", base)
    used += spent
    token = (page1.get("serpapi_pagination") or {}).get("next_page_token")
    if total > REVIEWS_PAGE_1 and token:
        _, spent = fetch(key, raw_dir / f"{pid}-reviews-2.json", {**base, "next_page_token": token, "num": 20})
        used += spent
    return used


# ── Perfil ───────────────────────────────────────────────────────────────────────
def age_days(iso: str | None, today: date) -> int | None:
    if not iso:
        return None
    try:
        return (today - datetime.fromisoformat(iso.replace("Z", "+00:00")).date()).days
    except ValueError:
        return None


GROUPS = {"accessibility": "Accesibilidad", "payments": "Pagos", "service_options": "Opciones de servicio",
          "highlights": "Destacado", "offerings": "Oferta", "amenities": "Servicios", "planning": "Planificación",
          "from_the_business": "Del negocio", "crowd": "Público", "parking": "Aparcamiento"}


def flatten_extensions(extensions) -> list[str]:
    """SerpAPI: [{"grupo": ["valor", ...]}, ...] → ["Grupo: valor", ...]."""
    out = []
    for group in extensions or []:
        if isinstance(group, dict):
            for name, values in group.items():
                for value in values if isinstance(values, list) else [values]:
                    out.append(f"{GROUPS.get(name, name)}: {value}")
    return out


def build_profile(business: dict, raw_dir: Path, today: date) -> dict:
    pid = business["place_id"]
    place_path = raw_dir / f"{pid}-place.json"
    place = json.loads(place_path.read_text(encoding="utf-8")) if place_path.exists() else {}
    info = place.get("place_results") or {}
    reviews, topics = [], []
    for n in (1, 2):
        path = raw_dir / f"{pid}-reviews-{n}.json"
        if path.exists():
            page = json.loads(path.read_text(encoding="utf-8"))
            reviews += page.get("reviews") or []
            topics = topics or page.get("topics") or []

    categories = info.get("type") or ([business["category"]] if business["category"] else [])
    if isinstance(categories, str):
        categories = [categories]
    attributes = flatten_extensions(info.get("extensions"))
    missing_attributes = flatten_extensions(info.get("unsupported_extensions"))
    review_ages = [a for a in (age_days(r.get("iso_date"), today) for r in reviews) if a is not None]
    total = info.get("reviews") if info.get("reviews") is not None else business["reviews"]
    sample_complete = len(reviews) >= (total or 0)
    last_12m = sum(1 for a in review_ages if a <= 365)
    # Si la muestra no llega a 12 meses atrás y faltan reseñas, la velocidad es un mínimo.
    velocity_is_min = not sample_complete and bool(review_ages) and max(review_ages) <= 365
    responded = sum(1 for r in reviews if r.get("response"))
    texts = [r["snippet"] for r in reviews if r.get("snippet")]
    posts = info.get("posts") or info.get("updates_from_business")
    qa = info.get("questions_and_answers")
    highlights = [s.get("snippet", "").strip('"') for s in (info.get("user_reviews") or {}).get("summary") or []
                  if isinstance(s, dict) and s.get("snippet")]
    distribution = {str(s.get("stars")): s.get("amount") for s in info.get("rating_summary") or [] if isinstance(s, dict)}

    return {
        "place_id": pid,
        "name": info.get("title") or business["name"],
        "data_id": info.get("data_id"),
        "address": info.get("address"),
        "phone": info.get("phone"),
        "website": info.get("website"),
        "domain": domain_of(info.get("website")),
        "description": info.get("description"),
        "description_known": "description" in info,  # SerpAPI no siempre la devuelve: ausente ≠ sin descripción
        "primary_category": categories[0] if categories else None,
        "secondary_categories": categories[1:],
        "attributes": attributes,
        "attributes_count": len(attributes),
        "missing_attributes": missing_attributes,
        "has_hours": bool(info.get("hours") or info.get("operating_hours")),
        "hours": info.get("hours"),
        "photo_groups": [img.get("title") for img in info.get("images") or [] if isinstance(img, dict)],
        "n_photos": info.get("photos_count") or info.get("total_photos"),
        "has_posts": bool(posts) if "posts" in info or "updates_from_business" in info else None,
        "has_qa": bool(qa) if "questions_and_answers" in info else None,
        "has_services": None,  # la lista de productos/servicios de la ficha no viene en SerpAPI
        "has_service_options": any(a.startswith(GROUPS["service_options"]) for a in attributes),
        "booking_link": info.get("reservation_link") or info.get("order_online_link"),
        "unclaimed": bool(info.get("unclaimed_listing") or business.get("unclaimed")),
        "avg_rating": info.get("rating", business["rating"]),
        "total_reviews": total or 0,
        "rating_distribution": distribution,
        "reviews_sampled": len(reviews),
        "last_review_age_days": min(review_ages) if review_ages else None,
        "reviews_last_12m": last_12m,
        "reviews_last_12m_is_min": velocity_is_min,
        "review_velocity_month": round(last_12m / 12, 1),
        "owner_response_rate": round(100 * responded / len(reviews)) if reviews else None,
        "reviews_with_text_pct": round(100 * len(texts) / len(reviews)) if reviews else None,
        "avg_review_length": round(sum(map(len, texts)) / len(texts)) if texts else None,
        "review_topics": [f'{t.get("keyword")} ({t.get("mentions")})' for t in topics[:8] if isinstance(t, dict)],
        "review_highlights": highlights,
        "grid": {k: business[k] for k in ("cells_top", "solv_pct", "avr", "reach_median_km", "reach_max_km")},
    }


# ── Salidas ──────────────────────────────────────────────────────────────────────
def pct(items: list, test) -> str:
    return f"{sum(1 for i in items if test(i))}/{len(items)}"


def write_report(path: Path, meta: dict, profiles: list[dict]) -> None:
    lines: list[str] = []
    add = lines.append
    add(f'# Perfiles GBP · {meta["label"]} · "{meta["keyword"]}"')
    add("")
    add(f'> Skill `gbp-deep-profile` · {meta["date"]} · {len(profiles)} negocios del grid `{meta["grid"]}` · '
        f'SerpAPI (google_maps + google_maps_reviews) · créditos consumidos: {cell(meta.get("credits_used"))}  ')
    add(f'> Excluidos del perfilado: {", ".join(meta["excluded_categories"])}.')
    add("")

    add("## Fichas")
    add("")
    add("| Negocio | Categoría principal | Secundarias | ★ | Reseñas | Últ. reseña (días) | Reseñas/mes (12 m) | "
        "Responde | Atributos | Horario | Web | Top 3 grid |")
    add("|---|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|:-:|")
    for p in profiles:
        velocity = fmt(p["review_velocity_month"]) + ("+" if p["reviews_last_12m_is_min"] else "")
        add(f'| {cell(p["name"])} | {cell(p["primary_category"])} | {cell(p["secondary_categories"])} | '
            f'{cell(p["avg_rating"])} | {p["total_reviews"]} | {cell(p["last_review_age_days"])} | {velocity} | '
            f'{"—" if p["owner_response_rate"] is None else str(p["owner_response_rate"]) + " %"} | '
            f'{p["attributes_count"]} | {"sí" if p["has_hours"] else "no"} | {cell(p["domain"])} | '
            f'{p["grid"]["cells_top"]}/49 |')
    add("")

    add("## Patrones")
    add("")
    primary = Counter(p["primary_category"] for p in profiles if p["primary_category"])
    secondary = Counter(c for p in profiles for c in p["secondary_categories"])
    attributes = Counter(a for p in profiles for a in p["attributes"])
    add(f'- **Categoría principal:** {", ".join(f"{c} ({n})" for c, n in primary.most_common())}.')
    add(f'- **Categorías secundarias más usadas:** '
        f'{", ".join(f"{c} ({n})" for c, n in secondary.most_common(10)) or "ninguna"}.')
    add(f'- **Atributos más repetidos:** {", ".join(f"{a} ({n})" for a, n in attributes.most_common(8)) or "ninguno"}.')
    known = [p for p in profiles if p["description_known"]]
    described = f' · **con descripción:** {pct(known, lambda p: p["description"])}' if known else ""
    add(f'- **Con web:** {pct(profiles, lambda p: p["website"])}{described} · **con horario:** '
        f'{pct(profiles, lambda p: p["has_hours"])} · **sin reclamar:** {pct(profiles, lambda p: p["unclaimed"])}.')
    reviewed = [p for p in profiles if p["total_reviews"]]
    if reviewed:
        add(f'- **Reseñas:** mediana {fmt(median(p["total_reviews"] for p in profiles), 0)} por ficha; '
            f'{pct(profiles, lambda p: not p["total_reviews"])} no tienen ninguna. Mediana de la última reseña: '
            f'{fmt(median(p["last_review_age_days"] for p in reviewed if p["last_review_age_days"] is not None), 0)} días.')
        rates = [p["owner_response_rate"] for p in reviewed if p["owner_response_rate"] is not None]
        if rates:
            add(f'- **Respuesta del propietario** (en las reseñas muestreadas): mediana {fmt(median(rates), 0)} %.')
    topics = Counter(t.rsplit(" (", 1)[0] for p in profiles for t in p["review_topics"])
    if topics:
        add(f'- **Temas que más salen en las reseñas:** {", ".join(t for t, _ in topics.most_common(10))}.')
    add("")

    quotes = [(p["name"], q) for p in profiles for q in p["review_highlights"][:2]]
    if quotes:
        add("## Lo que destacan los clientes (frases resumen de Google)")
        add("")
        lines.extend(f"- **{cell(name)}:** “{cell(quote)}”" for name, quote in quotes)
        add("")

    add("## QA")
    add("")
    issues = [f'- {p["name"]}: 0 reseñas (posible limited view: no tratar como ficha "fría" sin comprobarlo).'
              for p in profiles if not p["total_reviews"]]
    if all(p["has_posts"] is None for p in profiles):
        issues.append("- Posts no consultados: SerpAPI los da en una llamada aparte (google_maps_posts, 1 crédito "
                      "por ficha), así que last_post_age_days queda vacío.")
    if all(p["has_qa"] is None for p in profiles):
        issues.append("- SerpAPI no devuelve preguntas y respuestas ni descripción de estas fichas.")
    if all(p["n_photos"] is None for p in profiles):
        issues.append("- SerpAPI no devuelve el número de fotos ni la lista de productos/servicios: solo los grupos "
                      "de fotos y las opciones de servicio (atributos).")
    lines.extend(issues or ["- Sin incidencias."])
    add("")
    path.write_text("\n".join(lines), encoding="utf-8")


def build_outputs(out: Path, meta: dict, chosen: list[dict]) -> str:
    today = date.fromisoformat(meta["date"])
    profiles = [build_profile(b, out / "raw", today) for b in chosen if (out / "raw" / f'{b["place_id"]}-place.json').exists()]
    for p in profiles:
        save_json(out / f'{p["place_id"]}.json', p)
    write_csv(out / "_matrix.csv", [p | {"solv_pct": p["grid"]["solv_pct"], "cells_top": p["grid"]["cells_top"]}
                                    for p in profiles],
              ["place_id", "name", "primary_category", "secondary_categories", "n_photos", "has_posts",
               "total_reviews", "avg_rating", "owner_response_rate", "has_services", "has_qa", "attributes_count",
               "last_review_age_days", "review_velocity_month", "website", "description", "has_hours", "unclaimed",
               "cells_top", "solv_pct"])
    write_report(out / "_report.md", meta, profiles)
    try:
        shown = out.resolve().relative_to(ROOT)
    except ValueError:
        shown = out
    return f"✓ {len(profiles)} perfiles en {shown}"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--grid", type=Path, required=True, help="carpeta de un grid de gbp_grid_extractor.py")
    parser.add_argument("--label", required=True, help="nombre de la zona (para la carpeta de salida)")
    parser.add_argument("--top", type=int, default=TOP, help=f"negocios a perfilar por SoLV (por defecto {TOP})")
    parser.add_argument("--limit", type=int, help="procesa solo los N primeros (prueba)")
    parser.add_argument("--only", help="procesa solo el negocio cuyo nombre contenga este texto (prueba)")
    parser.add_argument("--dry-run", action="store_true", help="muestra la selección y el coste sin llamar a la API")
    parser.add_argument("--from-raw", action="store_true", help="recalcula desde raw/ sin gastar créditos")
    args = parser.parse_args()

    grid = json.loads((args.grid / "grid.json").read_text(encoding="utf-8"))
    chosen = select_businesses(grid, args.top, EXCLUDE_CATEGORIES)
    out = ROOT / "data" / "gbp-profiles" / f"{date.today().isoformat()}_{slugify(args.label)}"
    raw_dir = out / "raw"
    todo = chosen[:args.limit] if args.limit else chosen
    if args.only:
        todo = [b for b in todo if compact(args.only) in compact(b["name"])]

    if args.dry_run:
        cost = sum(1 + (1 if (b["reviews"] or 0) else 0) + (1 if (b["reviews"] or 0) > REVIEWS_PAGE_1 else 0)
                   for b in todo if not (raw_dir / f'{b["place_id"]}-place.json').exists())
        for b in todo:
            print(f'  · {b["name"][:46]:<46} {str(b["category"])[:22]:<22} {b["reviews"] or 0:>3} reseñas · top 3 en {b["cells_top"]}/49')
        print(f"Créditos estimados: {cost} · salida: {out}")
        return

    run_file = raw_dir / "run.json"
    run = json.loads(run_file.read_text(encoding="utf-8")) if run_file.exists() else {}
    if not args.from_raw:
        key = find_key()
        if not key:
            sys.exit("✗ Falta SERPAPI_KEY: pégala en .env (SERPAPI_KEY=...) o defínela como variable de entorno.")
        try:
            left = account_credits(key).get("total_searches_left")
        except RuntimeError as e:
            sys.exit(f"✗ SerpAPI: {e}")
        print(f"Créditos disponibles: {left}")
        raw_dir.mkdir(parents=True, exist_ok=True)
        used = 0
        for b in todo:
            try:
                spent = capture(key, b, raw_dir)
                used += spent
                print(f'  ✓ {b["name"][:50]} ({spent} créditos)')
            except RuntimeError as e:
                print(f'  ✗ {b["name"][:50]}: {e}')
        time.sleep(3)
        try:
            after = account_credits(key).get("total_searches_left")
        except RuntimeError:
            after = None
        run.setdefault("credits_before", left)
        run["requests_made"] = run.get("requests_made", 0) + used
        run["credits_after"] = after
        start = run["credits_before"]
        run["credits_used"] = start - after if isinstance(start, int) and isinstance(after, int) else None
        save_json(run_file, run)

    meta = {"skill": "gbp-deep-profile", "label": args.label, "keyword": grid["meta"]["keyword"],
            "date": out.name[:10], "grid": args.grid.name, "excluded_categories": EXCLUDE_CATEGORIES, **run}
    print(build_outputs(out, meta, todo))


if __name__ == "__main__":
    main()
