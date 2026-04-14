"""Bridge JS <-> Python para PyWebView."""
from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from backend.db.models import CarComponent, Championship, Circuit, ComponentType, Sponsor, Team
from backend.games.f1_manager.persistence.repository import F1Repository

if TYPE_CHECKING:
    import webview

logger = logging.getLogger(__name__)

SCREENS_DIR = Path(__file__).resolve().parents[4] / "ui" / "screens"


class F1ManagerAPI:
    """API expuesta al frontend HTML via PyWebView."""

    def __init__(
        self,
        repo: F1Repository,
        window_ref: "webview.Window | None" = None,
        race_launcher: Callable[[int], None] | None = None,
    ) -> None:
        self._repo = repo
        self._window = window_ref
        self._race_launcher = race_launcher
        self._current_screen = "dashboard"
        self._saved_strategies: dict[int, dict[str, Any]] = {}
        self._demo_started_races: set[int] = set()
        self._last_race_results: dict[str, Any] | None = None

    def set_window(self, window: "webview.Window") -> None:
        self._window = window

    def set_race_launcher(self, race_launcher: Callable[[int], None]) -> None:
        self._race_launcher = race_launcher

    def set_last_race_results(self, payload: dict[str, Any]) -> None:
        self._last_race_results = payload

    def get_last_race_results(self) -> dict:
        if self._last_race_results is None:
            return {"error": "No hay resultados de carrera disponibles"}
        return self._last_race_results

    def navigate(self, screen: str) -> dict:
        allowed = {"dashboard", "garage", "market", "finances", "strategy", "pre_race", "main_menu"}
        if screen not in allowed:
            return {"error": f"Pantalla desconocida: {screen}"}
        try:
            screen_path = SCREENS_DIR / f"{screen}.html"
            if not screen_path.exists():
                return {"error": f"Pantalla no encontrada: {screen}"}
            self._current_screen = screen
            # Importante: no cambiar de URL desde aqui para no invalidar callbacks
            # JS de pywebview durante la respuesta de esta llamada.
            return {"ok": True, "screen": screen, "url": screen_path.as_uri()}
        except Exception as exc:
            logger.exception("navigate error")
            return {"error": str(exc)}

    def get_menu_state(self) -> dict:
        try:
            team = self._repo.get_player_team()
            season = self._repo.get_active_season()
            if team is None or season is None:
                return {"error": "No hay partida activa"}

            next_race = self._repo.get_next_race(season.id)
            finance = self._repo.get_finance(team.id, season.id)
            championship = self._repo.get_championship(team.id, season.id)
            standings = self._repo.get_all_championships(season.id)

            leader_points = float(standings[0].points) if standings else 0.0
            points = float(championship.points) if championship else 0.0

            return {
                "team": {
                    "id": team.id,
                    "name": team.name,
                    "morale": float(team.morale),
                    "pitstop_mean_s": float(team.pitstop_mean_s),
                },
                "season": {
                    "year": season.year,
                    "race_current": self._repo.count_completed_races(season.id),
                    "race_total": self._repo.count_total_races(season.id),
                },
                "championship": {
                    "position": int(championship.position) if championship else 0,
                    "points": int(points),
                    "gap_to_leader": max(int(leader_points - points), 0),
                },
                "next_race": _serialize_next_race(self._repo, next_race),
                "budget": _serialize_budget(finance),
                "save": {"last_saved": "auto"},
                "notifications": self._build_notifications(team.id, season.id),
                "screen": self._current_screen,
            }
        except Exception as exc:
            logger.exception("get_menu_state error")
            return {"error": str(exc)}

    def get_dashboard(self) -> dict:
        try:
            base = self.get_menu_state()
            if "error" in base:
                return base

            team_id = int(base["team"]["id"])
            season = self._repo.get_active_season()
            if season is None:
                return {"error": "No hay temporada activa"}

            standings = self._repo.get_all_championships(season.id)
            standings_payload = []
            leader_points = max((float(item.points) for item in standings), default=1.0)
            for item in standings:
                standing_team = self._repo.get_team(item.team_id)
                standings_payload.append(
                    {
                        "id": item.team_id,
                        "name": standing_team.name if standing_team else f"Team {item.team_id}",
                        "points": int(item.points),
                        "position": int(item.position),
                        "color": "#e8001e" if item.team_id == team_id else "#6b6b80",
                        "is_player": item.team_id == team_id,
                        "pct": round((float(item.points) / leader_points) * 100),
                    }
                )

            drivers = self._repo.get_drivers_by_team(team_id)
            driver_payload = []
            team_points = int(base["championship"]["points"])
            for index, driver in enumerate(drivers, start=1):
                driver_payload.append(
                    {
                        "id": driver.id,
                        "name": driver.name,
                        "number": driver.number,
                        "nationality": driver.nationality,
                        "championship_pos": index,
                        "points": max(team_points // 2 - (index - 1) * 12, 0),
                        "contract_status": driver.contract_status.value,
                        "contract_end_year": driver.contract_end_year,
                        "morale": round(float(driver.morale), 2),
                        "form": ["W", "P", "P", "N", "R"] if index == 1 else ["N", "P", "R", "N", "P"],
                    }
                )

            components = self._repo.get_car_components(team_id)
            component_payload = {
                component.component_type.value: {
                    "rating": round(float(component.rating), 1),
                    "reliability": round(float(component.reliability), 3),
                }
                for component in components
            }
            avg_reliability = (
                sum(float(component.reliability) for component in components) / len(components)
                if components else 0.95
            )
            overall_rating = (
                sum(float(component.rating) for component in components) / len(components)
                if components else 85.0
            )
            dev_tokens_used = max((component.dev_tokens_used for component in components), default=0)

            base["championship_standings"] = standings_payload
            base["drivers"] = driver_payload
            base["car"] = {
                "overall_rating": round(overall_rating, 1),
                "avg_reliability": round(avg_reliability, 3),
                "dev_tokens_used": int(dev_tokens_used),
                "dev_tokens_total": 8,
                "components": component_payload,
            }
            return base
        except Exception as exc:
            logger.exception("get_dashboard error")
            return {"error": str(exc)}

    def get_garage(self) -> dict:
        try:
            team = self._repo.get_player_team()
            if team is None:
                return {"error": "No hay equipo de jugador"}

            components = self._repo.get_car_components(team.id)
            return {
                "team_name": team.name,
                "components": {
                    component.component_type.value: {
                        "rating": round(float(component.rating), 1),
                        "reliability": round(float(component.reliability), 3),
                        "uses_current": component.uses_current,
                        "uses_max": component.uses_max,
                        "dev_tokens_used": component.dev_tokens_used,
                    }
                    for component in components
                },
                "dev_tokens": {
                    "used": max((component.dev_tokens_used for component in components), default=0),
                    "total": 8,
                },
                "upgrades_available": _default_upgrades(),
            }
        except Exception as exc:
            logger.exception("get_garage error")
            return {"error": str(exc)}

    def apply_upgrade(self, component: str, upgrade_id: str) -> dict:
        try:
            team = self._repo.get_player_team()
            if team is None:
                return {"error": "No hay equipo de jugador"}

            upgrade = next((item for item in _default_upgrades() if item["id"] == upgrade_id), None)
            if upgrade is None:
                return {"error": "Upgrade no encontrado"}

            ok = self._repo.apply_upgrade(
                team_id=team.id,
                component_type=ComponentType(component),
                rating_delta=float(upgrade["rating_delta"]),
                token_cost=int(upgrade["token_cost"]),
                cost_m=float(upgrade["cost_m"]),
            )
            if not ok:
                return {"error": "Sin recursos suficientes"}

            new_rating = next(
                (
                    round(float(item.rating), 1)
                    for item in self._repo.get_car_components(team.id)
                    if item.component_type.value == component
                ),
                None,
            )
            return {"ok": True, "new_rating": new_rating}
        except Exception as exc:
            logger.exception("apply_upgrade error")
            return {"error": str(exc)}

    def get_driver_market(self) -> dict:
        try:
            team = self._repo.get_player_team()
            season = self._repo.get_active_season()
            if team is None or season is None:
                return {"error": "No hay partida activa"}

            finance = self._repo.get_finance(team.id, season.id)
            drivers = self._repo.get_free_agents()
            return {
                "budget_available_m": round((finance.budget_cap_m - finance.spent_m) if finance else 0.0, 1),
                "drivers": [
                    {
                        "id": driver.id,
                        "name": driver.name,
                        "number": driver.number,
                        "nationality": driver.nationality,
                        "age": driver.age,
                        "team_name": "Libre",
                        "pace": driver.pace,
                        "consistency": driver.consistency,
                        "tyre_management": driver.tyre_management,
                        "wet_skill": driver.wet_skill,
                        "salary_m": round(float(driver.contract_salary_m), 1),
                        "contract_status": driver.contract_status.value,
                        "contract_end_year": driver.contract_end_year,
                        "morale": round(float(driver.morale), 2),
                        "is_current": False,
                    }
                    for driver in drivers
                ],
            }
        except Exception as exc:
            logger.exception("get_driver_market error")
            return {"error": str(exc)}

    def make_driver_offer(self, driver_id: int, salary_m: float) -> dict:
        try:
            team = self._repo.get_player_team()
            season = self._repo.get_active_season()
            driver = self._repo.get_driver(driver_id)
            if team is None or season is None or driver is None:
                return {"error": "Piloto o equipo no encontrado"}

            min_salary = float(driver.contract_salary_m) * 0.9
            accepted = float(salary_m) >= min_salary
            if accepted:
                self._repo.update_driver_contract(driver_id, team.id, float(salary_m), season.year + 2)
                return {"ok": True, "accepted": True, "message": f"{driver.name} acepta la oferta."}
            return {
                "ok": True,
                "accepted": False,
                "message": f"{driver.name} rechaza la oferta.",
                "min_salary_m": round(min_salary, 1),
            }
        except Exception as exc:
            logger.exception("make_driver_offer error")
            return {"error": str(exc)}

    def get_finances(self) -> dict:
        try:
            team = self._repo.get_player_team()
            season = self._repo.get_active_season()
            if team is None or season is None:
                return {"error": "No hay partida activa"}

            finance = self._repo.get_finance(team.id, season.id)
            if finance is None:
                return {"error": "Sin datos financieros"}

            sponsors = self._repo.get_sponsors(team.id)
            total_income = float(finance.fom_prize_m + finance.sponsor_income_m)
            total_expense = float(
                finance.driver_salaries_m
                + finance.staff_salaries_m
                + finance.development_m
                + finance.logistics_m
            )
            return {
                "season_year": season.year,
                "budget": _serialize_budget(finance),
                "income": {
                    "total": round(total_income, 1),
                    "fom_prize": round(float(finance.fom_prize_m), 1),
                    "sponsors": round(float(finance.sponsor_income_m), 1),
                    "performance_bonus": 0.0,
                },
                "expenses": {
                    "total": round(total_expense, 1),
                    "driver_salaries": round(float(finance.driver_salaries_m), 1),
                    "staff_salaries": round(float(finance.staff_salaries_m), 1),
                    "development": round(float(finance.development_m), 1),
                    "logistics": round(float(finance.logistics_m), 1),
                },
                "profit": round(total_income - total_expense, 1),
                "sponsors": [_serialize_sponsor(sponsor, season.year) for sponsor in sponsors],
                "monthly_history": [],
            }
        except Exception as exc:
            logger.exception("get_finances error")
            return {"error": str(exc)}

    def get_strategy(self, race_id: int) -> dict:
        try:
            team = self._repo.get_player_team()
            race = self._repo.get_race(race_id)
            if team is None or race is None:
                return {"error": "Carrera no encontrada"}

            with self._repo.session() as session:
                circuit = session.get(Circuit, race.circuit_id)

            if circuit is None:
                return {"error": "Circuito no encontrado"}

            return {
                "race": {
                    "id": race.id,
                    "name": race.name,
                    "round": race.round_number,
                    "total_laps": circuit.total_laps,
                },
                "circuit": {
                    "name": circuit.name,
                    "tyre_wear_factor": float(circuit.tyre_wear_factor),
                    "sc_probability": float(circuit.sc_probability),
                    "overtaking_index": float(circuit.overtaking_index),
                    "rain_chance_pct": float(circuit.rain_chance_pct),
                },
                "drivers": [
                    {
                        "id": driver.id,
                        "name": driver.name,
                        "number": driver.number,
                        "planned_stops": self._saved_strategies.get(race_id, {}).get(str(driver.id), []),
                    }
                    for driver in self._repo.get_drivers_by_team(team.id)
                ],
                "tyre_degradation": {
                    "soft": {"window_laps": [14, 18], "base_deg": 0.038},
                    "medium": {"window_laps": [22, 28], "base_deg": 0.022},
                    "hard": {"window_laps": [30, 38], "base_deg": 0.014},
                },
                "weather_forecast": [
                    {"laps": "1-20", "condition": "dry", "rain_pct": 0},
                    {"laps": "21-40", "condition": "light_cloud", "rain_pct": 10},
                    {"laps": "41-55", "condition": "light_rain", "rain_pct": 30},
                ],
                "strategy_alternatives": _build_strategy_alternatives(circuit.total_laps),
            }
        except Exception as exc:
            logger.exception("get_strategy error")
            return {"error": str(exc)}

    def get_pre_race_state(self, race_id: int) -> dict:
        try:
            team = self._repo.get_player_team()
            race = self._repo.get_race(race_id)
            if team is None or race is None:
                return {"error": "Carrera no encontrada"}

            with self._repo.session() as session:
                circuit = session.get(Circuit, race.circuit_id)

            if circuit is None:
                return {"error": "Circuito no encontrado"}

            now = datetime.now()
            marker = (now.minute * 31 + race.id * 7) % 100
            rain_chance = int(float(circuit.rain_chance_pct))
            if marker < int(rain_chance * 0.6):
                condition = "wet"
                rain_intensity = round(min(1.0, 0.55 + rain_chance / 200), 2)
                track_state = "wet"
            elif marker < rain_chance:
                condition = "intermediate"
                rain_intensity = round(min(1.0, 0.25 + rain_chance / 300), 2)
                track_state = "damp"
            else:
                condition = "dry"
                rain_intensity = 0.0
                track_state = "dry"

            temp_air = int(float(circuit.avg_temp_c))
            temp_track = temp_air + (6 if condition == "dry" else 2)
            humidity = 50 + int(rain_intensity * 35)
            wind_kph = 8 + (race.round_number % 11)
            grip = round(1.0 - rain_intensity * 0.4, 2)

            saved = self._saved_strategies.get(race_id, {})
            saved_drivers = saved.get("drivers", {}) if isinstance(saved, dict) else {}

            drivers_payload: list[dict[str, Any]] = []
            for driver in self._repo.get_drivers_by_team(team.id):
                dkey = str(driver.id)
                dcfg = saved_drivers.get(dkey, {}) if isinstance(saved_drivers, dict) else {}
                drivers_payload.append(
                    {
                        "id": driver.id,
                        "name": driver.name,
                        "number": driver.number,
                        "strategy": {
                            "start_tyre": dcfg.get("start_tyre", "medium"),
                            "pit_plan": dcfg.get("pit_plan", ["hard"]),
                            "fuel_kg": dcfg.get("fuel_kg", 100),
                            "engine_mode": dcfg.get("engine_mode", "standard"),
                            "launch_attitude": dcfg.get("launch_attitude", "balanced"),
                        },
                    }
                )

            return {
                "race": {
                    "id": race.id,
                    "name": race.name,
                    "round": race.round_number,
                    "total_laps": circuit.total_laps,
                },
                "circuit": {
                    "name": circuit.name,
                    "lap_distance_km": float(circuit.lap_distance_km),
                },
                "current_conditions": {
                    "measured_at": now.strftime("%H:%M:%S"),
                    "condition": condition,
                    "track_state": track_state,
                    "rain_intensity": rain_intensity,
                    "temp_air_c": temp_air,
                    "temp_track_c": temp_track,
                    "humidity_pct": humidity,
                    "wind_kph": wind_kph,
                    "grip": grip,
                },
                "drivers": drivers_payload,
                "options": {
                    "tyres": ["soft", "medium", "hard", "inter", "wet"],
                    "engine_modes": ["eco", "standard", "push"],
                    "launch_attitudes": ["conservative", "balanced", "aggressive"],
                },
            }
        except Exception as exc:
            logger.exception("get_pre_race_state error")
            return {"error": str(exc)}

    def set_strategy(self, race_id: int, strategy: dict) -> dict:
        try:
            self._saved_strategies[race_id] = strategy
            return {"ok": True}
        except Exception as exc:
            logger.exception("set_strategy error")
            return {"error": str(exc)}

    def start_race(self, race_id: int) -> dict:
        try:
            if self._race_launcher is None:
                return {"error": "Race launcher no configurado"}

            logger.info("start_race solicitado para race_id=%s", race_id)

            demo_mode = os.getenv("DEMO_MODE", "true").lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            if demo_mode:
                race = self._repo.get_race(race_id)
                if race is None:
                    return {"error": f"Carrera no encontrada: {race_id}"}
                max_demo_races = int(os.getenv("DEMO_MAX_RACES", "2"))
                if race_id not in self._demo_started_races and len(self._demo_started_races) >= max_demo_races:
                    return {
                        "error": (
                            "Modo demo: limite de carreras alcanzado "
                            f"({max_demo_races}) en esta sesion. Cierra y abre el juego para reiniciar."
                        )
                    }
                self._demo_started_races.add(race_id)

            # Ejecutar la carrera en un hilo separado evita romper el callback
            # JS de pywebview al cambiar de pantalla durante la llamada API.
            threading.Thread(
                target=self._race_launcher,
                args=(race_id,),
                daemon=True,
                name=f"race-launcher-{race_id}",
            ).start()
            logger.info("start_race aceptado y encolado para race_id=%s", race_id)
            return {"ok": True, "race_id": race_id, "started": True}
        except Exception as exc:
            logger.exception("start_race error")
            return {"error": str(exc)}

    def ping(self) -> dict:
        return {"ok": True, "screen": self._current_screen}

    def _build_notifications(self, team_id: int, season_id: int) -> list[dict[str, Any]]:
        drivers = self._repo.get_drivers_by_team(team_id)
        expiring = [driver for driver in drivers if driver.contract_status.value == "expiring"]
        notifications = []
        if expiring:
            notifications.append(
                {
                    "title": "Contrato piloto",
                    "body": f"{expiring[0].name} termina contrato al final de temporada.",
                    "time_label": "HOY",
                    "color": "#f5a623",
                }
            )

        finance = self._repo.get_finance(team_id, season_id)
        if finance is not None:
            notifications.append(
                {
                    "title": "Control presupuestario",
                    "body": f"Restan {round(float(finance.budget_cap_m - finance.spent_m), 1)}M del budget cap.",
                    "time_label": "2D",
                    "color": "#0099ff",
                }
            )

        notifications.append(
            {
                "title": "Informe de simulador",
                "body": "Ritmo objetivo estimado entre P3 y P5 para la proxima ronda.",
                "time_label": "3D",
                "color": "#00d45e",
            }
        )
        return notifications[:4]


def _serialize_next_race(repo: F1Repository, race: Any) -> dict[str, Any]:
    if race is None:
        return {}

    circuit_name = ""
    with repo.session() as session:
        circuit = session.get(Circuit, race.circuit_id)
        if circuit is not None:
            circuit_name = circuit.name

    days_until = 12
    if race.race_date is not None:
        days_until = max((race.race_date.date() - datetime.now().date()).days, 0)

    return {
        "id": race.id,
        "name": race.name,
        "round": race.round_number,
        "circuit": circuit_name,
        "days_until": days_until,
        "weather_forecast": "SECO · Dom 20%",
    }


def _serialize_budget(finance: Any) -> dict[str, Any]:
    if finance is None:
        return {"cap": 150.0, "spent": 0.0, "available": 150.0, "spent_pct": 0, "projected_eoy": 0.0}
    available = float(finance.budget_cap_m - finance.spent_m)
    cap = float(finance.budget_cap_m)
    spent = float(finance.spent_m)
    spent_pct = round((spent / cap) * 100) if cap else 0
    return {
        "cap": round(cap, 1),
        "spent": round(spent, 1),
        "available": round(available, 1),
        "spent_pct": spent_pct,
        "projected_eoy": round(min(spent + 15.0, cap), 1),
    }


def _serialize_sponsor(sponsor: Sponsor, season_year: int) -> dict[str, Any]:
    return {
        "id": sponsor.id,
        "name": sponsor.name,
        "annual_income_m": round(float(sponsor.annual_income_m), 1),
        "contract_end_year": sponsor.contract_end_year,
        "is_active": sponsor.is_active,
        "expiring": sponsor.contract_end_year <= season_year,
    }


def _default_upgrades() -> list[dict[str, Any]]:
    return [
        {
            "id": "engine-spec-b",
            "component": "engine",
            "name": "Engine Spec B",
            "description": "Incremento de potencia con pequeno impacto presupuestario.",
            "rating_delta": 2.0,
            "token_cost": 1,
            "cost_m": 8.2,
            "available_from": 10,
        },
        {
            "id": "aero-floor-v2",
            "component": "aero",
            "name": "Floor V2",
            "description": "Paquete de carga para circuitos de apoyo medio.",
            "rating_delta": 1.5,
            "token_cost": 1,
            "cost_m": 5.6,
            "available_from": 9,
        },
    ]


def _build_strategy_alternatives(total_laps: int) -> list[dict[str, Any]]:
    third = max(total_laps // 3, 1)
    half = max(total_laps // 2, 1)
    return [
        {
            "id": "two_stop_s_m_s",
            "name": f"2 Stops - S·{third} / M·{third} / S·{max(total_laps - 2 * third, 1)}",
            "stints": [
                {"compound": "soft", "laps": third},
                {"compound": "medium", "laps": third},
                {"compound": "soft", "laps": max(total_laps - 2 * third, 1)},
            ],
            "projected_position": 3,
            "points": 15,
            "risk": "medium",
        },
        {
            "id": "one_stop_m_h",
            "name": f"1 Stop - M·{half} / H·{max(total_laps - half, 1)}",
            "stints": [
                {"compound": "medium", "laps": half},
                {"compound": "hard", "laps": max(total_laps - half, 1)},
            ],
            "projected_position": 5,
            "points": 10,
            "risk": "low",
        },
    ]
