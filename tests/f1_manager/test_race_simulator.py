"""
tests/f1_manager/test_race_simulator.py
Tests del simulador de carrera F1.
Sin dependencia de DB — todo en memoria con fixtures.
"""
from __future__ import annotations

import pytest

from backend.games.f1_manager.domain.entities import (
    Car,
    CarComponent,
    CarSetup,
    Circuit,
    ComponentType,
    Driver,
    DriverStats,
    EngineMode,
    RaceConfig,
    Team,
    TyreCompound,
    TyreState,
    WeatherCondition,
)
from backend.games.f1_manager.simulation.race_simulator import (
    RaceSimulator,
    TyreState,
    WeatherModel,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_circuit(sc_probability: float = 0.0) -> Circuit:
    return Circuit(
        id=1,
        name="Test Circuit",
        country="TC",
        total_laps=10,
        lap_distance_km=5.0,
        sc_probability=sc_probability,
        rain_chance_pct=0.0,
        avg_temp_c=25.0,
    )


def make_driver(id: int, number: int, pace: float = 80.0) -> Driver:
    return Driver(
        id=id,
        name=f"Driver {id}",
        number=number,
        nationality="XX",
        age=25,
        stats=DriverStats(
            pace=pace,
            consistency=80.0,
            tyre_management=80.0,
            wet_skill=80.0,
            overtaking=80.0,
            defending=80.0,
            starts=80.0,
        ),
    )


def make_car(team_id: int, rating: float = 80.0) -> Car:
    components = {
        ctype: CarComponent(component_type=ctype, rating=rating, reliability=0.99)
        for ctype in ComponentType
    }
    return Car(team_id=team_id, components=components)


def make_team(id: int, is_player: bool = False, car_rating: float = 80.0) -> Team:
    driver1 = make_driver(id=id * 2 - 1, number=id * 2 - 1)
    driver2 = make_driver(id=id * 2,     number=id * 2)
    driver1.team_id = id
    driver2.team_id = id
    return Team(
        id=id,
        name=f"Team {id}",
        short_name=f"T{id}",
        is_player=is_player,
        car=make_car(team_id=id, rating=car_rating),
        drivers=[driver1, driver2],
        morale=0.7,
        pitstop_mean_s=2.4,
        pitstop_std_s=0.1,
    )


def make_race_config(total_laps: int = 10, seed: int = 42) -> RaceConfig:
    return RaceConfig(
        race_id=1,
        circuit=make_circuit(),
        total_laps=total_laps,
        seed=seed,
        weather_seed=seed + 1,
    )


def make_simulator(
    n_teams: int = 3,
    total_laps: int = 10,
    seed: int = 42,
) -> RaceSimulator:
    teams = [make_team(i, is_player=(i == 1)) for i in range(1, n_teams + 1)]
    drivers = [d for t in teams for d in t.drivers]
    config = make_race_config(total_laps=total_laps, seed=seed)
    return RaceSimulator(config, teams, drivers)


# ── Tests básicos ──────────────────────────────────────────────────────────────

class TestRaceSimulator:

    def test_run_produces_correct_lap_count(self) -> None:
        """El simulador debe emitir exactamente total_laps snapshots."""
        sim = make_simulator(total_laps=5)
        snapshots = list(sim.run())
        assert len(snapshots) == 5

    def test_lap_numbers_are_sequential(self) -> None:
        sim = make_simulator(total_laps=8)
        laps = [s.lap for s in sim.run()]
        assert laps == list(range(1, 9))

    def test_all_cars_start_with_positive_time(self) -> None:
        sim = make_simulator(total_laps=3)
        for snapshot in sim.run():
            for car in snapshot.cars:
                if not car.dnf:
                    assert car.total_time_s > 0

    def test_positions_are_unique_per_lap(self) -> None:
        """No puede haber dos coches en la misma posición."""
        sim = make_simulator(n_teams=4, total_laps=5)
        for snapshot in sim.run():
            active = [c for c in snapshot.cars if not c.dnf]
            positions = [c.position for c in active]
            assert len(positions) == len(set(positions)), "Posiciones duplicadas"

    def test_positions_are_sorted_by_time(self) -> None:
        """P1 debe tener el menor tiempo total acumulado."""
        sim = make_simulator(n_teams=3, total_laps=10)
        snapshots = list(sim.run())
        final = snapshots[-1]
        active = sorted([c for c in final.cars if not c.dnf], key=lambda c: c.position)
        times  = [c.total_time_s for c in active]
        assert times == sorted(times), "Las posiciones no corresponden al tiempo"

    def test_fuel_decreases_each_lap(self) -> None:
        """El combustible debe disminuir cada vuelta."""
        sim = make_simulator(n_teams=1, total_laps=5)
        prev_fuel: dict[int, float] = {}
        for snapshot in sim.run():
            for car in snapshot.cars:
                if car.dnf:
                    continue
                if car.driver_id in prev_fuel and not car.in_pit:
                    assert car.fuel_kg <= prev_fuel[car.driver_id], "Combustible no decreció"
                prev_fuel[car.driver_id] = car.fuel_kg

    def test_tyre_wears_over_time(self) -> None:
        """El desgaste medio de neumáticos debe aumentar vuelta a vuelta."""
        sim = make_simulator(n_teams=1, total_laps=8)
        prev_wear: dict[int, float] = {}
        for snapshot in sim.run():
            for car in snapshot.cars:
                if car.dnf or car.in_pit:
                    continue
                wear = car.tyre.avg_wear
                if car.driver_id in prev_wear:
                    assert wear >= prev_wear[car.driver_id] - 0.001, "Desgaste retrocedió sin pitstop"
                prev_wear[car.driver_id] = wear

    def test_results_have_all_drivers(self) -> None:
        """get_results debe incluir un resultado por cada piloto."""
        n_teams = 4
        sim = make_simulator(n_teams=n_teams, total_laps=5)
        list(sim.run())  # ejecutar completamente
        results = sim.get_results()
        assert len(results) == n_teams * 2  # 2 pilotos por equipo

    def test_reproducibility_with_same_seed(self) -> None:
        """Dos simulaciones con el mismo seed deben dar los mismos resultados."""
        sim1 = make_simulator(seed=123, total_laps=10)
        sim2 = make_simulator(seed=123, total_laps=10)
        snaps1 = list(sim1.run())
        snaps2 = list(sim2.run())
        for s1, s2 in zip(snaps1, snaps2):
            times1 = sorted(c.total_time_s for c in s1.cars)
            times2 = sorted(c.total_time_s for c in s2.cars)
            assert times1 == times2, "Resultados no reproducibles"

    def test_different_seeds_give_different_results(self) -> None:
        """Seeds distintos deben producir carreras distintas."""
        sim1 = make_simulator(seed=1, total_laps=10)
        sim2 = make_simulator(seed=9999, total_laps=10)
        snaps1 = list(sim1.run())
        snaps2 = list(sim2.run())
        final1 = {c.driver_id: c.total_time_s for c in snaps1[-1].cars}
        final2 = {c.driver_id: c.total_time_s for c in snaps2[-1].cars}
        assert final1 != final2

    def test_points_awarded_correctly(self) -> None:
        """P1 debe recibir 25 puntos, P2 18, etc."""
        sim = make_simulator(n_teams=5, total_laps=5)
        list(sim.run())
        results = sim.get_results()
        by_pos = {r["finish_position"]: r["points"] for r in results if not r["dnf"]}
        from backend.games.f1_manager.simulation.race_simulator import POINTS_TABLE
        for pos, expected_pts in POINTS_TABLE.items():
            if pos in by_pos:
                assert by_pos[pos] == expected_pts


# ── Tests de degradación de neumáticos ───────────────────────────────────────

class TestTyreState:

    def test_new_tyre_full_performance(self) -> None:
        tyre = TyreState(compound=TyreCompound.SOFT)
        assert tyre.performance_factor == pytest.approx(1.0, abs=0.01)

    def test_worn_tyre_reduced_performance(self) -> None:
        tyre = TyreState(
            compound=TyreCompound.SOFT,
            wear_fl=0.9, wear_fr=0.9,
            wear_rl=0.9, wear_rr=0.9,
        )
        assert tyre.performance_factor < 0.85

    def test_avg_wear_calculation(self) -> None:
        tyre = TyreState(
            compound=TyreCompound.MEDIUM,
            wear_fl=0.2, wear_fr=0.4,
            wear_rl=0.3, wear_rr=0.5,
        )
        assert tyre.avg_wear == pytest.approx(0.35, abs=0.001)


# ── Tests del modelo de clima ─────────────────────────────────────────────────

class TestWeatherModel:

    def test_dry_circuit_stays_dry(self) -> None:
        """Con rain_chance=0 el clima debe permanecer seco."""
        circuit = make_circuit()
        circuit.rain_chance_pct = 0.0
        model = WeatherModel(circuit, seed=0)
        for lap in range(1, 50):
            state = model.update(lap, 70)
            assert state.condition == WeatherCondition.DRY

    def test_weather_model_deterministic(self) -> None:
        """Mismo seed → misma secuencia de clima."""
        circuit = make_circuit()
        circuit.rain_chance_pct = 0.8
        m1 = WeatherModel(circuit, seed=77)
        m2 = WeatherModel(circuit, seed=77)
        for lap in range(1, 30):
            s1 = m1.update(lap, 70)
            s2 = m2.update(lap, 70)
            assert s1.condition == s2.condition
