extends Node2D
class_name MusicBox

signal puzzle_completed

@export var num_keys: int = 5
@export var max_rounds: int = 5
@export var note_sounds: Array[AudioStream] = []
@export var base_note_duration: float = 0.5  ## Duration of each note in seconds
@export var base_pause_duration: float = 0.2  ## Pause between notes

# Visual settings
@export var key_width: float = 80.0
@export var key_height: float = 150.0
@export var key_spacing: float = 10.0

# Creepy settings
@export var pitch_reduction_per_round: float = 0.08  ## How much pitch drops each round
@export var duration_increase_per_round: float = 0.15  ## How much slower each round

@onready var keys_container: HBoxContainer = $KeysContainer
@onready var audio_player: AudioStreamPlayer = $AudioPlayer
@onready var debug_panel: VBoxContainer = $DebugPanel
@onready var round_label: Label = $DebugPanel/RoundLabel
@onready var sequence_label: Label = $DebugPanel/SequenceLabel
@onready var play_button: Button = $DebugPanel/PlayButton
@onready var autosolve_button: Button = $DebugPanel/AutosolveButton
@onready var reset_button: Button = $DebugPanel/ResetButton

var keys: Array[ColorRect] = []
var sequence: Array[int] = []
var player_input: Array[int] = []
var current_round: int = 0
var is_playing_sequence: bool = false
var is_player_turn: bool = false
var is_solved: bool = false

# Colors for keys
var key_colors: Array[Color] = [
	Color(0.8, 0.2, 0.2),  # Red
	Color(0.2, 0.7, 0.2),  # Green
	Color(0.2, 0.4, 0.9),  # Blue
	Color(0.9, 0.8, 0.1),  # Yellow
	Color(0.7, 0.2, 0.8),  # Purple
	Color(0.9, 0.5, 0.1),  # Orange
	Color(0.2, 0.8, 0.8),  # Cyan
]

var key_highlight_color: Color = Color(1, 1, 1, 0.8)


func _ready() -> void:
	_setup_keys()
	_connect_debug_buttons()
	_start_game()


func _setup_keys() -> void:
	# Clear existing keys
	for child in keys_container.get_children():
		child.queue_free()
	keys.clear()
	
	# Create keys
	for i in range(num_keys):
		var key = ColorRect.new()
		key.custom_minimum_size = Vector2(key_width, key_height)
		key.color = key_colors[i % key_colors.size()]
		key.name = "Key_%d" % i
		
		# Make it clickable
		key.mouse_filter = Control.MOUSE_FILTER_STOP
		key.gui_input.connect(_on_key_input.bind(i))
		
		# Store original color
		key.set_meta("original_color", key.color)
		key.set_meta("key_index", i)
		
		keys_container.add_child(key)
		keys.append(key)


func _connect_debug_buttons() -> void:
	play_button.pressed.connect(_on_play_button_pressed)
	autosolve_button.pressed.connect(_on_autosolve_pressed)
	reset_button.pressed.connect(_on_reset_pressed)


func _start_game() -> void:
	sequence.clear()
	player_input.clear()
	current_round = 0
	is_solved = false
	is_player_turn = false
	
	_next_round()


func _next_round() -> void:
	if current_round >= max_rounds:
		_win_game()
		return
	
	current_round += 1
	player_input.clear()
	
	# Add new note to sequence
	var new_note = randi() % num_keys
	sequence.append(new_note)
	
	_update_debug_ui()
	
	# Play the sequence after a short delay
	await get_tree().create_timer(0.5).timeout
	_play_sequence()


func _play_sequence() -> void:
	is_playing_sequence = true
	is_player_turn = false
	_set_keys_enabled(false)
	
	# Calculate creepy modifiers based on round
	var pitch_modifier = 1.0 - (current_round - 1) * pitch_reduction_per_round
	var duration_modifier = 1.0 + (current_round - 1) * duration_increase_per_round
	
	pitch_modifier = clampf(pitch_modifier, 0.5, 1.0)  # Don't go below 50% pitch
	
	for i in range(sequence.size()):
		var key_index = sequence[i]
		await _play_note(key_index, pitch_modifier, duration_modifier)
		await get_tree().create_timer(base_pause_duration * duration_modifier).timeout
	
	is_playing_sequence = false
	is_player_turn = true
	_set_keys_enabled(true)


func _play_note(key_index: int, pitch_modifier: float = 1.0, duration_modifier: float = 1.0) -> void:
	if key_index < 0 or key_index >= keys.size():
		return
	
	var key = keys[key_index]
	
	# Visual feedback - highlight
	var original_color: Color = key.get_meta("original_color")
	key.color = original_color.lightened(0.5)
	
	# Play sound if available
	if key_index < note_sounds.size() and note_sounds[key_index] != null:
		audio_player.stream = note_sounds[key_index]
		audio_player.pitch_scale = pitch_modifier
		audio_player.play()
	
	# Hold highlight
	await get_tree().create_timer(base_note_duration * duration_modifier).timeout
	
	# Restore color
	key.color = original_color


func _on_key_input(event: InputEvent, key_index: int) -> void:
	if not event is InputEventMouseButton:
		return
	
	var mouse_event = event as InputEventMouseButton
	if not mouse_event.pressed or mouse_event.button_index != MOUSE_BUTTON_LEFT:
		return
	
	if not is_player_turn or is_playing_sequence or is_solved:
		return
	
	_player_press_key(key_index)


func _player_press_key(key_index: int) -> void:
	player_input.append(key_index)
	
	# Visual and audio feedback
	_flash_key(key_index)
	
	# Check if correct
	var input_index = player_input.size() - 1
	if sequence[input_index] != key_index:
		# Wrong! Reset to current round
		_on_wrong_input()
		return
	
	# Check if sequence complete
	if player_input.size() == sequence.size():
		_on_correct_sequence()


func _flash_key(key_index: int) -> void:
	if key_index < 0 or key_index >= keys.size():
		return
	
	var key = keys[key_index]
	var original_color: Color = key.get_meta("original_color")
	
	# Play sound with current round's pitch modifier
	var pitch_modifier = 1.0 - (current_round - 1) * pitch_reduction_per_round
	pitch_modifier = clampf(pitch_modifier, 0.5, 1.0)
	
	if key_index < note_sounds.size() and note_sounds[key_index] != null:
		audio_player.stream = note_sounds[key_index]
		audio_player.pitch_scale = pitch_modifier
		audio_player.play()
	
	# Quick flash
	key.color = key_highlight_color
	
	var tween = create_tween()
	tween.tween_property(key, "color", original_color, 0.2)


func _on_wrong_input() -> void:
	# Flash all keys red briefly
	for key in keys:
		key.color = Color(1, 0, 0)
	
	await get_tree().create_timer(0.5).timeout
	
	# Restore colors
	for key in keys:
		key.color = key.get_meta("original_color")
	
	# Reset player input and replay sequence
	player_input.clear()
	await get_tree().create_timer(0.3).timeout
	_play_sequence()


func _on_correct_sequence() -> void:
	is_player_turn = false
	
	# Brief success flash
	for key in keys:
		key.color = Color(0.2, 1, 0.2)
	
	await get_tree().create_timer(0.3).timeout
	
	for key in keys:
		key.color = key.get_meta("original_color")
	
	# Next round
	_next_round()


func _win_game() -> void:
	is_solved = true
	is_player_turn = false
	_update_debug_ui()
	
	# Victory animation
	for i in range(3):
		for key in keys:
			key.color = Color(1, 0.9, 0.2)
		await get_tree().create_timer(0.2).timeout
		for key in keys:
			key.color = key.get_meta("original_color")
		await get_tree().create_timer(0.2).timeout
	
	puzzle_completed.emit()


func _set_keys_enabled(enabled: bool) -> void:
	for key in keys:
		key.mouse_filter = Control.MOUSE_FILTER_STOP if enabled else Control.MOUSE_FILTER_IGNORE


func _update_debug_ui() -> void:
	if is_solved:
		round_label.text = "COMPLETED! (%d rounds)" % max_rounds
	else:
		round_label.text = "Round: %d / %d | Sequence length: %d" % [current_round, max_rounds, sequence.size()]
	
	var seq_str = ""
	for i in range(sequence.size()):
		seq_str += str(sequence[i])
		if i < sequence.size() - 1:
			seq_str += " - "
	sequence_label.text = "Sequence: [%s]" % seq_str


# Debug button handlers

func _on_play_button_pressed() -> void:
	if is_playing_sequence or is_solved:
		return
	_play_sequence()


func _on_autosolve_pressed() -> void:
	if is_solved:
		return
	_win_game()


func _on_reset_pressed() -> void:
	_start_game()


# Public API

func reset() -> void:
	_start_game()


func get_current_round() -> int:
	return current_round


func get_sequence() -> Array[int]:
	return sequence.duplicate()
