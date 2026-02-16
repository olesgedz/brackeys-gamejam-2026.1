extends Area3D
class_name InteractivePicture

signal interaction_started

@export var target_scene: PackedScene

var is_interactable: bool = true

func _ready() -> void:
	pass

func can_interact() -> bool:
	return is_interactable

func show_tooltip() -> void:
	var hud = get_tree().get_first_node_in_group("hud")
	if hud:
		hud.show_interaction_prompt("Взаимодействовать [E]")

func hide_tooltip() -> void:
	var hud = get_tree().get_first_node_in_group("hud")
	if hud:
		hud.hide_interaction_prompt()

func interact() -> void:
	is_interactable = false
	hide_tooltip()
	interaction_started.emit()
	
	var game_manager = get_tree().get_first_node_in_group("game_manager")
	if game_manager:
		game_manager.transition_to_picture(self)
