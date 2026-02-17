@tool
extends Node3D
class_name Painting
## ============================================================================
## PAINTING — 3D interactive painting that launches minigames
## ============================================================================
##
## Place in level, configure via Inspector:
##   - painting_id: unique identifier
##   - minigame_type: which minigame to launch
##   - difficulty: 1-5
##   - art_texture: texture for the canvas
##
## States:
##   - AVAILABLE: can interact, launches minigame
##   - IN_PROGRESS: minigame is running
##   - COMPLETED: won, no more interaction
##
## Signals for external systems (dialogs, achievements, etc.)
##
## ============================================================================

#region SIGNALS
## Emitted when player starts interacting (minigame launches)
signal minigame_started(painting_id: String, minigame_type: MiniGameManagerClass.Type, difficulty: int)

## Emitted when minigame ends
signal minigame_finished(painting_id: String, result: IMiniGame.Result)

## Emitted only on WIN (convenience signal)
signal painting_completed(painting_id: String)

## Emitted when interaction is blocked
signal interaction_blocked(painting_id: String, reason: String)
#endregion


#region ENUMS
enum State {
	AVAILABLE,
	IN_PROGRESS,
	COMPLETED,
}
#endregion


#region EXPORTS
@export_group("Identity")
## Unique identifier for save/load
@export var painting_id: String = "painting_01"

@export_group("Minigame")
## Which minigame to launch
@export var minigame_type: MiniGameManagerClass.Type = MiniGameManagerClass.Type.MOCK_WIN_LOSE

## Difficulty level (1-5)
@export_range(1, 5) var difficulty: int = 1

@export_group("Appearance")
## Texture for the painting canvas
@export var art_texture: Texture2D:
	set(value):
		art_texture = value
		_update_art()

## Size of the painting (width x height in meters)
@export var painting_size: Vector2 = Vector2(1.0, 1.2):
	set(value):
		painting_size = value
		_update_size()

## Frame thickness
@export var frame_thickness: float = 0.05:
	set(value):
		frame_thickness = value
		_update_size()

@export_group("Behavior")
## Block interaction after WIN
@export var one_shot_on_win: bool = true

## Interaction distance
@export var interaction_distance: float = 2.5
#endregion


#region STATE
var current_state: State = State.AVAILABLE:
	set(value):
		current_state = value
		_update_visuals()
#endregion


#region NODE REFERENCES
@onready var canvas_mesh: MeshInstance3D = $CanvasMesh
@onready var frame_mesh: MeshInstance3D = $FrameMesh
@onready var interaction_area: Area3D = $InteractionArea
@onready var completed_indicator: Node3D = $CompletedIndicator
#endregion


#region LIFECYCLE
func _ready() -> void:
	if Engine.is_editor_hint():
		_update_art()
		_update_size()
		return
	
	# Check persistence
	if ProgressService and ProgressService.is_painting_completed(painting_id):
		current_state = State.COMPLETED
	
	_update_art()
	_update_size()
	_update_visuals()
	
	# Connect interaction
	if interaction_area:
		interaction_area.input_event.connect(_on_interaction_input)


func _update_art() -> void:
	if not canvas_mesh:
		return
	
	if art_texture:
		var material := StandardMaterial3D.new()
		material.albedo_texture = art_texture
		material.cull_mode = BaseMaterial3D.CULL_BACK
		canvas_mesh.material_override = material
	else:
		# Default gray placeholder
		var material := StandardMaterial3D.new()
		material.albedo_color = Color(0.3, 0.3, 0.35)
		canvas_mesh.material_override = material


func _update_size() -> void:
	if not canvas_mesh or not frame_mesh:
		return
	
	# Canvas is a QuadMesh facing +Z
	var canvas_quad := canvas_mesh.mesh as QuadMesh
	if canvas_quad:
		canvas_quad.size = painting_size
	
	# Frame surrounds canvas
	# TODO: Update frame mesh based on painting_size and frame_thickness


func _update_visuals() -> void:
	if Engine.is_editor_hint():
		return
	
	if completed_indicator:
		completed_indicator.visible = (current_state == State.COMPLETED)
	
	# Visual feedback for state
	match current_state:
		State.COMPLETED:
			if canvas_mesh and canvas_mesh.material_override:
				# Slight tint to show completion
				pass  # TODO: Add completion shader/effect
#endregion


#region INTERACTION
func _on_interaction_input(camera: Node, event: InputEvent, position: Vector3, normal: Vector3, shape_idx: int) -> void:
	if Engine.is_editor_hint():
		return
	
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
			interact()


## Called when player interacts with the painting
func interact() -> void:
	match current_state:
		State.AVAILABLE:
			_start_minigame()
		
		State.IN_PROGRESS:
			interaction_blocked.emit(painting_id, "Minigame already in progress")
		
		State.COMPLETED:
			interaction_blocked.emit(painting_id, "Already completed")


## Can be called externally (e.g., by player interaction system)
func try_interact() -> bool:
	if current_state == State.AVAILABLE:
		interact()
		return true
	return false


func _start_minigame() -> void:
	if not MiniGameManager:
		push_error("Painting: MiniGameManager autoload not found")
		return
	
	current_state = State.IN_PROGRESS
	
	var success := MiniGameManager.start_minigame(
		minigame_type,
		painting_id,
		difficulty,
		_on_minigame_result
	)
	
	if success:
		minigame_started.emit(painting_id, minigame_type, difficulty)
	else:
		current_state = State.AVAILABLE


func _on_minigame_result(result: IMiniGame.Result) -> void:
	minigame_finished.emit(painting_id, result)
	
	match result:
		IMiniGame.Result.WIN:
			if one_shot_on_win:
				current_state = State.COMPLETED
				# Persist
				if ProgressService:
					ProgressService.set_painting_completed(painting_id, true)
				painting_completed.emit(painting_id)
			else:
				current_state = State.AVAILABLE
		
		IMiniGame.Result.LOSE:
			# Allow retry
			current_state = State.AVAILABLE
		
		IMiniGame.Result.CANCEL:
			# Return to available, no consequence
			current_state = State.AVAILABLE
#endregion


#region UTILITY
## Force complete (for testing/cheats)
func force_complete() -> void:
	current_state = State.COMPLETED
	if ProgressService:
		ProgressService.set_painting_completed(painting_id, true)
	painting_completed.emit(painting_id)


## Reset to available (for testing)
func reset() -> void:
	current_state = State.AVAILABLE
	if ProgressService:
		ProgressService.set_painting_completed(painting_id, false)
#endregion
