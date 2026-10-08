# Plantilla · Pedir presupuesto (captación del lead)

| | |
|---|---|
| **URL** | `/presupuesto/` (acepta `?servicio=` y `?zona=` para rellenar el formulario desde cada landing) |
| **Schema** | `schema-templates/presupuesto.jsonld` (ContactPage + BreadcrumbList) |
| **Objetivo** | Recoger un lead **cualificado** según el briefing: datos de contacto, trabajo concreto, planos o fotos, rango de presupuesto y prioridad |

## Title y meta
- **Title**: `Pide presupuesto de carpintería | {{marca}}`
- **Meta description**: `Cuéntanos tu proyecto y te llamamos en menos de 2 días. Visita en 3–4 días laborables y presupuesto en 3–4 días.`

## Formulario (por orden)
| Campo | Tipo | Obligatorio | Por qué (briefing) |
|---|---|:-:|---|
| Nombre | texto | sí | contacto |
| Teléfono | `tel` | sí | "lo principal son los datos de contacto" |
| Email | `email` | no | contacto |
| Municipio | desplegable con **solo** los municipios de cobertura | sí | filtra los leads de zonas excluidas (Poio, Marín, Ponte Caldelas, Redondela…) |
| Servicio | desplegable con los 6 servicios (rellenado por `?servicio=`) | sí | saber el trabajo concreto |
| Describe el trabajo | texto largo | sí | trabajo concreto |
| Planos, bocetos o fotos | archivos (JPG/PNG/PDF, ≤ 10 MB) | no | "poder tener el proyecto, un plano o boceto, imágenes" |
| Presupuesto aproximado | rangos (< 5.000 €, 5–10.000 €, 10–15.000 €, > 15.000 €, no lo sé) | no | "rango de precio del presupuesto estimado" |
| ¿Qué priorizas? | precio / calidad y acabados / plazo | no | "saber si lo que busca es precio, calidad y buenos acabados" |
| ¿Para cuándo lo necesitas? | < 1 mes, 1–3 meses, > 3 meses | no | priorizar la agenda (2–3 cocinas/mes hasta fin de año) |
| Aceptación de la política de privacidad | casilla | sí | RGPD |

## Bloques de la página
1. **H1 · `Pide presupuesto sin compromiso`** con el teléfono y WhatsApp como alternativa al formulario.
2. El formulario.
3. **"Qué pasa después"** con los plazos reales: llamada en ≤ 2 días, visita en 3–4 días laborables, presupuesto en 3–4 días.
4. NAP, horario y mapa.

## Medición
- Evento de conversión por envío de formulario, clic en `tel:` y clic en WhatsApp (GA4 o Plausible), con `servicio` y `zona` como parámetros.
- Así se puede facturar y priorizar por línea de servicio.
