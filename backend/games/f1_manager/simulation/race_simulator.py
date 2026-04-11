"""
backend/games/f1_manager/simulation/race_simulator.py
Simulador de carrera F1 vuelta a vuelta.
Determinista dado un seed. Sin dependencias de DB ni ZeroMQ.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Iterator

import numpy as np

from backend.games.f1_manager.domain.entities import (
    Car,
    CarRaceState,
    Circuit,
    ComponentType,
    Driver,
    DriverStats,
    EngineMode,
    LapEvent,
    LapSnapshot,
    RaceConfig,
    Team,
    TyreCompound,
    TyreState,
    WeatherCondition,
    WeatherState,
)


# ── Constantes de simulación ──────────────────────────────────────────────────

# Tiempo base por vuelta en segundos (ajustado por circuito)
BASE_LAP_TIME_S: float = 90.0

# Puntos F1 por posición
POINTS_TABLE: dict[int, float] = {
    1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
    6: 8,  7: 6,  8: 4,  9: 2,  10: 1,
}

# Consumo de combustible por vuelta (kg)
FUEL_CONSUMPTION_BASE: float = 1.5

# Degradación base por compuesto por vuelta (0-1)
TYRE_DEG_BASE: dict[TyreCompound, float] = {
    TyreCompound.SOFT  : 0.038,
    TyreCompound.MEDIUM: 0.022,
    TyreCompound.HARD  : 0.014,
    TyreCompound.INTER : 0.020,
    TyreCompound.WET   : 0.012,
}

# Delta de rendimiento por compuesto en condiciones óptimas
TYRE_PACE_DELTA: dict[TyreCompound, float] = {
    TyreCompound.SOFT  :  0.8,   # segundos más rápido que medio
    TyreCompound.MEDIUM:  0.0,
    TyreCompound.HARD  : -0.4,
    TyreCompound.INTER : -1.5,   # en seco
    TyreCompound.WET   : -3.0,   # en seco
}

# Penalización tiempo de pit stop (parada + tiempo perdido en pit lane)
PIT_LANE_TIME_S: float = 20.0

# Modo motor — efecto en tiempo de vuelta y consumo
ENGINE_MODE_EFFECT: dict[EngineMode, tuple[float, float]] = {
    # (delta_lap_time_s, fuel_multiplier)
    EngineMode.ECO      : (0.6,  0.85),
    EngineMode.STANDARD : (0.0,  1.00),
    EngineMode.PUSH     : (-0.4, 1.20),
}


# ── Weather AI ────────────────────────────────────────────────────────────────

class WeatherModel:
    """Modelo estocástico de clima. Determinista dado un seed."""

    def __init__(self, circuit: Circuit, seed: int) -> None:
        self._rng = random.Random(seed)
        self._circuit = circuit
        self._state = WeatherState(
            condition=WeatherCondition.DRY,
            track_temp_c=circuit.avg_temp_c + 10,
            air_temp_c=circuit.avg_temp_c,
        )

    def update(self, lap: int, total_laps: int) -> WeatherState:
        """Calcula el estado del tiempo para esta vuelta."""
        # Probabilidad de cambio de condición aumenta en la segunda mitad
        progress = lap / total_laps
        change_prob = self._circuit.rain_chance_pct * (0.5 + progress * 0.5)

        if self._state.condition == WeatherCondition.DRY:
            if self._rng.random() < change_prob * 0.02:
                self._state = WeatherState(
                    condition=WeatherCondition.LIGHT_RAIN,
                    intensity=self._rng.uniform(0.2, 0.5),
                    track_temp_c=self._state.track_temp_c - 5,
                    air_temp_c=self._state.air_temp_c - 3,
                )
        elif self._state.condition == WeatherCondition.LIGHT_RAIN:
            roll = self._rng.random()
            if roll < 0.05:
                self._state.condition = WeatherCondition.HEAVY_RAIN
                self._state.intensity = min(1.0, self._state.intensity + 0.3)
            elif roll < 0.10:
                self._state.condition = WeatherCondition.DRY
                self._state.intensity = 0.0
        elif self._state.condition == WeatherCondition.HEAVY_RAIN:
            if self._rng.random() < 0.08:
                self._state.condition = WeatherCondition.LIGHT_RAIN
                self._state.intensity = max(0.2, self._state.intensity - 0.2)

        return self._state


# ── Race AI ───────────────────────────────────────────────────────────────────

class RaceAI:
    """
    IA de decisiones vuelta a vuelta para un coche.
    Determinista dado un seed por coche.
    """

    def __init__(self, team: Team, driver: Driver, seed: int) -> None:
        self._rng = random.Random(seed)
        self._team = team
        self._driver = driver

    def decide_pit(
        self,
        state: CarRaceState,
        lap: int,
        total_laps: int,
        weather: WeatherState,
        positions: list[CarRaceState],
    ) -> bool:
        """Decide si el coche debe entrar a pits esta vuelta."""
        if self._team.is_player:
            # El jugador controla sus propios pits vía estrategia planificada
            return self._check_planned_stop(state, lap)

        tyre_worn = state.tyre.avg_wear > (
            0.75 + self._team.ai_risk_appetite * 0.15
        )
        laps_remaining = total_laps - lap
        # No pirar en las últimas 3 vueltas salvo neumático destruido
        too_late = laps_remaining <= 3 and state.tyre.avg_wear < 0.90
        # Reacción al clima
        wrong_tyre = (
            weather.condition in (WeatherCondition.LIGHT_RAIN, WeatherCondition.HEAVY_RAIN)
            and state.tyre.compound in (TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD)
        )
        # Añadir variabilidad según agresividad
        noise = self._rng.gauss(0, 0.05)

        return (tyre_worn or wrong_tyre) and not too_late and noise > -0.03

    def _check_planned_stop(self, state: CarRaceState, lap: int) -> bool:
        """Para el equipo del jugador: seguir la estrategia planificada."""
        for stop_lap, _ in state.planned_stops:
            if stop_lap == lap:
                return True
        return False

    def choose_tyre(
        self,
        state: CarRaceState,
        lap: int,
        total_laps: int,
        weather: WeatherState,
    ) -> TyreCompound:
        """Elige compuesto para el siguiente stint."""
        laps_remaining = total_laps - lap

        if weather.condition in (WeatherCondition.LIGHT_RAIN, WeatherCondition.HEAVY_RAIN):
            return TyreCompound.INTER if weather.intensity < 0.6 else TyreCompound.WET

        if self._team.is_player:
            # El jugador definió la estrategia
            for stop_lap, compound in state.planned_stops:
                if stop_lap == lap:
                    return compound
            return TyreCompound.MEDIUM

        # IA rival
        if laps_remaining > 35:
            return TyreCompound.MEDIUM
        elif laps_remaining > 20:
            return self._rng.choice([TyreCompound.MEDIUM, TyreCompound.HARD])
        else:
            return self._rng.choice([TyreCompound.SOFT, TyreCompound.MEDIUM])

    def decide_engine_mode(
        self,
        state: CarRaceState,
        lap: int,
        total_laps: int,
    ) -> EngineMode:
        """IA de modo motor para rivales."""
        if self._team.is_player:
            return state.engine_mode

        laps_remaining = total_laps - lap
        if state.fuel_kg < 10:
            return EngineMode.ECO
        if laps_remaining <= 5 and self._team.ai_aggression > 0.6:
            return EngineMode.PUSH
        return EngineMode.STANDARD


# ── Simulador principal ───────────────────────────────────────────────────────

class RaceSimulator:
    """
    Simula una carrera de F1 vuelta a vuelta.

    Uso:
        sim = RaceSimulator(config, teams, drivers)
        for snapshot in sim.run():
            # procesar snapshot de vuelta
            zmq_publish(snapshot)
    """

    def __init__(
        self,
        config: RaceConfig,
        teams: list[Team],
        drivers: list[Driver],
    ) -> None:
        self._config = config
        self._circuit = config.circuit
        self._rng = random.Random(config.seed)
        self._np_rng = np.random.default_rng(config.seed)

        self._weather_model = WeatherModel(self._circuit, config.weather_seed)
        self._states: list[CarRaceState] = []
        self._ais: dict[int, RaceAI] = {}

        self._init_states(teams, drivers)

    def _init_states(self, teams: list[Team], drivers: list[Driver]) -> None:
        """Inicializa el estado de cada coche en parrilla."""
        all_entries: list[tuple[Team, Driver]] = []
        for team in teams:
            for driver in team.drivers:
                all_entries.append((team, driver))

        # Orden de parrilla simplificado — en producción vendrá de clasificación
        self._rng.shuffle(all_entries)

        for pos, (team, driver) in enumerate(all_entries, start=1):
            starting_compound = self._pick_starting_tyre(team)
            state = CarRaceState(
                driver_id=driver.id,
                team_id=team.id,
                car=team.car,
                tyre=TyreState(compound=starting_compound),
                position=pos,
                fuel_kg=110.0,
                engine_mode=EngineMode.STANDARD,
            )
            self._states.append(state)
            seed_ai = self._rng.randint(0, 999_999)
            self._ais[driver.id] = RaceAI(team, driver, seed_ai)

        # Mapa driver_id → driver para acceso rápido
        self._drivers: dict[int, Driver] = {d.id: d for d in drivers}
        self._teams: dict[int, Team] = {}
        for team in teams:
            self._teams[team.id] = team
            for driver in team.drivers:
                self._drivers[driver.id] = driver

    def _pick_starting_tyre(self, team: Team) -> TyreCompound:
        """Elige compuesto de salida (50% Medio, 30% Duro, 20% Blando)."""
        roll = self._rng.random()
        if roll < 0.20:
            return TyreCompound.SOFT
        elif roll < 0.70:
            return TyreCompound.MEDIUM
        else:
            return TyreCompound.HARD

    # ── Loop principal ────────────────────────────────────────────────────────

    def run(self) -> Iterator[LapSnapshot]:
        """Genera un LapSnapshot por cada vuelta de la carrera."""
        total = self._config.total_laps
        safety_car = False
        sc_laps_remaining = 0

        for lap in range(1, total + 1):
            weather = self._weather_model.update(lap, total)
            events: list[LapEvent] = []

            # Safety car aleatorio
            if not safety_car and self._rng.random() < self._circuit.sc_probability * 0.04:
                safety_car = True
                sc_laps_remaining = self._rng.randint(3, 6)
                events.append(LapEvent(lap=lap, event_type="safety_car", detail="Virtual safety car deployed"))
            if safety_car:
                sc_laps_remaining -= 1
                if sc_laps_remaining <= 0:
                    safety_car = False
                    events.append(LapEvent(lap=lap, event_type="safety_car_end", detail="Safety car withdrawn"))

            # Simular cada coche
            for state in self._states:
                if state.dnf:
                    continue
                driver = self._drivers[state.driver_id]
                team   = self._teams[state.team_id]
                ai     = self._ais[state.driver_id]

                # 1. Pitstop
                if ai.decide_pit(state, lap, total, weather, self._states):
                    new_compound = ai.choose_tyre(state, lap, total, weather)
                    self._do_pitstop(state, team, new_compound, lap, events)

                # 2. Modo motor (IA o jugador)
                state.engine_mode = ai.decide_engine_mode(state, lap, total)

                # 3. Calcular tiempo de vuelta
                lap_time = self._calc_lap_time(state, driver, weather, safety_car)
                state.current_lap_time_s = lap_time
                state.total_time_s += lap_time
                if lap_time < state.best_lap_s:
                    state.best_lap_s = lap_time

                # 4. Degradación de neumático
                self._apply_tyre_deg(state, weather, lap)

                # 5. Consumo de combustible
                mode_effect = ENGINE_MODE_EFFECT[state.engine_mode]
                state.fuel_kg = max(0.0, state.fuel_kg - FUEL_CONSUMPTION_BASE * mode_effect[1])

                # 6. ERS
                state.ers_charge = min(1.0, state.ers_charge + 0.15 - 0.10)

                # 7. Incidente / DNF
                if self._check_incident(state, driver):
                    state.dnf = True
                    state.dnf_reason = self._rng.choice(["Engine failure", "Collision", "Hydraulics", "Suspension"])
                    events.append(LapEvent(lap=lap, event_type="dnf", driver_id=driver.id, team_id=team.id, detail=state.dnf_reason))

                # 8. DRS simplificado
                state.drs_active = (not safety_car and state.gap_to_leader_s < 1.0 and state.gap_to_leader_s > 0)

            # 9. Recalcular posiciones y gaps
            self._update_positions()

            # 10. Fastest lap event
            fastest = min((s for s in self._states if not s.dnf), key=lambda s: s.current_lap_time_s, default=None)
            if fastest and lap > 5:
                events.append(LapEvent(
                    lap=lap, event_type="fastest_lap",
                    driver_id=fastest.driver_id, team_id=fastest.team_id,
                    detail=f"{fastest.current_lap_time_s:.3f}s",
                ))

            yield LapSnapshot(
                lap=lap,
                total_laps=total,
                cars=list(self._states),
                weather=weather,
                events=events,
                safety_car=safety_car,
            )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _calc_lap_time(
        self,
        state: CarRaceState,
        driver: Driver,
        weather: WeatherState,
        safety_car: bool,
    ) -> float:
        """Calcula el tiempo de vuelta en segundos."""
        base = BASE_LAP_TIME_S

        # Efecto del coche
        car_delta = (100.0 - state.car.overall_rating) * 0.04
        base += car_delta

        # Efecto del piloto (pace + consistency)
        driver_delta = (100.0 - driver.stats.pace) * 0.02
        base += driver_delta

        # Desgaste de neumático
        tyre_delta = (1.0 - state.tyre.performance_factor) * 3.5
        base += tyre_delta

        # Compuesto
        base -= TYRE_PACE_DELTA[state.tyre.compound]

        # Combustible (pesado → más lento; 0.03s por kg)
        base += state.fuel_kg * 0.03

        # Modo motor
        base += ENGINE_MODE_EFFECT[state.engine_mode][0]

        # Clima
        if weather.condition == WeatherCondition.LIGHT_RAIN:
            wet_skill_factor = (100 - driver.stats.wet_skill) * 0.01
            base += 3.0 + wet_skill_factor
            if state.tyre.compound not in (TyreCompound.INTER, TyreCompound.WET):
                base += 5.0  # penalización por neumático incorrecto
        elif weather.condition == WeatherCondition.HEAVY_RAIN:
            wet_skill_factor = (100 - driver.stats.wet_skill) * 0.015
            base += 8.0 + wet_skill_factor
            if state.tyre.compound != TyreCompound.WET:
                base += 10.0

        # Safety car
        if safety_car:
            base += 15.0

        # Ruido aleatorio (variabilidad natural)
        noise = float(self._np_rng.normal(0, 0.12))
        # Consistencia del piloto reduce el ruido
        consistency_factor = driver.stats.consistency / 100.0
        noise *= (1.0 - consistency_factor * 0.5)

        return max(60.0, base + noise)

    def _apply_tyre_deg(
        self,
        state: CarRaceState,
        weather: WeatherState,
        lap: int,
    ) -> None:
        """Aplica degradación de neumáticos para esta vuelta."""
        base_deg = TYRE_DEG_BASE[state.tyre.compound]
        circuit_factor = self._circuit.tyre_wear_factor

        # El setup de suspensión afecta al desgaste
        setup = state.car.setup
        stiffness_factor = 1.0 + (setup.suspension_stiffness - 6) * 0.04

        # Balance delantero/trasero asimétrico
        front_load = setup.front_bias_pct / 100.0
        rear_load  = 1.0 - front_load

        deg_front = base_deg * circuit_factor * stiffness_factor * (1.0 + (front_load - 0.5) * 0.4)
        deg_rear  = base_deg * circuit_factor * stiffness_factor * (1.0 + (rear_load - 0.5)  * 0.4)

        # Ruido por rueda
        noise_scale = 0.003
        state.tyre.wear_fl = min(1.0, state.tyre.wear_fl + deg_front + float(self._np_rng.normal(0, noise_scale)))
        state.tyre.wear_fr = min(1.0, state.tyre.wear_fr + deg_front + float(self._np_rng.normal(0, noise_scale)))
        state.tyre.wear_rl = min(1.0, state.tyre.wear_rl + deg_rear  + float(self._np_rng.normal(0, noise_scale)))
        state.tyre.wear_rr = min(1.0, state.tyre.wear_rr + deg_rear  + float(self._np_rng.normal(0, noise_scale)))

        state.tyre.age_laps += 1

    def _do_pitstop(
        self,
        state: CarRaceState,
        team: Team,
        new_compound: TyreCompound,
        lap: int,
        events: list[LapEvent],
    ) -> None:
        """Ejecuta un pit stop."""
        pit_time = self._rng.gauss(team.pitstop_mean_s, team.pitstop_std_s)
        pit_time = max(2.0, pit_time)
        total_pit_cost = PIT_LANE_TIME_S + pit_time

        state.total_time_s += total_pit_cost
        state.tyre = TyreState(compound=new_compound)
        state.in_pit = True
        state.pit_stops += 1

        events.append(LapEvent(
            lap=lap,
            event_type="pit_stop",
            driver_id=state.driver_id,
            team_id=state.team_id,
            detail=f"→ {new_compound.value} | {pit_time:.2f}s",
        ))

    def _check_incident(self, state: CarRaceState, driver: Driver) -> bool:
        """Evalúa si ocurre un DNF esta vuelta."""
        base_prob = 1.0 - state.car.avg_reliability
        # Modos agresivos aumentan la probabilidad
        mode_risk = {EngineMode.ECO: 0.5, EngineMode.STANDARD: 1.0, EngineMode.PUSH: 2.0}
        prob = base_prob * mode_risk[state.engine_mode] * 0.01  # ~1% base por vuelta si fiab=0
        return self._rng.random() < prob

    def _update_positions(self) -> None:
        """Recalcula posiciones según tiempo total acumulado."""
        active = [s for s in self._states if not s.dnf]
        dnf    = [s for s in self._states if s.dnf]

        active.sort(key=lambda s: s.total_time_s)
        leader_time = active[0].total_time_s if active else 0.0

        for pos, s in enumerate(active, start=1):
            s.position = pos
            s.gap_to_leader_s = s.total_time_s - leader_time

        for pos, s in enumerate(dnf, start=len(active) + 1):
            s.position = pos

    def get_results(self) -> list[dict]:
        """Resultados finales para persistir en DB."""
        results = []
        for state in self._states:
            points = POINTS_TABLE.get(state.position, 0.0)
            results.append({
                "driver_id"      : state.driver_id,
                "team_id"        : state.team_id,
                "finish_position": state.position,
                "points"         : points,
                "dnf"            : state.dnf,
                "dnf_reason"     : state.dnf_reason,
                "best_lap_s"     : state.best_lap_s if state.best_lap_s < float("inf") else None,
                "total_time_s"   : state.total_time_s,
                "pit_stops"      : state.pit_stops,
            })
        return results
