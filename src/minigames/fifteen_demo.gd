extends Control
class_name FifteenDemo

@onready var puzzle: FifteenPuzzle = $PuzzleContainer/FifteenPuzzle
@onready var rows_spin: SpinBox = $UI/GridSettings/RowsSpin
@onready var cols_spin: SpinBox = $UI/GridSettings/ColsSpin
@onready var difficulty_slider: HSlider = $UI/DifficultySettings/DifficultySlider
@onready var difficulty_label: Label = $UI/DifficultySettings/DifficultyValue
@onready var file_dialog: FileDialog = $FileDialog

var default_texture: Texture2D

func _ready() -> void:
	rows_spin.value = puzzle.rows
	cols_spin.value = puzzle.cols
	difficulty_slider.value = puzzle.shuffle_moves
	_update_difficulty_label(puzzle.shuffle_moves)
	
	# Connect signals
	rows_spin.value_changed.connect(_on_grid_changed)
	cols_spin.value_changed.connect(_on_grid_changed)
	difficulty_slider.value_changed.connect(_on_difficulty_changed)
	puzzle.puzzle_completed.connect(_on_puzzle_completed)
	
	# Load default image if exists
	if puzzle.image_texture == null:
		_load_default_image()

func _load_default_image() -> void:
	# Try to load icon as default
	var tex = load("res://icon.svg")
	if tex:
		puzzle.load_image(tex)

func _on_grid_changed(_value: float) -> void:
	puzzle.set_grid_size(int(rows_spin.value), int(cols_spin.value))

func _on_difficulty_changed(value: float) -> void:
	puzzle.shuffle_moves = int(value)
	_update_difficulty_label(int(value))

func _update_difficulty_label(moves: int) -> void:
	difficulty_label.text = "%d moves" % moves

func _on_load_button_pressed() -> void:
	file_dialog.popup_centered()

func _on_file_dialog_file_selected(path: String) -> void:
	var image = Image.load_from_file(path)
	if image:
		var texture = ImageTexture.create_from_image(image)
		puzzle.load_image(texture)

func _on_reset_button_pressed() -> void:
	puzzle.reset_puzzle()

func _on_puzzle_completed() -> void:
	print("Puzzle completed!")
