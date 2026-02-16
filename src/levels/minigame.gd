extends Control
class_name Minigame

signal game_completed
signal exit_requested

@onready var win_label: Label = $WinLabel
@onready var colored_square: Button = $ColoredSquare

func _ready() -> void:
	win_label.visible = false
	colored_square.pressed.connect(_on_square_pressed)

func _input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		exit_requested.emit()

func _on_square_pressed() -> void:
	win_label.visible = true
	colored_square.disabled = true
	game_completed.emit()
