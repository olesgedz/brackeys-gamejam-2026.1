extends IMiniGame
class_name FifteenMiniGame
## Wrapper for FifteenPuzzle to integrate with IMiniGame system

@export var puzzle_scene: PackedScene

var puzzle_instance: FifteenPuzzle


func _on_setup() -> void:
	# Wait for nodes to be ready
	if not is_node_ready():
		await ready
	
	var puzzle_viewport: SubViewport = $SubViewportContainer/SubViewport
	# Configure grid size based on difficulty
	var grid_configs = {
		1: Vector2i(2, 2),  # 2x2 = 3 tiles
		2: Vector2i(3, 2),  # 3x2 = 5 tiles
		3: Vector2i(3, 3),  # 3x3 = 8 tiles
		4: Vector2i(4, 3),  # 4x3 = 11 tiles
		5: Vector2i(4, 4),  # 4x4 = 15 tiles (classic)
	}
	
	var grid = grid_configs.get(difficulty, Vector2i(3, 2))
	
	# Instantiate puzzle into viewport
	if puzzle_scene:
		puzzle_instance = puzzle_scene.instantiate() as FifteenPuzzle
		puzzle_instance.cols = grid.x
		puzzle_instance.rows = grid.y
		puzzle_instance.puzzle_completed.connect(_on_puzzle_completed)
		puzzle_viewport.add_child(puzzle_instance)


func _on_puzzle_completed() -> void:
	# Small delay for satisfaction
	await get_tree().create_timer(0.5).timeout
	win()


func _on_cancel_pressed() -> void:
	cancel()
