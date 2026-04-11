# ============================================================
# main_menu.gd — Menú Principal F1 Manager
# Nodo raíz: Control (MainMenu)
# Recibe estado inicial via ZeroMQ REQ al arrancar.
# ============================================================
extends Control

# ── Señales ─────────────────────────────────────────────────
signal nav_requested(section: String)

# ── Referencias a nodos (asignar en editor) ──────────────────
@onready var label_team_name    : Label = $LeftPanel/LogoArea/LabelTeamName
@onready var label_season_year  : Label = $LeftPanel/LogoArea/LabelSeasonYear
@onready var label_champ_pos    : Label = $LeftPanel/SeasonCard/Stats/LabelChampPos
@onready var label_points       : Label = $LeftPanel/SeasonCard/Stats/LabelPoints
@onready var label_race_progress: Label = $LeftPanel/SeasonCard/Stats/LabelRaceProgress
@onready var label_next_race    : Label = $LeftPanel/NextRace/LabelName
@onready var label_next_circuit : Label = $LeftPanel/NextRace/LabelCircuit
@onready var label_next_days    : Label = $LeftPanel/NextRace/LabelDays
@onready var label_save_time    : Label = $LeftPanel/BottomBar/LabelSaveTime

# Hero stats (panel derecho)
@onready var label_hero_champ   : Label = $RightPanel/HomeScreen/HeroStats/CardChamp/Value
@onready var label_hero_budget  : Label = $RightPanel/HomeScreen/HeroStats/CardBudget/Value
@onready var label_hero_driver  : Label = $RightPanel/HomeScreen/HeroStats/CardDriver/Value
@onready var label_hero_reliability: Label = $RightPanel/HomeScreen/HeroStats/CardReliability/Value

# Notificaciones
@onready var notif_container    : VBoxContainer = $RightPanel/HomeScreen/Notifications

# Contenedores de pantalla
@onready var screen_home        : Control = $RightPanel/HomeScreen
@onready var screens            : Dictionary = {}

# Nav buttons
@onready var nav_buttons        : Array = []

# ZeroMQ (usa el singleton ZmqBus del proyecto)
# Ver: autoload/zmq_bus.gd
var _zmq : Node
var _using_mock_data := false

# ── Estado interno ───────────────────────────────────────────
var _current_section := "home"

# ────────────────────────────────────────────────────────────
func _ready() -> void:
	if has_node("/root/ZmqBus"):
		_zmq = get_node("/root/ZmqBus")
		_zmq.message_received.connect(_on_zmq_message)

	# Registrar pantallas de sub-secciones
	screens = {
		"home":     $RightPanel/HomeScreen,
		"calendar": $RightPanel/CalendarScreen,
		"garage":   $RightPanel/GarageScreen,
		"staff":    $RightPanel/StaffScreen,
		"finances": $RightPanel/FinancesScreen,
		"settings": $RightPanel/SettingsScreen,
	}

	# Registrar botones de navegación
	nav_buttons = [
		$LeftPanel/Nav/BtnHome,
		$LeftPanel/Nav/BtnCalendar,
		$LeftPanel/Nav/BtnGarage,
		$LeftPanel/Nav/BtnStaff,
		$LeftPanel/Nav/BtnFinances,
		$LeftPanel/Nav/BtnSettings,
	]

	_show_screen("home")
	_connect_nav_buttons()
	_request_initial_state()
	_animate_entrance()

# ── Petición de estado al backend ───────────────────────────
func _request_initial_state() -> void:
	if is_instance_valid(_zmq):
		_zmq.send_request({"type": "get_menu_state"})
		return

	_using_mock_data = true
	_update_display(_build_mock_state())

# ── Recepción de mensajes ZeroMQ ─────────────────────────────
func _on_zmq_message(msg: Dictionary) -> void:
	match msg.get("type", ""):
		"menu_state":
			_update_display(msg)
		"notification":
			_add_notification(msg)
		"save_confirmed":
			label_save_time.text = "Guardado hace un momento"

# ── Actualizar toda la UI con datos del backend ──────────────
func _update_display(data: Dictionary) -> void:
	# Identidad del equipo
	var team: Dictionary = data.get("team", {})
	var season: Dictionary = data.get("season", {})
	label_team_name.text   = team.get("name", "---")
	label_season_year.text = "Temporada %d" % season.get("year", 0)

	# Campeonato
	var champ: Dictionary = data.get("championship", {})
	label_champ_pos.text        = "%dº" % champ.get("position", 0)
	label_points.text           = str(champ.get("points", 0))
	var race_cur: int = season.get("race_current", 0)
	var race_tot: int = season.get("race_total", 0)
	label_race_progress.text    = "%d/%d" % [race_cur, race_tot]

	# Próxima carrera
	var nr: Dictionary = data.get("next_race", {})
	label_next_race.text    = nr.get("name", "---")
	label_next_circuit.text = nr.get("circuit", "---")
	label_next_days.text    = "%d días" % nr.get("days_until", 0)

	# Hero stats
	label_hero_champ.text = "%dº" % champ.get("position", 0)

	var budget: Dictionary = data.get("budget", {})
	var avail_m: float = float(budget.get("available", 0)) / 1_000_000.0
	label_hero_budget.text = "%.0fM" % avail_m

	var drivers: Array = data.get("drivers", [])
	if drivers.size() > 0:
		var d0: Dictionary = drivers[0]
		label_hero_driver.text = "P%d" % d0.get("championship_pos", 0)

	var car: Dictionary = data.get("car", {})
	var rel: float = float(car.get("avg_reliability", 0)) * 100.0
	label_hero_reliability.text = "%.0f%%" % rel

	# Notificaciones
	var notifs: Array = data.get("notifications", [])
	_populate_notifications(notifs)

	# Guardar timestamp
	var save_info: Dictionary = data.get("save", {})
	label_save_time.text = save_info.get("last_saved", "---")

# ── Notificaciones ───────────────────────────────────────────
func _populate_notifications(notifs: Array) -> void:
	# Limpiar contenedor
	for child in notif_container.get_children():
		child.queue_free()

	for i in range(min(notifs.size(), 3)):
		var n: Dictionary = notifs[i]
		var row := _build_notif_row(n)
		notif_container.add_child(row)
		# Animación de entrada escalonada
		var tween := create_tween()
		row.modulate.a = 0.0
		tween.tween_property(row, "modulate:a", 1.0, 0.3).set_delay(i * 0.08)

func _add_notification(n: Dictionary) -> void:
	var row := _build_notif_row(n)
	notif_container.add_child(row)
	notif_container.move_child(row, 0)
	var tween := create_tween()
	row.modulate.a = 0.0
	tween.tween_property(row, "modulate:a", 1.0, 0.3)

func _build_notif_row(n: Dictionary) -> PanelContainer:
	var row    := PanelContainer.new()
	var hbox   := HBoxContainer.new()
	var dot    := ColorRect.new()
	var label  := RichTextLabel.new()
	var time_l := Label.new()

	dot.custom_minimum_size = Vector2(6, 6)
	dot.color = Color(n.get("color", "#6b6b80"))

	label.bbcode_enabled = true
	label.text = "[b]%s[/b] %s" % [n.get("title", ""), n.get("body", "")]
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	label.fit_content = true

	time_l.text = n.get("time_label", "")

	hbox.add_child(dot)
	hbox.add_child(label)
	hbox.add_child(time_l)
	row.add_child(hbox)
	return row

func _connect_nav_buttons() -> void:
	var handlers := [
		Callable(self, "_on_nav_home"),
		Callable(self, "_on_nav_calendar"),
		Callable(self, "_on_nav_garage"),
		Callable(self, "_on_nav_staff"),
		Callable(self, "_on_nav_finances"),
		Callable(self, "_on_nav_settings"),
	]

	for i in range(min(nav_buttons.size(), handlers.size())):
		var button: Button = nav_buttons[i] as Button
		if not is_instance_valid(button):
			continue
		var handler: Callable = handlers[i]
		if not button.pressed.is_connected(handler):
			button.pressed.connect(handler)

func _build_mock_state() -> Dictionary:
	return {
		"type": "menu_state",
		"team": {
			"name": "Apex Racing",
		},
		"season": {
			"year": 2026,
			"race_current": 8,
			"race_total": 24,
		},
		"championship": {
			"position": 3,
			"points": 187,
			"gap_to_leader": 42,
		},
		"next_race": {
			"name": "Grand Prix de Montreal",
			"circuit": "Circuit Gilles Villeneuve",
			"days_until": 12,
		},
		"budget": {
			"available": 47_000_000,
		},
		"drivers": [
			{
				"name": "K. Hartmann",
				"championship_pos": 3,
			},
			{
				"name": "R. Vasquez",
				"championship_pos": 7,
			},
		],
		"car": {
			"avg_reliability": 0.96,
		},
		"save": {
			"last_saved": "Guardado local · mock",
		},
		"notifications": [
			{
				"title": "Contrato de R. Vasquez",
				"body": "expira al final de temporada. Negociacion pendiente de respuesta.",
				"time_label": "HOY",
				"color": "#f5a623",
			},
			{
				"title": "Actualizacion de motor",
				"body": "disponible. Coste estimado: 8.2M. Requiere homologacion.",
				"time_label": "2D",
				"color": "#0099ff",
			},
			{
				"title": "Simulacion de Montreal",
				"body": "completada. Ritmo proyectado: P3-P4 en clasificacion.",
				"time_label": "3D",
				"color": "#00d45e",
			},
		],
	}

# ── Navegación ───────────────────────────────────────────────

# Llamado por cada Button de navegación via señal pressed
func _on_nav_home()     -> void: _show_screen("home")
func _on_nav_calendar() -> void: _show_screen("calendar")
func _on_nav_garage()   -> void: _show_screen("garage")
func _on_nav_staff()    -> void: _show_screen("staff")
func _on_nav_finances() -> void: _show_screen("finances")
func _on_nav_settings() -> void: _show_screen("settings")

func _show_screen(section: String) -> void:
	_current_section = section

	# Ocultar todas
	for key in screens:
		screens[key].visible = false

	# Mostrar la activa con fade
	var target: Control = screens.get(section) as Control
	if is_instance_valid(target):
		target.visible = true
		target.modulate.a = 0.0
		var tween := create_tween()
		tween.tween_property(target, "modulate:a", 1.0, 0.25)

	# Actualizar estado visual de botones de nav
	_update_nav_state(section)

	# Notificar al backend qué sección está activa (opcional)
	nav_requested.emit(section)

func _update_nav_state(active: String) -> void:
	var sections: Array[String] = ["home","calendar","garage","staff","finances","settings"]
	for i in range(sections.size()):
		if i >= nav_buttons.size():
			continue
		var btn: Button = nav_buttons[i] as Button
		if not is_instance_valid(btn):
			continue
		# Aplica theme override o clase visual según si es el activo
		var is_active := sections[i] == active
		btn.set_meta("active", is_active)
		btn.disabled = is_active
		# El Theme del proyecto debe definir los estilos active/inactive

# ── Animación de entrada ─────────────────────────────────────
func _animate_entrance() -> void:
	var tween := create_tween().set_parallel(true)

	# Panel izquierdo: desliza desde la izquierda
	var left := $LeftPanel
	left.position.x -= 24
	left.modulate.a  = 0.0
	tween.tween_property(left, "position:x", left.position.x + 24, 0.6)\
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tween.tween_property(left, "modulate:a", 1.0, 0.5)

	# Panel derecho: fade
	var right := $RightPanel
	right.modulate.a = 0.0
	tween.tween_property(right, "modulate:a", 1.0, 0.7).set_delay(0.2)
