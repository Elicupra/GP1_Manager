# AGENTS.md — F1 Manager (Framework Tycoon)

> Guía maestra para agentes de IA que trabajen en este proyecto.
> **v2 — Stack 2D puro Python. Godot eliminado.**

---

## 1. Visión del Proyecto

**Juego principal:** F1 Manager — simulación de gestión de equipo de Fórmula 1.
**Modelo:** framework tycoon reutilizable; F1 Manager es la primera implementación.

---

## 2. Stack Tecnológico

| Capa | Tecnología | Justificación |
|---|---|---|
| Lógica / simulación | **Python 3.12+** | Ecosistema científico, rapidez de iteración |
| Carrera 2D | **Python Arcade 2.6+** | 2D nativo Python, sprites, sin dependencias externas |
| Menús / gestión | **PyWebView 5+** con HTML/CSS/JS | Ventana nativa con HTML; sin Electron ni servidor web |
| Reactividad JS | **Alpine.js** (local) | Ligero, sin build step, `x-data`/`x-bind`/`x-on` |
| Gráficos JS | **Chart.js** (local) | Línea, barras, donut — importado desde `ui/assets/js/` |
| Comunicación UI↔Python | **pywebview JS API bridge** | Llamadas directas sin sockets |
| Comunicación Arcade↔Core | **`queue.Queue`** Python | Todo en el mismo proceso, sin overhead de red |
| Base de datos | **SQLite** | Sin servidor, fichero único, abierto con DB Browser |
| ORM / migraciones | **SQLAlchemy 2 + Alembic** | Esquema versionado |
| Tests | **pytest** | Estándar Python |
| Empaquetado | **PyInstaller** | Binario único Windows/Linux |

### Por qué Arcade sobre Pygame
API moderna orientada a objetos, sprites/cámara/tilemaps nativos, mantenido activamente.

### Por qué PyWebView sobre Electron
Sin Node.js ni npm. Bridge directo Python↔JS. Distribuible con PyInstaller.

---

## 3. Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    PROCESO PYTHON                        │
│                                                          │
│  ┌──────────────┐   queue.Queue   ┌──────────────────┐  │
│  │  core/       │ ◄─────────────► │  Arcade 2D       │  │
│  │  simulation  │                 │  (vista carrera)  │  │
│  │  economy/ai  │                 └──────────────────┘  │
│  └──────┬───────┘                                        │
│         │ JS API bridge                                  │
│  ┌──────▼───────────────────────────────────────────┐   │
│  │  PyWebView — HTML/CSS/JS                          │   │
│  │  (menús, dashboard, garage, mercado, finanzas)    │   │
│  └──────┬────────────────────────────────────────────┘   │
│         │                                                 │
│  ┌──────▼──────────┐                                     │
│  │  SQLite (DB)    │                                     │
│  └─────────────────┘                                     │
└─────────────────────────────────────────────────────────┘
```

**Reglas estrictas:**
- Todo el estado vive en Python. JS solo muestra datos.
- Arcade solo para la carrera 2D. Menús siempre en PyWebView.
- JS nunca modifica estado — llama métodos de la API Python.
- DB solo accesible desde repositorios Python.

---

## 4. Modos de Ventana

### Modo Gestión (PyWebView)
Activo en: menú, dashboard, garage, mercado, finanzas, estrategia.

### Modo Carrera (Arcade 2D)
Activo durante la simulación. Vista top-down del circuito con sprites de coches.
Al terminar, vuelve a PyWebView.

```python
# Transición gestión → carrera
webview_window.hide()
run_arcade_race(race_config, result_queue)
webview_window.show()
```

---

## 5. Estructura de Directorios

```
project-root/
├── AGENTS.md
├── pyproject.toml
├── .env
├── main.py                          # Punto de entrada único
├── alembic/versions/
├── backend/
│   ├── core/
│   │   ├── simulation/              # Motor tick genérico
│   │   ├── economy/
│   │   ├── ai/
│   │   └── events/
│   ├── games/f1_manager/
│   │   ├── domain/                  # Entidades F1
│   │   ├── simulation/              # Simulador carrera
│   │   ├── economy/                 # Budget cap, sponsors
│   │   ├── ai/                      # IA rivales, mercado, clima
│   │   ├── persistence/             # Repositorios SQLAlchemy
│   │   └── api/js_api.py            # Bridge JS↔Python
│   └── db/models.py
├── ui/
│   ├── assets/
│   │   ├── css/main.css
│   │   ├── js/
│   │   │   ├── alpine.min.js        # Sin CDN en producción
│   │   │   └── chart.min.js
│   │   └── fonts/                   # Bebas Neue, Barlow, JetBrains Mono
│   └── screens/
│       ├── main_menu.html
│       ├── dashboard.html
│       ├── garage.html
│       ├── market.html
│       ├── finances.html
│       └── strategy.html
├── arcade_view/
│   ├── race_window.py               # Ventana Arcade principal
│   ├── sprites/
│   │   ├── car_sprite.py
│   │   └── track_sprite.py
│   └── assets/
│       ├── cars/                    # PNG top-down CC0
│       └── tracks/                  # Mapas de circuito PNG
├── data/game.db
├── tests/
│   ├── core/
│   └── f1_manager/
└── tools/
    ├── seed_db.py
    └── db_inspector.py
```

---

## 6. PyWebView JS API Bridge

```python
# backend/games/f1_manager/api/js_api.py
class F1ManagerAPI:
    def get_menu_state(self) -> dict: ...
    def get_dashboard(self) -> dict: ...
    def get_driver_market(self) -> dict: ...
    def make_driver_offer(self, driver_id: int, salary_m: float) -> dict: ...
    def get_garage(self) -> dict: ...
    def apply_upgrade(self, component: str, upgrade_id: str) -> dict: ...
    def get_finances(self) -> dict: ...
    def get_strategy(self, race_id: int) -> dict: ...
    def set_strategy(self, race_id: int, strategy: dict) -> dict: ...
    def start_race(self, race_id: int) -> dict: ...
    def navigate(self, screen: str) -> None: ...
```

```javascript
// Desde cualquier pantalla HTML (Alpine.js):
const data = await window.pywebview.api.get_dashboard();
this.budget   = data.budget;
this.position = data.championship.position;
```

---

## 7. Arcade 2D — Vista de Carrera

- Vista **top-down** del circuito (mapa estático 2D).
- Coches como sprites coloreados por equipo recorriendo el trazado.
- No es conducción — es visualización de la simulación Python.
- HUD dibujado con primitivas Arcade (`arcade.draw_text`), no con HTML.
- El simulador corre en hilo separado → snapshots en `queue.Queue` → Arcade los consume cada frame.

```python
class RaceWindow(arcade.Window):
    def on_update(self, delta_time):
        while not self.data_queue.empty():
            snapshot = self.data_queue.get_nowait()
            self._apply_snapshot(snapshot)   # mueve sprites
```

**Assets de carrera:**
- Circuitos: PNG top-down dibujados con Inkscape o assets CC0.
- Coches: rectángulos coloreados como punto de partida → PNG cuando estén disponibles.

---

## 8. Dominio, Simulación, IA y BD

Sin cambios respecto a v1. El backend Python generado anteriormente
(entidades, simulador, repositorio, seed_db) es válido tal cual.
Solo cambia el canal de salida: `queue.Queue` en lugar de ZeroMQ.

---

## 9. Convenciones Python

- PEP 8 + Black + Ruff. Type hints en funciones públicas.
- Docstrings Google style. Tests pytest sin DB real.
- Imports absolutos. `.env` para configuración.

## 10. Convenciones UI (HTML/JS)

- Alpine.js para reactividad. Chart.js para gráficos.
- CSS variables para paleta (definida en SKILL de UI).
- Sin frameworks CSS. CSS puro.
- JS nunca modifica estado — siempre via `pywebview.api`.
- Cada pantalla: HTML autocontenido con rutas relativas a `ui/assets/`.

## 11. Convenciones Arcade

- Un fichero por vista. Sprites en clases separadas.
- HUD en `on_draw()` con primitivas Arcade.
- Arcade no importa de `backend/` — recibe datos via `queue.Queue`.

---

## 12. Flujo de Desarrollo

1. Entidad → `domain/`
2. Modelo DB → `db/models.py` + Alembic
3. Repositorio → `persistence/`
4. Lógica → `simulation/` o `economy/`
5. Tests → `tests/`
6. API Python → `api/js_api.py`
7. Pantalla HTML → `ui/screens/`
8. Arcade (solo carrera) → `arcade_view/`

---

## 13. Entorno de Desarrollo

```bash
pip install -e ".[dev]"
python tools/seed_db.py
python main.py
pytest tests/ -v
pyinstaller main.spec   # empaquetar
```

---

## 14. Dependencias

```toml
dependencies = [
    "pywebview>=5.0",
    "arcade>=2.6",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "numpy>=1.26",
    "python-dotenv>=1.0",
]
```

---

## 15. Licencias

| Componente | Licencia |
|---|---|
| Python Arcade | MIT |
| PyWebView | BSD |
| Alpine.js | MIT |
| Chart.js | MIT |
| SQLAlchemy / Alembic | MIT |
| PyInstaller | GPL + bootloader exception |
| DB Browser for SQLite | MPL 2.0 |

---

## 16. Lo que NO cambia (válido de v1)

- Todo el backend Python: dominio, simulación, repositorios, modelos DB.
- Los 16 tests del simulador — siguen pasando sin modificación.
- `tools/seed_db.py` y `tools/db_inspector.py`.
- La lógica de IA y el modelo económico.

*v2 — Godot eliminado. Stack: PyWebView + Arcade 2D + Python puro.*
