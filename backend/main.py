"""
backend/main.py
Punto de entrada del backend F1 Manager.
Arranca el servidor ZeroMQ y el loop principal de simulación.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import zmq
from dotenv import load_dotenv

from backend.games.f1_manager.domain.entities import (
    EngineMode,
    RaceConfig,
    TyreCompound,
)
from backend.games.f1_manager.persistence.repository import F1Repository
from backend.games.f1_manager.simulation.race_simulator import RaceSimulator

load_dotenv()

DB_URL      = os.getenv("DB_URL",      "sqlite:///data/game.db")
PUB_PORT    = int(os.getenv("PUB_PORT", "5556"))   # backend → Godot
REP_PORT    = int(os.getenv("REP_PORT", "5557"))   # Godot → backend


def snapshot_to_dict(snapshot) -> dict:
    """Serializa un LapSnapshot a dict JSON-serializable."""
    return {
        "type"       : "race_tick",
        "lap"        : snapshot.lap,
        "total_laps" : snapshot.total_laps,
        "safety_car" : snapshot.safety_car,
        "weather"    : {
            "condition": snapshot.weather.condition.value,
            "intensity": snapshot.weather.intensity,
            "track_temp_c": snapshot.weather.track_temp_c,
        },
        "cars": [
            {
                "driver_id"     : c.driver_id,
                "team_id"       : c.team_id,
                "position"      : c.position,
                "lap_time_s"    : round(c.current_lap_time_s, 3),
                "total_time_s"  : round(c.total_time_s, 3),
                "best_lap_s"    : round(c.best_lap_s, 3) if c.best_lap_s < float("inf") else None,
                "gap_to_leader" : round(c.gap_to_leader_s, 3),
                "tyre": {
                    "compound": c.tyre.compound.value,
                    "age_laps": c.tyre.age_laps,
                    "wear_fl" : round(c.tyre.wear_fl, 3),
                    "wear_fr" : round(c.tyre.wear_fr, 3),
                    "wear_rl" : round(c.tyre.wear_rl, 3),
                    "wear_rr" : round(c.tyre.wear_rr, 3),
                    "avg_wear": round(c.tyre.avg_wear, 3),
                },
                "fuel_kg"       : round(c.fuel_kg, 2),
                "ers_charge"    : round(c.ers_charge, 3),
                "drs"           : c.drs_active,
                "engine_mode"   : c.engine_mode.value,
                "pit_stops"     : c.pit_stops,
                "dnf"           : c.dnf,
                "dnf_reason"    : c.dnf_reason,
            }
            for c in snapshot.cars
        ],
        "events": [
            {
                "event_type": e.event_type,
                "driver_id" : e.driver_id,
                "team_id"   : e.team_id,
                "detail"    : e.detail,
            }
            for e in snapshot.events
        ],
        "timestamp": int(time.time()),
    }


def handle_command(repo: F1Repository, msg: dict) -> dict:
    """Procesa un comando entrante desde Godot y retorna una respuesta."""
    cmd = msg.get("type", "")

    if cmd == "get_menu_state":
        team = repo.get_player_team()
        if not team:
            return {"error": "No player team found"}
        season = repo.get_active_season()
        next_race = repo.get_next_race(season.id) if season else None
        finance = repo.get_finance(team.id, season.id) if season else None
        return {
            "type": "menu_state",
            "team": {"id": team.id, "name": team.name},
            "season": {"year": season.year if season else 0},
            "championship": {},   # rellenar con consulta al campeonato
            "next_race": {
                "name": next_race.name if next_race else "—",
                "round": next_race.round_number if next_race else 0,
            },
            "budget": {
                "cap": finance.budget_cap_m if finance else 150.0,
                "spent": finance.spent_m if finance else 0.0,
            },
        }

    elif cmd == "set_engine_mode":
        # El jugador cambia el modo motor de su piloto durante la carrera
        # En producción actualiza el estado de simulación en curso
        return {"type": "ack", "cmd": cmd}

    elif cmd == "confirm_pitstop":
        return {"type": "ack", "cmd": cmd, "lap": msg.get("lap")}

    elif cmd == "make_driver_offer":
        driver_id = msg.get("driver_id")
        salary    = msg.get("salary_m", 0)
        return {"type": "offer_sent", "driver_id": driver_id, "salary_m": salary}

    return {"type": "error", "detail": f"Unknown command: {cmd}"}


def run_race(repo: F1Repository, race_id: int, pub_socket: zmq.Socket) -> None:
    """Ejecuta una carrera completa y publica cada vuelta."""
    import random
    season = repo.get_active_season()
    if not season:
        return

    teams   = repo.load_domain_teams()
    drivers = [d for t in teams for d in t.drivers]
    race_db = repo.get_race(race_id)
    if not race_db:
        return

    # Construir circuito de dominio desde la DB
    from backend.games.f1_manager.domain.entities import Circuit as DomCircuit
    circ_db = race_db.circuit
    circuit = DomCircuit(
        id=circ_db.id,
        name=circ_db.name,
        country=circ_db.country,
        total_laps=circ_db.total_laps,
        lap_distance_km=circ_db.lap_distance_km,
        tyre_wear_factor=circ_db.tyre_wear_factor,
        sc_probability=circ_db.sc_probability,
        rain_chance_pct=circ_db.rain_chance_pct,
        avg_temp_c=circ_db.avg_temp_c,
    )

    seed = random.randint(0, 999_999)
    config = RaceConfig(
        race_id=race_id,
        circuit=circuit,
        total_laps=circuit.total_laps,
        seed=seed,
        weather_seed=seed + 1,
    )

    sim = RaceSimulator(config, teams, drivers)
    for snapshot in sim.run():
        payload = json.dumps(snapshot_to_dict(snapshot))
        pub_socket.send_string(payload)
        time.sleep(0.5)   # velocidad de simulación — configurable

    # Guardar resultados
    results = sim.get_results()
    repo.save_race_results(race_id, results)


def main() -> None:
    Path("data").mkdir(exist_ok=True)
    repo = F1Repository(DB_URL)

    ctx = zmq.Context()

    # PUB socket — emite estado del juego hacia Godot
    pub = ctx.socket(zmq.PUB)
    pub.bind(f"tcp://*:{PUB_PORT}")

    # REP socket — recibe comandos desde Godot
    rep = ctx.socket(zmq.REP)
    rep.bind(f"tcp://*:{REP_PORT}")

    print(f"F1 Manager Backend iniciado")
    print(f"  PUB → tcp://*:{PUB_PORT}")
    print(f"  REP → tcp://*:{REP_PORT}")

    # Poller para no bloquear el REP mientras hay simulación
    poller = zmq.Poller()
    poller.register(rep, zmq.POLLIN)

    while True:
        socks = dict(poller.poll(timeout=100))
        if rep in socks:
            raw = rep.recv_string()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                rep.send_string(json.dumps({"error": "invalid json"}))
                continue

            if msg.get("type") == "start_race":
                rep.send_string(json.dumps({"type": "ack", "cmd": "start_race"}))
                run_race(repo, msg["race_id"], pub)
            else:
                response = handle_command(repo, msg)
                rep.send_string(json.dumps(response))


if __name__ == "__main__":
    main()
