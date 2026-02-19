extends CanvasLayer
## Pause menu - показывается по Escape

@onready var panel: PanelContainer = $Panel

var is_paused: bool = false


func _ready() -> void:
	hide()
	process_mode = Node.PROCESS_MODE_ALWAYS


func _input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		toggle_pause()


func toggle_pause() -> void:
	is_paused = !is_paused
	if is_paused:
		show()
		get_tree().paused = true
		Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	else:
		hide()
		get_tree().paused = false
		Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)


func _on_back_pressed() -> void:
	toggle_pause()


func _on_exit_pressed() -> void:
	get_tree().paused = false
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	get_tree().change_scene_to_file("res://src/ui/main_menu.tscn")
