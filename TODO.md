# TODO - GP1 Manager

## Prioridad alta (bloqueantes y consistencia)

- [ ] Corregir carga de carrera y circuito para evitar DetachedInstanceError.
  - Archivo: [backend/games/f1_manager/persistence/repository.py](backend/games/f1_manager/persistence/repository.py)
  - Archivo: [backend/main.py](backend/main.py)
- [ ] Corregir estado `in_pit` para que no quede permanente tras una parada.
  - Archivo: [backend/games/f1_manager/simulation/race_simulator.py](backend/games/f1_manager/simulation/race_simulator.py)
- [ ] Evitar asignar puntos a coches DNF en resultados finales.
  - Archivo: [backend/games/f1_manager/simulation/race_simulator.py](backend/games/f1_manager/simulation/race_simulator.py)

## Prioridad media (calidad de proyecto)

- [ ] Limpiar artefactos de carpetas/archivos con llaves en nombres dentro de backend/tests.
- [ ] Limpiar archivos temporales `*.tmp` en la raiz del proyecto.
- [ ] Mover/organizar archivos no pertenecientes al backend dentro de `backend/db/` (por ejemplo `main_menu.tscn`, `formula_car.zip`) si aplica.

## Entorno y tooling

- [ ] Instalar y configurar Godot 4 en PATH para ejecucion por terminal.
- [ ] Instalar dependencias Python dev (`pip install -e ".[dev]"`).
- [ ] Ejecutar tests con pytest y guardar resultado base.

## Backend y pruebas

- [ ] Agregar tests para los 3 bugs detectados del simulador/repositorio.
- [ ] Agregar tests de integracion minimos para `handle_command` en [backend/main.py](backend/main.py).
- [ ] Añadir validacion de schema de mensajes ZeroMQ (request/response).

## UI Godot

- [ ] Aplicar Theme y fuentes para acercar [main_menu.tscn](main_menu.tscn) al prototipo [menu_principal.html](menu_principal.html).
- [ ] Completar subpantallas (Calendario, Garage, Plantilla, Finanzas, Ajustes) en Godot.
- [ ] Integrar `ZmqBus` real y reemplazar modo mock cuando backend este operativo.
