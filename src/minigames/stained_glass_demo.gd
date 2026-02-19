extends Control
class_name StainedGlassDemo
## Demo wrapper for StainedGlass puzzle with debug UI

@onready var puzzle: StainedGlass = $SubViewportContainer/SubViewport/StainedGlass
@onready var pieces_label: Label = $DebugUI/PiecesLabel
@onready var show_targets_btn: Button = $DebugUI/ShowTargetsBtn
@onready var auto_solve_btn: Button = $DebugUI/AutoSolveBtn
@onready var reset_btn: Button = $DebugUI/ResetBtn
@onready var win_label: Label = $WinLabel

var showing_targets: bool = false


func _ready() -> void:
	show_targets_btn.pressed.connect(_on_show_targets_pressed)
	auto_solve_btn.pressed.connect(_on_auto_solve_pressed)
	reset_btn.pressed.connect(_on_reset_pressed)
	puzzle.puzzle_completed.connect(_on_puzzle_completed)
	_update_ui()


func _process(_delta: float) -> void:
	_update_ui()


func _update_ui() -> void:
	pieces_label.text = "Pieces: %d / %d" % [puzzle.get_placed_count(), puzzle.get_total_pieces()]


func _on_show_targets_pressed() -> void:
	showing_targets = not showing_targets
	puzzle.show_targets(showing_targets)
	show_targets_btn.text = "Hide Targets" if showing_targets else "Show Targets"


func _on_auto_solve_pressed() -> void:
	puzzle.auto_solve()


func _on_reset_pressed() -> void:
	puzzle.reset_puzzle()
	win_label.visible = false


func _on_puzzle_completed() -> void:
	win_label.visible = true
