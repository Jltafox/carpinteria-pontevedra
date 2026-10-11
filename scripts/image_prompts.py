"""
Prompts de Nano Banana para las 107 fotos de la web (uno por hueco de web/IMAGENES.csv).

Escribe web/IMAGENES-prompts.md (para copiar y pegar) y web/IMAGENES-prompts.csv. Cada imagen tiene un
«nombre para guardar» plano (p. ej. cocinas-a-medida__pontevedra__portada.png): guarda lo que genere Nano Banana
con ese nombre en la carpeta fotos-nanobanana/ y scripts/import_images.py lo recorta, redimensiona, convierte a
WebP y lo coloca en web/public/img/... con la ruta definitiva.

Uso:
    py scripts/image_prompts.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from local_pack_multi_city import ROOT, slugify

PAGES = ROOT / "web" / "src" / "data" / "pages.json"
OUT_MD = ROOT / "web" / "IMAGENES-prompts.md"
OUT_CSV = ROOT / "web" / "IMAGENES-prompts.csv"
INCLUDE_GALLERIES = False  # las galerías de «Trabajos realizados» serán fotos reales

STYLE = ("Photorealistic architectural photograph for a modern design magazine, full-frame camera, 24–35mm "
         "lens, soft natural daylight with warm accent lighting, realistic materials and fine wood grain. Contemporary "
         "design: clean lines, flush handle-less fronts, light natural oak combined with matte lacquer (white, warm grey "
         "or sage green), smooth plastered walls, uncluttered styling. Not rustic: no knotty reclaimed wood, no "
         "stone-heavy farmhouse look. No people in the frame unless the scene explicitly describes hands at work; hands "
         "only, never faces or heads. No text, no logos, no brand names or labels on machines, tools or appliances, no "
         "watermarks.")

ZONE = {
    "pontevedra": "Setting: a renovated contemporary flat in Pontevedra, Galicia (Spain), large window with soft "
                  "Atlantic light; Galician character only as a subtle accent (a glimpse of granite or the city).",
    "santiago-de-compostela": "Setting: a modern renovated flat in Santiago de Compostela, Galicia (Spain), tall "
                              "windows, overcast silver daylight, a glimpse of granite rooftops outside.",
    "sanxenxo": "Setting: a contemporary coastal home in Sanxenxo, Galicia (Spain), Rías Baixas, bright sea light, "
                "the ocean visible through large windows.",
}
DEFAULT_ZONE = ("Setting: a contemporary home in Galicia (Spain), soft Atlantic light; Galician character only as a "
                "subtle accent.")

HERO = {
    "home": "Interior of a working carpentry workshop: a workbench with oak boards, a kitchen cabinet carcass being "
            "assembled, clamps, chisels and sawdust, a panel saw in the background, warm daylight from large windows; "
            "a carpenter's hands (no face visible) marking a board with a pencil and square.",
    "sobre-nosotros": "Wide view of a clean, well-organised modern carpentry workshop: CNC panel saw, edge-banding machine, sheets of oak veneer and lacquered panels, finished cabinet modules wrapped and ready for delivery, bright daylight from high windows; no people.",
    "cocinas-a-medida": "A newly installed custom kitchen with oak wood fronts and a white porcelain countertop, "
                        "handle-less drawers, integrated appliances, warm under-cabinet lighting, a few everyday objects.",
    "armarios-a-medida": "A floor-to-ceiling built-in wardrobe with matte white sliding doors and an oak interior; one "
                         "door open showing hanging rails, drawers and shoe shelves, in a calm bedroom.",
    "muebles-a-medida": "A custom solid oak bookcase and TV unit spanning a living-room wall, fitted around a window, "
                        "books and plants on the shelves.",
    "rehabilitacion-de-madera": "A renovated contemporary living space under a restored timber roof: exposed new and original beams and rafters in light-toned wood, smooth white walls, large skylight, minimalist furniture; restoration finished, clean and bright.",
    "carpinteria-exterior": "A contemporary timber porch with slim square posts and a flat roof attached to a modern white house, slatted wood details, outdoor furniture, green lawn, soft light after rain.",
    "suelos-de-madera": "Wide-plank light oak floor with matte natural finish in a bright minimalist living room, white walls, flush skirting, large window light raking across the boards.",
}

AREA_HERO = {
    "cocinas-a-medida/pontevedra": "A custom kitchen fitted in a narrow city-centre flat: tall pantry columns, corner "
                                   "units and pull-out drawers making the most of every centimetre, oak and white fronts.",
    "cocinas-a-medida/santiago-de-compostela": "A renovated kitchen in an older city flat with high ceilings: oak and "
                                               "white lacquer fronts, a stone countertop, a powerful extractor hood, "
                                               "rain on the window.",
    "armarios-a-medida/pontevedra": "A built-in wardrobe with sliding doors in a compact bedroom of a city flat, "
                                    "interior with two hanging levels and drawers.",
    "armarios-a-medida/santiago-de-compostela": "A small walk-in dressing room with oak shelving, drawers and hanging "
                                                "rails in a city flat.",
    "muebles-a-medida/pontevedra": "A custom oak bookcase built around a window in a living room, with a window seat.",
    "muebles-a-medida/santiago-de-compostela": "A teenager's bedroom with a custom bed, desk and wardrobe unit in light "
                                               "birch wood, fitted into a small room.",
    "rehabilitacion-de-madera/pontevedra": "A renovated flat in a historic building with restored wooden floor beams left exposed on the ceiling, light oak floor, white walls, modern furniture.",
    "rehabilitacion-de-madera/santiago-de-compostela": "A modern loft created under a restored timber roof in an old building: new and original rafters in light wood, skylights, white walls, contemporary furniture.",
    "rehabilitacion-de-madera/sanxenxo": "A contemporary coastal home with a restored exposed timber roof structure over an open living space, large windows to the sea, white walls, light linen furniture.",
    "carpinteria-exterior/pontevedra": "A modern timber porch with slim posts and a flat roof on a contemporary family house, slatted wood screen, garden.",
    "carpinteria-exterior/santiago-de-compostela": "A minimalist timber pergola over a terrace and a matching slatted wooden storage shed in the garden of a contemporary house, light rain, green lawn.",
    "carpinteria/santiago-de-compostela": "A modern renovated flat with custom joinery: floor-to-ceiling oak shelving, a white lacquered kitchen and an oak staircase, tall windows with overcast daylight.",
}

SUB = {  # una escena por subservicio (clave = slug del H3)
    "diseno-de-cocina-con-render-3d": "A kitchen design printout and wood and countertop samples on a workshop table, "
                                      "with a laptop showing a 3D kitchen model (screen slightly out of focus).",
    "fabricacion-de-muebles-de-cocina-en-taller-propio": "Kitchen cabinet carcasses being assembled in a carpentry "
                                                         "workshop, edge-banded panels stacked, clamps.",
    "encimeras-de-porcelanico-granito-y-silestone": "Close-up of three kitchen countertop samples side by side — "
                                                    "porcelain, granite and quartz — on an oak cabinet.",
    "electrodomesticos-de-varias-marcas": "Integrated oven and microwave column in a custom wooden kitchen, no visible "
                                          "brand names.",
    "reforma-de-cocina-parte-de-carpinteria": "A kitchen under renovation: new cabinets being fitted against freshly "
                                              "plastered walls, protective sheets on the floor.",
    "montaje-por-equipo-propio": "Two installers' hands (no faces) levelling and fixing a kitchen wall cabinet with a "
                                 "spirit level and screwdriver.",
    "armarios-empotrados": "Built-in wardrobe filling a wall from floor to ceiling, hinged oak doors, one open.",
    "vestidores": "Open walk-in closet with oak shelves, drawers and hanging rails, soft light.",
    "frentes-e-interiores-de-armario": "Interior organisation of a wardrobe: drawers, trouser rack, shoe shelves and "
                                       "LED strip lighting.",
    "despensas-a-medida": "A custom pantry with adjustable shelves and pull-out baskets full of jars and food.",
    "huecos-irregulares-y-bajo-cubierta": "Wardrobe fitted under a sloping attic ceiling, modules of different heights.",
    "muebles-de-salon-y-librerias": "Wall-to-wall oak library shelving with books around a doorway.",
    "dormitorios-juveniles-e-infantiles": "Children's room with a custom raised bed, storage steps and a desk underneath.",
    "muebles-de-bano-a-medida": "Floating oak bathroom vanity with a stone basin and a mirror, tiled wall.",
    "recibidores-y-zapateros": "Entryway unit with a bench, hidden shoe storage and coat hooks in light wood.",
    "mobiliario-para-locales": "Custom oak counter and display shelves in a small local shop, empty of customers.",
    "tejados-y-cubiertas-de-madera": "Newly built timber roof structure — trusses, purlins and rafters in light-coloured wood — on a renovated house, seen from outside before the final roofing, clear sky.",
    "armazones-y-estructuras-de-madera": "New light-wood timber frame reinforcing an attic being converted into a modern bedroom, clean drywall partly installed.",
    "vigas-de-madera": "Close-up of a new laminated timber beam joined to an original beam with a black steel plate and bolts, in a renovation with white walls.",
    "forjados-de-madera": "Wooden floor structure during renovation: new joists neatly installed next to original ones, clean site, before laying the boards.",
    "refuerzo-y-sustitucion-de-piezas-danadas": "Carpenter's hands (no face) fitting a new section of timber into an old beam during a careful renovation, clean modern tools.",
    "porches-de-madera-a-medida": "Detail of a modern timber porch: square post and beam joint with concealed black steel connectors.",
    "pergolas": "Minimalist slatted timber pergola over a porcelain-tiled terrace with contemporary outdoor furniture.",
    "cobertizos-de-madera": "Modern slatted wood garden shed with a flat roof next to a contemporary house.",
    "puertas-exteriores-de-madera": "Contemporary solid oak entrance door with vertical grooves and a slim black pull handle, white façade.",
    "muebles-de-exterior-a-medida": "Custom minimalist wooden bench and dining table on a modern terrace after rain.",
    "tarima-de-madera": "Installer's hands (no face) laying light oak floorboards, tongue-and-groove joints visible, in a bright empty modern room.",
    "parquet": "Light oak herringbone parquet in a contemporary living room with white walls.",
    "pulido-y-barnizado": "Old wooden floor half sanded to bare light wood, half original, in a bright room being renovated; sanding machine without visible brand.",
    "escaleras-y-rodapies": "Contemporary staircase clad in light oak with flush oak skirting, white walls, minimalist handrail.",
}

GALLERY = {  # 5 variantes por servicio; cada página usa 3 distintas + el contexto de su zona
    "cocinas-a-medida": ["Detail of an opened kitchen drawer with a wooden cutlery organiser, oak fronts.",
                         "Oak kitchen island with a granite countertop and stools, pendant lights.",
                         "Tall pantry column with pull-out shelves in a custom kitchen.",
                         "Corner of a kitchen with oven columns and matte white lacquer fronts.",
                         "U-shaped kitchen with open oak shelves and a quartz countertop."],
    "armarios-a-medida": ["Interior of a built-in wardrobe with drawers, hanging rail and LED strip.",
                          "Wardrobe adapted to a sloping attic ceiling.",
                          "Shallow hallway storage cupboard with hinged painted doors.",
                          "Walk-in closet with a central island of drawers.",
                          "Under-stairs cupboard with pull-out baskets."],
    "muebles-a-medida": ["Wall-to-wall oak shelving in a reading corner.",
                         "Floating bathroom vanity in oak with a stone basin.",
                         "Entryway bench with shoe storage and coat hooks.",
                         "Children's bunk bed with storage steps.",
                         "Custom oak TV unit with closed storage and open shelves."],
    "rehabilitacion-de-madera": ["New chestnut beam joined to an old one with a steel plate.",
                                 "Attic with restored roof rafters and new boarding.",
                                 "Replaced wooden floor joists before laying new planks.",
                                 "Restored beamed ceiling in a stone house interior, finished.",
                                 "Roof structure of a stone house seen from outside during restoration."],
    "carpinteria-exterior": ["Timber porch post-and-beam joint with galvanised brackets.",
                             "Pine pergola over a paved terrace.",
                             "Wooden tool and firewood shed in a garden.",
                             "Solid wood entrance door in a granite doorway.",
                             "Custom outdoor wooden bench and table on a terrace."],
    "suelos-de-madera": ["Herringbone oak parquet floor.", "Sanding an old wooden floor.",
                         "Wooden staircase with matching floor."],
}
OFFSET = {"pillar": 0, "pontevedra": 1, "santiago-de-compostela": 2, "sanxenxo": 3}
HOME_GALLERY = ["Finished custom oak kitchen in a Galician home.",
                "Restored exposed wooden beams in a granite house.",
                "Timber porch on a stone house in green countryside."]
HUB_GALLERY = ["Built-in wardrobe in a city flat.", "Renovated kitchen with oak fronts.",
               "Timber porch on a house near Santiago in the rain."]


def ratio(img: dict) -> str:
    return {(1500, 1000): "3:2", (900, 600): "3:2", (1200, 900): "4:3"}.get((img["width"], img["height"]), "3:2")


def file_name(src: str) -> str:
    return src.removeprefix("/img/").removesuffix(".webp").replace("/", "__") + ".png"


def prompt_for(page: dict, use: str, img: dict, index: int = 0, sub_slug: str = "") -> str:
    p = page["params"]
    service, zone = p.get("servicio"), p.get("zona")
    if use == "portada":
        key = f"{service}/{zone}" if page["type"] == "service-area" else f"carpinteria/{zone}" if page["type"] == "hub" else None
        scene = AREA_HERO.get(key) or HERO.get(service) or HERO.get(page["type"]) or HERO["home"]
    elif use == "subservicio":
        scene = SUB[sub_slug]
    elif page["type"] == "home":
        scene = HOME_GALLERY[index]
    elif page["type"] == "hub":
        scene = HUB_GALLERY[index]
    else:
        variants = GALLERY[service]
        scene = variants[(OFFSET["pillar" if page["type"] == "pillar" else zone] + index) % len(variants)]
    context = ZONE.get(zone, DEFAULT_ZONE)
    if page["type"] in ("home", "sobre-nosotros") and use == "portada":
        context = "Setting: A Estrada, Galicia (Spain)."
    return f"{scene} {context} {STYLE} Aspect ratio {ratio(img)}."


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    pages = json.loads(PAGES.read_text(encoding="utf-8"))["pages"]
    rows, seen = [], set()
    for page in pages:
        found = [("portada", page["hero_image"], 0, "")] if "hero_image" in page else []
        for section in page["sections"]:
            found += [("subservicio", i["image"], 0, slugify(i["h3"])) for i in section.get("items", []) if "image" in i]
            if INCLUDE_GALLERIES:
                found += [("galería", img, n, "") for n, img in enumerate(section.get("images", []))]
        for use, img, n, sub in found:
            if img["src"] in seen:
                continue
            seen.add(img["src"])
            rows.append({"orden": len(rows) + 1, "guardar_como": file_name(img["src"]), "destino": "web/public" + img["src"],
                         "proporcion": ratio(img), "tamano_final": f'{img["width"]}x{img["height"]}',
                         "pagina": page["route"], "uso": use, "prompt": prompt_for(page, use, img, n, sub)})

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    lines = ["# Prompts para Nano Banana · fotos de carpinteriaurexal.es", "",
             f"{len(rows)} imágenes (portadas y subservicios; las galerías de proyectos serán fotos reales).", "",
             "**Genera las imágenes en el orden de esta lista** y descárgalas tal cual en `fotos-nanobanana/` "
             "(raíz del proyecto), sin renombrar. `py scripts/import_images.py --por-orden` las asigna por hora de "
             "descarga a cada nombre, te enseña la correspondencia y, al confirmar, las recorta, convierte a WebP y "
             "coloca en la web. Si regeneras una imagen, **borra la descarga descartada** para no descuadrar el orden.",
             "", "También puedes renombrarlas tú con el nombre de cada título y ejecutar `py scripts/import_images.py`.", ""]
    current = None
    for r in rows:
        if r["pagina"] != current:
            current = r["pagina"]
            lines += ["", f"## Página `{current}`", ""]
        done = (ROOT / r["destino"]).exists()
        lines += [f'### {r["orden"]}. {r["guardar_como"]}' + (" · ✓ hecha" if done else ""), "",
                  f'- **Uso:** {r["uso"]} · **proporción** {r["proporcion"]} · **tamaño final** {r["tamano_final"]} px',
                  f'- **Destino:** `{r["destino"]}`', "", "```text", r["prompt"], "```", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"✓ {len(rows)} prompts → {OUT_MD.relative_to(ROOT)} y {OUT_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
