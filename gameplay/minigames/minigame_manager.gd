extends Node
class_name MiniGameManagerClass
## ============================================================================
## MINIGAME MANAGER — Handles minigame instantiation and lifecycle
## ============================================================================
##
## Autoload that:
##   - Maps minigame_type to PackedScene
##   - Instantiates and displays minigames
##   - Routes results back to caller
##
## Usage:
##   MiniGameManager.start_minigame(
##       MiniGameManager.Type.FIFTEEN_PUZZLE,
##       "painting_01",
##       3,
##       callback_func
##   )
##
## ============================================================================

## Available minigame types
enum Type {
	NONE,
	MOCK_WIN_LOSE,      # Testing mock
	FIFTEEN_PUZZLE,     # Пятнашки
	MORSE_CODE,         # Стуки/морзянка
	MUSIC_BOX,          # Музыкальная шкатулка
	STAINED_GLASS,      # Витраж
}

## Registry: Type -> PackedScene path
const MINIGAME_SCENES: Dictionary = {
	Type.MOCK_WIN_LOSE: "res://gameplay/minigames/mock/mock_minigame.tscn",
	Type.FIFTEEN_PUZZLE: "res://gameplay/minigames/fifteen/fifteen_minigame.tscn",
	Type.MORSE_CODE: "res://gameplay/minigames/mock/mock_minigame.tscn",          # TODO: real scene
	Type.MUSIC_BOX: "res://gameplay/minigames/mock/mock_minigame.tscn",           # TODO: real scene
	Type.STAINED_GLASS: "res://gameplay/minigames/mock/mock_minigame.tscn",       # TODO: real scene
}

## Currently active minigame instance
var _current_minigame: IMiniGame = null

## Callback for current minigame result
var _result_callback: Callable

## Canvas layer for displaying minigames (overlay)
var _canvas_layer: CanvasLayer

## Emitted when any minigame starts
signal minigame_started(minigame_type: Type, painting_id: String)

## Emitted when any minigame finishes
signal minigame_finished(minigame_type: Type, painting_id: String, result: IMiniGame.Result)


func _ready() -> void:
	# Create canvas layer for minigame overlay
	_canvas_layer = CanvasLayer.new()
	_canvas_layer.name = "MiniGameLayer"
	_canvas_layer.layer = 50
	add_child(_canvas_layer)


#region PUBLIC API
## Check if a minigame is currently active
func is_minigame_active() -> bool:
	return _current_minigame != null


## Start a minigame
## @param type: Which minigame to launch
## @param painting_id: ID of the painting that triggered this
## @param difficulty: Difficulty level (1-5)
## @param on_result: Callback func(result: IMiniGame.Result)
## @param extra_params: Optional additional parameters
func start_minigame(
	type: Type,
	painting_id: String,
	difficulty: int,
	on_result: Callable,
	extra_params: Dictionary = {}
) -> bool:
	if is_minigame_active():
		push_warning("MiniGameManager: Cannot start minigame, one is already active")
		return false
	
	if type == Type.NONE:
		push_warning("MiniGameManager: Cannot start minigame of type NONE")
		return false
	
	var scene_path: String = MINIGAME_SCENES.get(type, "")
	if scene_path.is_empty():
		push_error("MiniGameManager: No scene registered for type %s" % Type.keys()[type])
		return false
	
	var packed_scene := load(scene_path) as PackedScene
	if not packed_scene:
		push_error("MiniGameManager: Failed to load scene: %s" % scene_path)
		return false
	
	# Instantiate minigame
	var instance := packed_scene.instantiate()
	if not instance is IMiniGame:
		push_error("MiniGameManager: Scene is not an IMiniGame: %s" % scene_path)
		instance.queue_free()
		return false
	
	_current_minigame = instance as IMiniGame
	_result_callback = on_result
	
	# Setup and connect
	_current_minigame.setup(painting_id, difficulty, extra_params)
	_current_minigame.finished.connect(_on_minigame_finished.bind(type, painting_id))
	
	# Add to canvas layer (fullscreen overlay)
	_canvas_layer.add_child(_current_minigame)
	
	# Pause the game tree (minigame runs independently)
	get_tree().paused = true
	_current_minigame.process_mode = Node.PROCESS_MODE_ALWAYS
	
	# Sync state with GameManager
	if GameManager:
		GameManager.change_state(GameManager.State.MINIGAME)
	
	# Show mouse for minigame UI
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	
	minigame_started.emit(type, painting_id)
	return true


## Force-close the current minigame (emergency)
func force_close_minigame() -> void:
	if _current_minigame:
		_on_minigame_finished(IMiniGame.Result.CANCEL, Type.NONE, "")
#endregion


#region INTERNAL
func _on_minigame_finished(result: IMiniGame.Result, type: Type, painting_id: String) -> void:
	if not _current_minigame:
		return
	
	# Cleanup
	_current_minigame.queue_free()
	_current_minigame = null
	
	# Unpause game
	get_tree().paused = false
	
	# Sync state with GameManager
	if GameManager:
		GameManager.change_state(GameManager.State.PLAYING)
	
	# Restore mouse capture (FPS game)
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	
	# Emit signal
	minigame_finished.emit(type, painting_id, result)
	
	# Call the callback
	if _result_callback.is_valid():
		_result_callback.call(result)
		_result_callback = Callable()
#endregion


#region UTILITY
## Get display name for minigame type
static func get_type_name(type: Type) -> String:
	match type:
		Type.NONE: return "None"
		Type.MOCK_WIN_LOSE: return "Test (Mock)"
		Type.FIFTEEN_PUZZLE: return "Fifteen Puzzle"
		Type.MORSE_CODE: return "Morse Code"
		Type.MUSIC_BOX: return "Music Box"
		Type.STAINED_GLASS: return "Stained Glass"
		_: return "Unknown"
#endregion
