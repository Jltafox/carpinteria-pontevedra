# Plantilla · Servicio × zona (el corazón del SEO local)

| | |
|---|---|
| **URL** | `/{{servicio_slug}}/{{zona_slug}}/` (11 páginas en fase 1: ver `servicio_x_zona` en `url-map.yaml`) |
| **Schema** | `schema-templates/service-area.jsonld` (Service + `areaServed` City + BreadcrumbList + FAQPage) |
| **Keyword principal** | "{{servicio}} en {{zona}}" y las variantes con zona de `url-map.yaml` |
| **Longitud** | 700–1.000 palabras. **Al menos el 40 % del texto es exclusivo de la zona**: si dos páginas de la misma zona o del mismo servicio se parecen más que eso, no se publica (riesgo de *doorway pages*) |

## Title y meta
- **Title** (≤ 60 caracteres): `{{servicio}} en {{zona}} | {{marca}}`
- **Meta description** (≤ 155): `{{servicio}} en {{zona}} con fabricación en taller propio y montaje por nuestro equipo. Visita en 3–4 días laborables. Pide presupuesto: {{telefono}}`

> La ciudad en title y H1 solo la tienen 2 de las 8 webs competidoras (hipótesis 6).

## Estructura

### H1 · `{{servicio}} en {{zona}}`
**Hero** (por encima del pliegue en móvil):
- Subtítulo de una línea con el diferencial: fabricación propia, montaje propio y plazos claros.
- Tres CTA visibles sin hacer scroll:
  - botón de llamada `tel:{{telefono}}`;
  - WhatsApp `https://wa.me/{{whatsapp}}`;
  - botón "Pedir presupuesto" que lleva a `/presupuesto/?servicio={{servicio_slug}}&zona={{zona_slug}}`.
- Imagen real de un trabajo, en WebP/AVIF con `width` y `height`. Es el LCP: precargarla.

> Solo 3 de 8 competidores enlazan el teléfono y 3 tienen formulario.

### H2 · `{{servicio}} para viviendas de {{zona}}`
Texto exclusivo de la zona:
- tipo de vivienda habitual (pisos del centro, casas de piedra en parroquias, chalés…);
- barrios y parroquias donde se trabaja, desde `barrios_parroquias` (p. ej. {{barrios}});
- particularidades del clima gallego: humedad y madera tratada.

Nada de rellenar con el nombre de la zona: tiene que aportar información real.

### H2 · Qué incluye
Lista de `{{subservicios}}`, una H3 por subservicio con 2–3 frases cada una (ver la tabla de servicios en `service-pillar.md`).

### H2 · Cómo trabajamos y en qué plazos
Proceso en 4 pasos con los plazos reales del briefing:
1. Te llamamos en menos de 2 días.
2. Visita y medición en 3–4 días laborables.
3. Diseño y presupuesto en 3–4 días desde la visita (o desde que nos envías planos).
4. Fabricación en taller propio y montaje por nuestro equipo.

> Los plazos son una de las dos preocupaciones principales del cliente según el briefing.

### H2 · ¿Cuánto cuesta {{servicio_minuscula}} en {{zona}}?
- Rangos orientativos *(pendiente de confirmar con Fervenza qué se publica)* y factores que mueven el precio: metros, materiales, herrajes y montaje.
- Responde a las búsquedas de precio del KW research ("precio armario empotrado por m2", "cuánto cuesta un porche de madera"…).
- El precio es la otra gran preocupación del cliente.

### H2 · Trabajos realizados
3–6 fotos de proyectos **reales** de este servicio, con pie de foto (qué se hizo y en qué municipio). Si el proyecto es en la zona, mejor.

> 6 de 8 competidores tienen galería.

### H2 · Lo que dicen nuestros clientes
2–3 testimonios **reales**, con permiso, y enlace a las reseñas de Google.

- Temas que valoran los clientes de la zona según las reseñas de los competidores: acabados, seriedad con los plazos, limpieza en el montaje, diseño.
- **Sin** marcado `AggregateRating` si las reseñas no están en la página.

### H2 · Preguntas frecuentes sobre {{servicio_minuscula}} en {{zona}}
Mínimo 5 preguntas: 3 del servicio (ver la tabla de semillas en `service-pillar.md`) y **2 específicas de la zona** (p. ej. "¿Trabajáis en {{barrio_ejemplo}}?" o "¿Cuánto tardáis en venir a {{zona}}?").

Se marcan con FAQPage. Solo 1 de 8 competidores lo tiene.

### H2 · También trabajamos en
- Bloque de zonas cercanas con `zonas_cercanas` en texto (sin enlace hasta que existan sus páginas en fase 2).
- Enlaces a "{{servicio}} en {{otra_zona}}".

### H2 · Otros servicios en {{zona}}
Enlaces a las otras páginas de servicio de la misma zona y al hub `/carpinteria/{{zona_slug}}/` (ver `internal-linking.yaml`).

### Cierre
- CTA repetido (teléfono, WhatsApp y formulario).
- **NAP idéntico al de la ficha de Google** (nombre, dirección y teléfono).
- Mapa de Google embebido con carga diferida (`loading="lazy"`). Solo 1 de 8 competidores lo tiene.

## Checklist antes de publicar
- [ ] H1 único con servicio y zona.
- [ ] ≥ 40 % de texto exclusivo frente a las páginas hermanas.
- [ ] ≥ 5 FAQ, con 2 de la zona.
- [ ] Fotos reales con `alt` descriptivo.
- [ ] CTA visibles en el primer pantallazo móvil.
- [ ] JSON-LD de `service-area.jsonld` con los valores reales; validado en Rich Results Test.
- [ ] Breadcrumb visible: Inicio › {{servicio}} › {{zona}}.
