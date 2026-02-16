extends Node
class_name GameManager

@onready var main_scene: Node3D = get_tree().get_first_node_in_group("main_scene")
@onready var player: FlyingCamera = get_tree().get_first_node_in_group("player")

var minigame_scene: PackedScene = preload("res://scenes/minigame.tscn")
var current_minigame: Node = null
var current_picture: InteractivePicture = null

var player_entry_position: Vector3
var player_entry_rotation: Vector3

var transition_tween: Tween = null

func _ready() -> void:
	add_to_group("game_manager")

func transition_to_picture(picture: InteractivePicture) -> void:
	current_picture = picture
	
	# Сохраняем позицию входа
	player_entry_position = player.global_position
	player_entry_rotation = player.rotation
	
	# Отключаем управление игроком
	player.set_physics_process(false)
	player.set_process_input(false)
	
	# Получаем позицию картины
	var picture_pos = picture.global_position
	var picture_forward = -picture.global_transform.basis.z
	var target_pos = picture_pos + picture_forward * 0.5
	
	# Анимация приближения
	transition_tween = create_tween()
	transition_tween.set_ease(Tween.EASE_IN_OUT)
	transition_tween.set_trans(Tween.TRANS_CUBIC)
	
	transition_tween.tween_property(player, "global_position", target_pos, 1.0)
	transition_tween.parallel().tween_method(_fade_to_white, 0.0, 1.0, 1.0)
	
	await transition_tween.finished
	
	# Загружаем мини-игру
	_enter_minigame()

func _fade_to_white(value: float) -> void:
	var hud = get_tree().get_first_node_in_group("hud")
	if hud:
		hud.set_fade(value)

func _enter_minigame() -> void:
	# Скрываем 3D сцену
	main_scene.visible = false
	
	# Создаём мини-игру
	current_minigame = minigame_scene.instantiate()
	current_minigame.game_completed.connect(_on_minigame_completed)
	current_minigame.exit_requested.connect(_on_minigame_exit)
	get_tree().root.add_child(current_minigame)
	
	# Убираем белый экран
	_fade_to_white(0.0)
	
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func _on_minigame_completed() -> void:
	# Можно добавить особую логику при победе
	pass

func _on_minigame_exit() -> void:
	_exit_minigame()

func _exit_minigame() -> void:
	# Fade to white перед выходом
	var hud = get_tree().get_first_node_in_group("hud")
	if hud:
		hud.set_fade(1.0)
	
	if current_minigame:
		current_minigame.queue_free()
		current_minigame = null
	
	# Показываем 3D сцену
	main_scene.visible = true
	
	# Возвращаем игрока на позицию входа (выталкиваем обратно в комнату)
	player.global_position = player_entry_position
	player.rotation = player_entry_rotation
	
	# Анимация выхода — fade из белого
	transition_tween = create_tween()
	transition_tween.set_ease(Tween.EASE_OUT)
	transition_tween.set_trans(Tween.TRANS_CUBIC)
	transition_tween.tween_method(_fade_to_white, 1.0, 0.0, 0.5)
	
	# Возвращаем управление
	player.set_physics_process(true)
	player.set_process_input(true)
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	
	if current_picture:
		current_picture.is_interactable = true
		current_picture = null
