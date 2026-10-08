"""
local-seo-pattern-aggregator · qué tienen los negocios que dominan el Local Pack frente al resto.

Implementa 03-skills/local-seo-pattern-aggregator/SKILL.md del repo "Clase 1 · Agentes IA para SEO y webs
hiperoptimizadas" (YinyangSEO Academy). Cruza tres capas (no gasta créditos):
  1. Grid de Maps (gbp_grid_extractor.py): todos los negocios visibles → Grupo A (top 3 en ≥ N puntos) vs B.
  2. Perfiles GBP (gbp_deep_profile.py): señales de ficha de los líderes.
  3. Webs (web_pattern_extractor.py): señales on-page de esos líderes.
Tests sin dependencias: Fisher exacto (sí/no), permutación de medianas (numéricas) y Spearman con permutación.

Uso:
    py scripts/local_seo_pattern_aggregator.py --grid <carpeta grid> --profiles <carpeta perfiles> \\
        --web <carpeta web-patterns> --local-pack <carpeta local-pack> --label pontevedra
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from datetime import date
from math import comb
from pathlib import Path
from statistics import median

from local_pack_multi_city import ROOT, compact, fmt, km, save_json, slugify, write_csv

MIN_TOP = 5  # Grupo A: top 3 en ≥ 5 de los 49 puntos del grid (≈ 10 %)
NOISE = {"Parada de autobús"}  # no son negocios
CARPENTRY = {"Carpintería", "Carpintero", "Ebanista"}
METAL = re.compile(r"metálica|aluminio|acero|inoxidable|pvc", re.I)
P_SIGNIFICANT = 0.1  # regla de la skill: p > 0,1 = no significativa
SEED = 7


# ── Estadística sin dependencias ─────────────────────────────────────────────────
def fisher(a: int, b: int, c: int, d: int) -> float:
    """p bilateral del test exacto de Fisher para [[a, b], [c, d]]."""
    n1, n2, k = a + b, c + d, a + c
    total = n1 + n2

    def prob(x: int) -> float:
        return comb(k, x) * comb(total - k, n1 - x) / comb(total, n1)

    observed = prob(a)
    return min(1.0, sum(prob(x) for x in range(max(0, k - n2), min(k, n1) + 1) if prob(x) <= observed * (1 + 1e-7)))


def permutation_median(xa: list[float], xb: list[float], iters: int = 10000) -> float:
    rng = random.Random(SEED)
    observed = abs(median(xa) - median(xb))
    pooled, na, hits = xa + xb, len(xa), 0
    for _ in range(iters):
        rng.shuffle(pooled)
        if abs(median(pooled[:na]) - median(pooled[na:])) >= observed - 1e-12:
            hits += 1
    return (hits + 1) / (iters + 1)


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            result[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return result


def pearson(x: list[float], y: list[float]) -> float:
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = sum((a - mx) ** 2 for a in x) ** 0.5
    sy = sum((b - my) ** 2 for b in y) ** 0.5
    return sxy / (sx * sy) if sx and sy else 0.0


def spearman(x: list[float], y: list[float], iters: int = 5000) -> tuple[float, float]:
    rx, ry = ranks(x), ranks(y)
    rho = pearson(rx, ry)
    rng = random.Random(SEED)
    shuffled, hits = ry[:], 0
    for _ in range(iters):
        rng.shuffle(shuffled)
        if abs(pearson(rx, shuffled)) >= abs(rho) - 1e-12:
            hits += 1
    return round(rho, 2), (hits + 1) / (iters + 1)


# ── Carga y cruce ────────────────────────────────────────────────────────────────
def load_grid(folder: Path) -> tuple[dict, list[dict]]:
    grid = json.loads((folder / "grid.json").read_text(encoding="utf-8"))
    center = (grid["meta"]["center"]["lat"], grid["meta"]["center"]["lng"])
    businesses = []
    for b in grid["businesses"]:
        if b["category"] in NOISE:
            continue
        businesses.append(b | {
            "name_has_keyword": "carpinter" in compact(b["name"]),
            "carpentry_category": b["category"] in CARPENTRY,
            "exact_category": b["category"] == "Carpintería",
            "metal_category": bool(METAL.search(b["category"] or "")),
            "has_website": bool(b["domain"]) and b["domain"] not in ("instagram.com", "facebook.com"),
            "has_reviews": bool(b["reviews"]),
            "reviews_10plus": (b["reviews"] or 0) >= 10,
            "rating_45plus": (b["rating"] or 0) >= 4.5,
            "distance_center_km": round(km(center, (b["lat"], b["lng"])), 1) if b["lat"] is not None else None,
        })
    return grid["meta"], businesses


def compare(group_a: list[dict], group_b: list[dict], layer: str, booleans: dict, numerics: dict) -> list[dict]:
    rows = []
    total = len(group_a) + len(group_b)
    for feature, label in booleans.items():
        a = [x[feature] for x in group_a if x.get(feature) is not None]
        b = [x[feature] for x in group_b if x.get(feature) is not None]
        coverage = round(100 * (len(a) + len(b)) / total)
        if not a or not b:
            continue
        p = fisher(sum(a), len(a) - sum(a), sum(b), len(b) - sum(b))
        pa, pb = 100 * sum(a) / len(a), 100 * sum(b) / len(b)
        rows.append({"layer": layer, "feature": feature, "label": label, "type": "sí/no", "n_A": len(a), "n_B": len(b),
                     "coverage_pct": coverage, "value_A": f"{pa:.0f} %", "value_B": f"{pb:.0f} %",
                     "diff": round(pa - pb), "p_value": round(p, 3), "significant": p <= P_SIGNIFICANT and coverage >= 50})
    for feature, label in numerics.items():
        a = [float(x[feature]) for x in group_a if x.get(feature) is not None]
        b = [float(x[feature]) for x in group_b if x.get(feature) is not None]
        coverage = round(100 * (len(a) + len(b)) / total)
        if len(a) < 2 or len(b) < 2:
            continue
        p = permutation_median(a, b)
        rows.append({"layer": layer, "feature": feature, "label": label, "type": "mediana", "n_A": len(a), "n_B": len(b),
                     "coverage_pct": coverage, "value_A": fmt(median(a)), "value_B": fmt(median(b)),
                     "diff": round(median(a) - median(b), 2), "p_value": round(p, 3),
                     "significant": p <= P_SIGNIFICANT and coverage >= 50})
    return rows


def correlations(rows: list[dict], target: str, features: dict, layer: str) -> list[dict]:
    out = []
    for feature, label in features.items():
        pairs = [(float(r[feature]), float(r[target])) for r in rows
                 if r.get(feature) is not None and r.get(target) is not None]
        if len(pairs) < 5 or len({x for x, _ in pairs}) < 2:
            continue
        rho, p = spearman([x for x, _ in pairs], [y for _, y in pairs])
        out.append({"layer": layer, "feature": feature, "label": label, "type": f"Spearman con {target}",
                    "n_A": len(pairs), "n_B": "", "coverage_pct": round(100 * len(pairs) / len(rows)),
                    "value_A": rho, "value_B": "", "diff": "", "p_value": round(p, 3), "significant": p <= P_SIGNIFICANT})
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--web", type=Path, required=True)
    parser.add_argument("--local-pack", type=Path, help="carpeta de local_pack_multi_city.py (cruce con el orgánico)")
    parser.add_argument("--label", required=True)
    parser.add_argument("--min-top", type=int, default=MIN_TOP, help=f"Grupo A: top 3 en ≥ N puntos (por defecto {MIN_TOP})")
    args = parser.parse_args()

    meta, businesses = load_grid(args.grid)
    profiles = {p["place_id"]: p for p in (json.loads(f.read_text(encoding="utf-8"))
                                           for f in args.profiles.glob("ChIJ*.json"))}
    web = {}
    with (args.web / "matrix.csv").open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            web[row["business"]] = row

    # Cruce: grid ↔ perfil (place_id) ↔ web (nombre del negocio en la matriz web)
    for b in businesses:
        p = profiles.get(b["place_id"])
        if p:
            b.update({"profiled": True, "secondary_count": len(p["secondary_categories"]),
                      "attributes_count": p["attributes_count"], "has_hours": p["has_hours"],
                      "review_velocity_month": p["review_velocity_month"],
                      "owner_response_rate": p["owner_response_rate"], "last_review_age_days": p["last_review_age_days"]})
            w = web.get(p["name"])
            if w:
                b.update({"web_words": int(w["content_words_count"] or 0), "web_services": int(w["n_services_listed"] or 0),
                          "web_localbusiness_schema": w["has_localbusiness_schema"] == "True",
                          "web_title_city": w["title_has_location"] == "True",
                          "web_h1_keyword": w["h1_keyword_match"] == "True",
                          "web_schema_pct": int(w["schema_completeness_pct"] or 0)})

    group_a = [b for b in businesses if b["cells_top"] >= args.min_top]
    group_b = [b for b in businesses if b["cells_top"] < args.min_top]

    rows = compare(group_a, group_b, "1 · Ficha básica (grid)", {
        "exact_category": "Categoría principal = «Carpintería» (igual que la búsqueda)",
        "carpentry_category": "Categoría principal de la familia carpintería (Carpintería, Carpintero, Ebanista)",
        "metal_category": "Categoría de carpintería metálica / aluminio",
        "name_has_keyword": "Nombre con «carpintería/carpintero»",
        "has_website": "Web propia enlazada en la ficha",
        "unclaimed": "Ficha sin reclamar",
        "has_reviews": "Tiene al menos 1 reseña",
        "reviews_10plus": "10 reseñas o más",
        "rating_45plus": "Nota ≥ 4,5",
    }, {
        "reviews": "Nº de reseñas",
        "rating": "Nota media",
        "distance_center_km": "Distancia de la ficha al centro de Pontevedra (km)",
    })
    rows += correlations(businesses, "cells_top", {"reviews": "Reseñas ↔ puntos en top 3",
                                                   "rating": "Nota ↔ puntos en top 3",
                                                   "distance_center_km": "Distancia al centro ↔ puntos en top 3"},
                         "1 · Ficha básica (grid)")
    profiled = [b for b in businesses if b.get("profiled")]
    rows += correlations(profiled, "cells_top", {
        "secondary_count": "Nº de categorías secundarias", "attributes_count": "Nº de atributos",
        "review_velocity_month": "Reseñas/mes (12 meses)", "owner_response_rate": "% de respuesta del propietario",
        "last_review_age_days": "Antigüedad de la última reseña (días)", "reviews": "Nº de reseñas"},
        "2 · Perfil GBP (líderes)")
    with_web = [b for b in profiled if "web_words" in b]
    rows += correlations(with_web, "cells_top", {
        "web_words": "Palabras en la portada", "web_services": "Servicios en encabezados",
        "web_schema_pct": "Completitud del schema LocalBusiness (%)"}, "3 · Web (líderes)")

    organic = {}
    if args.local_pack:
        consolidated = json.loads((args.local_pack / "consolidated.json").read_text(encoding="utf-8"))
        for city in consolidated["cities"]:
            for r in city["organic"]:
                organic.setdefault(r["domain"], []).append(f'{city["city"]} #{r["rank"]}')

    out = ROOT / "data" / "patterns" / slugify(meta["keyword"]) / f"{date.today().isoformat()}_{slugify(args.label)}"
    out.mkdir(parents=True, exist_ok=True)
    columns = ["name", "place_id", "category", "rating", "reviews", "cells_top", "solv_pct", "avr", "name_has_keyword",
               "carpentry_category", "has_website", "unclaimed", "distance_center_km", "reach_median_km",
               "secondary_count", "attributes_count", "review_velocity_month", "owner_response_rate",
               "web_words", "web_services", "web_localbusiness_schema", "web_title_city", "domain"]
    write_csv(out / "group-A-winners.csv", sorted(group_a, key=lambda b: -b["cells_top"]), columns)
    write_csv(out / "group-B-rest.csv", sorted(group_b, key=lambda b: -b["cells_top"]), columns)
    write_csv(out / "feature-comparison.csv", rows, ["layer", "feature", "label", "type", "n_A", "n_B", "coverage_pct",
                                                     "value_A", "value_B", "diff", "p_value", "significant"])
    save_json(out / "stats.json", {
        "meta": {"keyword": meta["keyword"], "grid_center": meta["center"]["label"], "grid_size": meta["size"],
                 "min_top": args.min_top, "n_A": len(group_a), "n_B": len(group_b), "n_profiled": len(profiled),
                 "n_web": len(with_web)},
        "comparison": rows,
        "winners_in_organic": {b["name"]: organic.get(b["domain"], []) for b in group_a if b["domain"]},
        "profiled": [{k: b.get(k) for k in columns} for b in profiled],
    })

    print(f"Grupo A: {len(group_a)} negocios (top 3 en ≥ {args.min_top}/49) · Grupo B: {len(group_b)} · "
          f"perfilados: {len(profiled)} · con web analizada: {len(with_web)}")
    for r in rows:
        mark = "★" if r["significant"] else " "
        values = f'A {r["value_A"]} · B {r["value_B"]}' if r["value_B"] != "" else f'rho {r["value_A"]}'
        print(f' {mark} [{r["layer"][:1]}] {r["label"][:62]:<62} {values:<22} p={r["p_value"]} n={r["n_A"]}/{r["n_B"]}')
    print("Ganadores con web en el orgánico (local-pack):",
          {k: v for k, v in (json.loads((out / "stats.json").read_text(encoding="utf-8"))["winners_in_organic"]).items() if v}
          or "ninguno")
    print("Grupo A:", "; ".join(f'{b["name"]} ({b["cells_top"]}, {b["category"]}, {b["reviews"] or 0}r, '
                                f'{b["distance_center_km"]} km)' for b in sorted(group_a, key=lambda b: -b["cells_top"])))
    print(f"→ {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
