extends Node3D

@export var transition_time := 0.6
@export var zoom_fov := 40.0
@export var ray_length := 1000.0

#@onready var area: Area3D = $InteractionArea
@onready var screen_mesh: MeshInstance3D = $MeshInstance3D
@onready var camera_target: Marker3D = $CameraAnchor
@onready var subviewport: SubViewport = $SubViewport
@onready var player: FlyingCamera = $"../Player"
var player_body: Node = null
var player_camera: Camera3D = null

var player_inside := false
var active := false

var original_transform: Transform3D
var original_fov: float

func _ready():
	# Required for keyboard input forwarding
	subviewport.handle_input_locally = false
	player_camera = player.get_node("Camera3D")


func _unhandled_input(event):
	# Enter
	if event.is_action_pressed("interact"):
		enter_terminal()
		return

	# Exit
	#if active and event.is_action_pressed("exit_terminal"):
		#exit_terminal()
		#return

	# Forward input when active
	if active:
		forward_keyboard(event)
		forward_mouse(event)

# -------------------------
# ENTER / EXIT
# -------------------------

func enter_terminal():
	if active:
		return

	active = true

	original_transform = player_camera.global_transform
	original_fov = player_camera.fov

	#if player_body.has_method("disable_movement"):
		#player_body.disable_movement()

	var tween = create_tween()
	tween.set_ease(Tween.EASE_IN_OUT)
	tween.set_trans(Tween.TRANS_CUBIC)

	tween.tween_property(
		player_camera,
		"global_transform",
		camera_target.global_transform,
		transition_time
	)

	tween.parallel().tween_property(
		player_camera,
		"fov",
		zoom_fov,
		transition_time
	)

	tween.finished.connect(_on_enter_finished)

func _on_enter_finished():
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)

func exit_terminal():
	if not active:
		return

	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

	var tween = create_tween()
	tween.set_ease(Tween.EASE_IN_OUT)
	tween.set_trans(Tween.TRANS_CUBIC)

	tween.tween_property(
		player_camera,
		"global_transform",
		original_transform,
		transition_time
	)

	tween.parallel().tween_property(
		player_camera,
		"fov",
		original_fov,
		transition_time
	)

	tween.finished.connect(_on_exit_finished)

func _on_exit_finished():
	active = false

	if player_body and player_body.has_method("enable_movement"):
		player_body.enable_movement()

# -------------------------
# INPUT FORWARDING
# -------------------------

func forward_keyboard(event):
	if event is InputEventKey:
		subviewport.push_input(event)

func forward_mouse(event):
	if not (event is InputEventMouseButton or event is InputEventMouseMotion):
		return

	var mouse_pos = get_viewport().get_mouse_position()

	var from = player_camera.project_ray_origin(mouse_pos)
	var to = from + player_camera.project_ray_normal(mouse_pos) * ray_length

	var query = PhysicsRayQueryParameters3D.create(from, to)
	query.collide_with_areas = false
	query.collide_with_bodies = true

	var result = get_world_3d().direct_space_state.intersect_ray(query)
	print("Result: ", result)  # Print the whole result to see what's available

	if result and result.get("collider") == screen_mesh.get_node("StaticBody3D"):
		#if result.has("uv"):
			#var uv = result["uv"]  # Access uv from dictionary
			#var viewport_size = subviewport.siz
			#var local_pos = Vector2(uv.x * viewport_size.x, (1.0 - uv.y) * viewport_size.y)
			push_mouse_event(event, mouse_pos)
		#else:
			#print("No UV data in ray intersection result")

func push_mouse_event(event, pos: Vector2):
	var new_event

	if event is InputEventMouseButton:
		new_event = InputEventMouseButton.new()
		new_event.button_index = event.button_index
		new_event.pressed = event.pressed
		new_event.double_click = event.double_click
		new_event.position = pos

	elif event is InputEventMouseMotion:
		new_event = InputEventMouseMotion.new()
		new_event.position = pos
		new_event.relative = event.relative

	subviewport.push_input(new_event)
