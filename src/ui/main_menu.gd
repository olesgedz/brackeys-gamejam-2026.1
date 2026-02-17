extends Control
## Main Menu - Start, Settings, Exit

@onready var main_buttons: VBoxContainer = $MainButtons
@onready var settings_panel: PanelContainer = $SettingsPanel

@onready var master_slider: HSlider = $SettingsPanel/MarginContainer/VBoxContainer/MasterVolume/HSlider
@onready var music_slider: HSlider = $SettingsPanel/MarginContainer/VBoxContainer/MusicVolume/HSlider
@onready var sfx_slider: HSlider = $SettingsPanel/MarginContainer/VBoxContainer/SFXVolume/HSlider

@onready var master_label: Label = $SettingsPanel/MarginContainer/VBoxContainer/MasterVolume/ValueLabel
@onready var music_label: Label = $SettingsPanel/MarginContainer/VBoxContainer/MusicVolume/ValueLabel
@onready var sfx_label: Label = $SettingsPanel/MarginContainer/VBoxContainer/SFXVolume/ValueLabel


func _ready() -> void:
	settings_panel.hide()
	main_buttons.show()
	
	# Initialize sliders from saved settings
	master_slider.value = GameSettings.master_volume
	music_slider.value = GameSettings.music_volume
	sfx_slider.value = GameSettings.sfx_volume
	
	_update_volume_labels()
	
	# Connect slider signals
	master_slider.value_changed.connect(_on_master_volume_changed)
	music_slider.value_changed.connect(_on_music_volume_changed)
	sfx_slider.value_changed.connect(_on_sfx_volume_changed)


func _update_volume_labels() -> void:
	master_label.text = "%d%%" % int(master_slider.value * 100)
	music_label.text = "%d%%" % int(music_slider.value * 100)
	sfx_label.text = "%d%%" % int(sfx_slider.value * 100)


func _on_start_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main.tscn")


func _on_settings_pressed() -> void:
	main_buttons.hide()
	settings_panel.show()


func _on_exit_pressed() -> void:
	GameSettings.save_settings()
	get_tree().quit()


func _on_back_pressed() -> void:
	GameSettings.save_settings()
	settings_panel.hide()
	main_buttons.show()


func _on_master_volume_changed(value: float) -> void:
	GameSettings.master_volume = value
	_update_volume_labels()


func _on_music_volume_changed(value: float) -> void:
	GameSettings.music_volume = value
	_update_volume_labels()


func _on_sfx_volume_changed(value: float) -> void:
	GameSettings.sfx_volume = value
	_update_volume_labels()
