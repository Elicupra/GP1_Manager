# ============================================================
# main_menu.tscn — Jerarquía de nodos Godot 4
# Pegar en godot/scenes/main_menu/main_menu.tscn
#
# Convención: PascalCase para nodos, snake_case para variables.
# Todos los estilos se definen en el Theme del proyecto.
# ============================================================

# ÁRBOL DE NODOS
# ──────────────────────────────────────────────────────────
# MainMenu (Control) [script: main_menu.gd]
# │   anchors: full rect
# │
# ├─ BgLayer (Control)
# │   ├─ CircuitLines (TextureRect)        # textura de grilla animada
# │   ├─ BgGlow (ColorRect)               # gradiente radial rojo
# │   └─ SpeedStripe (ColorRect)          # línea diagonal animada
# │
# ├─ LeftPanel (PanelContainer)
# │   │   custom_minimum_size: (420, 0)
# │   │   size_flags_vertical: EXPAND_FILL
# │   │
# │   ├─ VBoxContainer
# │   │   ├─ LogoArea (VBoxContainer)
# │   │   │   ├─ LabelGameLabel (Label)       # "TEMPORADA 2026"
# │   │   │   ├─ LabelTeamName (Label)        # "APEX RACING"
# │   │   │   └─ LabelSeasonYear (Label)      # subtítulo
# │   │   │
# │   │   ├─ SeasonCard (PanelContainer)
# │   │   │   └─ VBoxContainer
# │   │   │       ├─ LabelSeasonTag (Label)
# │   │   │       └─ Stats (HBoxContainer)
# │   │   │           ├─ LabelChampPos (Label)
# │   │   │           ├─ LabelPoints (Label)
# │   │   │           └─ LabelRaceProgress (Label)
# │   │   │
# │   │   ├─ NextRace (VBoxContainer)
# │   │   │   ├─ LabelNextRaceTag (Label)
# │   │   │   ├─ LabelName (Label)
# │   │   │   └─ HBoxContainer
# │   │   │       ├─ LabelCircuit (Label)
# │   │   │       └─ LabelDays (Label)
# │   │   │
# │   │   ├─ Nav (VBoxContainer)
# │   │   │   ├─ BtnHome (Button)             # señal pressed → _on_nav_home()
# │   │   │   ├─ BtnCalendar (Button)
# │   │   │   ├─ BtnGarage (Button)
# │   │   │   ├─ BtnStaff (Button)
# │   │   │   ├─ BtnFinances (Button)
# │   │   │   └─ BtnSettings (Button)
# │   │   │
# │   │   └─ BottomBar (HBoxContainer)
# │   │       ├─ LabelVersion (Label)
# │   │       └─ LabelSaveTime (Label)
# │
# └─ RightPanel (Control)
#     │   size_flags_horizontal: EXPAND_FILL
#     │
#     ├─ HomeScreen (VBoxContainer)           # visible por defecto
#     │   ├─ LabelWelcomeTeam (Label)
#     │   ├─ HeroStats (GridContainer)        # columns: 2
#     │   │   ├─ CardChamp (PanelContainer)
#     │   │   │   └─ VBoxContainer
#     │   │   │       ├─ LabelChampLabel (Label)
#     │   │   │       ├─ Value (Label)        # hero number grande
#     │   │   │       └─ LabelChampSub (Label)
#     │   │   ├─ CardBudget (PanelContainer)
#     │   │   │   └─ VBoxContainer
#     │   │   │       ├─ LabelBudgetLabel (Label)
#     │   │   │       ├─ Value (Label)
#     │   │   │       └─ LabelBudgetSub (Label)
#     │   │   ├─ CardDriver (PanelContainer)
#     │   │   │   └─ VBoxContainer
#     │   │   │       ├─ LabelDriverLabel (Label)
#     │   │   │       ├─ Value (Label)
#     │   │   │       └─ LabelDriverSub (Label)
#     │   │   └─ CardReliability (PanelContainer)
#     │   │       └─ VBoxContainer
#     │   │           ├─ LabelRelLabel (Label)
#     │   │           ├─ Value (Label)
#     │   │           └─ LabelRelSub (Label)
#     │   └─ Notifications (VBoxContainer)   # poblado dinámicamente
#     │
#     ├─ CalendarScreen (VBoxContainer)      # visible: false
#     │   ├─ SubTitle (Label)
#     │   └─ OptionGrid (GridContainer)      # columns: 2
#     │       ├─ OptionCard_PrepGP (PanelContainer + VBox + Labels)
#     │       ├─ OptionCard_Results (PanelContainer + VBox + Labels)
#     │       ├─ OptionCard_FullCal (PanelContainer + VBox + Labels)
#     │       └─ OptionCard_Champs (PanelContainer + VBox + Labels)
#     │
#     ├─ GarageScreen (VBoxContainer)        # visible: false
#     │   └─ [misma estructura que CalendarScreen]
#     │
#     ├─ StaffScreen (VBoxContainer)         # visible: false
#     │   └─ [misma estructura]
#     │
#     ├─ FinancesScreen (VBoxContainer)      # visible: false
#     │   └─ [misma estructura]
#     │
#     └─ SettingsScreen (VBoxContainer)      # visible: false
#         └─ [misma estructura]

# ──────────────────────────────────────────────────────────
# NOTAS DE IMPLEMENTACIÓN
# ──────────────────────────────────────────────────────────
#
# 1. Theme del proyecto (res://theme/f1_theme.tres):
#    - Definir StyleBoxFlat para PanelContainer con bg #111118 y border #2a2a38
#    - Button normal/hover/pressed con los colores del SKILL.md
#    - Label font_color: #f0f0f5, font_color_disabled: #6b6b80
#    - Fuentes: BebasNeue.ttf, BarlowCondensed.ttf, JetBrainsMono.ttf
#      Descargar de Google Fonts, poner en res://assets/fonts/
#
# 2. Conexión de señales (en el editor o en _ready):
#    $LeftPanel/VBoxContainer/Nav/BtnHome.pressed.connect(_on_nav_home)
#    $LeftPanel/VBoxContainer/Nav/BtnCalendar.pressed.connect(_on_nav_calendar)
#    ... etc.
#
# 3. Autoload ZmqBus (res://autoload/zmq_bus.gd):
#    Gestiona la comunicación ZeroMQ con el backend Python.
#    Emite la señal: message_received(msg: Dictionary)
#    Expone el método: send_request(msg: Dictionary)
#
# 4. Dimensiones objetivo:
#    - Diseñado para 1920x1080 (fullscreen)
#    - LeftPanel: anchors left=0, top=0, right=0, bottom=1 + custom_min_size.x=420
#    - RightPanel: anchors left=0, top=0, right=1, bottom=1 (SIZE_EXPAND_FILL)
