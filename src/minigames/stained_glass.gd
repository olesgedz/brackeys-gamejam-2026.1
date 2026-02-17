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
var showing_targets: bool = false

## Node references
@onready var frame_container: Node2D = $FrameContainer
@onready var fragments_container: Node2D = $FragmentsContainer
@onready var targets_container: Node2D = $TargetsContainer
@onready var debug_ui: Control = $DebugUI
@onready var pieces_label: Label = $DebugUI/PiecesLabel
@onready var show_targets_btn: Button = $DebugUI/ShowTargetsBtn
@onready var auto_solve_btn: Button = $DebugUI/AutoSolveBtn
@onready var reset_btn: Button = $DebugUI/ResetBtn
@onready var win_label: Label = $WinLabel

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
	_setup_debug_ui()
	_setup_puzzle()

func _setup_debug_ui() -> void:
	show_targets_btn.pressed.connect(_on_show_targets_pressed)
	auto_solve_btn.pressed.connect(_on_auto_solve_pressed)
	reset_btn.pressed.connect(_on_reset_pressed)
	_update_pieces_label()

func _setup_puzzle() -> void:
	_clear_all()
	_draw_frame()
	_create_fragments()
	_scatter_fragments()
	_update_pieces_label()

func _clear_all() -> void:
	for child in fragments_container.get_children():
		child.queue_free()
	for child in targets_container.get_children():
		child.queue_free()
	fragments.clear()
	placed_count = 0
	is_complete = false
	if win_label:
		win_label.visible = false

func _draw_frame() -> void:
	# Frame is drawn via _draw() in FrameContainer
	frame_container.queue_redraw()

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
	fragment.placed.connect(_on_fragment_placed)
	fragment.picked_up.connect(_on_fragment_picked_up)
	return fragment

func _create_placeholder_fragment(index: int, color: Color, target: Vector2, size: Vector2) -> FragmentPiece:
	var fragment = FragmentPiece.new()
	fragment.name = "Fragment_%d" % index
	fragment.target_position = target
	fragment.snap_distance = snap_distance
	fragment.set_placeholder(color, size)
	fragment.placed.connect(_on_fragment_placed)
	fragment.picked_up.connect(_on_fragment_picked_up)
	return fragment

func _create_target_indicator(pos: Vector2, size: Vector2, index: int) -> void:
	var indicator = ColorRect.new()
	indicator.name = "Target_%d" % index
	indicator.size = size
	indicator.position = pos - size / 2
	indicator.color = Color(1, 1, 1, 0.15)
	indicator.visible = showing_targets
	targets_container.add_child(indicator)

func _scatter_fragments() -> void:
	for fragment in fragments:
		if not fragment.is_placed:
			var random_pos = Vector2(
				randf_range(scatter_area.position.x, scatter_area.position.x + scatter_area.size.x),
				randf_range(scatter_area.position.y, scatter_area.position.y + scatter_area.size.y)
			)
			fragment.position = random_pos

func _on_fragment_placed(fragment: FragmentPiece) -> void:
	placed_count += 1
	_update_pieces_label()
	_check_win()

func _on_fragment_picked_up(fragment: FragmentPiece) -> void:
	if fragment.is_placed:
		fragment.is_placed = false
		placed_count = maxi(0, placed_count - 1)
		_update_pieces_label()

func _check_win() -> void:
	if placed_count >= total_pieces and not is_complete:
		is_complete = true
		if win_label:
			win_label.visible = true
		puzzle_completed.emit()

func _update_pieces_label() -> void:
	if pieces_label:
		pieces_label.text = "Pieces: %d / %d" % [placed_count, total_pieces]

## Debug UI handlers

func _on_show_targets_pressed() -> void:
	showing_targets = not showing_targets
	for child in targets_container.get_children():
		child.visible = showing_targets
	show_targets_btn.text = "Hide Targets" if showing_targets else "Show Targets"

func _on_auto_solve_pressed() -> void:
	for fragment in fragments:
		if not fragment.is_placed:
			fragment.snap_to_target()
			placed_count += 1
	_update_pieces_label()
	_check_win()

func _on_reset_pressed() -> void:
	for fragment in fragments:
		fragment.is_placed = false
	placed_count = 0
	is_complete = false
	if win_label:
		win_label.visible = false
	_scatter_fragments()
	_update_pieces_label()

## Public API

func reset_puzzle() -> void:
	_on_reset_pressed()

func load_textures(textures: Array[Texture2D]) -> void:
	fragment_textures = textures
	_setup_puzzle()


## FragmentPiece - Inner class for draggable pieces
class FragmentPiece extends Node2D:
	signal placed(fragment: FragmentPiece)
	signal picked_up(fragment: FragmentPiece)
	
	var target_position: Vector2 = Vector2.ZERO
	var snap_distance: float = 30.0
	var is_placed: bool = false
	var is_dragging: bool = false
	var drag_offset: Vector2 = Vector2.ZERO
	var piece_size: Vector2 = Vector2(60, 80)
	
	var visual: ColorRect
	var sprite: Sprite2D
	var glow_rect: ColorRect
	var use_texture: bool = false
	
	func _ready() -> void:
		z_index = 0
	
	func set_placeholder(color: Color, size: Vector2) -> void:
		piece_size = size
		use_texture = false
		
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
		
		# Border effect
		var border = ColorRect.new()
		border.size = size
		border.position = -size / 2
		border.color = Color(0.2, 0.2, 0.2, 1)
		border.z_index = -1
		border.size += Vector2(4, 4)
		border.position -= Vector2(2, 2)
		add_child(border)
		border.move_to_front()
		visual.move_to_front()
	
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
	
	func _input(event: InputEvent) -> void:
		if event is InputEventMouseButton:
			if event.button_index == MOUSE_BUTTON_LEFT:
				if event.pressed:
					if _is_mouse_over():
						is_dragging = true
						drag_offset = position - get_global_mouse_position()
						z_index = 100  # Bring to front while dragging
						if is_placed:
							picked_up.emit(self)
				else:
					if is_dragging:
						is_dragging = false
						z_index = 0
						_try_snap()
		
		if event is InputEventMouseMotion and is_dragging:
			position = get_global_mouse_position() + drag_offset
	
	func _is_mouse_over() -> bool:
		var mouse_pos = get_local_mouse_position()
		var half_size = piece_size / 2
		return mouse_pos.x >= -half_size.x and mouse_pos.x <= half_size.x \
			and mouse_pos.y >= -half_size.y and mouse_pos.y <= half_size.y
	
	func _try_snap() -> void:
		var distance = position.distance_to(target_position)
		if distance <= snap_distance and not is_placed:
			snap_to_target()
			placed.emit(self)
	
	func snap_to_target() -> void:
		position = target_position
		is_placed = true
		_play_snap_effect()
	
	func _play_snap_effect() -> void:
		# Brief glow effect
		glow_rect.visible = true
		
		# Scale pulse
		var original_scale = scale
		var tween = create_tween()
		tween.tween_property(self, "scale", original_scale * 1.1, 0.1)
		tween.tween_property(self, "scale", original_scale, 0.1)
		tween.tween_callback(func(): glow_rect.visible = false)


## FrameVisual - Inner class for drawing the frame
class FrameVisual extends Node2D:
	var frame_rect: Rect2 = Rect2(50, 50, 300, 400)
	var frame_color: Color = Color(0.4, 0.3, 0.2, 1)
	var border_width: float = 8.0
	
	func _draw() -> void:
		# Draw frame border
		var outer = frame_rect.grow(border_width)
		draw_rect(outer, frame_color, true)
		
		# Draw inner (transparent area for pieces)
		draw_rect(frame_rect, Color(0.15, 0.15, 0.2, 1), true)
		
		# Draw decorative inner border
		draw_rect(frame_rect.grow(-2), Color(0.5, 0.4, 0.3, 1), false, 2.0)
