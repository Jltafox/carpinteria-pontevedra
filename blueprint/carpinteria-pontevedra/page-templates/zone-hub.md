# Plantilla · Hub de zona ("carpintería en {{zona}}")

| | |
|---|---|
| **URL** | `/carpinteria/{{zona_slug}}/`. Solo zonas con `hub: true` en `url-map.yaml` (fase 1: Pontevedra y Santiago de Compostela) |
| **Schema** | `schema-templates/zone-hub.jsonld` (CollectionPage + ItemList de los servicios de la zona + BreadcrumbList) |
| **Keyword principal** | "carpintería en {{zona}}", "carpintería de madera en {{zona}}" (Pontevedra: 20 + 10 búsquedas/mes; Santiago: 10) |
| **Longitud** | 500–800 palabras, exclusivas de la zona |

## Title y meta
- **Title**: `Carpintería en {{zona}}: cocinas, armarios y rehabilitación | {{marca}}`
- **Meta description**: `Carpintería de madera en {{zona}} y alrededores: {{servicios_zona}}. Visita en 3–4 días laborables. Llámanos: {{telefono}}`

## Estructura
1. **H1 · `Carpintería de madera en {{zona}}`** + los tres CTA.
2. **H2 · Servicios en {{zona}}.**
   - Tarjetas enlazadas a cada `/{{servicio}}/{{zona_slug}}/`.
   - Si un servicio no tiene página en la zona (p. ej. suelos), se enlaza su pilar.
3. **H2 · Barrios y parroquias donde trabajamos**, desde `barrios_parroquias`, con una frase sobre el tipo de encargo habitual en cada uno.
4. **H2 · Trabajos en {{zona}}.** Proyectos reales de la zona, si los hay.
5. **H2 · Zonas cercanas.** `zonas_cercanas` en texto y enlace al otro hub.
6. **Cierre**: CTA, NAP y mapa.

## Relación con la ficha de Google
**Pontevedra:** si la primera ficha se abre en Pontevedra, su campo "sitio web" debe apuntar a **este hub** (o a la home si la marca solo tiene una ficha).

El grid mostró que una ficha domina unos 3 km a su alrededor: el hub refuerza esa zona y las páginas de servicio × zona captan el resto por orgánico.
