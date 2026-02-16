extends CanvasLayer
class_name HUD

@onready var crosshair: TextureRect = $Crosshair
@onready var interaction_label: Label = $InteractionLabel
@onready var fade_rect: ColorRect = $FadeRect

func _ready() -> void:
	add_to_group("hud")
	interaction_label.visible = false
	fade_rect.color = Color(1, 1, 1, 0)

func show_interaction_prompt(text: String) -> void:
	interaction_label.text = text
	interaction_label.visible = true

func hide_interaction_prompt() -> void:
	interaction_label.visible = false

func set_fade(value: float) -> void:
	fade_rect.color = Color(1, 1, 1, value)
