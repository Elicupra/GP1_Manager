---
name: f1-manager-ui
description: >
  Genera pantallas UI/UX para el juego F1 Manager. Úsalo siempre que el usuario
  pida una pantalla, componente, prototipo o interfaz del juego — dashboard del
  equipo, HUD de carrera, mercado de pilotos, menú principal, garage, finanzas,
  estrategia, etc. Produce primero un prototipo HTML/React interactivo de alta
  calidad visual para validar el diseño, luego genera la traducción equivalente
  en GDScript + Godot Control nodes lista para pegar en el proyecto. Activa este
  skill ante cualquier mención de "pantalla", "UI", "interfaz", "HUD", "menú",
  "dashboard" o "diseño" en el contexto del proyecto F1 Manager.
---

# F1 Manager UI Skill

Genera interfaces para el juego F1 Manager en dos fases:
1. **Prototipo HTML/React** — para validar diseño visualmente en el navegador.
2. **Traducción Godot** — GDScript + escena `.tscn` equivalente para el proyecto real.

---

## Estética del Proyecto

**Dirección visual:** Industrial-luxe. Inspirado en los paneles de telemetría reales
de F1, los cockpits de monoplaza y los centros de operación de los grandes equipos.

**Paleta base:**
```
--bg-primary:    #0a0a0f   (negro carbono)
--bg-panel:      #111118   (panel oscuro)
--bg-card:       #1a1a24
--accent-red:    #e8001e   (rojo F1 / acento primario)
--accent-amber:  #f5a623   (alertas, neumáticos blandos)
--accent-green:  #00d45e   (positivo, neumáticos medios)
--accent-blue:   #0099ff   (lluvia, info)
--text-primary:  #f0f0f5
--text-muted:    #6b6b80
--border:        #2a2a38
--glow-red:      rgba(232,0,30,0.15)
```

**Tipografía:**
- Display / títulos: `Bebas Neue` o `Barlow Condensed` (bold)
- Datos / telemetría: `JetBrains Mono` o `Roboto Mono`
- Cuerpo / UI: `Barlow` (regular / medium)

**Principios de composición:**
- Datos densos pero legibles — el usuario necesita procesar mucho en poco tiempo.
- Líneas finas, bordes sutiles, sin sombras blandas — todo debe parecer hardware real.
- Los números cambian con animación de conteo (nunca saltan bruscamente).
- Código de color consistente: rojo = crítico/alerta, ámbar = atención, verde = OK, azul = info.
- Iconografía geométrica y limpia. Sin emojis.

---

## Proceso de Generación

### Paso 1 — Entender la pantalla

Identifica qué tipo de pantalla es y qué datos necesita mostrar:

| Pantalla | Datos clave |
|---|---|
| Dashboard equipo | Posición campeonato, presupuesto, próxima carrera, estado pilotos/coche |
| HUD carrera | Posiciones, gaps, neumático, combustible, vuelta actual, clima, DRS |
| Mercado pilotos | Lista de pilotos, stats, salario, disponibilidad, filtros |
| Garage / coche | Componentes, fiabilidad, tokens de desarrollo, homologación |
| Finanzas | Presupuesto anual, ingresos, gastos, cap proyección |
| Estrategia carrera | Stint plan, ventana de parada, delta de neumáticos |
| Menú principal | Navegación, estado temporada, notificaciones |

### Paso 2 — Prototipo HTML

Genera un archivo HTML autocontenido (sin dependencias externas salvo Google Fonts
y opcionalmente Chart.js desde CDN) con:

- Datos de muestra **realistas** (nombres, números, estados verosímiles de F1).
- Animaciones CSS para entradas de pantalla y actualizaciones de datos.
- Interactividad básica donde aplique (tabs, hover states, toggles).
- Responsive mínimo: diseñado para 1920×1080, legible en 1280×720.
- Comentarios en el HTML indicando qué datos vienen del backend Python vía ZeroMQ.

**Estructura del archivo HTML:**
```html
<!-- F1 Manager — [Nombre Pantalla] -->
<!-- Datos marcados con: <!-- ZMQ: campo_json --> -->
```

### Paso 3 — Traducción Godot

Después de que el usuario valide el prototipo, genera:

1. **Escena `.tscn`** — jerarquía de Control nodes equivalente.
2. **Script `.gd`** — GDScript que:
   - Recibe mensajes ZeroMQ del backend Python.
   - Actualiza los nodos con los datos recibidos.
   - Implementa las animaciones equivalentes con Tween.
   - Sigue las convenciones del proyecto (ver AGENTS.md §10).

**Mapeo HTML → Godot:**
```
<div class="panel">     → PanelContainer
<span class="data">     → Label (con theme override)
<canvas> / chart        → TextureRect + datos desde Python
<button>                → Button (señal → ZeroMQ REQ)
flexbox layout          → HBoxContainer / VBoxContainer
grid layout             → GridContainer
```

---

## Datos de Muestra Estándar

Usa siempre estos datos ficticios para prototipos (evita marcas reales de F1):

```json
{
  "team": "Apex Racing",
  "drivers": [
    {"name": "K. Hartmann", "number": 44, "nationality": "DE"},
    {"name": "R. Vasquez", "number": 7,  "nationality": "MX"}
  ],
  "championship": {"position": 3, "points": 187, "gap_to_leader": 42},
  "budget": {"total": 145000000, "spent": 98000000, "cap": 150000000},
  "next_race": {"name": "Grand Prix de Montréal", "circuit": "Circuit Gilles Villeneuve", "days_until": 12},
  "car": {
    "engine": {"rating": 87, "reliability": 0.94},
    "chassis": {"rating": 91, "reliability": 0.97},
    "aero": {"rating": 84, "reliability": 0.99}
  }
}
```

---

## Convenciones de Código

**HTML/CSS:**
- Variables CSS en `:root` para toda la paleta.
- Clases semánticas: `.panel`, `.data-value`, `.data-label`, `.alert`, `.status-ok/warn/critical`.
- Sin frameworks CSS (no Bootstrap, no Tailwind) — CSS puro para portabilidad.

**GDScript:**
- Nombres de nodos: `PascalCase`.
- Variables y señales: `snake_case`.
- Separar lógica de datos (`_on_zmq_message`) de lógica de render (`_update_display`).
- Comentario encima de cada función pública con descripción de una línea.

---

## Checklist de Calidad

Antes de entregar cualquier pantalla, verificar:

- [ ] Datos de muestra son realistas y completos (sin "Lorem ipsum" ni "N/A").
- [ ] Código de colores es consistente con la paleta del proyecto.
- [ ] Los números críticos (presupuesto, puntos, gaps) tienen unidades visibles.
- [ ] Hay al menos una animación de entrada.
- [ ] El archivo HTML funciona solo, sin servidor.
- [ ] Los comentarios `<!-- ZMQ: -->` marcan todos los campos dinámicos.
- [ ] La traducción Godot mantiene la misma jerarquía visual.
