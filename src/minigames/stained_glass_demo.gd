extends Control

@onready var puzzle: StainedGlass = $PuzzleContainer/StainedGlass
@onready var snap_spin: SpinBox = $UI/Settings/SnapSpin
@onready var frame_w_spin: SpinBox = $UI/Settings/FrameWSpin
@onready var frame_h_spin: SpinBox = $UI/Settings/FrameHSpin
@onready var pieces_spin: SpinBox = $UI/Settings/PiecesSpin

func _ready() -> void:
	snap_spin.value = puzzle.snap_distance
	frame_w_spin.value = puzzle.frame_size.x
	frame_h_spin.value = puzzle.frame_size.y
	# pieces_spin - placeholder, actual pieces determined by textures
	
	snap_spin.value_changed.connect(_on_snap_changed)
	frame_w_spin.value_changed.connect(_on_frame_w_changed)
	frame_h_spin.value_changed.connect(_on_frame_h_changed)
	puzzle.puzzle_completed.connect(_on_puzzle_completed)

func _on_snap_changed(value: float) -> void:
	puzzle.snap_distance = value

func _on_frame_w_changed(value: float) -> void:
	puzzle.frame_size.x = value

func _on_frame_h_changed(value: float) -> void:
	puzzle.frame_size.y = value

func _on_apply_pressed() -> void:
	puzzle.reset_puzzle()

func _on_puzzle_completed() -> void:
	print("Stained Glass completed!")
