# GP1 Manager

Proyecto de simulacion tipo F1 Manager con arquitectura separada:
- Backend Python para logica de simulacion y persistencia.
- Frontend Godot para UI/escenas.
- Prototipos HTML para validar pantallas antes de pasarlas a Godot.

## Estado actual del proyecto

### Lo que ya existe
- Proyecto Godot minimo arrancable con escena principal: [project.godot](project.godot).
- Menu principal inicial en Godot:
  - Script: [main_menu.gd](main_menu.gd)
  - Escena: [main_menu.tscn](main_menu.tscn)
- Prototipos UI HTML:
  - [menu_principal.html](menu_principal.html)
  - [hud_carrera.html](hud_carrera.html)
- Backend Python base:
  - Entry point: [backend/main.py](backend/main.py)
  - Simulador: [backend/games/f1_manager/simulation/race_simulator.py](backend/games/f1_manager/simulation/race_simulator.py)
  - Repositorio DB: [backend/games/f1_manager/persistence/repository.py](backend/games/f1_manager/persistence/repository.py)
  - Modelos SQLAlchemy: [backend/db/models.py](backend/db/models.py)
- Seeder de base de datos: [tools/seed_db.py](tools/seed_db.py)
- Tests iniciales del simulador: [tests/f1_manager/test_race_simulator.py](tests/f1_manager/test_race_simulator.py)

### Estado de ejecucion local conocido
- Godot no esta detectado en PATH en esta maquina (comando godot4 falla).
- pytest no esta instalado en el entorno actual (comando pytest falla).

## Stack tecnico

- Python 3.12+
- SQLAlchemy 2.x
- Alembic
- pyzmq
- numpy
- python-dotenv
- Godot 4.x (GDScript)

Dependencias Python declaradas en [pyproject.toml](pyproject.toml).

## Estructura relevante

- backend/
  - main.py
  - db/
    - models.py
  - games/f1_manager/
    - domain/entities.py
    - simulation/race_simulator.py
    - persistence/repository.py
- tests/
  - f1_manager/test_race_simulator.py
- tools/
  - seed_db.py
- main_menu.gd
- main_menu.tscn
- menu_principal.html
- hud_carrera.html

## Como levantar el proyecto (estado actual)

### 1) Crear entorno Python e instalar dependencias

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2) Crear y poblar base de datos

```powershell
python tools/seed_db.py
```

### 3) Ejecutar backend

```powershell
python backend/main.py
```

Puertos por defecto:
- PUB: 5556
- REP: 5557

Se pueden cambiar con variables de entorno `PUB_PORT`, `REP_PORT`, `DB_URL`.

### 4) Ejecutar Godot

Opciones:
- Abrir Godot 4 y cargar esta carpeta.
- O por consola (si Godot esta en PATH):

```powershell
godot4 --path D:\GitHub\GP1_Manager
```

## Riesgos tecnicos abiertos detectados

1. Posible DetachedInstanceError al leer `race_db.circuit` fuera de sesion activa (repositorio/backend).
2. `in_pit` queda en `true` tras pit stop y no se resetea en vueltas siguientes.
3. Pilotos DNF pueden acabar recibiendo puntos en `get_results`.
4. Hay artefactos de estructura con nombres raros (carpetas/archivos con llaves) que conviene limpiar.

Ver plan de trabajo en [TODO.md](TODO.md).

## Notas

- Este README describe el estado real actual del repositorio, no una arquitectura futura ideal.
- Se recomienda limpiar archivos temporales `*.tmp` y artefactos de estructura antes de ampliar el backend.
