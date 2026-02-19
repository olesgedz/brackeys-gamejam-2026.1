extends Node
class_name DialogServiceClass
## ============================================================================
## DIALOG SERVICE — Facade for running dialogues with cutscene mode
## ============================================================================
##
## Usage:
##   DialogService.start_dialogue("intro_sanatorium")
##   await DialogService.dialogue_finished
##
## Or with callback:
##   DialogService.start_dialogue("intro", {}, func(outcome): print(outcome))
##
## Features:
##   - Finds generated Dialogic timeline by ID
##   - Enters cutscene mode (pauses gameplay, shows cursor)
##   - Exits cutscene mode when dialogue ends
##   - Emits signals for external systems
##
## ============================================================================

#region SIGNALS
## Emitted when a dialogue starts
signal dialogue_started(dialogue_id: String)

## Emitted when a dialogue finishes
## @param dialogue_id: The dialogue that ended
## @param outcome: Result string (from 'end: "outcome"' in YAML) or empty
signal dialogue_finished(dialogue_id: String, outcome: String)

## Emitted when dialogue emits a custom signal (from YAML 'signal:' nodes)
signal dialogue_signal(signal_name: String, args: Dictionary)
#endregion

#region CONFIGURATION
## Path to generated dialogue files
const DIALOGUES_PATH := "res://dialogues_generated/"

## Enable debug logging
@export var debug_mode: bool = false
#endregion

#region STATE
## Currently running dialogue ID
var current_dialogue_id: String = ""

## Is a dialogue currently active
var is_dialogue_active: bool = false

## Callback for current dialogue
var _finish_callback: Callable

## Stored state before cutscene
var _pre_cutscene_mouse_mode: Input.MouseMode
var _pre_cutscene_paused: bool
#endregion

#region LIFECYCLE
func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	
	# Connect to Dialogic signals if available
	_connect_dialogic_signals()
#endregion

#region PUBLIC API
## Start a dialogue by ID
## @param dialogue_id: The dialogue ID (matches YAML 'id' field)
## @param context: Optional context variables to pass
## @param on_finished: Optional callback func(outcome: String)
## @returns: true if dialogue started successfully
func start_dialogue(dialogue_id: String, context: Dictionary = {}, on_finished: Callable = Callable()) -> bool:
	if is_dialogue_active:
		push_warning("DialogService: Cannot start dialogue, one is already active")
		return false
	
	var timeline_path := DIALOGUES_PATH + dialogue_id + ".dtl"
	
	if not ResourceLoader.exists(timeline_path):
		push_error("DialogService: Timeline not found: " + timeline_path)
		return false
	
	current_dialogue_id = dialogue_id
	is_dialogue_active = true
	_finish_callback = on_finished
	
	# Enter cutscene mode
	_enter_cutscene_mode()
	
	# Start Dialogic
	if _start_dialogic_timeline(timeline_path, context):
		dialogue_started.emit(dialogue_id)
		_log("Started dialogue: " + dialogue_id)
		return true
	else:
		# Failed to start, cleanup
		_exit_cutscene_mode()
		current_dialogue_id = ""
		is_dialogue_active = false
		return false


## Check if a dialogue exists
func has_dialogue(dialogue_id: String) -> bool:
	var timeline_path := DIALOGUES_PATH + dialogue_id + ".dtl"
	return ResourceLoader.exists(timeline_path)


## Force stop current dialogue (emergency)
func stop_dialogue() -> void:
	if not is_dialogue_active:
		return
	
	_stop_dialogic()
	_on_dialogue_ended("")
#endregion

#region CUTSCENE MODE
func _enter_cutscene_mode() -> void:
	# Store current state
	_pre_cutscene_mouse_mode = Input.get_mouse_mode()
	_pre_cutscene_paused = get_tree().paused
	
	# Show mouse cursor
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	
	# Pause gameplay (Dialogic UI should have process_mode = ALWAYS)
	get_tree().paused = true
	
	_log("Entered cutscene mode")


func _exit_cutscene_mode() -> void:
	# Restore mouse mode
	Input.set_mouse_mode(_pre_cutscene_mouse_mode)
	
	# Restore pause state
	get_tree().paused = _pre_cutscene_paused
	
	_log("Exited cutscene mode")
#endregion

#region DIALOGIC INTEGRATION
func _connect_dialogic_signals() -> void:
	# Dialogic 2 uses Dialogic singleton
	if not Engine.has_singleton("Dialogic"):
		# Dialogic might be autoloaded differently, try direct access
		var dialogic = get_node_or_null("/root/Dialogic")
		if dialogic:
			_connect_to_dialogic_node(dialogic)
		else:
			push_warning("DialogService: Dialogic not found. Dialogue system will use fallback mode.")


func _connect_to_dialogic_node(dialogic: Node) -> void:
	if dialogic.has_signal("timeline_ended"):
		dialogic.timeline_ended.connect(_on_dialogic_timeline_ended)
	if dialogic.has_signal("signal_event"):
		dialogic.signal_event.connect(_on_dialogic_signal)


func _start_dialogic_timeline(timeline_path: String, context: Dictionary) -> bool:
	# Try Dialogic 2 API
	var dialogic = get_node_or_null("/root/Dialogic")
	if dialogic and dialogic.has_method("start"):
		# Set context variables
		for key in context:
			if dialogic.has_method("set_variable"):
				dialogic.set_variable(key, context[key])
		
		# Start timeline
		dialogic.start(timeline_path)
		return true
	
	# Fallback: Try loading and parsing ourselves
	push_warning("DialogService: Dialogic.start() not available, using fallback")
	return _start_fallback_dialogue(timeline_path)


func _stop_dialogic() -> void:
	var dialogic = get_node_or_null("/root/Dialogic")
	if dialogic and dialogic.has_method("end_timeline"):
		dialogic.end_timeline()


func _on_dialogic_timeline_ended() -> void:
	_on_dialogue_ended("")


func _on_dialogic_signal(signal_name: String, args: Array) -> void:
	var args_dict: Dictionary = {}
	if args.size() > 0 and args[0] is Dictionary:
		args_dict = args[0]
	dialogue_signal.emit(signal_name, args_dict)
#endregion

#region FALLBACK (when Dialogic unavailable)
func _start_fallback_dialogue(timeline_path: String) -> bool:
	# Minimal fallback: show a popup with "dialogue unavailable"
	# In real usage, Dialogic should be properly configured
	
	# Load the timeline JSON to at least validate it exists
	var file := FileAccess.open(timeline_path, FileAccess.READ)
	if not file:
		return false
	
	var content := file.get_as_text()
	file.close()
	
	var json := JSON.new()
	if json.parse(content) != OK:
		push_error("DialogService: Failed to parse timeline: " + timeline_path)
		return false
	
	# For now, just auto-complete after a delay
	# This lets the game flow work even without Dialogic UI
	push_warning("DialogService: Using fallback mode - dialogue will auto-complete")
	
	get_tree().create_timer(0.5).timeout.connect(func():
		_on_dialogue_ended("fallback")
	)
	
	return true
#endregion

#region INTERNAL
func _on_dialogue_ended(outcome: String) -> void:
	var finished_id := current_dialogue_id
	
	# Exit cutscene mode
	_exit_cutscene_mode()
	
	# Reset state
	current_dialogue_id = ""
	is_dialogue_active = false
	
	# Emit signal
	dialogue_finished.emit(finished_id, outcome)
	_log("Dialogue finished: " + finished_id + " (outcome: " + outcome + ")")
	
	# Call callback if provided
	if _finish_callback.is_valid():
		_finish_callback.call(outcome)
		_finish_callback = Callable()


func _log(message: String) -> void:
	if debug_mode:
		print("[DialogService] " + message)
#endregion
