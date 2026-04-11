"""
backend/db/models.py
Modelos SQLAlchemy 2.x para F1 Manager.
Todas las entidades del juego en un único módulo.
Solo los repositorios deben importar desde aquí.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarativa compartida por todos los modelos."""
    pass


# ── Enums ────────────────────────────────────────────────────────────────────

class TyreCompound(str, enum.Enum):
    SOFT   = "soft"
    MEDIUM = "medium"
    HARD   = "hard"
    INTER  = "inter"
    WET    = "wet"


class WeatherCondition(str, enum.Enum):
    DRY         = "dry"
    LIGHT_CLOUD = "light_cloud"
    LIGHT_RAIN  = "light_rain"
    HEAVY_RAIN  = "heavy_rain"


class EngineMode(str, enum.Enum):
    ECO      = "eco"
    STANDARD = "standard"
    PUSH     = "push"


class ContractStatus(str, enum.Enum):
    ACTIVE    = "active"
    EXPIRING  = "expiring"   # último año
    EXPIRED   = "expired"
    PENDING   = "pending"    # oferta enviada, sin respuesta


class SessionType(str, enum.Enum):
    FP1       = "fp1"
    FP2       = "fp2"
    FP3       = "fp3"
    QUALI     = "quali"
    SPRINT    = "sprint"
    RACE      = "race"


class ComponentType(str, enum.Enum):
    ENGINE    = "engine"
    CHASSIS   = "chassis"
    AERO      = "aero"
    SUSPENSION= "suspension"
    ERS       = "ers"
    GEARBOX   = "gearbox"


# ── Season ───────────────────────────────────────────────────────────────────

class Season(Base):
    """Temporada de campeonato."""
    __tablename__ = "seasons"

    id          : Mapped[int]      = mapped_column(Integer, primary_key=True)
    year        : Mapped[int]      = mapped_column(Integer, unique=True, nullable=False)
    is_active   : Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at  : Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    races       : Mapped[list[Race]]       = relationship(back_populates="season", cascade="all, delete-orphan")
    championships: Mapped[list[Championship]] = relationship(back_populates="season")


# ── Circuit ──────────────────────────────────────────────────────────────────

class Circuit(Base):
    """Circuito — datos estáticos reutilizables entre temporadas."""
    __tablename__ = "circuits"

    id              : Mapped[int]   = mapped_column(Integer, primary_key=True)
    name            : Mapped[str]   = mapped_column(String(100), nullable=False)
    country         : Mapped[str]   = mapped_column(String(60), nullable=False)
    city            : Mapped[str]   = mapped_column(String(60), nullable=False)
    lap_distance_km : Mapped[float] = mapped_column(Float, nullable=False)
    total_laps      : Mapped[int]   = mapped_column(Integer, nullable=False)
    # Parámetros de simulación
    overtaking_index: Mapped[float] = mapped_column(Float, default=0.5)   # 0-1
    tyre_wear_factor : Mapped[float]= mapped_column(Float, default=1.0)
    brake_wear_factor: Mapped[float]= mapped_column(Float, default=1.0)
    downforce_sensitivity: Mapped[float] = mapped_column(Float, default=1.0)
    sc_probability  : Mapped[float] = mapped_column(Float, default=0.3)   # prob. safety car
    # Clima típico
    rain_chance_pct : Mapped[float] = mapped_column(Float, default=0.2)
    avg_temp_c      : Mapped[float] = mapped_column(Float, default=25.0)

    races           : Mapped[list[Race]] = relationship(back_populates="circuit")


# ── Team ─────────────────────────────────────────────────────────────────────

class Team(Base):
    """Equipo de F1 — jugador o rival."""
    __tablename__ = "teams"

    id          : Mapped[int]   = mapped_column(Integer, primary_key=True)
    name        : Mapped[str]   = mapped_column(String(80), unique=True, nullable=False)
    short_name  : Mapped[str]   = mapped_column(String(20), nullable=False)
    is_player   : Mapped[bool]  = mapped_column(Boolean, default=False)
    # IA de equipo rival
    ai_aggression  : Mapped[float] = mapped_column(Float, default=0.5)   # 0-1
    ai_risk_appetite: Mapped[float]= mapped_column(Float, default=0.5)
    # Moral
    morale      : Mapped[float] = mapped_column(Float, default=0.7)      # 0-1
    # Pit stop
    pitstop_mean_s : Mapped[float] = mapped_column(Float, default=2.5)
    pitstop_std_s  : Mapped[float] = mapped_column(Float, default=0.3)

    drivers         : Mapped[list[Driver]]   = relationship(back_populates="team")
    car_components  : Mapped[list[CarComponent]] = relationship(back_populates="team", cascade="all, delete-orphan")
    finances        : Mapped[list[TeamFinance]]  = relationship(back_populates="team", cascade="all, delete-orphan")
    sponsors        : Mapped[list[Sponsor]]      = relationship(back_populates="team")
    championships   : Mapped[list[Championship]] = relationship(back_populates="team")
    race_entries    : Mapped[list[RaceEntry]]    = relationship(back_populates="team")


# ── Driver ───────────────────────────────────────────────────────────────────

class Driver(Base):
    """Piloto — estadísticas, contrato y estado."""
    __tablename__ = "drivers"

    id              : Mapped[int]            = mapped_column(Integer, primary_key=True)
    name            : Mapped[str]            = mapped_column(String(80), nullable=False)
    number          : Mapped[int]            = mapped_column(Integer, unique=True)
    nationality     : Mapped[str]            = mapped_column(String(3))   # ISO 3166-1 alpha-2
    age             : Mapped[int]            = mapped_column(Integer)
    team_id         : Mapped[Optional[int]]  = mapped_column(ForeignKey("teams.id"), nullable=True)

    # Stats base 0-100
    pace            : Mapped[float] = mapped_column(Float, default=75.0)
    consistency     : Mapped[float] = mapped_column(Float, default=75.0)
    tyre_management : Mapped[float] = mapped_column(Float, default=75.0)
    wet_skill       : Mapped[float] = mapped_column(Float, default=75.0)
    overtaking      : Mapped[float] = mapped_column(Float, default=75.0)
    defending       : Mapped[float] = mapped_column(Float, default=75.0)
    starts          : Mapped[float] = mapped_column(Float, default=75.0)
    # Estado
    morale          : Mapped[float] = mapped_column(Float, default=0.7)  # 0-1
    fitness         : Mapped[float] = mapped_column(Float, default=1.0)  # 0-1
    # Contrato
    contract_salary_m: Mapped[float]          = mapped_column(Float, default=10.0)
    contract_end_year: Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    contract_status  : Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus), default=ContractStatus.ACTIVE
    )

    team            : Mapped[Optional[Team]] = relationship(back_populates="drivers")
    race_results    : Mapped[list[DriverResult]] = relationship(back_populates="driver")


# ── Car Components ────────────────────────────────────────────────────────────

class CarComponent(Base):
    """Componente del coche de un equipo."""
    __tablename__ = "car_components"
    __table_args__ = (UniqueConstraint("team_id", "component_type"),)

    id              : Mapped[int]           = mapped_column(Integer, primary_key=True)
    team_id         : Mapped[int]           = mapped_column(ForeignKey("teams.id"), nullable=False)
    component_type  : Mapped[ComponentType] = mapped_column(Enum(ComponentType), nullable=False)

    # Rendimiento 0-100
    rating          : Mapped[float] = mapped_column(Float, default=70.0)
    # Sub-atributos JSON-encoded (ej: {"power":87,"ers_efficiency":89})
    sub_ratings     : Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Fiabilidad 0-1
    reliability     : Mapped[float] = mapped_column(Float, default=0.95)
    # Uso
    uses_current    : Mapped[int]   = mapped_column(Integer, default=0)
    uses_max        : Mapped[int]   = mapped_column(Integer, default=8)
    # Desarrollo
    dev_tokens_used : Mapped[int]   = mapped_column(Integer, default=0)
    last_updated_race: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    team            : Mapped[Team] = relationship(back_populates="car_components")


# ── Race ─────────────────────────────────────────────────────────────────────

class Race(Base):
    """Gran Premio — contiene varias sesiones."""
    __tablename__ = "races"

    id              : Mapped[int]   = mapped_column(Integer, primary_key=True)
    season_id       : Mapped[int]   = mapped_column(ForeignKey("seasons.id"), nullable=False)
    circuit_id      : Mapped[int]   = mapped_column(ForeignKey("circuits.id"), nullable=False)
    round_number    : Mapped[int]   = mapped_column(Integer, nullable=False)
    name            : Mapped[str]   = mapped_column(String(120), nullable=False)
    race_date       : Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_completed    : Mapped[bool]  = mapped_column(Boolean, default=False)
    # Condiciones reales (registradas post-carrera)
    weather_condition: Mapped[WeatherCondition] = mapped_column(
        Enum(WeatherCondition), default=WeatherCondition.DRY
    )
    temperature_c   : Mapped[float] = mapped_column(Float, default=25.0)
    safety_car_laps : Mapped[int]   = mapped_column(Integer, default=0)

    season          : Mapped[Season]        = relationship(back_populates="races")
    circuit         : Mapped[Circuit]       = relationship(back_populates="races")
    entries         : Mapped[list[RaceEntry]]    = relationship(back_populates="race", cascade="all, delete-orphan")
    driver_results  : Mapped[list[DriverResult]] = relationship(back_populates="race", cascade="all, delete-orphan")


# ── RaceEntry ─────────────────────────────────────────────────────────────────

class RaceEntry(Base):
    """Participación de un equipo en una carrera con su estrategia."""
    __tablename__ = "race_entries"
    __table_args__ = (UniqueConstraint("race_id", "team_id"),)

    id              : Mapped[int]  = mapped_column(Integer, primary_key=True)
    race_id         : Mapped[int]  = mapped_column(ForeignKey("races.id"), nullable=False)
    team_id         : Mapped[int]  = mapped_column(ForeignKey("teams.id"), nullable=False)
    # Setup aero 1-11
    aero_level      : Mapped[int]  = mapped_column(Integer, default=6)
    front_bias_pct  : Mapped[float]= mapped_column(Float, default=50.0)
    suspension_stiffness: Mapped[int] = mapped_column(Integer, default=6)
    brake_bias_pct  : Mapped[float]= mapped_column(Float, default=55.0)
    engine_mode     : Mapped[EngineMode] = mapped_column(Enum(EngineMode), default=EngineMode.STANDARD)

    race            : Mapped[Race] = relationship(back_populates="entries")
    team            : Mapped[Team] = relationship(back_populates="race_entries")


# ── DriverResult ─────────────────────────────────────────────────────────────

class DriverResult(Base):
    """Resultado de un piloto en una carrera."""
    __tablename__ = "driver_results"
    __table_args__ = (UniqueConstraint("race_id", "driver_id"),)

    id              : Mapped[int]           = mapped_column(Integer, primary_key=True)
    race_id         : Mapped[int]           = mapped_column(ForeignKey("races.id"), nullable=False)
    driver_id       : Mapped[int]           = mapped_column(ForeignKey("drivers.id"), nullable=False)
    grid_position   : Mapped[int]           = mapped_column(Integer)
    finish_position : Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    points          : Mapped[float]         = mapped_column(Float, default=0.0)
    fastest_lap     : Mapped[bool]          = mapped_column(Boolean, default=False)
    dnf             : Mapped[bool]          = mapped_column(Boolean, default=False)
    dnf_reason      : Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    best_lap_time_s : Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_time_s    : Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pit_stops       : Mapped[int]           = mapped_column(Integer, default=0)
    tyre_sequence   : Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    race            : Mapped[Race]   = relationship(back_populates="driver_results")
    driver          : Mapped[Driver] = relationship(back_populates="race_results")


# ── Championship ─────────────────────────────────────────────────────────────

class Championship(Base):
    """Clasificación de constructores por temporada."""
    __tablename__ = "championships"
    __table_args__ = (UniqueConstraint("season_id", "team_id"),)

    id              : Mapped[int]   = mapped_column(Integer, primary_key=True)
    season_id       : Mapped[int]   = mapped_column(ForeignKey("seasons.id"), nullable=False)
    team_id         : Mapped[int]   = mapped_column(ForeignKey("teams.id"), nullable=False)
    points          : Mapped[float] = mapped_column(Float, default=0.0)
    position        : Mapped[int]   = mapped_column(Integer, default=0)

    season          : Mapped[Season] = relationship(back_populates="championships")
    team            : Mapped[Team]   = relationship(back_populates="championships")


# ── TeamFinance ───────────────────────────────────────────────────────────────

class TeamFinance(Base):
    """Snapshot financiero de un equipo por temporada."""
    __tablename__ = "team_finances"
    __table_args__ = (UniqueConstraint("team_id", "season_id"),)

    id              : Mapped[int]   = mapped_column(Integer, primary_key=True)
    team_id         : Mapped[int]   = mapped_column(ForeignKey("teams.id"), nullable=False)
    season_id       : Mapped[int]   = mapped_column(Integer, nullable=False)
    budget_cap_m    : Mapped[float] = mapped_column(Float, default=150.0)
    spent_m         : Mapped[float] = mapped_column(Float, default=0.0)
    # Ingresos
    fom_prize_m     : Mapped[float] = mapped_column(Float, default=0.0)
    sponsor_income_m: Mapped[float] = mapped_column(Float, default=0.0)
    # Gastos
    driver_salaries_m  : Mapped[float] = mapped_column(Float, default=0.0)
    staff_salaries_m   : Mapped[float] = mapped_column(Float, default=0.0)
    development_m      : Mapped[float] = mapped_column(Float, default=0.0)
    logistics_m        : Mapped[float] = mapped_column(Float, default=0.0)

    team            : Mapped[Team] = relationship(back_populates="finances")


# ── Sponsor ───────────────────────────────────────────────────────────────────

class Sponsor(Base):
    """Contrato de patrocinio."""
    __tablename__ = "sponsors"

    id              : Mapped[int]   = mapped_column(Integer, primary_key=True)
    team_id         : Mapped[int]   = mapped_column(ForeignKey("teams.id"), nullable=False)
    name            : Mapped[str]   = mapped_column(String(80), nullable=False)
    annual_income_m : Mapped[float] = mapped_column(Float, nullable=False)
    contract_end_year: Mapped[int]  = mapped_column(Integer, nullable=False)
    # Condiciones de bonus
    bonus_condition : Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bonus_amount_m  : Mapped[float]         = mapped_column(Float, default=0.0)
    is_active       : Mapped[bool]          = mapped_column(Boolean, default=True)

    team            : Mapped[Team] = relationship(back_populates="sponsors")
