# TODO - GP1 Manager

## Prioridad alta (migracion v2)

- [x] Reemplazar AGENTS.md con especificacion v2 (PyWebView + Arcade).
- [x] Crear `main.py` en raiz como entrypoint unico.
- [x] Crear estructura base:
  - `backend/core/*`
  - `backend/games/f1_manager/api/*`
  - `ui/*`
  - `arcade_view/*`
  - `alembic/*`
- [x] Completar pantallas de gestion:
  - `dashboard.html` ✅
  - `garage.html` ✅
  - `market.html` ✅
  - `finances.html` ✅
  - `strategy.html` ✅
- [x] Integrar visualización de carrera en HTML (reemplazando Arcade).
- [x] Conectar `start_race` para flujo gestion -> carrera -> gestion.
- [x] Corregir crash al iniciar GP (Arcade threading → HTML Canvas).
- [x] Corregir guardado de `driver_results` (grid_position NOT NULL).
- [x] Agregar controles de velocidad de reproducción (÷4, ÷2, Normal, ×2, ×4, Pausa).
- [x] Usar imagen del circuito (canada.png) como fondo de carrera.
- [x] Establecer tiempo de vuelta realista: 1:17.300 (77.3 segundos).
- [ ] Flujo pre-race obligatorio antes de iniciar carrera (sin forecast).
  - Pantalla dedicada de estrategia previa por coche.
  - Mostrar solo condiciones actuales de pista y meteorologia en el momento.
  - Confirmacion de estrategia y countdown de 10 segundos.
  - Inicio automatico de carrera tras countdown.
- [ ] Estrategia por coche antes de salida.
  - Neumatico de salida y secuencia de paradas.
  - Combustible inicial.
  - Modo motor y actitud de salida.
- [ ] Robustecer inicio de carrera y pasar pruebas.
  - Mantener `start_race` estable en PyWebView.
  - Validar con pytest que no hay regresiones de simulador.

## Prioridad media (backend)

- [ ] Corregir carga de carrera y circuito para evitar DetachedInstanceError.
  - Archivo: [backend/games/f1_manager/persistence/repository.py](backend/games/f1_manager/persistence/repository.py)
- [ ] Corregir estado `in_pit` para que no quede permanente tras una parada.
  - Archivo: [backend/games/f1_manager/simulation/race_simulator.py](backend/games/f1_manager/simulation/race_simulator.py)
- [ ] Evitar asignar puntos a coches DNF en resultados finales.
  - Archivo: [backend/games/f1_manager/simulation/race_simulator.py](backend/games/f1_manager/simulation/race_simulator.py)

## Entorno y tooling

- [ ] Instalar dependencias Python dev (`pip install -e ".[dev]"`).
- [ ] Ejecutar migraciones con Alembic (`alembic upgrade head`).
- [ ] Ejecutar tests con pytest y guardar baseline.

## Backend y pruebas

- [ ] Agregar tests para los 3 bugs detectados del simulador/repositorio.
- [ ] Agregar tests de integracion para [backend/games/f1_manager/api/js_api.py](backend/games/f1_manager/api/js_api.py).
- [ ] Validar contrato de datos UI para PyWebView.

## TODO - Consideraciones nuevas de carrera

- [ ] Modelo de vuelta por recorrido real del circuito 2D.
  - Implementar progreso de vuelta basado en distancia acumulada sobre el trazado 2D (spline o path de la imagen del circuito).
  - Definir que una vuelta se completa al cerrar el recorrido completo del trazado, no por tick.
  - Separar tick de simulacion y avance espacial para evitar equivalencia 1 tick = 1 vuelta.
  - Añadir pruebas para validar conversion distancia -> progreso -> vuelta completada.

- [ ] Modo boxes interactivo para estrategia y gestion en carrera.
  - Crear panel de boxes con estado de coche y piloto (neumaticos, combustible, desgaste, danos, ritmo).
  - Mostrar telemetria minima de carrera: gaps, tiempos por vuelta, mejor vuelta, posicion en pista y delta con rivales.
  - Permitir decisiones del jugador en tiempo real (parada, compuesto, ajustes de ritmo/energia, ordenes de equipo).
  - Modelar decisiones de CPU en paralelo y su impacto en posiciones, undercut/overcut, trafico y resultado final.
  - Persistir eventos de estrategia (pit in/out, stint, ordenes) para analisis posterior.

- [ ] Flujo de fin de carrera estable + persistencia de resultados.
  - Corregir cierre inesperado al finalizar carrera para volver siempre a pantalla de gestion.
  - Asegurar guardado atomico de resultados finales antes del retorno a UI de gestion.
  - Mostrar resumen post-carrera (clasificacion, puntos, vuelta rapida, incidentes, estrategia) y confirmar guardado.
  - Añadir test de integracion para validar ciclo completo: iniciar GP -> finalizar -> volver a gestion sin cerrar app.

- [ ] Vistas de modo carrera durante simulacion.
  - Vista Mix (mapa + estrategia).
  - Vista Mapa.
  - Vista Estrategia.
  - Controles de tiempo compartidos entre vistas.

- [ ] Ordenes en carrera por piloto con seleccion multiple.
  - Seleccion individual por coche.
  - Seleccion multiple para aplicar la misma orden a ambos.
