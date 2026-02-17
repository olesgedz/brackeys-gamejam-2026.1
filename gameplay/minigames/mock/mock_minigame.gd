extends IMiniGame
## Mock Minigame — For testing Painting integration
##
## Shows three buttons: Win, Lose, Cancel
## Displays painting_id and difficulty for verification

@onready var title_label: Label = $Panel/VBox/TitleLabel
@onready var info_label: Label = $Panel/VBox/InfoLabel


func _on_setup() -> void:
	# Display parameters for testing verification
	if title_label:
		title_label.text = "Mock Minigame"
	if info_label:
		info_label.text = "Painting: %s\nDifficulty: %d" % [painting_id, difficulty]


func _on_win_pressed() -> void:
	win()


func _on_lose_pressed() -> void:
	lose()


func _on_cancel_pressed() -> void:
	cancel()
