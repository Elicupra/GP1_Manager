---
name: f1-manager-ui
description: >
  Genera pantallas UI/UX para el juego F1 Manager. Úsalo siempre que el usuario
  pida una pantalla, componente, prototipo o interfaz del juego — dashboard del
  equipo, HUD de carrera, mercado de pilotos, menú principal, garage, finanzas,
  estrategia, etc. Produce HTML+CSS+Alpine.js listo para usar en PyWebView
  (aplicación de escritorio Windows/Linux). Activa este skill ante cualquier
  mención de "pantalla", "UI", "interfaz", "HUD", "menú", "dashboard" o
  "diseño" en el contexto del proyecto F1 Manager.
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

# F1 Manager UI Skill — v2 (PyWebView + Alpine.js)

Las pantallas son archivos HTML que se muestran en una ventana nativa de escritorio
via **PyWebView**. No hay servidor web, no hay Electron, no hay React.

**Stack de UI:**
- HTML + CSS puro (sin frameworks)
- **Alpine.js** para reactividad (`x-data`, `x-bind`, `x-on`, `x-show`, `x-for`)
- **Chart.js** para gráficos (importado desde `ui/assets/js/chart.min.js`)
- **`window.pywebview.api`** para comunicarse con el backend Python

---

## Estética del Proyecto

**Dirección visual:** Industrial-luxe. Paneles de telemetría F1, cockpits, centros de operación.

**Paleta base:**
```css
--bg-primary:  #0a0a0f
--bg-panel:    #111118
--bg-card:     #1a1a24
--accent-red:  #e8001e
--accent-amber:#f5a623
--accent-green:#00d45e
--accent-blue: #0099ff
--text-primary:#f0f0f5
--text-muted:  #6b6b80
--border:      #2a2a38
--glow-red:    rgba(232,0,30,0.12)
```

**Tipografía:** Bebas Neue (títulos) · Barlow Condensed (UI) · Barlow (cuerpo) · JetBrains Mono (datos)

**Principios:** Datos densos legibles · Líneas finas · Rojo=crítico, Ámbar=atención, Verde=OK, Azul=info · Sin emojis

---

## Proceso de Generación

### Paso 1 — Pantalla y datos

| Pantalla | API Python |
|---|---|
| Menú principal | `get_menu_state()` |
| Dashboard | `get_dashboard()` |
| Garage | `get_garage()` |
| Mercado pilotos | `get_driver_market()` |
| Finanzas | `get_finances()` |
| Estrategia | `get_strategy(race_id)` |

### Paso 2 — HTML de producción (PyWebView-ready)

El archivo va directamente a `ui/screens/`. Es el archivo final, no un prototipo.

**Estructura obligatoria:**
```html
<!-- F1 Manager — [Nombre Pantalla] -->
<!-- ui/screens/nombre.html -->
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>F1 Manager — [Nombre]</title>
  <script src="../assets/js/alpine.min.js" defer></script>
  <!-- <script src="../assets/js/chart.min.js"></script> solo si hay gráficos -->
  <style>
    :root { /* variables de paleta */ }
    /* CSS puro. Sin frameworks. */
  </style>
</head>
<body>
  <div x-data="screen()" x-init="init()">
    <div x-show="loading" class="loading-overlay">CARGANDO...</div>
    <div x-show="!loading">
      <!-- contenido -->
    </div>
  </div>

  <script>
    function screen() {
      return {
        loading: true,
        data: {},

        async init() {
          this.data = await window.pywebview.api.get_XXX();
          this.loading = false;
        },

        async navigate(s) {
          await window.pywebview.api.navigate(s);
        }
      }
    }

    // Mock para desarrollo en navegador sin PyWebView
    if (!window.pywebview) {
      window.pywebview = { api: {
        get_XXX: async () => MOCK_DATA,
        navigate: async (s) => console.log('navigate:', s),
      }};
    }
  </script>
</body>
</html>
```

### Paso 3 — Patrones Alpine.js

```html
<!-- Texto reactivo -->
<span x-text="data.championship?.position + 'º'"></span>

<!-- Lista dinámica -->
<template x-for="driver in data.drivers" :key="driver.id">
  <div x-text="driver.name"></div>
</template>

<!-- Condicional -->
<div x-show="data.budget?.spent_pct > 90">Presupuesto crítico</div>

<!-- Clase dinámica -->
<div :class="data.morale > 0.7 ? 'status-ok' : 'status-warn'"></div>

<!-- Acción del usuario -->
<button @click="await window.pywebview.api.make_driver_offer(driver.id, salary)">
  Enviar oferta
</button>
```

### Paso 4 — Reglas PyWebView

- `window.pywebview.api` se usa para **todo** — lecturas y escrituras.
- No usar `fetch()` para llamar al backend.
- No usar `localStorage`/`sessionStorage` — el estado vive en Python.
- Envolver init en `window.addEventListener('pywebviewready', ...)` si hay
  riesgo de que Alpine monte antes de que el bridge esté listo.
- Todos los métodos API retornan dict JSON. Nunca lanzan excepciones al JS —
  retornan `{"error": "..."}` en caso de fallo.

---

## Datos de Muestra Estándar (Mock)

```javascript
const MOCK_DATA = {
  team: { id: 1, name: "Apex Racing" },
  season: { year: 2026, race_current: 8, race_total: 24 },
  championship: { position: 3, points: 187, gap_to_leader: 42 },
  budget: { cap: 150.0, spent: 100.5, available: 49.5, spent_pct: 67, projected_eoy: 143.2 },
  next_race: { id: 9, name: "Grand Prix de Montréal", circuit: "Circuit Gilles Villeneuve",
               round: 9, days_until: 12, weather_forecast: "LLUVIA LIGERA · Dom 40%" },
  drivers: [
    { id: 1, name: "K. Hartmann", number: 44, nationality: "DE",
      championship_pos: 3, points: 124, contract_status: "active",
      contract_end_year: 2028, morale: 0.85, form: ["W","W","P","P","R"] },
    { id: 2, name: "R. Vasquez", number: 7, nationality: "MX",
      championship_pos: 8, points: 63, contract_status: "expiring",
      contract_end_year: 2026, morale: 0.55, form: ["N","P","P","R","N"] }
  ],
  car: {
    overall_rating: 87.8, avg_reliability: 0.96,
    dev_tokens_used: 6, dev_tokens_total: 8,
    components: {
      engine:     { rating: 87, reliability: 0.94 },
      chassis:    { rating: 91, reliability: 0.97 },
      aero:       { rating: 84, reliability: 0.99 },
      suspension: { rating: 86, reliability: 0.99 },
      ers:        { rating: 89, reliability: 0.96 },
      gearbox:    { rating: 88, reliability: 0.98 }
    }
  },
  notifications: [
    { title: "Contrato R. Vasquez", body: "Expira al final de temporada.",
      time_label: "HOY", color: "#f5a623" },
    { title: "Actualización de motor", body: "Disponible desde GP 10. Coste 8.2M.",
      time_label: "2D",  color: "#0099ff" },
    { title: "Aprobación FIA", body: "ERS Spec B homologado.",
      time_label: "3D",  color: "#00d45e" }
  ]
};
```

---

## Navegación entre Pantallas

```javascript
// Siempre via Python:
await window.pywebview.api.navigate('dashboard');
await window.pywebview.api.navigate('garage');
await window.pywebview.api.navigate('market');
await window.pywebview.api.navigate('finances');
await window.pywebview.api.navigate('strategy');
await window.pywebview.api.navigate('main_menu');
// Iniciar carrera (cierra PyWebView, abre Arcade 2D):
await window.pywebview.api.start_race(raceId);
```

Python ejecuta:
```python
window.load_url(f"file://{SCREENS_DIR}/{screen}.html")
```

---

## Actualización en Tiempo Real (polling ligero)

Solo para pantallas que lo necesitan:
```javascript
startPolling() {
  this.pollInterval = setInterval(async () => {
    this.data = await window.pywebview.api.get_live_state();
  }, 1000);
},
destroy() { clearInterval(this.pollInterval); }
```

---

## Checklist de Calidad

- [ ] `x-data="screen()"` + `x-init="init()"` en el nodo raíz
- [ ] `init()` llama a `window.pywebview.api.get_XXX()`
- [ ] Estado `loading` implementado con skeleton o mensaje
- [ ] Todas las acciones usan `pywebview.api`
- [ ] Navegación usa `pywebview.api.navigate()`
- [ ] Rutas de assets relativas: `../assets/js/alpine.min.js`
- [ ] Mock `window.pywebview` para desarrollo en navegador
- [ ] Paleta CSS de variables en todo el archivo
- [ ] Datos de muestra realistas en el mock
- [ ] Animación de entrada presente
- [ ] Sin CDN hardcodeado (solo rutas locales)
- [ ] Sin `localStorage`, sin `fetch()` al backend
