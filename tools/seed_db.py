"""
tools/seed_db.py
Puebla la base de datos con datos iniciales para una nueva partida.
Uso: python tools/seed_db.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.db.models import (
    Base,
    CarComponent,
    Championship,
    Circuit,
    ComponentType,
    ContractStatus,
    Driver,
    EngineMode,
    Race,
    Season,
    Sponsor,
    Team,
    TeamFinance,
    TyreCompound,
    WeatherCondition,
)

DB_URL = "sqlite:///data/game.db"


def seed(db_url: str = DB_URL) -> None:
    engine = create_engine(db_url, echo=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with Session(engine) as s:

        # ── Temporada ─────────────────────────────────────────────────────
        season = Season(year=2026, is_active=True)
        s.add(season)
        s.flush()

        # ── Circuitos ─────────────────────────────────────────────────────
        circuits = [
            Circuit(name="Grand Prix de Bahréin",    country="BH", city="Sakhir",     lap_distance_km=5.412, total_laps=57, tyre_wear_factor=1.3, sc_probability=0.25, rain_chance_pct=0.05, avg_temp_c=32.0),
            Circuit(name="Grand Prix de Arabia Saudí",country="SA",city="Jeddah",     lap_distance_km=6.174, total_laps=50, tyre_wear_factor=1.0, sc_probability=0.45, rain_chance_pct=0.03, avg_temp_c=28.0),
            Circuit(name="Grand Prix de Australia",  country="AU", city="Melbourne",  lap_distance_km=5.278, total_laps=58, tyre_wear_factor=1.1, sc_probability=0.40, rain_chance_pct=0.20, avg_temp_c=22.0),
            Circuit(name="Grand Prix de Japón",      country="JP", city="Suzuka",     lap_distance_km=5.807, total_laps=53, tyre_wear_factor=1.2, sc_probability=0.30, rain_chance_pct=0.35, avg_temp_c=18.0),
            Circuit(name="Grand Prix de China",      country="CN", city="Shanghai",   lap_distance_km=5.451, total_laps=56, tyre_wear_factor=1.1, sc_probability=0.28, rain_chance_pct=0.30, avg_temp_c=20.0),
            Circuit(name="Grand Prix de Miami",      country="US", city="Miami",      lap_distance_km=5.412, total_laps=57, tyre_wear_factor=1.2, sc_probability=0.38, rain_chance_pct=0.15, avg_temp_c=30.0),
            Circuit(name="Grand Prix de Mónaco",     country="MC", city="Montecarlo", lap_distance_km=3.337, total_laps=78, tyre_wear_factor=0.7, sc_probability=0.60, rain_chance_pct=0.25, avg_temp_c=22.0, overtaking_index=0.1),
            Circuit(name="Grand Prix de España",     country="ES", city="Barcelona",  lap_distance_km=4.657, total_laps=66, tyre_wear_factor=1.4, sc_probability=0.20, rain_chance_pct=0.10, avg_temp_c=28.0),
            Circuit(name="Grand Prix de Montréal",   country="CA", city="Montréal",   lap_distance_km=4.361, total_laps=70, tyre_wear_factor=1.0, sc_probability=0.42, rain_chance_pct=0.25, avg_temp_c=25.0, overtaking_index=0.7),
            Circuit(name="Grand Prix de Austria",    country="AT", city="Spielberg",  lap_distance_km=4.318, total_laps=71, tyre_wear_factor=1.1, sc_probability=0.28, rain_chance_pct=0.30, avg_temp_c=23.0),
        ]
        s.add_all(circuits)
        s.flush()

        # ── Equipos ───────────────────────────────────────────────────────
        teams_data = [
            dict(name="Apex Racing",      short_name="APX", is_player=True,  ai_aggression=0.5, ai_risk_appetite=0.5, pitstop_mean_s=2.41),
            dict(name="Kronos Motorsport",short_name="KRN", is_player=False, ai_aggression=0.8, ai_risk_appetite=0.7, pitstop_mean_s=2.32),
            dict(name="Vertex Racing",    short_name="VTX", is_player=False, ai_aggression=0.6, ai_risk_appetite=0.6, pitstop_mean_s=2.45),
            dict(name="Solaris F1",       short_name="SLR", is_player=False, ai_aggression=0.4, ai_risk_appetite=0.4, pitstop_mean_s=2.55),
            dict(name="Phoenix GP",       short_name="PHX", is_player=False, ai_aggression=0.5, ai_risk_appetite=0.5, pitstop_mean_s=2.60),
        ]
        teams = [Team(**d) for d in teams_data]
        s.add_all(teams)
        s.flush()

        # ── Componentes de coche ──────────────────────────────────────────
        car_ratings = {
            "Apex Racing"      : {ComponentType.ENGINE:87, ComponentType.CHASSIS:91, ComponentType.AERO:84, ComponentType.SUSPENSION:86, ComponentType.ERS:89, ComponentType.GEARBOX:88},
            "Kronos Motorsport": {ComponentType.ENGINE:95, ComponentType.CHASSIS:93, ComponentType.AERO:92, ComponentType.SUSPENSION:90, ComponentType.ERS:94, ComponentType.GEARBOX:91},
            "Vertex Racing"    : {ComponentType.ENGINE:90, ComponentType.CHASSIS:88, ComponentType.AERO:89, ComponentType.SUSPENSION:87, ComponentType.ERS:88, ComponentType.GEARBOX:87},
            "Solaris F1"       : {ComponentType.ENGINE:83, ComponentType.CHASSIS:85, ComponentType.AERO:82, ComponentType.SUSPENSION:83, ComponentType.ERS:81, ComponentType.GEARBOX:84},
            "Phoenix GP"       : {ComponentType.ENGINE:79, ComponentType.CHASSIS:81, ComponentType.AERO:80, ComponentType.SUSPENSION:80, ComponentType.ERS:78, ComponentType.GEARBOX:80},
        }
        reliability_map = {
            "Apex Racing"      : 0.95,
            "Kronos Motorsport": 0.97,
            "Vertex Racing"    : 0.96,
            "Solaris F1"       : 0.93,
            "Phoenix GP"       : 0.91,
        }
        for team in teams:
            ratings = car_ratings[team.name]
            rel     = reliability_map[team.name]
            for ctype, rating in ratings.items():
                s.add(CarComponent(
                    team_id=team.id,
                    component_type=ctype,
                    rating=float(rating),
                    reliability=rel,
                    sub_ratings=json.dumps({"primary": rating, "secondary": rating - 4}),
                ))

        # ── Pilotos ───────────────────────────────────────────────────────
        drivers_data = [
            # Apex Racing (equipo jugador)
            dict(name="K. Hartmann", number=44, nationality="DE", age=28, team_id=teams[0].id,
                 pace=94.0, consistency=91.0, tyre_management=88.0, wet_skill=90.0,
                 overtaking=87.0, defending=85.0, starts=89.0,
                 contract_salary_m=18.0, contract_end_year=2028, contract_status=ContractStatus.ACTIVE),
            dict(name="R. Vasquez",  number=7,  nationality="MX", age=27, team_id=teams[0].id,
                 pace=85.0, consistency=82.0, tyre_management=83.0, wet_skill=81.0,
                 overtaking=80.0, defending=78.0, starts=82.0,
                 contract_salary_m=13.0, contract_end_year=2026, contract_status=ContractStatus.EXPIRING),
            # Kronos
            dict(name="N. Marchetti",number=23, nationality="IT", age=26, team_id=teams[1].id,
                 pace=97.0, consistency=94.0, tyre_management=92.0, wet_skill=93.0,
                 overtaking=95.0, defending=91.0, starts=94.0,
                 contract_salary_m=35.0, contract_end_year=2028, contract_status=ContractStatus.ACTIVE),
            dict(name="A. Kowalski", number=8,  nationality="PL", age=24, team_id=teams[1].id,
                 pace=89.0, consistency=85.0, tyre_management=84.0, wet_skill=86.0,
                 overtaking=83.0, defending=80.0, starts=85.0,
                 contract_salary_m=20.0, contract_end_year=2027, contract_status=ContractStatus.ACTIVE),
            # Vertex
            dict(name="T. Okonkwo",  number=11, nationality="NG", age=29, team_id=teams[2].id,
                 pace=91.0, consistency=89.0, tyre_management=90.0, wet_skill=88.0,
                 overtaking=86.0, defending=87.0, starts=88.0,
                 contract_salary_m=22.0, contract_end_year=2027, contract_status=ContractStatus.ACTIVE),
            dict(name="L. Svensson", number=55, nationality="SE", age=31, team_id=teams[2].id,
                 pace=87.0, consistency=92.0, tyre_management=91.0, wet_skill=85.0,
                 overtaking=80.0, defending=88.0, starts=86.0,
                 contract_salary_m=14.0, contract_end_year=2027, contract_status=ContractStatus.ACTIVE),
            # Solaris
            dict(name="C. Müller",   number=81, nationality="DE", age=33, team_id=teams[3].id,
                 pace=84.0, consistency=90.0, tyre_management=89.0, wet_skill=83.0,
                 overtaking=78.0, defending=86.0, starts=84.0,
                 contract_salary_m=11.0, contract_end_year=2026, contract_status=ContractStatus.EXPIRING),
            dict(name="P. Laurent",  number=4,  nationality="FR", age=25, team_id=teams[3].id,
                 pace=86.0, consistency=83.0, tyre_management=82.0, wet_skill=84.0,
                 overtaking=82.0, defending=80.0, starts=83.0,
                 contract_salary_m=9.0,  contract_end_year=2027, contract_status=ContractStatus.ACTIVE),
            # Phoenix — mercado libre
            dict(name="R. Tanaka",   number=22, nationality="JP", age=22, team_id=teams[4].id,
                 pace=91.0, consistency=79.0, tyre_management=78.0, wet_skill=87.0,
                 overtaking=88.0, defending=75.0, starts=80.0,
                 contract_salary_m=7.0,  contract_end_year=2026, contract_status=ContractStatus.EXPIRING),
            dict(name="E. Dubois",   number=63, nationality="FR", age=26, team_id=teams[4].id,
                 pace=87.0, consistency=86.0, tyre_management=85.0, wet_skill=83.0,
                 overtaking=81.0, defending=82.0, starts=84.0,
                 contract_salary_m=8.0,  contract_end_year=2027, contract_status=ContractStatus.ACTIVE),
            # Agente libre
            dict(name="F. Van Der Berg", number=3, nationality="NL", age=25, team_id=None,
                 pace=97.0, consistency=88.0, tyre_management=89.0, wet_skill=92.0,
                 overtaking=95.0, defending=88.0, starts=91.0,
                 contract_salary_m=32.0, contract_end_year=None, contract_status=ContractStatus.EXPIRED),
        ]
        drivers = [Driver(**d) for d in drivers_data]
        s.add_all(drivers)
        s.flush()

        # ── Carreras ──────────────────────────────────────────────────────
        for i, circuit in enumerate(circuits, start=1):
            race = Race(
                season_id=season.id,
                circuit_id=circuit.id,
                round_number=i,
                name=circuit.name,
                is_completed=(i <= 8),  # 8 carreras ya completadas
            )
            s.add(race)
        s.flush()

        # ── Campeonato inicial ────────────────────────────────────────────
        champ_data = [
            (teams[0], 187, 3),
            (teams[1], 229, 1),
            (teams[2], 201, 2),
            (teams[3], 154, 4),
            (teams[4], 112, 5),
        ]
        for team, pts, pos in champ_data:
            s.add(Championship(season_id=season.id, team_id=team.id, points=pts, position=pos))

        # ── Finanzas ──────────────────────────────────────────────────────
        finance_data = [
            dict(team_id=teams[0].id, season_id=season.id, budget_cap_m=150.0, spent_m=100.5,
                 fom_prize_m=42.0, sponsor_income_m=38.5,
                 driver_salaries_m=31.0, staff_salaries_m=18.5, development_m=22.4,
                 logistics_m=8.8),
            dict(team_id=teams[1].id, season_id=season.id, budget_cap_m=150.0, spent_m=142.0,
                 fom_prize_m=60.0, sponsor_income_m=65.0,
                 driver_salaries_m=55.0, staff_salaries_m=25.0, development_m=38.0,
                 logistics_m=10.0),
        ]
        for fd in finance_data:
            s.add(TeamFinance(**fd))

        # ── Sponsors ─────────────────────────────────────────────────────
        s.add_all([
            Sponsor(team_id=teams[0].id, name="NovaTech Systems", annual_income_m=22.0, contract_end_year=2027, is_active=True),
            Sponsor(team_id=teams[0].id, name="Meridian Energy",  annual_income_m=9.5,  contract_end_year=2026, is_active=True,
                    bonus_condition="top_3_constructors", bonus_amount_m=3.0),
            Sponsor(team_id=teams[0].id, name="Vantara Finance",  annual_income_m=7.0,  contract_end_year=2028, is_active=True),
        ])

        s.commit()
        print(f"OK Base de datos poblada: {db_url}")
        print(f"  Temporada: {season.year}")
        print(f"  Circuitos: {len(circuits)}")
        print(f"  Equipos  : {len(teams)}")
        print(f"  Pilotos  : {len(drivers)}")
        print(f"  Carreras : {len(circuits)}")


if __name__ == "__main__":
    Path("data").mkdir(exist_ok=True)
    seed()
