extends Control
class_name IMiniGame
## ============================================================================
## IMINIGAME — Base class / contract for all minigames
## ============================================================================
##
## All minigames must extend this class and:
##   1. Call finish(Result.WIN/LOSE/CANCEL) when done
##   2. Optionally override setup() to receive parameters
##
## Usage in minigame:
##   extends IMiniGame
##   
##   func _on_player_wins():
##       finish(Result.WIN)
##
## ============================================================================

## Result of minigame completion
enum Result {
	WIN,
	LOSE,
	CANCEL,
}

## Emitted when minigame ends (MiniGameManager listens to this)
signal finished(result: Result)

## Parameters passed from Painting
var painting_id: String = ""
var difficulty: int = 1
var extra_params: Dictionary = {}


#region LIFECYCLE
## Called by MiniGameManager after instantiation
## Override to setup your minigame with parameters
func setup(p_painting_id: String, p_difficulty: int, p_params: Dictionary = {}) -> void:
	painting_id = p_painting_id
	difficulty = p_difficulty
	extra_params = p_params
	_on_setup()


## Override this for custom setup logic
func _on_setup() -> void:
	pass


func _input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		cancel()
#endregion


#region MINIGAME CONTROL
## Call this to end the minigame
func finish(result: Result) -> void:
	finished.emit(result)


## Convenience methods
func win() -> void:
	finish(Result.WIN)


func lose() -> void:
	finish(Result.LOSE)


func cancel() -> void:
	finish(Result.CANCEL)
#endregion
