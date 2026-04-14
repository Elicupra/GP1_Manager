"""
backend/games/f1_manager/persistence/repository.py
Repositorio principal F1 Manager.
Único punto de acceso a la base de datos para el juego.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.db.models import (
    Base,
    CarComponent,
    Championship,
    Circuit,
    ComponentType,
    Driver,
    DriverResult,
    Race,
    RaceEntry,
    Season,
    Sponsor,
    Team,
    TeamFinance,
    TyreCompound,
)
from backend.games.f1_manager.domain import entities as dom


class F1Repository:
    """
    Repositorio central del juego F1 Manager.
    Convierte entre modelos SQLAlchemy (DB) y entidades de dominio (simulación).
    """

    def __init__(self, db_url: str = "sqlite:///data/game.db") -> None:
        self._engine = create_engine(db_url, echo=False)
        self._Session = sessionmaker(bind=self._engine, expire_on_commit=False)
        Base.metadata.create_all(self._engine)

    # ── Sesión ────────────────────────────────────────────────────────────────

    def session(self) -> Session:
        """Retorna una nueva sesión. Usar con context manager."""
        return self._Session()

    # ── Season ────────────────────────────────────────────────────────────────

    def get_active_season(self) -> Optional[Season]:
        """Retorna la temporada activa."""
        with self._Session() as s:
            return s.scalars(select(Season).where(Season.is_active == True)).first()

    def create_season(self, year: int) -> Season:
        """Crea una nueva temporada y la marca como activa."""
        with self._Session() as s:
            # Desactivar temporadas anteriores
            for season in s.scalars(select(Season)).all():
                season.is_active = False
            new_season = Season(year=year, is_active=True)
            s.add(new_season)
            s.commit()
            s.refresh(new_season)
            return new_season

    # ── Teams ─────────────────────────────────────────────────────────────────

    def get_all_teams(self) -> list[Team]:
        """Retorna todos los equipos con sus relaciones cargadas."""
        with self._Session() as s:
            return list(s.scalars(select(Team)).all())

    def get_player_team(self) -> Optional[Team]:
        """Retorna el equipo del jugador."""
        with self._Session() as s:
            return s.scalars(select(Team).where(Team.is_player == True)).first()

    def get_team(self, team_id: int) -> Optional[Team]:
        """Retorna un equipo por ID."""
        with self._Session() as s:
            return s.get(Team, team_id)

    def update_team_morale(self, team_id: int, delta: float) -> None:
        """Ajusta la moral del equipo en ±delta."""
        with self._Session() as s:
            team = s.get(Team, team_id)
            if team:
                team.morale = max(0.0, min(1.0, team.morale + delta))
                s.commit()

    # ── Drivers ───────────────────────────────────────────────────────────────

    def get_driver(self, driver_id: int) -> Optional[Driver]:
        with self._Session() as s:
            return s.get(Driver, driver_id)

    def get_drivers_by_team(self, team_id: int) -> list[Driver]:
        with self._Session() as s:
            return list(s.scalars(select(Driver).where(Driver.team_id == team_id)).all())

    def get_free_agents(self) -> list[Driver]:
        """Pilotos sin equipo (mercado libre)."""
        with self._Session() as s:
            return list(s.scalars(select(Driver).where(Driver.team_id == None)).all())

    def update_driver_contract(
        self,
        driver_id: int,
        team_id: int,
        salary_m: float,
        end_year: int,
    ) -> None:
        """Firma o renueva contrato de un piloto."""
        with self._Session() as s:
            driver = s.get(Driver, driver_id)
            if driver:
                driver.team_id         = team_id
                driver.contract_salary_m = salary_m
                driver.contract_end_year = end_year
                from backend.db.models import ContractStatus
                driver.contract_status   = ContractStatus.ACTIVE
                s.commit()

    # ── Car Components ────────────────────────────────────────────────────────

    def get_car_components(self, team_id: int) -> list[CarComponent]:
        with self._Session() as s:
            return list(s.scalars(
                select(CarComponent).where(CarComponent.team_id == team_id)
            ).all())

    def apply_upgrade(
        self,
        team_id: int,
        component_type: ComponentType,
        rating_delta: float,
        token_cost: int,
        cost_m: float,
    ) -> bool:
        """Aplica una mejora a un componente. Retorna True si tiene recursos."""
        with self._Session() as s:
            comp = s.scalars(
                select(CarComponent).where(
                    CarComponent.team_id == team_id,
                    CarComponent.component_type == component_type,
                )
            ).first()
            if not comp:
                return False
            tokens_available = 8 - comp.dev_tokens_used
            if tokens_available < token_cost:
                return False
            comp.rating = min(100.0, comp.rating + rating_delta)
            comp.dev_tokens_used += token_cost
            s.commit()
            return True

    # ── Race ─────────────────────────────────────────────────────────────────

    def get_race(self, race_id: int) -> Optional[Race]:
        with self._Session() as s:
            return s.get(Race, race_id)

    def count_completed_races(self, season_id: int) -> int:
        """Cuenta las carreras ya completadas de la temporada."""
        with self._Session() as s:
            return len(
                list(
                    s.scalars(
                        select(Race).where(
                            Race.season_id == season_id,
                            Race.is_completed == True,
                        )
                    ).all()
                )
            )

    def count_total_races(self, season_id: int) -> int:
        """Cuenta todas las carreras de la temporada."""
        with self._Session() as s:
            return len(list(s.scalars(select(Race).where(Race.season_id == season_id)).all()))

    def get_races_by_season(self, season_id: int) -> list[Race]:
        with self._Session() as s:
            return list(s.scalars(
                select(Race)
                .where(Race.season_id == season_id)
                .order_by(Race.round_number)
            ).all())

    def get_next_race(self, season_id: int) -> Optional[Race]:
        with self._Session() as s:
            return s.scalars(
                select(Race)
                .where(Race.season_id == season_id, Race.is_completed == False)
                .order_by(Race.round_number)
            ).first()

    def save_race_results(
        self,
        race_id: int,
        results: list[dict],
    ) -> None:
        """Persiste los resultados de carrera y actualiza el campeonato."""
        with self._Session() as s:
            race = s.get(Race, race_id)
            if not race:
                return
            race.is_completed = True

            for index, r in enumerate(results, start=1):
                # grid_position comes from race simulator's initial order
                grid_position = int(r.get("grid_position") or index)
                dr = DriverResult(
                    race_id         = race_id,
                    driver_id       = r["driver_id"],
                    grid_position   = grid_position,
                    finish_position = r["finish_position"],
                    points          = r["points"],
                    dnf             = r["dnf"],
                    dnf_reason      = r.get("dnf_reason"),
                    best_lap_time_s = r.get("best_lap_s"),
                    total_time_s    = r.get("total_time_s"),
                    pit_stops       = r.get("pit_stops", 0),
                )
                s.add(dr)

                # Actualizar championship del equipo
                champ = s.scalars(
                    select(Championship).where(
                        Championship.season_id == race.season_id,
                        Championship.team_id   == r["team_id"],
                    )
                ).first()
                if champ:
                    champ.points += r["points"]

            s.commit()
            self._update_championship_positions(race.season_id, s)
            s.commit()

    def _update_championship_positions(self, season_id: int, s: Session) -> None:
        champs = list(s.scalars(
            select(Championship).where(Championship.season_id == season_id)
        ).all())
        champs.sort(key=lambda c: c.points, reverse=True)
        for pos, c in enumerate(champs, start=1):
            c.position = pos

    def get_championship(self, team_id: int, season_id: int) -> Optional[Championship]:
        """Retorna la fila de campeonato de un equipo."""
        with self._Session() as s:
            return s.scalars(
                select(Championship).where(
                    Championship.team_id == team_id,
                    Championship.season_id == season_id,
                )
            ).first()

    def get_all_championships(self, season_id: int) -> list[Championship]:
        """Retorna la clasificación completa de constructores."""
        with self._Session() as s:
            return list(
                s.scalars(
                    select(Championship)
                    .where(Championship.season_id == season_id)
                    .order_by(Championship.position)
                ).all()
            )

    # ── Finance ───────────────────────────────────────────────────────────────

    def get_finance(self, team_id: int, season_id: int) -> Optional[TeamFinance]:
        with self._Session() as s:
            return s.scalars(
                select(TeamFinance).where(
                    TeamFinance.team_id  == team_id,
                    TeamFinance.season_id == season_id,
                )
            ).first()

    def get_sponsors(self, team_id: int) -> list[Sponsor]:
        """Retorna los sponsors del equipo."""
        with self._Session() as s:
            return list(s.scalars(select(Sponsor).where(Sponsor.team_id == team_id)).all())

    def add_expense(self, team_id: int, season_id: int, amount_m: float, category: str) -> None:
        """Registra un gasto en el presupuesto."""
        with self._Session() as s:
            finance = s.scalars(
                select(TeamFinance).where(
                    TeamFinance.team_id  == team_id,
                    TeamFinance.season_id == season_id,
                )
            ).first()
            if not finance:
                return
            finance.spent_m += amount_m
            if category == "development":
                finance.development_m += amount_m
            elif category == "driver_salary":
                finance.driver_salaries_m += amount_m
            elif category == "staff":
                finance.staff_salaries_m += amount_m
            elif category == "logistics":
                finance.logistics_m += amount_m
            s.commit()

    def add_income(self, team_id: int, season_id: int, amount_m: float, source: str) -> None:
        """Registra un ingreso."""
        with self._Session() as s:
            finance = s.scalars(
                select(TeamFinance).where(
                    TeamFinance.team_id  == team_id,
                    TeamFinance.season_id == season_id,
                )
            ).first()
            if not finance:
                return
            if source == "fom":
                finance.fom_prize_m += amount_m
            elif source == "sponsor":
                finance.sponsor_income_m += amount_m
            s.commit()

    # ── Conversión dominio ←→ DB ──────────────────────────────────────────────

    def load_domain_teams(self) -> list[dom.Team]:
        """Carga todos los equipos como entidades de dominio para la simulación."""
        db_teams = self.get_all_teams()
        domain_teams: list[dom.Team] = []
        for db_team in db_teams:
            components = self.get_car_components(db_team.id)
            domain_comps: dict[dom.ComponentType, dom.CarComponent] = {}
            for c in components:
                ctype = dom.ComponentType(c.component_type.value)
                import json
                sub = json.loads(c.sub_ratings) if c.sub_ratings else {}
                domain_comps[ctype] = dom.CarComponent(
                    component_type=ctype,
                    rating=c.rating,
                    reliability=c.reliability,
                    sub_ratings=sub,
                )
            car = dom.Car(team_id=db_team.id, components=domain_comps)

            db_drivers = self.get_drivers_by_team(db_team.id)
            domain_drivers: list[dom.Driver] = []
            for d in db_drivers:
                stats = dom.DriverStats(
                    pace=d.pace,
                    consistency=d.consistency,
                    tyre_management=d.tyre_management,
                    wet_skill=d.wet_skill,
                    overtaking=d.overtaking,
                    defending=d.defending,
                    starts=d.starts,
                )
                domain_drivers.append(dom.Driver(
                    id=d.id, name=d.name, number=d.number,
                    nationality=d.nationality, age=d.age,
                    stats=stats, morale=d.morale, fitness=d.fitness,
                    team_id=d.team_id,
                ))

            domain_teams.append(dom.Team(
                id=db_team.id,
                name=db_team.name,
                short_name=db_team.short_name,
                is_player=db_team.is_player,
                car=car,
                drivers=domain_drivers,
                morale=db_team.morale,
                pitstop_mean_s=db_team.pitstop_mean_s,
                pitstop_std_s=db_team.pitstop_std_s,
                ai_aggression=db_team.ai_aggression,
                ai_risk_appetite=db_team.ai_risk_appetite,
            ))
        return domain_teams
