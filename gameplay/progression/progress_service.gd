extends Node
class_name ProgressServiceClass
## ============================================================================
## PROGRESS SERVICE — Persistence layer for game progression
## ============================================================================
##
## Tracks which paintings have been completed.
## Currently in-memory; ready for file-based persistence.
##
## Usage:
##   ProgressService.is_painting_completed("painting_01")
##   ProgressService.set_painting_completed("painting_01")
##   ProgressService.reset_all()
##
## ============================================================================

const SAVE_PATH := "user://progress.json"

## Completed paintings: painting_id -> true
var _completed_paintings: Dictionary = {}

## Emitted when any painting is marked completed
signal painting_progress_changed(painting_id: String, completed: bool)


func _ready() -> void:
	_load_progress()


#region PUBLIC API
## Check if a painting has been completed
func is_painting_completed(painting_id: String) -> bool:
	return _completed_paintings.get(painting_id, false)


## Mark a painting as completed
func set_painting_completed(painting_id: String, completed: bool = true) -> void:
	if _completed_paintings.get(painting_id, false) != completed:
		_completed_paintings[painting_id] = completed
		painting_progress_changed.emit(painting_id, completed)
		_save_progress()


## Get all completed painting IDs
func get_completed_paintings() -> Array:
	var result: Array = []
	for id in _completed_paintings:
		if _completed_paintings[id]:
			result.append(id)
	return result


## Get completion count
func get_completed_count() -> int:
	var count := 0
	for id in _completed_paintings:
		if _completed_paintings[id]:
			count += 1
	return count


## Reset all progress (for testing/new game)
func reset_all() -> void:
	_completed_paintings.clear()
	_save_progress()
#endregion


#region PERSISTENCE
func _save_progress() -> void:
	var data := {
		"completed_paintings": _completed_paintings,
		"timestamp": Time.get_unix_time_from_system(),
	}
	var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(data, "\t"))
		file.close()


func _load_progress() -> void:
	if not FileAccess.file_exists(SAVE_PATH):
		return
	
	var file := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if not file:
		return
	
	var json := JSON.new()
	if json.parse(file.get_as_text()) == OK:
		var data: Dictionary = json.data
		_completed_paintings = data.get("completed_paintings", {})
	file.close()
#endregion
