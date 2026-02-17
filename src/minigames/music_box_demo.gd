extends Control

@onready var puzzle: MusicBox = $PuzzleContainer/MusicBox
@onready var keys_spin: SpinBox = $UI/Settings/KeysSpin
@onready var rounds_spin: SpinBox = $UI/Settings/RoundsSpin
@onready var note_dur_spin: SpinBox = $UI/Settings/NoteDurSpin
@onready var pitch_drop_spin: SpinBox = $UI/Settings/PitchDropSpin
@onready var tempo_slow_spin: SpinBox = $UI/Settings/TempoSlowSpin

func _ready() -> void:
	keys_spin.value = puzzle.num_keys
	rounds_spin.value = puzzle.max_rounds
	note_dur_spin.value = puzzle.base_note_duration
	pitch_drop_spin.value = puzzle.pitch_reduction_per_round * 100
	tempo_slow_spin.value = puzzle.duration_increase_per_round * 100
	
	keys_spin.value_changed.connect(_on_keys_changed)
	rounds_spin.value_changed.connect(_on_rounds_changed)
	note_dur_spin.value_changed.connect(_on_note_dur_changed)
	pitch_drop_spin.value_changed.connect(_on_pitch_changed)
	tempo_slow_spin.value_changed.connect(_on_tempo_changed)
	puzzle.puzzle_completed.connect(_on_puzzle_completed)

func _on_keys_changed(value: float) -> void:
	puzzle.num_keys = int(value)

func _on_rounds_changed(value: float) -> void:
	puzzle.max_rounds = int(value)

func _on_note_dur_changed(value: float) -> void:
	puzzle.base_note_duration = value

func _on_pitch_changed(value: float) -> void:
	puzzle.pitch_reduction_per_round = value / 100.0

func _on_tempo_changed(value: float) -> void:
	puzzle.duration_increase_per_round = value / 100.0

func _on_apply_pressed() -> void:
	puzzle.reset_game()

func _on_puzzle_completed() -> void:
	print("Music Box completed!")
