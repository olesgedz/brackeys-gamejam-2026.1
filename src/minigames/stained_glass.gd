extends Node2D
class_name StainedGlass

signal puzzle_completed

## Configuration
@export var fragment_textures: Array[Texture2D] = []
@export var snap_distance: float = 30.0
@export var frame_size: Vector2 = Vector2(300, 400)
@export var frame_position: Vector2 = Vector2(50, 50)
@export var scatter_area: Rect2 = Rect2(400, 50, 300, 400)

## Internal state
var fragments: Array[FragmentPiece] = []
var placed_count: int = 0
var total_pieces: int = 0
var is_complete: bool = false
var dragged_fragment: FragmentPiece = null  # Only one at a time!

## Node references
@onready var frame_container: Node2D = $FrameContainer
@onready var fragments_container: Node2D = $FragmentsContainer
@onready var targets_container: Node2D = $TargetsContainer

## Placeholder colors for testing
const PLACEHOLDER_COLORS: Array[Color] = [
	Color(0.8, 0.2, 0.2, 0.85),  # Red
	Color(0.2, 0.6, 0.9, 0.85),  # Blue
	Color(0.2, 0.8, 0.3, 0.85),  # Green
	Color(0.9, 0.8, 0.2, 0.85),  # Yellow
	Color(0.7, 0.3, 0.8, 0.85),  # Purple
	Color(0.9, 0.5, 0.2, 0.85),  # Orange
	Color(0.3, 0.8, 0.8, 0.85),  # Cyan
]

func _ready() -> void:
	setup_puzzle()


func setup_puzzle() -> void:
	_clear_all()
	_create_fragments()
	_scatter_fragments()


func _clear_all() -> void:
	for child in fragments_container.get_children():
		child.queue_free()
	for child in targets_container.get_children():
		child.queue_free()
	fragments.clear()
	placed_count = 0
	is_complete = false
	dragged_fragment = null


func _create_fragments() -> void:
	var use_textures = fragment_textures.size() > 0
	var piece_count = fragment_textures.size() if use_textures else PLACEHOLDER_COLORS.size()
	total_pieces = mini(piece_count, 7)  # Cap at 7 pieces
	
	# Calculate grid layout for target positions
	var cols = 3
	var rows = ceili(float(total_pieces) / cols)
	var cell_width = frame_size.x / cols
	var cell_height = frame_size.y / rows
	var piece_size = Vector2(cell_width * 0.8, cell_height * 0.8)
	
	for i in range(total_pieces):
		var row = i / cols
		var col = i % cols
		
		# Target position within frame
		var target_pos = frame_position + Vector2(
			col * cell_width + cell_width / 2,
			row * cell_height + cell_height / 2
		)
		
		# Create fragment piece
		var fragment: FragmentPiece
		if use_textures and i < fragment_textures.size():
			fragment = _create_textured_fragment(i, fragment_textures[i], target_pos, piece_size)
		else:
			fragment = _create_placeholder_fragment(i, PLACEHOLDER_COLORS[i], target_pos, piece_size)
		
		fragments_container.add_child(fragment)
		fragments.append(fragment)
		
		# Create target indicator
		_create_target_indicator(target_pos, piece_size, i)


func _create_textured_fragment(index: int, texture: Texture2D, target: Vector2, size: Vector2) -> FragmentPiece:
	var fragment = FragmentPiece.new()
	fragment.name = "Fragment_%d" % index
	fragment.target_position = target
	fragment.snap_distance = snap_distance
	fragment.set_texture(texture, size)
	return fragment


func _create_placeholder_fragment(index: int, color: Color, target: Vector2, size: Vector2) -> FragmentPiece:
	var fragment = FragmentPiece.new()
	fragment.name = "Fragment_%d" % index
	fragment.target_position = target
	fragment.snap_distance = snap_distance
	fragment.set_placeholder(color, size)
	return fragment


func _create_target_indicator(pos: Vector2, size: Vector2, index: int) -> void:
	var indicator = ColorRect.new()
	indicator.name = "Target_%d" % index
	indicator.size = size
	indicator.position = pos - size / 2
	indicator.color = Color(1, 1, 1, 0.15)
	indicator.visible = false  # Hidden by default
	targets_container.add_child(indicator)


func _scatter_fragments() -> void:
	for fragment in fragments:
		if not fragment.is_placed:
			var random_pos = Vector2(
				randf_range(scatter_area.position.x, scatter_area.position.x + scatter_area.size.x),
				randf_range(scatter_area.position.y, scatter_area.position.y + scatter_area.size.y)
			)
			fragment.position = random_pos


## Input handling - single drag at a time
func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_try_pick_fragment()
		else:
			_release_fragment()
	
	elif event is InputEventMouseMotion and dragged_fragment:
		dragged_fragment.position = get_local_mouse_position() + dragged_fragment.drag_offset


func _try_pick_fragment() -> void:
	if dragged_fragment:
		return
	
	var mouse_pos = get_local_mouse_position()
	
	# Find topmost fragment under cursor (reverse order = top first)
	for i in range(fragments.size() - 1, -1, -1):
		var fragment = fragments[i]
		if fragment.is_point_inside(mouse_pos):
			_start_drag(fragment, mouse_pos)
			return


func _start_drag(fragment: FragmentPiece, mouse_pos: Vector2) -> void:
	dragged_fragment = fragment
	fragment.drag_offset = fragment.position - mouse_pos
	fragment.z_index = 100
	
	if fragment.is_placed:
		fragment.is_placed = false
		placed_count = maxi(0, placed_count - 1)


func _release_fragment() -> void:
	if not dragged_fragment:
		return
	
	var fragment = dragged_fragment
	dragged_fragment = null
	fragment.z_index = 0
	
	# Try to snap
	var distance = fragment.position.distance_to(fragment.target_position)
	if distance <= snap_distance and not fragment.is_placed:
		fragment.snap_to_target()
		placed_count += 1
		_check_win()


func _check_win() -> void:
	if placed_count >= total_pieces and not is_complete:
		is_complete = true
		puzzle_completed.emit()


## Public API

func get_placed_count() -> int:
	return placed_count


func get_total_pieces() -> int:
	return total_pieces


func show_targets(visible: bool) -> void:
	for child in targets_container.get_children():
		child.visible = visible


func auto_solve() -> void:
	for fragment in fragments:
		if not fragment.is_placed:
			fragment.snap_to_target()
			placed_count += 1
	_check_win()


func reset_puzzle() -> void:
	for fragment in fragments:
		fragment.is_placed = false
	placed_count = 0
	is_complete = false
	dragged_fragment = null
	_scatter_fragments()


## =========================================================================
## FragmentPiece - Draggable piece (input handled by parent)
## =========================================================================
class FragmentPiece extends Node2D:
	var target_position: Vector2 = Vector2.ZERO
	var snap_distance: float = 30.0
	var is_placed: bool = false
	var drag_offset: Vector2 = Vector2.ZERO
	var piece_size: Vector2 = Vector2(60, 80)
	
	var visual: ColorRect
	var sprite: Sprite2D
	var glow_rect: ColorRect
	var use_texture: bool = false
	
	func set_placeholder(color: Color, size: Vector2) -> void:
		piece_size = size
		use_texture = false
		
		# Border
		var border = ColorRect.new()
		border.size = size + Vector2(4, 4)
		border.position = -size / 2 - Vector2(2, 2)
		border.color = Color(0.2, 0.2, 0.2, 1)
		add_child(border)
		
		# Main visual
		visual = ColorRect.new()
		visual.size = size
		visual.position = -size / 2
		visual.color = color
		add_child(visual)
		
		# Glow overlay (hidden by default)
		glow_rect = ColorRect.new()
		glow_rect.size = size + Vector2(8, 8)
		glow_rect.position = -size / 2 - Vector2(4, 4)
		glow_rect.color = Color(1, 1, 1, 0.5)
		glow_rect.visible = false
		glow_rect.z_index = -1
		add_child(glow_rect)
	
	func set_texture(texture: Texture2D, size: Vector2) -> void:
		piece_size = size
		use_texture = true
		
		sprite = Sprite2D.new()
		sprite.texture = texture
		sprite.scale = size / texture.get_size()
		add_child(sprite)
		
		# Glow overlay
		glow_rect = ColorRect.new()
		glow_rect.size = size + Vector2(8, 8)
		glow_rect.position = -size / 2 - Vector2(4, 4)
		glow_rect.color = Color(1, 1, 0.7, 0.6)
		glow_rect.visible = false
		glow_rect.z_index = -1
		add_child(glow_rect)
	
	func is_point_inside(point: Vector2) -> bool:
		var local = point - position
		var half = piece_size / 2
		return local.x >= -half.x and local.x <= half.x and local.y >= -half.y and local.y <= half.y
	
	func snap_to_target() -> void:
		position = target_position
		is_placed = true
		_play_snap_effect()
	
	func _play_snap_effect() -> void:
		if glow_rect:
			glow_rect.visible = true
		
		var original_scale = scale
		var tween = create_tween()
		tween.tween_property(self, "scale", original_scale * 1.1, 0.1)
		tween.tween_property(self, "scale", original_scale, 0.1)
		tween.tween_callback(func(): 
			if glow_rect:
				glow_rect.visible = false
		)
