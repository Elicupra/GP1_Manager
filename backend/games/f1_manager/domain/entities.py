"""
backend/games/f1_manager/domain/entities.py
Entidades de dominio puras — sin dependencia de SQLAlchemy.
Se usan en la simulación. Los repositorios las convierten desde/hacia modelos DB.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Enums de dominio ─────────────────────────────────────────────────────────

class TyreCompound(str, Enum):
    SOFT   = "soft"
    MEDIUM = "medium"
    HARD   = "hard"
    INTER  = "inter"
    WET    = "wet"


class WeatherCondition(str, Enum):
    DRY         = "dry"
    LIGHT_CLOUD = "light_cloud"
    LIGHT_RAIN  = "light_rain"
    HEAVY_RAIN  = "heavy_rain"


class EngineMode(str, Enum):
    ECO      = "eco"
    STANDARD = "standard"
    PUSH     = "push"


class ComponentType(str, Enum):
    ENGINE     = "engine"
    CHASSIS    = "chassis"
    AERO       = "aero"
    SUSPENSION = "suspension"
    ERS        = "ers"
    GEARBOX    = "gearbox"


# ── Driver ───────────────────────────────────────────────────────────────────

@dataclass
class DriverStats:
    """Estadísticas de un piloto. Valores 0-100."""
    pace            : float = 75.0
    consistency     : float = 75.0
    tyre_management : float = 75.0
    wet_skill       : float = 75.0
    overtaking      : float = 75.0
    defending       : float = 75.0
    starts          : float = 75.0


@dataclass
class Driver:
    """Piloto en una carrera."""
    id          : int
    name        : str
    number      : int
    nationality : str
    age         : int
    stats       : DriverStats
    morale      : float = 0.7   # 0-1
    fitness     : float = 1.0   # 0-1
    team_id     : Optional[int] = None


# ── Tyre ─────────────────────────────────────────────────────────────────────

@dataclass
class TyreState:
    """Estado actual de los neumáticos en carrera."""
    compound    : TyreCompound
    age_laps    : int   = 0
    # Desgaste por rueda 0-1 (0=nuevo, 1=destruido)
    wear_fl     : float = 0.0
    wear_fr     : float = 0.0
    wear_rl     : float = 0.0
    wear_rr     : float = 0.0
    # Temperatura 0-1 (0=fría, 1=en ventana óptima, >1=sobrecalentada)
    temp_fl     : float = 0.5
    temp_fr     : float = 0.5
    temp_rl     : float = 0.5
    temp_rr     : float = 0.5

    @property
    def avg_wear(self) -> float:
        """Desgaste medio de las cuatro ruedas."""
        return (self.wear_fl + self.wear_fr + self.wear_rl + self.wear_rr) / 4.0

    @property
    def performance_factor(self) -> float:
        """Factor multiplicador de rendimiento según desgaste (1.0 = perfecto)."""
        # Degradación no lineal: suave hasta 60%, rápida después
        avg = self.avg_wear
        if avg < 0.6:
            return 1.0 - avg * 0.15
        return 1.0 - 0.09 - (avg - 0.6) * 0.6


# ── Car ──────────────────────────────────────────────────────────────────────

@dataclass
class CarComponent:
    """Componente del coche con su estado actual."""
    component_type  : ComponentType
    rating          : float   # 0-100
    reliability     : float   # 0-1
    sub_ratings     : dict[str, float] = field(default_factory=dict)


@dataclass
class CarSetup:
    """Configuración del coche para una sesión."""
    aero_level          : int   = 6    # 1-11
    front_bias_pct      : float = 50.0
    suspension_stiffness: int   = 6    # 1-11
    brake_bias_pct      : float = 55.0
    engine_mode         : EngineMode = EngineMode.STANDARD


@dataclass
class Car:
    """Coche de un equipo — componentes + setup."""
    team_id     : int
    components  : dict[ComponentType, CarComponent] = field(default_factory=dict)
    setup       : CarSetup = field(default_factory=CarSetup)

    @property
    def overall_rating(self) -> float:
        """Rating global ponderado del coche."""
        weights = {
            ComponentType.ENGINE     : 0.30,
            ComponentType.CHASSIS    : 0.20,
            ComponentType.AERO       : 0.25,
            ComponentType.SUSPENSION : 0.10,
            ComponentType.ERS        : 0.10,
            ComponentType.GEARBOX    : 0.05,
        }
        total = 0.0
        for ctype, weight in weights.items():
            comp = self.components.get(ctype)
            total += (comp.rating if comp else 60.0) * weight
        return total

    @property
    def avg_reliability(self) -> float:
        """Fiabilidad media de todos los componentes."""
        comps = list(self.components.values())
        if not comps:
            return 1.0
        return sum(c.reliability for c in comps) / len(comps)


# ── Race state ────────────────────────────────────────────────────────────────

@dataclass
class CarRaceState:
    """Estado en carrera de un coche, vuelta a vuelta."""
    driver_id   : int
    team_id     : int
    car         : Car
    tyre        : TyreState
    position    : int   = 0
    fuel_kg     : float = 110.0
    ers_charge  : float = 1.0    # 0-1
    drs_active  : bool  = False
    in_pit      : bool  = False
    dnf         : bool  = False
    dnf_reason  : str   = ""
    current_lap_time_s: float = 0.0
    total_time_s      : float = 0.0
    best_lap_s        : float = float("inf")
    gap_to_leader_s   : float = 0.0
    pit_stops   : int   = 0
    engine_mode : EngineMode = EngineMode.STANDARD
    # Estrategia planificada: lista de (vuelta_pit, compuesto)
    planned_stops: list[tuple[int, TyreCompound]] = field(default_factory=list)


# ── Weather ───────────────────────────────────────────────────────────────────

@dataclass
class WeatherState:
    """Estado climático en un momento de la carrera."""
    condition   : WeatherCondition = WeatherCondition.DRY
    intensity   : float = 0.0    # 0-1 (solo relevante en lluvia)
    track_temp_c: float = 35.0
    air_temp_c  : float = 25.0
    wind_speed  : float = 5.0


# ── Circuit ───────────────────────────────────────────────────────────────────

@dataclass
class Circuit:
    """Circuito con sus parámetros de simulación."""
    id                  : int
    name                : str
    country             : str
    total_laps          : int
    lap_distance_km     : float
    overtaking_index    : float = 0.5
    tyre_wear_factor    : float = 1.0
    brake_wear_factor   : float = 1.0
    downforce_sensitivity: float = 1.0
    sc_probability      : float = 0.3
    rain_chance_pct     : float = 0.2
    avg_temp_c          : float = 25.0


# ── Team ─────────────────────────────────────────────────────────────────────

@dataclass
class Team:
    """Equipo de F1 con su coche, pilotos y estado."""
    id              : int
    name            : str
    short_name      : str
    is_player       : bool
    car             : Car
    drivers         : list[Driver] = field(default_factory=list)
    morale          : float = 0.7
    pitstop_mean_s  : float = 2.5
    pitstop_std_s   : float = 0.3
    # IA parámetros
    ai_aggression   : float = 0.5
    ai_risk_appetite: float = 0.5


# ── Race ─────────────────────────────────────────────────────────────────────

@dataclass
class RaceConfig:
    """Configuración de una carrera antes de empezar."""
    race_id     : int
    circuit     : Circuit
    total_laps  : int
    seed        : int   # para reproducibilidad
    weather_seed: int


@dataclass
class LapEvent:
    """Evento ocurrido en una vuelta (pit, incidente, safety car, etc.)."""
    lap         : int
    event_type  : str   # "pit_stop", "dnf", "safety_car", "fastest_lap", etc.
    driver_id   : Optional[int] = None
    team_id     : Optional[int] = None
    detail      : str = ""


@dataclass
class LapSnapshot:
    """Estado completo de la carrera tras una vuelta."""
    lap         : int
    total_laps  : int
    cars        : list[CarRaceState]
    weather     : WeatherState
    events      : list[LapEvent] = field(default_factory=list)
    safety_car  : bool = False
