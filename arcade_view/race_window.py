"""Arcade 2D race window fed by queue snapshots from the simulator thread."""
from __future__ import annotations

import math
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any

try:
    import arcade
except ImportError:  # pragma: no cover - optional at test time
    arcade = None


SCREEN_W = 1280
SCREEN_H = 720
TITLE = "F1 Manager - Carrera"
BG_COLOR = (10, 10, 15)
TRACK_COLOR = (40, 40, 52)
TRACK_INNER = (18, 18, 28)
HUD_COLOR = (240, 240, 245)
MUTED = (110, 110, 128)

TEAM_COLORS = [
    (232, 0, 30),
    (0, 153, 255),
    (245, 166, 35),
    (0, 212, 94),
    (204, 68, 255),
    (255, 102, 0),
    (0, 204, 204),
    (255, 204, 0),
]


@dataclass
class CarSpriteState:
    driver_id: int
    team_id: int
    color: tuple[int, int, int]
    position: int = 0
    target_x: float = 0.0
    target_y: float = 0.0
    x: float = 0.0
    y: float = 0.0
    gap_s: float = 0.0
    tyre_label: str = "M"
    fuel_kg: float = 110.0
    dnf: bool = False
    is_player: bool = False

    def ease(self, dt: float) -> None:
        self.x += (self.target_x - self.x) * min(dt * 6.0, 1.0)
        self.y += (self.target_y - self.y) * min(dt * 6.0, 1.0)


class RaceWindow(arcade.Window if arcade is not None else object):
    """Simple but real 2D race visualization for manual testing."""

    def __init__(
        self,
        data_queue: Queue,
        race_name: str,
        total_laps: int,
        track_key: str = "generic",
        player_team_id: int = 1,
    ) -> None:
        if arcade is None:
            raise RuntimeError("Arcade no esta instalado en el entorno actual")
        super().__init__(SCREEN_W, SCREEN_H, TITLE, update_rate=1 / 60)
        arcade.set_background_color(BG_COLOR)
        self.data_queue = data_queue
        self.race_name = race_name
        self.total_laps = total_laps
        self.track_key = track_key
        self.player_team_id = player_team_id
        self.current_lap = 0
        self.latest_events: list[str] = []
        self.safety_car = False
        self.weather_label = "DRY"
        self._finish_timer = 0.0
        self._finished = False
        self._cars: dict[int, CarSpriteState] = {}
        self._team_palette: dict[int, tuple[int, int, int]] = {}

    def on_update(self, delta_time: float) -> None:
        while True:
            try:
                snapshot = self.data_queue.get_nowait()
            except Empty:
                break
            else:
                self._apply_snapshot(snapshot)

        for car in self._cars.values():
            car.ease(delta_time)

        if self._finished:
            self._finish_timer += delta_time
            if self._finish_timer >= 2.0:
                arcade.close_window()

    def on_draw(self) -> None:
        self.clear()
        self._draw_track()
        self._draw_cars()
        self._draw_hud()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.ESCAPE:
            arcade.close_window()

    def _apply_snapshot(self, snapshot: Any) -> None:
        self.current_lap = int(getattr(snapshot, "lap", self.current_lap))
        self.total_laps = int(getattr(snapshot, "total_laps", self.total_laps))
        self.safety_car = bool(getattr(snapshot, "safety_car", False))

        weather = getattr(snapshot, "weather", None)
        if weather is not None:
            condition = getattr(weather, "condition", "DRY")
            self.weather_label = getattr(condition, "value", str(condition)).upper()

        events = getattr(snapshot, "events", [])
        self.latest_events = []
        for event in events[-3:]:
            event_type = getattr(event, "event_type", "event")
            detail = getattr(event, "detail", "")
            self.latest_events.append(f"{event_type.upper()} {detail}".strip())

        cars = sorted(getattr(snapshot, "cars", []), key=lambda item: getattr(item, "position", 99))
        leader_progress = ((self.current_lap - 1) + 0.92) / max(self.total_laps, 1)

        for index, car_state in enumerate(cars):
            driver_id = int(getattr(car_state, "driver_id"))
            team_id = int(getattr(car_state, "team_id"))
            car = self._cars.get(driver_id)
            if car is None:
                color = self._team_palette.setdefault(
                    team_id,
                    TEAM_COLORS[len(self._team_palette) % len(TEAM_COLORS)],
                )
                car = CarSpriteState(
                    driver_id=driver_id,
                    team_id=team_id,
                    color=color,
                    is_player=team_id == self.player_team_id,
                )
                car.x, car.y = self._track_point(index / max(len(cars), 1))
                self._cars[driver_id] = car

            gap_s = float(getattr(car_state, "gap_to_leader_s", 0.0))
            progress = (leader_progress - (gap_s / max(self.total_laps * 90.0, 1.0)) - index * 0.004) % 1.0
            target_x, target_y = self._track_point(progress)
            car.position = int(getattr(car_state, "position", index + 1))
            car.target_x = target_x
            car.target_y = target_y
            car.gap_s = gap_s
            car.fuel_kg = float(getattr(car_state, "fuel_kg", 0.0))
            tyre = getattr(car_state, "tyre", None)
            compound = getattr(tyre, "compound", "medium") if tyre is not None else "medium"
            car.tyre_label = getattr(compound, "value", str(compound))[0].upper()
            car.dnf = bool(getattr(car_state, "dnf", False))

        if self.current_lap >= self.total_laps:
            self._finished = True

    def _draw_track(self) -> None:
        cx = SCREEN_W / 2
        cy = SCREEN_H / 2 - 20
        outer_w = 860
        outer_h = 440
        inner_w = 700
        inner_h = 280
        points = 96

        outer = [self._ellipse_point(cx, cy, outer_w / 2, outer_h / 2, i / points) for i in range(points + 1)]
        inner = [self._ellipse_point(cx, cy, inner_w / 2, inner_h / 2, i / points) for i in range(points + 1)]

        for idx in range(points):
            arcade.draw_line(*outer[idx], *outer[idx + 1], TRACK_COLOR, 18)
            arcade.draw_line(*inner[idx], *inner[idx + 1], TRACK_INNER, 18)

        sx, sy = self._track_point(0.0)
        arcade.draw_line(sx - 10, sy - 18, sx - 10, sy + 18, (255, 255, 255), 3)
        arcade.draw_text("START", sx + 8, sy - 10, MUTED, 10)

    def _draw_cars(self) -> None:
        for car in sorted(self._cars.values(), key=lambda item: item.position, reverse=True):
            if car.dnf:
                arcade.draw_text("X", car.x - 5, car.y - 8, MUTED, 14, bold=True)
                continue
            arcade.draw_circle_filled(car.x + 2, car.y - 2, 8, (0, 0, 0, 100))
            arcade.draw_ellipse_filled(car.x, car.y, 18, 10, car.color)
            if car.is_player:
                arcade.draw_ellipse_outline(car.x, car.y, 22, 14, (255, 255, 255), 2)
            arcade.draw_text(str(car.position), car.x - 4, car.y - 5, (255, 255, 255), 9, bold=True)

    def _draw_hud(self) -> None:
        top = SCREEN_H - 34
        arcade.draw_text(self.race_name.upper(), 22, top, HUD_COLOR, 18, bold=True)
        arcade.draw_text(
            f"VUELTA {self.current_lap}/{self.total_laps}",
            22,
            top - 26,
            HUD_COLOR,
            14,
        )
        arcade.draw_text(f"CLIMA {self.weather_label}", 22, top - 48, MUTED, 12)
        if self.safety_car:
            arcade.draw_text("SAFETY CAR", SCREEN_W / 2 - 70, top - 10, (245, 166, 35), 18, bold=True)

        right_x = SCREEN_W - 290
        arcade.draw_text("TOP 6", right_x, top, MUTED, 11, bold=True)
        for offset, car in enumerate(sorted(self._cars.values(), key=lambda item: item.position)[:6]):
            gap_text = "LIDER" if car.position == 1 else f"+{car.gap_s:.1f}s"
            arcade.draw_text(
                f"P{car.position}  #{car.driver_id:<2}  {gap_text:<8}  {car.tyre_label}",
                right_x,
                top - 22 - offset * 18,
                HUD_COLOR if car.is_player else MUTED,
                11,
            )

        event_y = 28
        for index, event in enumerate(self.latest_events[-3:]):
            arcade.draw_text(event[:48], 22, event_y + index * 16, MUTED, 11)

        if self._finished:
            arcade.draw_lbwh_rectangle_filled((SCREEN_W / 2) - 180, (SCREEN_H / 2) - 45, 360, 90, (10, 10, 20, 220))
            arcade.draw_text("CARRERA FINALIZADA", SCREEN_W / 2 - 130, SCREEN_H / 2 + 10, HUD_COLOR, 22, bold=True)
            arcade.draw_text("Volviendo al dashboard...", SCREEN_W / 2 - 105, SCREEN_H / 2 - 18, MUTED, 12)

    def _track_point(self, progress: float) -> tuple[float, float]:
        cx = SCREEN_W / 2
        cy = SCREEN_H / 2 - 20
        rx = 390
        ry = 180 if self.track_key == "generic" else 170
        angle = (progress * math.pi * 2) - math.pi / 2
        return cx + math.cos(angle) * rx, cy + math.sin(angle) * ry

    @staticmethod
    def _ellipse_point(cx: float, cy: float, rx: float, ry: float, progress: float) -> tuple[float, float]:
        angle = (progress * math.pi * 2) - math.pi / 2
        return cx + math.cos(angle) * rx, cy + math.sin(angle) * ry


def run_race_window(
    data_queue: Queue,
    race_name: str = "Gran Premio",
    total_laps: int = 70,
    track_key: str = "generic",
    player_team_id: int = 1,
) -> None:
    """Create and run the Arcade race window until it is closed."""
    if arcade is None:
        raise RuntimeError("Arcade no esta instalado en el entorno actual")

    window = RaceWindow(
        data_queue=data_queue,
        race_name=race_name,
        total_laps=total_laps,
        track_key=track_key,
        player_team_id=player_team_id,
    )
    arcade.run()
