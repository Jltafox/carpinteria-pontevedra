# Web de captación · carpintería (Astro)

Generada con la skill `landing-generator-servicio-barrio` a partir de [`blueprint/carpinteria-pontevedra/`](../blueprint/carpinteria-pontevedra/README.md).
Son 26 páginas estáticas sin JavaScript en el navegador: solo un script de 10 líneas en `/presupuesto/` que rellena el servicio y el municipio cuando se llega desde una landing.

## Cómo funciona
| Archivo | Qué es | Quién lo edita |
|---|---|---|
| `src/data/business.json` | Marca, NAP, teléfono, WhatsApp, dominio, datos legales, proyectos, testimonios y `publicar_precios` | **Tú** |
| `src/data/pages.json` | Las 26 páginas ya compuestas (textos, enlaces y JSON-LD) | Generado por `py scripts/landing_generator.py` |
| `src/data/areas-served.json` | Zonas, cobertura y municipios excluidos (fuente de verdad de zonas) | Generado |
| `blueprint/carpinteria-pontevedra/content/*.json` | Textos de servicios y zonas | A mano. Después se regenera |

Mientras un dato de `business.json` esté vacío, la web lo muestra como `{{variable}}`. Además:
- en modo desarrollo sale un aviso amarillo con la lista de datos pendientes;
- cada página lleva `noindex`;
- `robots.txt` bloquea el rastreo.

Así no se puede indexar por error una web a medio rellenar.

## Fotos
Las 111 fotos ya tienen su URL definitiva. La lista completa, con ruta, uso, tamaño, alt propuesto y páginas donde aparece, está en [`IMAGENES.csv`](IMAGENES.csv).

Basta con guardar cada foto en `web/public/img/...` con ese nombre, en WebP y al tamaño indicado, y la web la muestra sola. Mientras no exista, se ve un hueco rayado con la ruta y el tamaño.

Al subir las fotos reales, sustituye el alt propuesto por uno que describa lo que se ve en cada una.

## Comandos
Desde la raíz del proyecto, para regenerar las páginas tras editar el blueprint o los textos:

```bash
py scripts/landing_generator.py
```

Desde la carpeta `web/`, para instalar dependencias:

```bash
npm install
```

Para arrancar en local (http://localhost:4321):

```bash
npm run dev
```

Para comprobar que `business.json` está completo y generar `dist/` para publicar:

```bash
npm run release
```

## Antes de publicar
Estado a 14/10/2026. `npm run release` falla mientras falte algún dato obligatorio.

- [ ] **Titular de la web:** razón social, NIF y domicilio de Dixitalea (`titular_legal`, `nif`, `domicilio_legal`). Si es sociedad, también `datos_registrales` (Registro Mercantil, tomo, folio, hoja).
- [ ] **Formulario:** enviar una prueba desde la web, pulsar «Activate Form» en el email de FormSubmit y sustituir `form_endpoint` por la URL con hash que da FormSubmit.
- [ ] **Ficha de Google:** cuando exista, `gbp_url` y `maps_embed_url` (sin ellos el mapa usa la dirección).
- [ ] **Correo:** comprobar que `contacto@carpinteriaurexal.es` llega a admin@dixitalea.com (Cloudflare Email Routing). Opcional: registro DMARC.
- [ ] **Contenido real:** `testimonios` reales y con permiso; fotos reales de trabajos para reactivar `/proyectos/`.
- [ ] **Precios:** activar `publicar_precios` solo si Fervenza confirma los rangos de cocinas.
- [ ] **QA:** `landing-qa-runner` (Playwright y Lighthouse con `blueprint/carpinteria-pontevedra/lighthouse-budget.json`).
- [ ] **Indexar:** `"indexable": true` en `business.json` y quitar el bloque `X-Robots-Tag` de `public/_headers`. Después, purgar la caché de Cloudflare.

Hecho: dominio y DNS en Cloudflare, redirecciones www→raíz y http→https, textos legales, banner de cookies, logo y favicon.

## Imágenes
`scripts/import_images.py` guarda cada foto en WebP y, si mide más de 1000 px de ancho, también una versión `-800.webp` para móvil. `Img.astro` la añade al `srcset` si existe.

## Página de trabajos realizados (desactivada)
`/proyectos/` y las galerías no se publican hasta tener fotos reales. Para activarla:
1. En `scripts/web_blueprint_generator.py`, poner `SHOW_PROJECTS = True`.
2. Renombrar `src/pages/_proyectos.astro` a `src/pages/proyectos.astro`.
3. Quitar la línea `/proyectos/ / 302` de `public/_redirects`.
4. Ejecutar `py scripts/web_blueprint_generator.py` y `py scripts/landing_generator.py`.
