extends Node
## Global game settings autoload
## Manages audio volumes and saves/loads settings

const SETTINGS_PATH := "user://settings.cfg"

# Audio bus indices
var _master_bus_idx: int
var _music_bus_idx: int
var _sfx_bus_idx: int

# Volume values (0.0 to 1.0)
var master_volume: float = 1.0:
	set(value):
		master_volume = clamp(value, 0.0, 1.0)
		_apply_volume(_master_bus_idx, master_volume)
		
var music_volume: float = 0.8:
	set(value):
		music_volume = clamp(value, 0.0, 1.0)
		_apply_volume(_music_bus_idx, music_volume)
		
var sfx_volume: float = 0.8:
	set(value):
		sfx_volume = clamp(value, 0.0, 1.0)
		_apply_volume(_sfx_bus_idx, sfx_volume)


func _ready() -> void:
	# Cache bus indices
	_master_bus_idx = AudioServer.get_bus_index("Master")
	_music_bus_idx = AudioServer.get_bus_index("Music")
	_sfx_bus_idx = AudioServer.get_bus_index("SFX")
	
	# Load saved settings
	load_settings()
	
	# Apply volumes on startup
	_apply_volume(_master_bus_idx, master_volume)
	_apply_volume(_music_bus_idx, music_volume)
	_apply_volume(_sfx_bus_idx, sfx_volume)


func _apply_volume(bus_idx: int, volume: float) -> void:
	if bus_idx < 0:
		return
	# Convert linear (0-1) to dB (-80 to 0)
	if volume <= 0.0:
		AudioServer.set_bus_mute(bus_idx, true)
	else:
		AudioServer.set_bus_mute(bus_idx, false)
		AudioServer.set_bus_volume_db(bus_idx, linear_to_db(volume))


func save_settings() -> void:
	var config := ConfigFile.new()
	config.set_value("audio", "master_volume", master_volume)
	config.set_value("audio", "music_volume", music_volume)
	config.set_value("audio", "sfx_volume", sfx_volume)
	config.save(SETTINGS_PATH)


func load_settings() -> void:
	var config := ConfigFile.new()
	if config.load(SETTINGS_PATH) == OK:
		master_volume = config.get_value("audio", "master_volume", 1.0)
		music_volume = config.get_value("audio", "music_volume", 0.8)
		sfx_volume = config.get_value("audio", "sfx_volume", 0.8)
