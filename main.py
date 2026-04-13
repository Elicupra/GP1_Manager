"""Punto de entrada único del juego F1 Manager."""
from __future__ import annotations

import logging
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import text

from backend.db.models import Circuit
from backend.games.f1_manager.api.js_api import F1ManagerAPI
from backend.games.f1_manager.domain.entities import Circuit as DomainCircuit
from backend.games.f1_manager.domain.entities import RaceConfig
from backend.games.f1_manager.persistence.repository import F1Repository
from backend.games.f1_manager.simulation.race_simulator import RaceSimulator

ROOT_DIR = Path(__file__).resolve().parent
SCREENS_DIR = ROOT_DIR / "ui" / "screens"
DATA_DIR = ROOT_DIR / "data"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("f1_manager")


class RaceLauncher:
    """Orquesta la transición entre la gestión PyWebView y la carrera Arcade."""

    def __init__(self, repo: F1Repository, window: Any) -> None:
        self._repo = repo
        self._window = window

    def launch(self, race_id: int) -> None:
        race = self._repo.get_race(race_id)
        if race is None:
            logger.error("Carrera %s no encontrada", race_id)
            return

        with self._repo.session() as session:
            circuit_row = session.get(Circuit, race.circuit_id)

        if circuit_row is None:
            logger.error("Circuito %s no encontrado", race.circuit_id)
            return

        teams = self._repo.load_domain_teams()
        drivers = [driver for team in teams for driver in team.drivers]
        player_team = self._repo.get_player_team()

        domain_circuit = DomainCircuit(
            id=circuit_row.id,
            name=circuit_row.name,
            country=circuit_row.country,
            total_laps=circuit_row.total_laps,
            lap_distance_km=circuit_row.lap_distance_km,
            overtaking_index=circuit_row.overtaking_index,
            tyre_wear_factor=circuit_row.tyre_wear_factor,
            brake_wear_factor=circuit_row.brake_wear_factor,
            downforce_sensitivity=circuit_row.downforce_sensitivity,
            sc_probability=circuit_row.sc_probability,
            rain_chance_pct=circuit_row.rain_chance_pct,
            avg_temp_c=circuit_row.avg_temp_c,
        )

        seed = int(time.time()) % 1_000_000
        config = RaceConfig(
            race_id=race_id,
            circuit=domain_circuit,
            total_laps=domain_circuit.total_laps,
            seed=seed,
            weather_seed=seed + 1,
        )

        data_queue: queue.Queue = queue.Queue(maxsize=200)
        simulator = RaceSimulator(config, teams, drivers)
        finished = threading.Event()
        results: list[dict[str, Any]] = []

        def run_simulation() -> None:
            try:
                tick_delay = float(os.getenv("SIM_TICK_DELAY", "0.2"))
                for snapshot in simulator.run():
                    try:
                        data_queue.put(snapshot, timeout=0.5)
                    except queue.Full:
                        pass
                    time.sleep(max(tick_delay, 0.01))
                results.extend(simulator.get_results())
            finally:
                finished.set()

        try:
            self._window.hide()
        except Exception:
            logger.exception("No se pudo ocultar PyWebView antes de arrancar Arcade")

        sim_thread = threading.Thread(target=run_simulation, daemon=True)
        sim_thread.start()

        try:
            from arcade_view.race_window import run_race_window

            run_race_window(
                data_queue=data_queue,
                race_name=race.name,
                total_laps=domain_circuit.total_laps,
                track_key=_circuit_to_track_key(circuit_row.name),
                player_team_id=player_team.id if player_team else 1,
            )
        except Exception:
            logger.exception("Fallo lanzando la ventana Arcade")
        finally:
            finished.wait(timeout=30)
            if results:
                self._repo.save_race_results(race_id, results)
            try:
                self._window.show()
                self._window.load_url((SCREENS_DIR / "dashboard.html").as_uri())
            except Exception:
                logger.exception("No se pudo restaurar PyWebView tras la carrera")


def _circuit_to_track_key(circuit_name: str) -> str:
    name = circuit_name.lower()
    if "montreal" in name or "montr" in name:
        return "montreal"
    return "generic"


def _db_url() -> str:
    return os.getenv("DB_URL", f"sqlite:///{DATA_DIR / 'game.db'}")


def _ensure_db(db_url: str) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    repo = F1Repository(db_url)
    with repo.session() as session:
        team_count = session.execute(text("SELECT COUNT(*) FROM teams")).scalar()
    if not team_count:
        logger.info("Base de datos vacia; ejecutando seed inicial")
        from tools.seed_db import seed

        seed(db_url)


def build_api() -> F1ManagerAPI:
    load_dotenv()
    db_url = _db_url()
    _ensure_db(db_url)
    repo = F1Repository(db_url)
    return F1ManagerAPI(repo=repo)


def main() -> None:
    load_dotenv()
    api = build_api()
    start_screen = os.getenv("START_SCREEN", "dashboard")
    start_path = (SCREENS_DIR / f"{start_screen}.html").resolve()
    if not start_path.exists():
        start_path = (SCREENS_DIR / "dashboard.html").resolve()

    try:
        import webview
    except ImportError:
        state = api.get_dashboard()
        print("PyWebView no instalado. Estado inicial del dashboard:")
        print(state)
        return

    window = webview.create_window(
        title="F1 Manager",
        url=start_path.as_uri(),
        js_api=api,
        width=int(os.getenv("WINDOW_W", "1440")),
        height=int(os.getenv("WINDOW_H", "900")),
        resizable=True,
        min_size=(1100, 680),
    )

    api.set_window(window)
    api.set_race_launcher(RaceLauncher(api._repo, window).launch)

    start_kwargs: dict[str, Any] = {
        "debug": os.getenv("DEBUG", "false").lower() == "true",
        "http_server": False,
    }
    if os.name == "nt":
        start_kwargs["gui"] = "edgechromium"

    logger.info("Abriendo PyWebView en %s", start_path.name)
    webview.start(**start_kwargs)


if __name__ == "__main__":
    main()
