extends Node2D
class_name FifteenPuzzle

signal puzzle_completed

@export var rows: int = 4
@export var cols: int = 4
@export var puzzle_size: Vector2 = Vector2(400, 400)
@export var image_texture: Texture2D
@export_range(5, 200, 5) var shuffle_moves: int = 50
@export var tear_texture: Texture2D  ## Texture for torn edges between tiles
@export var developer_mode: bool = false  ## Enables right-click swap cheats
@export var slide_sounds: Array[AudioStream] = []  ## Sound bank for tile movement

@onready var tiles_container: Node2D = $TilesContainer
@onready var tears_container: Node2D = $TearsContainer
@onready var win_label: Label = $WinLabel
@onready var audio_player: AudioStreamPlayer = $AudioPlayer

var tiles: Array = []  # 2D array of tile nodes
var empty_pos: Vector2i = Vector2i(0, 0)  # Position of empty slot
var tile_size: Vector2 = Vector2.ZERO
var is_solved: bool = false

# Developer mode swap
var dev_selected_tile: TextureButton = null
var dev_selected_pos: Vector2i = Vector2i(-1, -1)

func _ready() -> void:
	win_label.visible = false
	if image_texture:
		setup_puzzle()

func setup_puzzle() -> void:
	_clear_tiles()
	_clear_tears()
	
	tile_size = Vector2(puzzle_size.x / cols, puzzle_size.y / rows)
	
	# Create tiles array
	tiles = []
	for row in range(rows):
		var row_array = []
		for col in range(cols):
			row_array.append(null)
		tiles.append(row_array)
	
	# Create tile nodes
	var tile_index = 0
	for row in range(rows):
		for col in range(cols):
			# Last tile is empty
			if row == rows - 1 and col == cols - 1:
				empty_pos = Vector2i(col, row)
				continue
			
			var tile = _create_tile(row, col, tile_index)
			tiles[row][col] = tile
			tiles_container.add_child(tile)
			tile_index += 1
	
	# Shuffle
	_shuffle_puzzle()
	
	# Update tear overlays
	_update_tears()

func _create_tile(original_row: int, original_col: int, index: int) -> TextureButton:
	var tile = TextureButton.new()
	tile.name = "Tile_%d" % index
	
	# Create AtlasTexture for this piece
	var atlas = AtlasTexture.new()
	atlas.atlas = image_texture
	atlas.region = Rect2(
		original_col * (image_texture.get_width() / float(cols)),
		original_row * (image_texture.get_height() / float(rows)),
		image_texture.get_width() / float(cols),
		image_texture.get_height() / float(rows)
	)
	
	tile.texture_normal = atlas
	tile.ignore_texture_size = true
	tile.stretch_mode = TextureButton.STRETCH_SCALE
	tile.custom_minimum_size = tile_size
	tile.size = tile_size
	
	# Store original position for win checking
	tile.set_meta("original_row", original_row)
	tile.set_meta("original_col", original_col)
	
	# Position
	tile.position = Vector2(original_col * tile_size.x, original_row * tile_size.y)
	
	tile.pressed.connect(_on_tile_pressed.bind(tile))
	tile.gui_input.connect(_on_tile_gui_input.bind(tile))
	
	return tile

func _on_tile_pressed(tile: TextureButton) -> void:
	if is_solved:
		return
	
	# Find tile position in grid
	var tile_pos = _find_tile_position(tile)
	if tile_pos == Vector2i(-1, -1):
		return
	
	# Check if adjacent to empty
	if _is_adjacent_to_empty(tile_pos):
		_swap_with_empty(tile_pos)
		_update_tears()
		_check_win()

func _on_tile_gui_input(event: InputEvent, tile: TextureButton) -> void:
	if not developer_mode or is_solved:
		return
	
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
		_dev_handle_right_click(tile)

func _find_tile_position(tile: TextureButton) -> Vector2i:
	for row in range(rows):
		for col in range(cols):
			if tiles[row][col] == tile:
				return Vector2i(col, row)
	return Vector2i(-1, -1)

func _is_adjacent_to_empty(pos: Vector2i) -> bool:
	var diff = (pos - empty_pos).abs()
	return (diff.x == 1 and diff.y == 0) or (diff.x == 0 and diff.y == 1)

func _swap_with_empty(tile_pos: Vector2i) -> void:
	var tile = tiles[tile_pos.y][tile_pos.x]
	
	# Update array
	tiles[empty_pos.y][empty_pos.x] = tile
	tiles[tile_pos.y][tile_pos.x] = null
	
	# Animate tile movement
	var tween = create_tween()
	tween.tween_property(tile, "position", Vector2(empty_pos.x * tile_size.x, empty_pos.y * tile_size.y), 0.1)
	
	# Play slide sound
	_play_random_slide_sound()
	
	# Update empty position
	empty_pos = tile_pos

func _play_random_slide_sound() -> void:
	if slide_sounds.is_empty() or audio_player == null:
		return
	
	var random_sound = slide_sounds[randi() % slide_sounds.size()]
	audio_player.stream = random_sound
	audio_player.pitch_scale = randf_range(0.9, 1.1)  # Slight pitch variation
	audio_player.play()

func _check_win() -> void:
	for row in range(rows):
		for col in range(cols):
			# Skip empty position (should be at bottom-right)
			if row == rows - 1 and col == cols - 1:
				continue
			
			var tile = tiles[row][col]
			if tile == null:
				return  # Empty tile in wrong place
			
			var orig_row = tile.get_meta("original_row")
			var orig_col = tile.get_meta("original_col")
			
			if orig_row != row or orig_col != col:
				return  # Tile in wrong place
	
	# All tiles in correct position!
	is_solved = true
	win_label.visible = true
	puzzle_completed.emit()

func _shuffle_puzzle() -> void:
	# Perform random valid moves to shuffle
	for i in range(shuffle_moves):
		var adjacent = _get_adjacent_to_empty()
		if adjacent.size() > 0:
			var random_pos = adjacent[randi() % adjacent.size()]
			_swap_with_empty_instant(random_pos)

func _get_adjacent_to_empty() -> Array[Vector2i]:
	var adjacent: Array[Vector2i] = []
	var directions = [Vector2i(0, -1), Vector2i(0, 1), Vector2i(-1, 0), Vector2i(1, 0)]
	
	for dir in directions:
		var new_pos = empty_pos + dir
		if new_pos.x >= 0 and new_pos.x < cols and new_pos.y >= 0 and new_pos.y < rows:
			adjacent.append(new_pos)
	
	return adjacent

func _swap_with_empty_instant(tile_pos: Vector2i) -> void:
	var tile = tiles[tile_pos.y][tile_pos.x]
	if tile == null:
		return
	
	# Update array
	tiles[empty_pos.y][empty_pos.x] = tile
	tiles[tile_pos.y][tile_pos.x] = null
	
	# Update position instantly
	tile.position = Vector2(empty_pos.x * tile_size.x, empty_pos.y * tile_size.y)
	
	# Update empty position
	empty_pos = tile_pos

func _clear_tiles() -> void:
	for child in tiles_container.get_children():
		child.queue_free()
	tiles = []

func _clear_tears() -> void:
	if tears_container:
		for child in tears_container.get_children():
			child.queue_free()

## Developer Mode

func _dev_handle_right_click(tile: TextureButton) -> void:
	var tile_pos = _find_tile_position(tile)
	
	if dev_selected_tile == null:
		# First selection
		dev_selected_tile = tile
		dev_selected_pos = tile_pos
		tile.modulate = Color(1, 1, 0.5)  # Highlight yellow
	else:
		# Second selection - swap
		if tile == dev_selected_tile:
			# Deselect
			dev_selected_tile.modulate = Color.WHITE
			dev_selected_tile = null
			dev_selected_pos = Vector2i(-1, -1)
		else:
			# Swap the two tiles
			_dev_swap_tiles(dev_selected_pos, tile_pos)
			dev_selected_tile.modulate = Color.WHITE
			dev_selected_tile = null
			dev_selected_pos = Vector2i(-1, -1)
			_update_tears()
			_check_win()

func _dev_select_empty() -> void:
	# Called when right-clicking on empty space (handled in _input)
	if not developer_mode or is_solved:
		return
	
	if dev_selected_tile != null:
		# Swap selected tile with empty
		_dev_swap_tiles(dev_selected_pos, empty_pos)
		dev_selected_tile.modulate = Color.WHITE
		dev_selected_tile = null
		dev_selected_pos = Vector2i(-1, -1)
		_update_tears()
		_check_win()

func _dev_swap_tiles(pos1: Vector2i, pos2: Vector2i) -> void:
	var tile1 = tiles[pos1.y][pos1.x]
	var tile2 = tiles[pos2.y][pos2.x]
	
	# Swap in array
	tiles[pos1.y][pos1.x] = tile2
	tiles[pos2.y][pos2.x] = tile1
	
	# Update positions visually
	if tile1:
		tile1.position = Vector2(pos2.x * tile_size.x, pos2.y * tile_size.y)
	if tile2:
		tile2.position = Vector2(pos1.x * tile_size.x, pos1.y * tile_size.y)
	
	# Update empty_pos if involved
	if tile1 == null:
		empty_pos = pos2
	elif tile2 == null:
		empty_pos = pos1

func _input(event: InputEvent) -> void:
	if not developer_mode or is_solved:
		return
	
	# Handle right-click on empty space
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
		var local_pos = tiles_container.get_local_mouse_position()
		var grid_pos = Vector2i(int(local_pos.x / tile_size.x), int(local_pos.y / tile_size.y))
		
		# Check if clicking on empty space
		if grid_pos == empty_pos and grid_pos.x >= 0 and grid_pos.x < cols and grid_pos.y >= 0 and grid_pos.y < rows:
			_dev_select_empty()

## Tear Overlays

func _update_tears() -> void:
	_clear_tears()
	
	if tear_texture == null or tears_container == null:
		return
	
	# Check horizontal tears (between vertically adjacent tiles)
	for row in range(rows - 1):
		for col in range(cols):
			if not _are_vertically_connected(row, col):
				_add_horizontal_tear(row, col)
	
	# Check vertical tears (between horizontally adjacent tiles)
	for row in range(rows):
		for col in range(cols - 1):
			if not _are_horizontally_connected(row, col):
				_add_vertical_tear(row, col)

func _are_vertically_connected(row: int, col: int) -> bool:
	# Check if tile at (row, col) connects properly with tile at (row+1, col)
	var tile_above = tiles[row][col]
	var tile_below = tiles[row + 1][col]
	
	if tile_above == null or tile_below == null:
		return true  # Empty space doesn't show tear
	
	var orig_row_above = tile_above.get_meta("original_row")
	var orig_col_above = tile_above.get_meta("original_col")
	var orig_row_below = tile_below.get_meta("original_row")
	var orig_col_below = tile_below.get_meta("original_col")
	
	# They connect if they were originally adjacent vertically
	return orig_col_above == orig_col_below and orig_row_above + 1 == orig_row_below

func _are_horizontally_connected(row: int, col: int) -> bool:
	# Check if tile at (row, col) connects properly with tile at (row, col+1)
	var tile_left = tiles[row][col]
	var tile_right = tiles[row][col + 1]
	
	if tile_left == null or tile_right == null:
		return true  # Empty space doesn't show tear
	
	var orig_row_left = tile_left.get_meta("original_row")
	var orig_col_left = tile_left.get_meta("original_col")
	var orig_row_right = tile_right.get_meta("original_row")
	var orig_col_right = tile_right.get_meta("original_col")
	
	# They connect if they were originally adjacent horizontally
	return orig_row_left == orig_row_right and orig_col_left + 1 == orig_col_right

func _add_horizontal_tear(row: int, col: int) -> void:
	var tear = TextureRect.new()
	tear.texture = tear_texture
	tear.stretch_mode = TextureRect.STRETCH_SCALE
	
	# Scale to tile width, maintain aspect ratio
	var tex_w = tear_texture.get_width()
	var tex_h = tear_texture.get_height()
	var scale_factor = tile_size.x / tex_w
	tear.size = Vector2(tile_size.x, tex_h * scale_factor)
	
	# Center on the seam between row and row+1
	tear.position = Vector2(col * tile_size.x, (row + 1) * tile_size.y - tear.size.y / 2)
	tears_container.add_child(tear)

func _add_vertical_tear(row: int, col: int) -> void:
	var tear = TextureRect.new()
	tear.texture = tear_texture
	tear.stretch_mode = TextureRect.STRETCH_SCALE
	
	# Scale to tile height, maintain aspect ratio
	var tex_w = tear_texture.get_width()
	var tex_h = tear_texture.get_height()
	var scale_factor = tile_size.y / tex_w
	var tear_width = tile_size.y  # After rotation this becomes visual height
	var tear_height = tex_h * scale_factor  # After rotation this becomes visual width (thickness)
	
	tear.size = Vector2(tear_width, tear_height)
	
	# Set pivot to center for easier rotation handling
	tear.pivot_offset = tear.size / 2
	
	# Rotate 90 degrees
	tear.rotation = PI / 2
	
	# Position at seam center between col and col+1
	var seam_x = (col + 1) * tile_size.x
	var seam_center_y = row * tile_size.y + tile_size.y / 2
	tear.position = Vector2(seam_x - tear_height / 2, seam_center_y - tear_width / 2)
	
	tears_container.add_child(tear)

## Public API

func load_image(texture: Texture2D) -> void:
	image_texture = texture
	setup_puzzle()

func set_grid_size(new_rows: int, new_cols: int) -> void:
	rows = new_rows
	cols = new_cols
	if image_texture:
		setup_puzzle()

func reset_puzzle() -> void:
	is_solved = false
	win_label.visible = false
	setup_puzzle()
