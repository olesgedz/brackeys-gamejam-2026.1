extends Node
class_name GameManagerClass
## ============================================================================
## GAME MANAGER - Central game state and flow controller
## ============================================================================
##
## Autoload singleton managing:
## - Game states and transitions
## - Scene loading with fade effects
## - Save/Load system
## - Player progress tracking
## - Global game events
##
## Usage:
##   GameManager.change_state(GameManager.State.PLAYING)
##   GameManager.load_scene("res://scenes/room.tscn")
##   GameManager.save_game()
##
## Signals:
##   state_changed(old_state, new_state) - When game state changes
##   scene_changing(scene_path) - Before scene transition starts
##   scene_changed(scene_path) - After scene fully loaded
##   progress_updated(key, value) - When any progress value changes
##   painting_healed(painting_id) - When player heals a painting
##
## ============================================================================

#region SIGNALS
## Emitted when game state changes
signal state_changed(old_state: State, new_state: State)

## Emitted before scene transition starts
signal scene_changing(scene_path: String)

## Emitted after scene fully loaded and fade-in complete
signal scene_changed(scene_path: String)

## Emitted when any progress value changes
signal progress_updated(key: String, value: Variant)

## Emitted when a painting minigame is completed
signal painting_healed(painting_id: String)

## Emitted when game is saved
signal game_saved()

## Emitted when game is loaded
signal game_loaded()
#endregion

#region ENUMS
## All possible game states
enum State {
	NONE,           ## Initial/undefined state
	MENU,           ## Main menu
	LOADING,        ## Loading screen
	PLAYING,        ## Normal gameplay (exploring room)
	PAUSED,         ## Game paused
	MINIGAME,       ## Inside a painting minigame
	DIALOGUE,       ## Dialogue/cutscene playing
	INVENTORY,      ## Inventory open
	TRANSITIONING,  ## Scene transition in progress
}
#endregion

#region CONFIGURATION
## Save file path
const SAVE_PATH := "user://savegame.json"

## Transition fade duration in seconds
@export var fade_duration: float = 0.5

## Enable debug prints
@export var debug_mode: bool = false
#endregion

#region STATE
## Current game state
var current_state: State = State.NONE:
	set(value):
		if current_state != value:
			var old = current_state
			current_state = value
			state_changed.emit(old, value)
			_log("State: %s -> %s" % [State.keys()[old], State.keys()[value]])

## Previous state (for returning from pause/inventory)
var previous_state: State = State.NONE

## Currently loaded scene path
var current_scene_path: String = ""

## Is game currently transitioning between scenes
var is_transitioning: bool = false
#endregion

#region PLAYER PROGRESS
## ============================================================================
## PROGRESS DATA - Customize these for your game!
## ============================================================================

## Which paintings have been healed (painting_id -> true)
var healed_paintings: Dictionary = {}

## Current room/area the player is in
var current_room: String = "sanatorium_room"

## Player's current health/sanity (0-100)
var player_sanity: int = 100

## Items collected (item_id -> count)
var inventory: Dictionary = {}

## Story flags (flag_name -> bool)
var story_flags: Dictionary = {}

## Total playtime in seconds
var playtime_seconds: float = 0.0

## Number of deaths/failures
var death_count: int = 0

## Custom data bucket for extensibility
var custom_data: Dictionary = {}
#endregion

#region SCENE REFERENCES
## Reference to fade overlay (created on _ready)
var _fade_overlay: ColorRect

## Reference to current scene root
var _current_scene: Node
#endregion

#region LIFECYCLE
func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS  # Run even when paused
	_create_fade_overlay()
	_log("GameManager initialized")


func _process(delta: float) -> void:
	# Track playtime only when playing
	if current_state == State.PLAYING:
		playtime_seconds += delta
#endregion

#region STATE MANAGEMENT
## Change game state with optional previous state tracking
func change_state(new_state: State, track_previous: bool = true) -> void:
	if track_previous and current_state != State.TRANSITIONING:
		previous_state = current_state
	current_state = new_state


## Return to previous state (useful for pause menu)
func return_to_previous_state() -> void:
	if previous_state != State.NONE:
		current_state = previous_state


## Pause the game
func pause_game() -> void:
	if current_state == State.PLAYING or current_state == State.MINIGAME:
		change_state(State.PAUSED)
		get_tree().paused = true


## Resume the game
func resume_game() -> void:
	get_tree().paused = false
	return_to_previous_state()


## Check if game is in a playable state
func is_playing() -> bool:
	return current_state in [State.PLAYING, State.MINIGAME]
#endregion

#region SCENE TRANSITIONS
## Load a scene with fade transition
## @param scene_path: Path to scene (e.g., "res://scenes/room.tscn")
## @param fade_out: Whether to fade out before loading
## @param fade_in: Whether to fade in after loading
func load_scene(scene_path: String, fade_out: bool = true, fade_in: bool = true) -> void:
	if is_transitioning:
		_log("Already transitioning, ignoring load_scene call")
		return
	
	is_transitioning = true
	change_state(State.TRANSITIONING, false)
	scene_changing.emit(scene_path)
	
	# Fade out
	if fade_out:
		await _fade_to_black()
	
	# Load the scene
	var packed_scene := load(scene_path) as PackedScene
	if not packed_scene:
		push_error("Failed to load scene: " + scene_path)
		is_transitioning = false
		return
	
	# Remove old scene
	if _current_scene:
		_current_scene.queue_free()
	
	# Instance new scene
	_current_scene = packed_scene.instantiate()
	get_tree().root.add_child(_current_scene)
	get_tree().current_scene = _current_scene
	current_scene_path = scene_path
	
	# Fade in
	if fade_in:
		await _fade_from_black()
	
	is_transitioning = false
	scene_changed.emit(scene_path)
	_log("Scene loaded: " + scene_path)


## Reload current scene
func reload_current_scene() -> void:
	if current_scene_path:
		await load_scene(current_scene_path)


## Internal: Fade to black
func _fade_to_black() -> void:
	_fade_overlay.show()
	var tween := create_tween()
	tween.tween_property(_fade_overlay, "modulate:a", 1.0, fade_duration)
	await tween.finished


## Internal: Fade from black
func _fade_from_black() -> void:
	var tween := create_tween()
	tween.tween_property(_fade_overlay, "modulate:a", 0.0, fade_duration)
	await tween.finished
	_fade_overlay.hide()


## Internal: Create the fade overlay
func _create_fade_overlay() -> void:
	_fade_overlay = ColorRect.new()
	_fade_overlay.name = "FadeOverlay"
	_fade_overlay.color = Color.BLACK
	_fade_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade_overlay.modulate.a = 0.0
	_fade_overlay.hide()
	
	# Add to CanvasLayer so it's always on top
	var canvas := CanvasLayer.new()
	canvas.name = "FadeCanvas"
	canvas.layer = 100
	canvas.add_child(_fade_overlay)
	add_child(canvas)
#endregion

#region PROGRESS TRACKING
## Mark a painting as healed
func heal_painting(painting_id: String) -> void:
	if not healed_paintings.get(painting_id, false):
		healed_paintings[painting_id] = true
		painting_healed.emit(painting_id)
		progress_updated.emit("painting_healed", painting_id)
		_log("Painting healed: " + painting_id)


## Check if a painting is healed
func is_painting_healed(painting_id: String) -> bool:
	return healed_paintings.get(painting_id, false)


## Get count of healed paintings
func get_healed_count() -> int:
	return healed_paintings.size()


## Add item to inventory
func add_item(item_id: String, count: int = 1) -> void:
	inventory[item_id] = inventory.get(item_id, 0) + count
	progress_updated.emit("inventory", {item_id: inventory[item_id]})
	_log("Item added: %s x%d" % [item_id, count])


## Remove item from inventory
func remove_item(item_id: String, count: int = 1) -> bool:
	var current := inventory.get(item_id, 0) as int
	if current >= count:
		inventory[item_id] = current - count
		if inventory[item_id] <= 0:
			inventory.erase(item_id)
		progress_updated.emit("inventory", {item_id: inventory.get(item_id, 0)})
		return true
	return false


## Check if player has item
func has_item(item_id: String, count: int = 1) -> bool:
	return inventory.get(item_id, 0) >= count


## Set a story flag
func set_flag(flag_name: String, value: bool = true) -> void:
	story_flags[flag_name] = value
	progress_updated.emit("flag", {flag_name: value})
	_log("Flag set: %s = %s" % [flag_name, value])


## Check a story flag
func get_flag(flag_name: String) -> bool:
	return story_flags.get(flag_name, false)


## Modify player sanity
func modify_sanity(amount: int) -> void:
	var old_sanity := player_sanity
	player_sanity = clampi(player_sanity + amount, 0, 100)
	if player_sanity != old_sanity:
		progress_updated.emit("sanity", player_sanity)
		_log("Sanity: %d -> %d" % [old_sanity, player_sanity])


## Record a death
func record_death() -> void:
	death_count += 1
	progress_updated.emit("deaths", death_count)
#endregion

#region SAVE/LOAD
## Save current game state
func save_game() -> bool:
	var save_data := {
		"version": 1,
		"timestamp": Time.get_unix_time_from_system(),
		"playtime": playtime_seconds,
		"current_room": current_room,
		"player_sanity": player_sanity,
		"healed_paintings": healed_paintings,
		"inventory": inventory,
		"story_flags": story_flags,
		"death_count": death_count,
		"custom_data": custom_data,
	}
	
	var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if not file:
		push_error("Failed to open save file for writing")
		return false
	
	file.store_string(JSON.stringify(save_data, "\t"))
	file.close()
	
	game_saved.emit()
	_log("Game saved")
	return true


## Load game state from file
func load_game() -> bool:
	if not FileAccess.file_exists(SAVE_PATH):
		_log("No save file found")
		return false
	
	var file := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if not file:
		push_error("Failed to open save file for reading")
		return false
	
	var json_string := file.get_as_text()
	file.close()
	
	var json := JSON.new()
	if json.parse(json_string) != OK:
		push_error("Failed to parse save file")
		return false
	
	var data: Dictionary = json.data
	
	# Load values with defaults for backwards compatibility
	playtime_seconds = data.get("playtime", 0.0)
	current_room = data.get("current_room", "sanatorium_room")
	player_sanity = data.get("player_sanity", 100)
	healed_paintings = data.get("healed_paintings", {})
	inventory = data.get("inventory", {})
	story_flags = data.get("story_flags", {})
	death_count = data.get("death_count", 0)
	custom_data = data.get("custom_data", {})
	
	game_loaded.emit()
	_log("Game loaded")
	return true


## Check if save file exists
func has_save_file() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


## Delete save file
func delete_save() -> void:
	if FileAccess.file_exists(SAVE_PATH):
		DirAccess.remove_absolute(SAVE_PATH)
		_log("Save file deleted")


## Start a new game (reset all progress)
func new_game() -> void:
	healed_paintings.clear()
	inventory.clear()
	story_flags.clear()
	custom_data.clear()
	current_room = "sanatorium_room"
	player_sanity = 100
	playtime_seconds = 0.0
	death_count = 0
	_log("New game started")
#endregion

#region MINIGAME INTEGRATION
## Start a minigame (call from painting interaction)
## @param minigame_id: Identifier for the minigame/painting
## @param minigame_scene: Path to minigame scene
func start_minigame(minigame_id: String, minigame_scene: String) -> void:
	change_state(State.MINIGAME)
	# Store which minigame we're in
	custom_data["current_minigame"] = minigame_id
	await load_scene(minigame_scene)


## Complete current minigame successfully
func complete_minigame() -> void:
	var minigame_id: String = custom_data.get("current_minigame", "")
	if minigame_id:
		heal_painting(minigame_id)
		custom_data.erase("current_minigame")
	
	# Return to room
	# TODO: Replace with actual room scene path
	change_state(State.PLAYING)
	# await load_scene("res://scenes/room.tscn")


## Exit minigame without completing (give up)
func exit_minigame() -> void:
	custom_data.erase("current_minigame")
	change_state(State.PLAYING)
	# await load_scene("res://scenes/room.tscn")
#endregion

#region UTILITIES
## Get formatted playtime string (HH:MM:SS)
func get_playtime_formatted() -> String:
	var total_seconds := int(playtime_seconds)
	var hours := total_seconds / 3600
	var minutes := (total_seconds % 3600) / 60
	var seconds := total_seconds % 60
	return "%02d:%02d:%02d" % [hours, minutes, seconds]


## Internal: Debug logging
func _log(message: String) -> void:
	if debug_mode:
		print("[GameManager] " + message)
#endregion

#region GAME-SPECIFIC PRESETS (Mend)
## ============================================================================
## MEND-SPECIFIC DATA
## Add your game's specific paintings, items, flags here!
## ============================================================================

## All paintings in the game (id -> display name)
const PAINTINGS := {
	"fifteen_puzzle": "The Broken Family",
	"morse_code": "The Silent Message", 
	"music_box": "The Lost Melody",
	"stained_glass": "The Shattered Faith",
}

## All collectible items
const ITEMS := {
	"key_rusty": "Rusty Key",
	"note_doctor": "Doctor's Note",
	"medicine_bottle": "Medicine Bottle",
	"photo_family": "Family Photograph",
}

## Story flag definitions (for documentation)
const FLAGS := {
	"met_nurse": "Player has encountered the nurse",
	"found_diary": "Player found the child's diary",
	"heard_whispers": "Player heard whispers from paintings",
	"ending_good": "Achieved good ending",
	"ending_bad": "Achieved bad ending",
}


## Get painting display name
func get_painting_name(painting_id: String) -> String:
	return PAINTINGS.get(painting_id, painting_id)


## Get item display name  
func get_item_name(item_id: String) -> String:
	return ITEMS.get(item_id, item_id)


## Check if all paintings are healed (win condition)
func all_paintings_healed() -> bool:
	for painting_id in PAINTINGS.keys():
		if not is_painting_healed(painting_id):
			return false
	return true
#endregion
