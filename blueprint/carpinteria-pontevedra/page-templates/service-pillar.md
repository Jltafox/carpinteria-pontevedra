# Plantilla · Página pilar de servicio

| | |
|---|---|
| **URL** | `/{{servicio_slug}}/` (6 pilares: cocinas, armarios, muebles, rehabilitación, exterior, suelos) |
| **Schema** | `schema-templates/service-pillar.jsonld` (Service + OfferCatalog de subservicios + BreadcrumbList + FAQPage) |
| **Keyword principal** | La de mayor volumen de la línea en `url-map.yaml` (p. ej. "diseño de cocina", "armarios a medida", "reformas viviendas madera") |
| **Longitud** | 1.000–1.500 palabras. Carpimoble, el competidor más trabajado, tiene 1.501 en su portada; la mediana del resto es ~450 |

## Title y meta
- **Title**: `{{servicio}} en Pontevedra y Santiago | {{marca}}`
- **Meta description**: `{{servicio_tipo}} con taller propio en A Estrada y montaje por nuestro equipo. Te llamamos en menos de 2 días. Presupuesto: {{telefono}}`

## Estructura
1. **H1 · `{{servicio}}`** + subtítulo con el diferencial y los tres CTA (teléfono, WhatsApp, presupuesto), igual que en `service-area.md`.
2. **H2 · Qué hacemos.** Una H3 por subservicio (tabla de abajo), 80–150 palabras cada una, con foto real.
3. **H2 · Cómo trabajamos y plazos.** Mismo bloque de proceso que en servicio × zona.
4. **H2 · Precio orientativo y de qué depende.** Responde a las búsquedas de precio de la línea.
5. **H2 · Materiales y acabados.** Vocabulario que comparten las webs del sector: madera, materiales, calidad, acabados, fabricación, montaje.
6. **H2 · Dónde trabajamos.**
   - Tarjetas enlazadas a cada `/{{servicio_slug}}/{{zona}}/` de fase 1.
   - Debajo, texto con el resto de municipios de la cobertura del briefing.
7. **H2 · Trabajos realizados** y **H2 · Opiniones** (reales).
8. **H2 · Preguntas frecuentes** (≥ 6, marcadas con FAQPage).
9. **H2 · Servicios relacionados** (`related` de cada servicio) y CTA final.

## Notas por servicio

| Servicio | Subservicios (H3) | Semillas de FAQ (del KW research y el briefing) | Ojo |
|---|---|---|---|
| **Cocinas a medida** | Diseño con render 3D · Fabricación en taller propio · Encimeras de porcelánico, granito y Silestone · Electrodomésticos de varias marcas · Reforma de cocina (carpintería) · Montaje | ¿Cuánto cuesta una cocina a medida? · ¿Qué incluye el presupuesto de una cocina nueva? · ¿El diseño tiene coste? (se descuenta si se acepta) · ¿Cuánto tarda la fabricación y el montaje? · ¿Qué encimera elijo? | Línea prioritaria del cliente. Precios orientativos del briefing: de ~7.000 € (3 m lineales, gama económica) a ~15.000 € (5–6 m lineales, alta gama). **Confirmar si se publican** |
| **Armarios y vestidores a medida** | Armarios empotrados · Vestidores · Frentes e interiores · Despensas · Huecos irregulares y bajo cubierta | ¿Cuánto cuesta un armario empotrado por m²? · ¿Y un vestidor a medida? · ¿Aprovecháis huecos irregulares o abuhardillados? · ¿Cuánto tarda? | 9 de las 25 keywords de la línea preguntan por el precio |
| **Muebles a medida** | Salón y librerías · Dormitorios juveniles e infantiles · Muebles de baño a medida · Recibidores · Mobiliario para locales | ¿Cuánto cuestan los muebles a medida? · ¿Qué madera usáis? · ¿Hacéis muebles de baño resistentes a la humedad? | Los muebles de baño (120 búsquedas/mes) van aquí como H3 en fase 1 |
| **Rehabilitación de madera en viviendas** | Tejados y cubiertas de madera · Armazones y estructuras · Vigas · Forjados · Refuerzo y sustitución de piezas | ¿Se puede rehabilitar un forjado de madera o hay que sustituirlo? · ¿Cómo sé si una viga está dañada? · ¿Necesito proyecto o licencia? · ¿Cuánto dura la obra? · ¿Trabajáis en casas de piedra? | Enfocada a **viviendas**. El briefing dice "reformas… solo carpintería": no prometer albañilería ni dirección de obra. Si hace falta técnico o licencia, explicar cómo se coordina (**confirmar con Fervenza**) |
| **Carpintería exterior de madera** | Porches · Pérgolas · Cobertizos · Puertas exteriores · Muebles de exterior | ¿Cuánto cuesta un porche de madera? · ¿Qué madera aguanta el clima gallego? · ¿Un porche necesita licencia? · ¿Qué mantenimiento lleva? | En Maps, "carpintería" en Galicia se mezcla con aluminio y PVC (34 % del resto del grid): decir siempre **de madera**. Ventanas: **confirmar** si Fervenza las hace |
| **Suelos de madera** | Tarima · Parquet · Pulido y barnizado · Escaleras y rodapiés | ¿Tarima o parquet? · ¿Se puede pulir un suelo antiguo? | Sin demanda local en el KW research: solo pilar, sin páginas por zona |
