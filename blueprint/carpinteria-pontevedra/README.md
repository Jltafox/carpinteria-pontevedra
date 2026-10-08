# Blueprint · web de captación de carpintería (Pontevedra · Santiago · Sanxenxo)

Plano de la web generado con la skill `web-blueprint-generator` a partir de
[`data/patterns/carpinteria/2026-10-07_pontevedra/hypotheses.md`](../../data/patterns/carpinteria/2026-10-07_pontevedra/hypotheses.md).
Es el input de la siguiente skill, `landing-generator-servicio-barrio` (Astro por defecto).

## Archivos
| Archivo | Qué es | Cómo se edita |
|---|---|---|
| `url-map.yaml` | Las 26 URLs de fase 1: servicios, zonas, keywords y fase 2 | **Generado.** Editar `scripts/web_blueprint_generator.py` y relanzarlo |
| `internal-linking.yaml` | Reglas y enlaces salientes de cada URL | **Generado** |
| `schema-templates/*.jsonld` | JSON-LD por tipo de página con `{{variables}}` | **Generado y validado** contra schema.org |
| `lighthouse-budget.json` | Presupuesto de rendimiento en formato Lighthouse | **Generado** |
| `page-templates/*.md` | Title, meta, H1–H3, secciones, CTA y contenido mínimo por tipo de página | A mano |

En los JSON-LD, una lista con un solo elemento de ejemplo (FAQ, ofertas, ítems) significa "repetir por cada elemento".

```bash
py scripts/web_blueprint_generator.py
```

Este comando regenera los archivos y valida tres cosas:
- el JSON-LD contra el vocabulario oficial de schema.org;
- que todo queda a 3 clics o menos de la home (ahora: 2);
- que ninguna zona enlazada está fuera de la cobertura del briefing.

## Decisiones y por qué
| Decisión | Dato que la respalda |
|---|---|
| Arquitectura **servicio × zona** (`/{servicio}/{zona}/`) + hubs `/carpinteria/{zona}/` | Hipótesis 6: el orgánico de "carpintería" es de los directorios y solo Carpimoble usa servicio × ciudad. Una ficha cubre unos 3 km; la web capta el resto |
| **Ciudad en title y H1**, CTA de teléfono, WhatsApp y formulario arriba, mapa, FAQ | Solo 2 de 8 competidores ponen la ciudad, 3 de 8 enlazan el teléfono, 1 de 8 tiene mapa y 1 de 8 tiene FAQPage |
| **Schema** HomeAndConstructionBusiness + Service con `areaServed` + FAQPage + BreadcrumbList | Solo 1 de 8 tiene LocalBusiness y ninguno tiene Service |
| **Zonas de fase 1**: Pontevedra, Santiago y Sanxenxo (solo rehabilitación) | Pontevedra: probable primera ficha y 796 búsquedas/mes. Santiago: 1.312 búsquedas/mes, se capta por orgánico. "reformas madera sanxenxo": 60/mes |
| **Resto de la cobertura en fase 2** | Sin búsquedas locales en el KW research. Páginas por zona casi iguales = riesgo de *doorway pages* |
| **Suelos de madera solo como pilar** | 0 búsquedas locales en el KW research |
| **Rehabilitación de madera enfocada a viviendas** (tejados, armazones, vigas, forjados) | Indicación del cliente. Es la línea con más intención: "reformas viviendas madera" 90 y "reformas carpintería madera" 90 |
| **≥ 40 % de texto exclusivo** por página servicio × zona | Calidad frente a páginas duplicadas |
| **Opiniones reales sin `AggregateRating`** | Hipótesis 4: las reseñas no explican la visibilidad. Sirven para convertir |
| **Precio y plazos visibles** | Briefing: son las dos preocupaciones principales del cliente |

**Dos ajustes respecto a la plantilla de la skill:**
- El pilar va en `/{servicio}/` en lugar de `/servicios/{slug}/`. Así la jerarquía queda limpia (Inicio › Servicio › Zona).
- `areaServed` usa `City` en vez de `PostalAddress`, porque schema.org no admite PostalAddress en esa propiedad.

## Variables a rellenar
| Variable | Valor |
|---|---|
| `marca` | Nombre comercial (hipótesis 2: con "Carpintería") |
| `dominio` | |
| `telefono`, `whatsapp`, `email` | |
| `calle`, `cp`, `localidad`, `provincia` | |
| `lat`, `lng` | |
| `abre`, `cierra` | |
| `gbp_url` | |
| `logo_url`, `imagen_url` | |

## Ficha de Google (hipótesis 1–3)
- **Categoría principal:** Carpintería.
- **Categorías secundarias:** las `categoria_gbp` de `url-map.yaml`:
  - Tienda de muebles de cocina
  - Tienda de armarios
  - Fábrica de muebles
  - Fábrica de puertas
  - Servicio de instalación de suelos de madera
- **NAP:** idéntico en la ficha, en el pie de la web y en el schema.
- **Sitio web de la ficha:** la home, que ataca Pontevedra y hace de hub de esa zona (no existe `/carpinteria/pontevedra/`).

## Rendimiento
`lighthouse-budget.json` fija los umbrales "bueno" de Core Web Vitals: LCP ≤ 2,5 s, CLS ≤ 0,1, TBT ≤ 200 ms y JS ≤ 60 KB. Astro sin JavaScript en cliente los cumple de serie.

La comparación con la competencia está pendiente: PageSpeed no respondió sin clave. Con `PAGESPEED_API_KEY` en `.env` se mide relanzando `scripts/web_pattern_extractor.py`.

## Pendiente de confirmar antes de generar
1. Nombre comercial, NAP, teléfono, WhatsApp y dominio.
2. Si se publican los **rangos de precio** de cocinas del briefing (~7.000–15.000 €).
3. Subservicios que no aparecen explícitos en el briefing: **ventanas de madera** y tratamiento de la madera (carcoma, humedad).
4. **Rehabilitación estructural:** hasta dónde llega la parte de carpintería y cómo se coordina con técnico o licencia.
5. **Fotos y testimonios reales** de trabajos de Fervenza, con permiso.
6. **Legal:**
   - El aviso legal debe identificar al titular de la web (LSSI).
   - La política de privacidad del formulario debe informar de que los datos se comunican a la carpintería que ejecuta el trabajo (RGPD).
