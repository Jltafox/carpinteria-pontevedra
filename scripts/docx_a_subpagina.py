"""Convierte un texto de Word (.docx) en una subpágina de servicio para la web.

Uso:
    py scripts/docx_a_subpagina.py TEXTO.docx --ruta /cocinas-a-medida/diseno/ \
        --title "Diseño de cocinas a medida con render 3D | Urexal" \
        --description "…" --miga "Diseño de cocinas" --item-padre "Diseño de cocina con render 3D" \
        --hero /img/cocinas-a-medida/diseno-de-cocina-con-render-3d.webp

Escribe blueprint/carpinteria-pontevedra/content/subpaginas/{servicio}__{slug}.json, que lee
scripts/landing_generator.py. Convenciones del Word (las del redactor):
- Estilos Título 1/2/3 para H1/H2/H3; los prefijos «H1.», «H2.» y «H3.» se quitan.
- Un párrafo «CTA: texto» es un botón a /presupuesto/.
- Listas con viñetas: si empiezan en negrita («**Algo:** resto»), la negrita es el titular del punto.
Cada bloque H2 se convierte en la sección que mejor encaja: preguntas frecuentes (faq), pasos numerados (process),
apartados H3 (items), texto con listas (rich), y el último bloque, si acaba en CTA, en el cierre de la página.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "blueprint" / "carpinteria-pontevedra" / "content" / "subpaginas"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def paragraphs(path: Path) -> list[dict]:
    """Párrafos del Word: nivel de título, si es viñeta, y trozos de texto con su negrita."""
    with zipfile.ZipFile(path) as z:
        doc = ET.fromstring(z.read("word/document.xml"))
        names = {}
        if "word/styles.xml" in z.namelist():
            for s in ET.fromstring(z.read("word/styles.xml")).iter(W + "style"):
                n = s.find(W + "name")
                names[s.get(W + "styleId")] = (n.get(W + "val") if n is not None else "").lower()
    out = []
    for p in doc.find(W + "body").iter(W + "p"):
        ppr = p.find(W + "pPr")
        style = ""
        bullet = False
        if ppr is not None:
            ps = ppr.find(W + "pStyle")
            style = names.get(ps.get(W + "val"), "") if ps is not None else ""
            bullet = ppr.find(W + "numPr") is not None
        runs = []
        for r in p.iter(W + "r"):
            text = "".join(t.text or "" for t in r.iter(W + "t"))
            if text:
                b = r.find(W + "rPr")
                bold = b is not None and b.find(W + "b") is not None and b.find(W + "b").get(W + "val") not in ("0", "false")
                runs.append((text, bold))
        text = "".join(t for t, _ in runs).strip()
        if not text:
            continue
        level = int(m.group(1)) if (m := re.search(r"(?:heading|título|titulo)\s*(\d)", style)) else 0
        out.append({"level": level, "bullet": bullet, "runs": runs, "text": text})
    return out


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"^H[1-6]\.\s*", "", text)).strip()


def cta_label(text: str) -> str | None:
    m = re.match(r"^\**\s*CTA\s*\**\s*:\s*(.+)$", text, re.I)
    return m.group(1).strip() if m else None


def bullet(p: dict) -> dict:
    """«**Titular:** resto» → {lead, text}; sin negrita inicial → {text}."""
    runs = p["runs"]
    if runs and runs[0][1]:
        lead, i = "", 0
        while i < len(runs) and runs[i][1]:
            lead += runs[i][0]
            i += 1
        rest = "".join(t for t, _ in runs[i:])
        lead, rest = lead.strip(), rest.strip()
        if lead.endswith(":"):
            lead = lead[:-1].strip()
        rest = rest.lstrip(":").strip()
        if rest:
            return {"lead": lead, "text": rest}
    return {"text": clean(p["text"])}


def blocks_of(items: list[dict]) -> list[dict]:
    """Párrafos, viñetas agrupadas en listas y CTA, en orden."""
    blocks: list[dict] = []
    for p in items:
        if (label := cta_label(p["text"])):
            blocks.append({"type": "cta", "label": label})
        elif p["bullet"]:
            if not blocks or blocks[-1]["type"] != "ul":
                blocks.append({"type": "ul", "items": []})
            blocks[-1]["items"].append(bullet(p))
        else:
            blocks.append({"type": "p", "text": clean(p["text"])})
    return blocks


def section(h2: str, body: list[dict]) -> dict:
    """Elige el tipo de sección según la forma del bloque H2."""
    first_h3 = next((i for i, p in enumerate(body) if p["level"] == 3), None)
    if first_h3 is None:
        return {"kind": "rich", "h2": h2, "blocks": blocks_of(body)}
    intro, groups = body[:first_h3], []
    for p in body[first_h3:]:
        if p["level"] == 3:
            groups.append({"h3": clean(p["text"]), "body": []})
        else:
            groups[-1]["body"].append(p)
    # Un CTA al final del último apartado es el botón de la sección, no parte del apartado
    cta = None
    if groups and groups[-1]["body"] and cta_label(groups[-1]["body"][-1]["text"]):
        cta = cta_label(groups[-1]["body"].pop(-1)["text"])
    text_of = lambda g: " ".join(clean(p["text"]) for p in g["body"] if not p["bullet"])
    intro_blocks = blocks_of(intro)
    if re.search(r"preguntas frecuentes", h2, re.I):
        s = {"kind": "faq", "h2": h2, "faqs": [{"q": g["h3"], "a": text_of(g)} for g in groups]}
    elif len(groups) >= 3 and all(re.match(r"^\d+[.)]\s", g["h3"]) for g in groups):
        s = {"kind": "process", "h2": h2, "intro": [b["text"] for b in intro_blocks if b["type"] == "p"],
             "steps": [{"h3": g["h3"], "text": text_of(g)} for g in groups]}
    else:
        s = {"kind": "items", "h2": h2, "intro": intro_blocks,
             "items": [{"h3": g["h3"], "text": text_of(g)} for g in groups]}
    if cta:
        s["cta"] = cta
    return s


def convert(path: Path) -> dict:
    ps = paragraphs(path)
    h1 = next((clean(p["text"]) for p in ps if p["level"] == 1), "")
    head, chunks = [], []
    for p in ps:
        if p["level"] == 1:
            continue
        if p["level"] == 2:
            chunks.append({"h2": clean(p["text"]), "body": []})
        elif chunks:
            chunks[-1]["body"].append(p)
        else:
            head.append(p)
    intro = [b for b in blocks_of(head)]
    lead = next((b["text"] for b in intro if b["type"] == "p"), "")
    page = {
        "h1": h1,
        "lead": lead,
        "intro": [b["text"] for b in intro if b["type"] == "p"][1:],
        "cta_label": next((b["label"] for b in intro if b["type"] == "cta"), None),
        "sections": [],
        "cta_final": None,
    }
    for i, c in enumerate(chunks):
        blocks = blocks_of(c["body"])
        last = i == len(chunks) - 1
        if last and blocks and blocks[-1]["type"] == "cta" and all(b["type"] in ("p", "cta") for b in blocks):
            page["cta_final"] = {"h2": c["h2"], "paragraphs": [b["text"] for b in blocks if b["type"] == "p"],
                                 "label": blocks[-1]["label"]}
        else:
            page["sections"].append(section(c["h2"], c["body"]))
    return page


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx", type=Path)
    ap.add_argument("--ruta", required=True, help="/servicio/slug/")
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", required=True)
    ap.add_argument("--miga", required=True, help="nombre corto en las migas de pan")
    ap.add_argument("--item-padre", help="subservicio del pilar que enlazará a esta página")
    ap.add_argument("--hero", help="imagen de portada (/img/...)")
    ap.add_argument("--hero-alt", default="")
    args = ap.parse_args()

    parts = args.ruta.strip("/").split("/")
    if len(parts) != 2:
        sys.exit("✗ La ruta debe ser /servicio/slug/")
    page = {"ruta": f"/{parts[0]}/{parts[1]}/", "servicio": parts[0], "slug": parts[1], "title": args.title,
            "description": args.description, "miga": args.miga, "item_padre": args.item_padre,
            "hero": args.hero, "hero_alt": args.hero_alt, **convert(args.docx)}
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"{parts[0]}__{parts[1]}.json"
    if target.exists():  # los enlaces internos se deciden aparte: no se pierden al reconvertir
        page["enlaces"] = json.loads(target.read_text(encoding="utf-8")).get("enlaces", [])
    target.write_text(json.dumps(page, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    kinds = ", ".join(f'{s["kind"]}' for s in page["sections"])
    words = len(json.dumps(page, ensure_ascii=False).split())
    print(f"✓ {target.relative_to(ROOT)} · H1: {page['h1']} · {len(page['sections'])} secciones ({kinds})"
          + (" + cierre" if page["cta_final"] else "") + f" · ~{words} palabras")


if __name__ == "__main__":
    main()
