# Hipótesis priorizadas — "carpintería" · Pontevedra

> Skill `local-seo-pattern-aggregator` · 2026-10-07 · datos: grid de Google Maps 7×7 (radio 5 km) centrado en Pontevedra,
> 11 perfiles GBP, 8 webs y el orgánico de 5 ciudades. Sin créditos de SerpAPI.
>
> - **Grupo A · ganadores:** 12 negocios en el top 3 en ≥ 5 de los 49 puntos del grid.
> - **Grupo B · resto:** 88 negocios que aparecen en el top 20 de Maps pero rara vez en el top 3.
> - Tests: Fisher exacto (sí/no), permutación de medianas y Spearman. **★ = significativa (p ≤ 0,1).**
> - Detalle de cada señal: `feature-comparison.csv`.

## Lo que separa a los ganadores

### 1. [HIGH · easy] ★ Categoría principal de la familia carpintería
**75 % del grupo A** usa Carpintería, Carpintero o Ebanista como categoría principal, **frente al 36 % del resto** (p = 0,014).

- Poner exactamente "Carpintería" no marca diferencia por sí solo: 42 % frente a 28 %, no significativo. Lo que pesa es estar en la familia de categorías que encaja con la búsqueda.
- El resto está lleno de carpintería metálica o de aluminio (34 % del grupo B).

→ **Accionable en la ficha nueva:**
- Categoría principal: Carpintería.
- Secundarias por línea de servicio, las mismas que ya usan los líderes con más señales: Tienda de muebles de cocina, Tienda de armarios, Fábrica de muebles, Fábrica de puertas y Servicio de instalación de suelos de madera.

### 2. [HIGH · medium] ★ Nombre que contiene "carpintería / carpintero"
**58 % del grupo A** frente al **26 % del resto** (p = 0,04).

Es la segunda señal más clara. Ejemplos: Carpintería Abilleira es #2 del grid con 0 reseñas, y Carpintería Martínez Paz es #1 con 11 reseñas y 3,5★.

→ **Accionable si el nombre comercial de la nueva marca incluye la palabra.** Es "medium" porque depende de la decisión de marca, no de optimizar.

### 3. [MEDIUM · decisión de ubicación] ★ La cercanía manda
- **Cercanía al centro:** las fichas más próximas al centro aparecen en el top 3 en más puntos (Spearman −0,22, p = 0,03, 100 negocios). Es una correlación débil pero consistente.
- **Alcance limitado:** los ganadores salen en el top 3 a una mediana de 2–3 km de su ficha.
- **Cada uno gana su zona:** los 12 ganadores están repartidos entre 1,1 y 6,6 km del centro; cada uno domina su sector del grid.

→ **Accionable al elegir dónde va la ficha.** Una ficha gana su entorno de unos 3 km, no todo Pontevedra. Para el centro (la zona fuerte del grid) se compite con Grupo Arta (59 reseñas) y Carvedra.

## Lo que NO separa a los ganadores (útil para no gastar esfuerzo en lo que no mueve la aguja)

### 4. [MEDIUM · medium] Reseñas y nota no explican la visibilidad
| Señal | Grupo A | Grupo B | Significativo |
|---|:-:|:-:|:-:|
| Mediana de reseñas | 11,5 | 8 | No (p = 0,37) |
| Nota media | 4,5 | 4,5 | No (p = 0,93) |
| Fichas con 10 reseñas o más | 50 % | 36 % | No |

- Correlación entre reseñas y puntos en el top 3: **−0,04**.
- La actividad es baja: el líder en ritmo no pasa de 1 reseña al mes y la mitad de los perfilados tiene la última reseña de hace más de 140 días.

→ Las reseñas no son la barrera de entrada en Pontevedra. Basta con llegar al nivel de credibilidad del top (10–15 reseñas, 4,5★ o más). Un ritmo constante de 1–2 reseñas reales al mes ya supera a todos los competidores, y sirve sobre todo para convertir más que para posicionar.

### 5. [LOW · easy] Profundidad de la ficha y web: sin efecto medible entre los líderes
Dentro de los 11 perfilados y las 8 webs, nada correlaciona de forma significativa con la visibilidad:

| Señal | Correlación con puntos en top 3 |
|---|:-:|
| Categorías secundarias | 0,28 |
| Atributos | −0,12 |
| Ritmo de reseñas | 0,02 |
| % de respuesta del propietario | 0,0 |
| Palabras en la portada | 0,2 |
| Completitud del schema | 0,3 |

Con estas muestras tan pequeñas no se puede afirmar que no influyan, solo que no son lo que distingue a estos ganadores.

→ Son higiene básica y ayudan a convertir una vez visible: horario, atributos, responder reseñas y web enlazada. Hay dos tendencias sin significación: el grupo A tiene más web propia (75 % frente a 51 %) y menos fichas sin reclamar (8 % frente a 27 %).

## Oportunidad fuera del Local Pack

### 6. [HIGH · easy] El orgánico está libre de carpinterías
**Ninguna web del grupo A aparece en el top 10 orgánico** de "carpintería" en ninguna de las 5 ciudades. Esas posiciones las ocupan directorios: Páginas Amarillas, Habitissimo, QDQ, Cronoshare, ProntoPro y Taskia.

Además, las webs de los líderes están poco trabajadas:

| Señal on-page | Webs que la tienen (de 8) |
|---|:-:|
| Schema LocalBusiness | 1 |
| Schema Service | 0 |
| Ciudad en el title | 2 |
| Mapa embebido | 1 |

Solo Carpimoble tiene arquitectura de servicio × ciudad (`/armarios-pontevedra`, `/muebles-a-medida-pontevedra`…).

→ Es la vía para captar el volumen de Pontevedra y Santiago (796 y 1.312 búsquedas al mes en tu KW research) más allá del radio de unos 3 km que cubre una ficha:
- Una web con páginas de servicio × zona.
- Schema LocalBusiness, Service y FAQPage.
- Contacto visible arriba.

Esta hipótesis no sale del test A/B: es una oportunidad que se ve en los datos. Es la que alimenta `web-blueprint-generator`.

## Calidad y límites

- **Muestras:** grupo A de 12 y grupo B de 88 en la capa de ficha básica (cumple el mínimo de 5 de la skill). Las capas de perfil (11) y web (8) son exploratorias.
- **Alcance:** una sola keyword ("carpintería"), un solo grid (Pontevedra) y un solo día. Correlación no es causalidad.
- **Exclusiones:** quedan fuera las 2 paradas de autobús que aparecen en Maps. Las señales con p > 0,1 se marcan como no significativas. Ninguna señal tiene cobertura inferior al 50 %.
- **Cómo validarlo:** repetir el grid con otras keywords del KW research ("cocinas a medida", "muebles a medida", "armarios a medida"…) para ver si los patrones 1–3 se mantienen por línea de servicio.
