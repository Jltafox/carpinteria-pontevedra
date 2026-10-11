"""
Importa las imágenes de Nano Banana a la web: recorta a la proporción exacta (desde el centro), redimensiona al
tamaño final, convierte a WebP y guarda en web/public/img/... según web/IMAGENES-prompts.csv.

Uso:
    py scripts/import_images.py --por-orden            # descargas sin renombrar: muestra qué nombre recibe cada una
    py scripts/import_images.py --por-orden --aplicar  # renombra por orden de descarga e importa
    py scripts/import_images.py                        # archivos ya renombrados en fotos-nanobanana/
    py scripts/import_images.py --src otra/carpeta

Requiere Pillow:  py -m pip install pillow
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from local_pack_multi_city import ROOT

CSV_FILE = ROOT / "web" / "IMAGENES-prompts.csv"
QUALITY = 80  # WebP: buen equilibrio peso/calidad para fotos


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", type=Path, default=ROOT / "fotos-nanobanana")
    parser.add_argument("--por-orden", action="store_true",
                        help="asigna las descargas sin renombrar, por hora de descarga, a las imágenes pendientes de la lista")
    parser.add_argument("--aplicar", action="store_true", help="con --por-orden: renombra e importa (sin él solo muestra)")
    args = parser.parse_args()

    rows = list(csv.DictReader(CSV_FILE.open(encoding="utf-8-sig"), delimiter=";"))
    images = [p for p in args.src.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
    if args.por_orden:
        known = {Path(r["guardar_como"]).stem.lower() for r in rows}
        loose = sorted((p for p in images if p.stem.lower() not in known), key=lambda p: p.stat().st_mtime)
        named = {p.stem.lower() for p in images}
        pending = [r for r in rows if Path(r["guardar_como"]).stem.lower() not in named and not (ROOT / r["destino"]).exists()]
        if len(loose) > len(pending):
            print(f"⚠ Hay {len(loose)} descargas sin nombre y solo {len(pending)} imágenes pendientes: sobran "
                  f"{len(loose) - len(pending)} (¿descartes sin borrar?). Revisa antes de aplicar.")
        pairs = list(zip(loose, pending))
        for source, row in pairs:
            print(f'  {row["orden"]:>3}. {source.name}  →  {row["guardar_como"]}')
        if not args.aplicar:
            print(f"(revisión) {len(pairs)} asignaciones. Si es correcto: py scripts/import_images.py --por-orden --aplicar")
            return
        for source, row in pairs:
            source.rename(source.with_name(Path(row["guardar_como"]).stem + source.suffix.lower()))
        images = [p for p in args.src.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]

    try:
        from PIL import Image, ImageOps
    except ImportError:
        sys.exit("✗ Falta Pillow: py -m pip install pillow")
    available = {p.stem.lower(): p for p in images}
    done, missing = 0, []
    for row in rows:
        source = available.get(Path(row["guardar_como"]).stem.lower())
        if not source:
            missing.append(row["guardar_como"])
            continue
        width, height = (int(v) for v in row["tamano_final"].split("x"))
        with Image.open(source) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img = ImageOps.fit(img, (width, height), Image.LANCZOS, centering=(0.5, 0.5))
            target = ROOT / row["destino"]
            target.parent.mkdir(parents=True, exist_ok=True)
            img.save(target, "WEBP", quality=QUALITY, method=6)
        done += 1
        print(f'  ✓ {source.name} → {row["destino"]} ({target.stat().st_size // 1024} KB)')
    unknown = sorted(set(available) - {Path(r["guardar_como"]).stem.lower() for r in rows})
    print(f"✓ {done} importadas · faltan {len(missing)} de {len(rows)}")
    if unknown:
        print("⚠ Archivos con nombre no reconocido (revisa «Guardar como»):", ", ".join(unknown[:10]))


if __name__ == "__main__":
    main()
