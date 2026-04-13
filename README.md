# GP1 Manager

Proyecto de simulacion tipo F1 Manager sobre stack Python puro:
- Backend Python para dominio, simulacion y persistencia.
- Gestion/UI con PyWebView + HTML/CSS/JS.
- Visualizacion de carrera 2D con Arcade.

## Stack tecnico

- Python 3.12+
- PyWebView 5+
- Arcade 2.6+
- SQLAlchemy 2.x
- Alembic
- numpy
- python-dotenv

Dependencias declaradas en [pyproject.toml](pyproject.toml).

## Estructura relevante

- [main.py](main.py): punto de entrada unico de la app.
- [backend/core](backend/core): primitivas genericas reutilizables.
- [backend/games/f1_manager](backend/games/f1_manager): implementacion especifica de F1 Manager.
- [backend/games/f1_manager/api/js_api.py](backend/games/f1_manager/api/js_api.py): puente JS↔Python.
- [ui/screens/main_menu.html](ui/screens/main_menu.html): pantalla principal de gestion.
- [ui/screens/hud_carrera.html](ui/screens/hud_carrera.html): HUD de carrera prototipo.
- [arcade_view/race_window.py](arcade_view/race_window.py): adaptador de snapshots de carrera.
- [backend/db/models.py](backend/db/models.py): modelos SQLAlchemy.
- [tools/seed_db.py](tools/seed_db.py): seeder inicial.
- [tools/db_inspector.py](tools/db_inspector.py): inspeccion simple de SQLite.

## Como levantar el proyecto

1. Crear entorno e instalar dependencias.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

2. Crear y poblar base de datos.

```powershell
python tools/seed_db.py
```

3. Ejecutar migraciones (opcional en esta fase, recomendado para evolucion de esquema).

```powershell
alembic upgrade head
```

4. Arrancar aplicacion.

```powershell
python main.py
```

5. Ejecutar pruebas.

```powershell
pytest tests/ -v
```

## Nota de compatibilidad

Se mantiene [backend/main.py](backend/main.py) como wrapper temporal para redirigir al nuevo entrypoint.
