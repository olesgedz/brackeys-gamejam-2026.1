extends CharacterBody3D
class_name FlyingCamera

@export var move_speed: float = 5.0
@export var mouse_sensitivity: float = 0.002
@export var interaction_distance: float = 3.0
@export var jump_velocity: float = 4.0


@onready var camera: Camera3D = $Camera3D
@onready var raycast: RayCast3D = $Camera3D/RayCast3D

var current_interactable: Node = null
var can_move: bool = true

var gravity = ProjectSettings.get_setting("physics/3d/default_gravity")

func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * mouse_sensitivity)
		camera.rotate_x(-event.relative.y * mouse_sensitivity)
		camera.rotation.x = clamp(camera.rotation.x, -PI/2, PI/2)
	
	if event.is_action_pressed("interact") and current_interactable:
		current_interactable.interact()
	
	if event.is_action_pressed("ui_cancel"):
		if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		else:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _physics_process(_delta: float) -> void:
	if not is_on_floor():
		print("fall")
		velocity.y -= gravity * _delta
	## Get the input direction and handle the movement/deceleration.
	## As good practice, you should replace UI actions with custom gameplay actions.
	#var input_dir = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	#var direction = (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
	#if direction:
		#motion_velocity.x = direction.x * SPEED
		#motion_velocity.z = direction.z * SPEED
	#else:
		#motion_velocity.x = move_toward(motion_velocity.x, 0, SPEED)
		#motion_velocity.z = move_toward(motion_velocity.z, 0, SPEED)
	if is_on_floor() and can_move:
		var input_dir := Vector3.ZERO
		if Input.is_action_pressed("move_forward"):
			input_dir -= transform.basis.z
		if Input.is_action_pressed("move_back"):
			input_dir += transform.basis.z
		if Input.is_action_pressed("move_left"):
			input_dir -= transform.basis.x
		if Input.is_action_pressed("move_right"):
			input_dir += transform.basis.x
		if Input.is_action_pressed("move_up"):
			velocity.y = jump_velocity
		if Input.is_action_pressed("move_down"):
			input_dir -= Vector3.UP
		
		input_dir = input_dir.normalized()
		velocity = input_dir * move_speed
	move_and_slide()
	_check_interactable()


func  disable_movement():
	can_move = false

func  enable_movement():
	can_move = true

func _check_interactable() -> void:
	if raycast.is_colliding():
		var collider = raycast.get_collider()
		# Check collider or its parent for interactable methods
		var interactable = _get_interactable(collider)
		if interactable:
			var distance = global_position.distance_to(raycast.get_collision_point())
			if distance <= interaction_distance and interactable.can_interact():
				if current_interactable != interactable:
					if current_interactable:
						current_interactable.hide_tooltip()
					current_interactable = interactable
					current_interactable.show_tooltip()
				return
	
	if current_interactable:
		current_interactable.hide_tooltip()
		current_interactable = null


func _get_interactable(node: Node) -> Node:
	# Check node itself
	if node and node.has_method("can_interact"):
		return node
	# Check parent (for Area3D children of interactables)
	if node and node.get_parent() and node.get_parent().has_method("can_interact"):
		return node.get_parent()
	return null
