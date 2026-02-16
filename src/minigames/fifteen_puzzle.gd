extends Node2D
class_name FifteenPuzzle

signal puzzle_completed

@export var rows: int = 4
@export var cols: int = 4
@export var puzzle_size: Vector2 = Vector2(400, 400)
@export var image_texture: Texture2D
@export_range(5, 200, 5) var shuffle_moves: int = 50

@onready var tiles_container: Node2D = $TilesContainer
@onready var win_label: Label = $WinLabel

var tiles: Array = []  # 2D array of tile nodes
var empty_pos: Vector2i = Vector2i(0, 0)  # Position of empty slot
var tile_size: Vector2 = Vector2.ZERO
var is_solved: bool = false

func _ready() -> void:
	win_label.visible = false
	if image_texture:
		setup_puzzle()

func setup_puzzle() -> void:
	_clear_tiles()
	
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
		_check_win()

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
	
	# Update empty position
	empty_pos = tile_pos

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
