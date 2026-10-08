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
1. Rellenar `src/data/business.json`. `npm run release` falla mientras falte algo.
2. **Legal:** revisar `/aviso-legal/`, `/politica-de-privacidad/` y `/cookies/`, que son plantillas.
3. **Formulario:** configurar el endpoint del formulario en `form_endpoint` (Formspree, Netlify Forms, Getform…).
4. **Contenido real:** añadir `proyectos` y `testimonios` reales y con permiso. Mientras estén vacíos, esas secciones no se muestran.
5. **Precios:** activar `publicar_precios` solo si Fervenza confirma los rangos de cocinas.
6. **QA:** pasar `landing-qa-runner` (Playwright y Lighthouse con `blueprint/carpinteria-pontevedra/lighthouse-budget.json`).
